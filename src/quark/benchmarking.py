from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from itertools import chain
from time import perf_counter
from typing import Any

from anytree import NodeMixin

from quark.core import Backtrack, Core, Sleep
from quark.plugin_manager import factory
from quark.quark_logging import set_logging_depth


# === Module Datatypes ===
@dataclass(frozen=True)
class ModuleInfo:
    name: str
    params: dict[str, Any]


@dataclass(frozen=True)
class ModuleRunMetrics:
    module_info: ModuleInfo
    preprocess_time: float
    postprocess_time: float
    additional_metrics: dict
    unique_name: str

    @classmethod
    def create(
        cls,
        module_info: ModuleInfo,
        module: Core,
        preprocess_time: float,
        postprocess_time: float,
    ) -> ModuleRunMetrics:
        unique_name: str
        match module.get_unique_name():
            case None:
                unique_name = module_info.name + str.join(
                    "_",
                    (str(v) for v in module_info.params.values()),
                )
            case name:
                unique_name = name
        return cls(
            module_info=module_info,
            preprocess_time=preprocess_time,
            postprocess_time=postprocess_time,
            additional_metrics=module.get_metrics(),
            unique_name=unique_name,
        )


# === Module Datatypes ===


# === Pipeline Run Progress ===
@dataclass(frozen=True)
class FinishedPipelineRun:
    """The result of running one benchmarking pipeline.

    Captures the results of one pipeline run, consisting of the result of the last postprocessing step, total time
    spent in all pre and postprocessing steps combined, and a list of module run metrics for each of the executed
    modules. This is different from a tree run in that it only represents the result of running one pipeline, while a
    tree run represents one or more pipeline runs.
    """

    result: Any
    steps: list[ModuleRunMetrics]


@dataclass(frozen=True)
class InProgressPipelineRun:
    downstream_data: Any
    metrics_up_to_now: list[ModuleRunMetrics]


@dataclass(frozen=True)
class PausedPipelineRun:
    pass


PipelineRunStatus = InProgressPipelineRun | PausedPipelineRun
# === Pipeline Run Progress ===


# === Tree Results ===
@dataclass(frozen=True)
class FinishedTreeRun:
    finished_pipeline_runs: list[FinishedPipelineRun]


@dataclass(frozen=True)
class InterruptedTreeRun:
    finished_pipeline_runs: list[FinishedPipelineRun]
    paused_pipeline_runs: list[PausedPipelineRun]
    rest_tree: ModuleNode


TreeRunResult = FinishedTreeRun | InterruptedTreeRun
# === Tree Results ===


# @dataclass(frozen=True)
# class PreprocessResult:
#     time: float
#     data: Any

# @dataclass(frozen=True)
# class PostprocessResult:
#     time: float
#     data: Any


@dataclass
class ModuleNode(NodeMixin):
    """A module node in the pipeline tree.

    The module will provide the output of its preprocess step to every child node. Every child module will later
    provide their postprocess output back to this node. When first created, a module node only stores its module
    information and its parent node. The module itself is only crated shortly before it is used. The preprocess time
    is stored after the preprocess step is run.
    """

    module_info: ModuleInfo
    module: Core | None = None  # The module is not created before it is needed

    preprocess_finished: bool = False
    preprocess_time: float | None = None
    preprocessed_data: Any | None = None

    interrupted_during_preprocess = False
    data_stored_by_preprocess_interrupt: Any | None = None

    interrupted_during_postprocess = False
    data_stored_by_postprocess_interrupt: list[InProgressPipelineRun] | None = None

    def __init__(self, module_info: ModuleInfo, parent: ModuleNode | None = None) -> None:
        super().__init__()
        self.module_info = module_info
        self.parent = parent


class PipelineRunResultEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if not isinstance(o, FinishedPipelineRun):
            # Let the base class default method raise the TypeError
            return super().default(o)
        d = o.__dict__.copy()
        d["steps"] = [step.__dict__ for step in o.steps]
        for step in d["steps"]:
            step["module_info"] = step["module_info"].__dict__
        return d


def run_pipeline_tree(pipeline_tree: ModuleNode) -> TreeRunResult:
    """Run pipelines by traversing the given pipeline tree.

    The pipeline tree represents one or more pipelines, where each node is a module. A node can provide its output to
    any of its child nodes, each choice representing a distinct pipeline. The tree is traversed in a depth-first
    manner, storing the result from each preprocess step to re-use as input for each child node. When a leaf node is
    reached, the tree is traversed back up to the root node, running every postprocessing step along the way.

    :param pipeline_tree: Root nodes of a pipeline tree, representing one or more pipelines
    :return: A tuple of a list of BenchmarkRun objects, one for each leaf node, and an optional interruption that is
    set if an interruption happened
    """

    def imp(
        node: ModuleNode,
        upstream_data: Any,  # noqa: ANN401
        depth: int,
    ) -> list[PipelineRunStatus]:
        set_logging_depth(depth)
        logging.info(f"Running preprocess for module {node.module_info}")

        preprocessed_data: Any
        if node.module is None:
            logging.info(f"Creating module instance for {node.module_info}")
            node.module = factory.create(node.module_info.name, node.module_info.params)
        if node.preprocess_finished:  # After an interrupted run is resumed, some steps will already be finished
            logging.info(f"Preprocessing of module {node.module_info} already done, skipping")
            preprocessed_data = node.preprocessed_data
        else:
            if node.interrupted_during_preprocess:
                upstream_data = node.data_stored_by_preprocess_interrupt
            t1 = perf_counter()
            match node.module.preprocess(upstream_data):
                case Sleep(stored_data):
                    node.interrupted_during_preprocess = True
                    node.data_stored_by_preprocess_interrupt = stored_data
                    return [PausedPipelineRun()]
                case Backtrack(_):
                    # TODO
                    raise NotImplementedError
                case preprocessed_data:
                    node.preprocess_time = perf_counter() - t1
                    logging.info(f"Preprocess for module {node.module_info} took {node.preprocess_time} seconds")
                    node.preprocess_finished = True
                    node.preprocessed_data = preprocessed_data

        assert node.module is not None  # noqa: S101 Otherwise Pylint complains
        assert node.preprocess_time is not None  # noqa: S101 Otherwise Pylint complains

        results: list[PipelineRunStatus] = []  # Will be returned later
        downstream_results = (
            (imp(child, preprocessed_data, depth + 1) for child in node.children)
            if node.children
            else iter([[InProgressPipelineRun(downstream_data=None, metrics_up_to_now=[])]])
        )
        if node.data_stored_by_postprocess_interrupt is not None:
            downstream_results = chain(downstream_results, iter([node.data_stored_by_postprocess_interrupt]))

        for downstream_result in downstream_results:
            set_logging_depth(depth)
            for pipeline_run_status in downstream_result:
                match pipeline_run_status:
                    case PausedPipelineRun():
                        results.append(pipeline_run_status)
                    case InProgressPipelineRun(downstream_data, metrics_up_to_now):
                        logging.info(f"Running postprocess for module {node.module_info}")
                        t1 = perf_counter()
                        match node.module.postprocess(downstream_data):
                            case Sleep(stored_data):
                                # TODO
                                raise NotImplementedError
                            case Backtrack():
                                # TODO
                                raise NotImplementedError
                            case postprocessed_data:
                                postprocess_time = perf_counter() - t1
                                logging.info(
                                    f"Postprocess for module {node.module_info} took {postprocess_time} seconds",
                                )
                                module_run_metrics = ModuleRunMetrics.create(
                                    module_info=node.module_info,
                                    module=node.module,
                                    preprocess_time=node.preprocess_time,
                                    postprocess_time=postprocess_time,
                                )
                                results.append(
                                    InProgressPipelineRun(
                                        downstream_data=postprocessed_data,
                                        metrics_up_to_now=[*metrics_up_to_now, module_run_metrics],
                                    ),
                                )
        return results

    results = imp(pipeline_tree, None, 0)

    finished_pipeline_runs = [
        FinishedPipelineRun(result=r.downstream_data, steps=r.metrics_up_to_now)
        for r in results
        if isinstance(r, InProgressPipelineRun)
    ]

    paused_pipeline_runs = [r for r in results if isinstance(r, PausedPipelineRun)]

    if paused_pipeline_runs:
        return InterruptedTreeRun(
            finished_pipeline_runs=finished_pipeline_runs,
            paused_pipeline_runs=paused_pipeline_runs,
            rest_tree=pipeline_tree,
        )
    return FinishedTreeRun(finished_pipeline_runs=finished_pipeline_runs)
