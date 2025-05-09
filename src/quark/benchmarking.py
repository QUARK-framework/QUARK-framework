# ruff: noqa: ANN401

"""Collection of datatypes and functions used to run a benchmarking tree."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from itertools import chain
from time import perf_counter
from typing import TYPE_CHECKING, Any

from anytree import NodeMixin

from quark.core import Backtrack, Core, Data, Sleep
from quark.plugin_manager import factory
from quark.quark_logging import set_logging_depth

if TYPE_CHECKING:
    from quark.interface_types import InterfaceType


@dataclass(frozen=True)
class ModuleInfo:
    """Encapsulates information to represent and create a module.

    ModuleInfo is used in multiple other composite types.
    Everything stored here will be added to the results after a benchmarking run.
    Therefore, the data is intentionally kept as concise and human-readable as possible.
    """

    name: str
    params: dict[str, Any]


@dataclass(frozen=True)
class ModuleRunMetrics:
    """Encapsulates information about the result of the pre and postprocessing steps of one module.

    Everything stored here will be added to the results after a benchmarking run.
    Therefore, the data is intentionally kept as concise and human-readable as possible.
    """

    # === set by config file ===
    module_info: ModuleInfo
    preprocess_time: float
    postprocess_time: float
    # =/= set by config file =/=

    # === chosen manually by module or created automatically if nothing is given ===
    additional_metrics: dict
    unique_name: str
    # =/= chosen manually by module or created automatically if nothing is given =/=

    @classmethod
    def create(
        cls,
        module_info: ModuleInfo,
        module: Core,
        preprocess_time: float,
        postprocess_time: float,
    ) -> ModuleRunMetrics:
        # TODO this docstring is not very good
        """Create a ModuleRunMetrics object."""
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


# === Pipeline Run Progress ===
@dataclass(frozen=True)
class FinishedPipelineRun:
    """The result of running one benchmarking pipeline.

    Captures the results of one pipeline run, consisting of the result of the last postprocessing step, total time
    spent in all pre- and postprocessing steps combined, and a list of module run metrics for each of the executed
    modules. This is different from a tree run in that it only represents the result of running one pipeline, while a
    tree run represents one or more pipeline runs.
    """

    result: InterfaceType
    steps: list[ModuleRunMetrics]


@dataclass(frozen=True)
class _InProgressPipelineRun:
    """An in-progress pipeline run that was not interrupted or paused yet, used by run_pipeline_tree.imp()."""

    downstream_data: Any  # The result of a child node's postprocessing step
    metrics_up_to_now: list[ModuleRunMetrics]  # The aggregated metrics from all modules included in this pipeline.


@dataclass(frozen=True)
class _PausedPipelineRun:
    pass


_PipelineRunStatus = _InProgressPipelineRun | _PausedPipelineRun
# === Pipeline Run Progress ===


# === Tree Results ===
@dataclass(frozen=True)
class FinishedTreeRun:
    """Represents a tree run where every pipeline finished and no interruptions remain to be handled."""

    finished_pipeline_runs: list[FinishedPipelineRun]


@dataclass(frozen=True)
class InterruptedTreeRun:
    """Represents a tree run where one or more modules were interrupted."""

    finished_pipeline_runs: list[FinishedPipelineRun]  # Metrics of finished pipeline runs
    rest_tree: ModuleNode  # The remaining pipeline tree without nodes that are already finished


TreeRunResult = FinishedTreeRun | InterruptedTreeRun
# === Tree Results ===


@dataclass
class ModuleNode(NodeMixin):
    """A module node in the pipeline tree.

    The module will provide the output of its preprocess step to every child node. Every child module will later
    provide its postprocess output back to this node. When first created, a module node only stores its module
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
    data_stored_by_postprocess_interrupt: list[_InProgressPipelineRun] | None = None

    def __init__(self, module_info: ModuleInfo, parent: ModuleNode | None = None) -> None:
        """Initialize a ModuleNode.

        For a newly created ModuleNode object, only the module_info attribute must be set. All other attributes will be
        set only at the time they are needed. Together with the fact that nodes are deleted when they are no longer
        needed, this ensures that a pipeline tree only contains necessary data at all times, saving memory.
        """
        super().__init__()
        self.module_info = module_info
        self.parent = parent


def run_pipeline_tree(pipeline_tree: ModuleNode) -> TreeRunResult:
    """Run pipelines by traversing the given pipeline tree.

    The pipeline tree represents one or more pipelines, where each node is a module. A node provides its output to
    any of its child nodes (if there are any). Each child node represents a distinct pipeline. The tree is traversed
    recursively in a depth-first manner, storing the result from each preprocess step to re-use as input for each child
    node. The return value of recursively calling a child node includes all metrics from all pipeline runs represented
    by the subtree starting at that child.
    """

    def imp(
        node: ModuleNode,
        upstream_data: Any,
        depth: int,
    ) -> list[_PipelineRunStatus]:
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
                    return [_PausedPipelineRun()]
                case Backtrack(_):
                    # TODO
                    raise NotImplementedError
                case Data(preprocessed_data):
                    node.preprocess_time = perf_counter() - t1
                    logging.info(f"Preprocess for module {node.module_info} took {node.preprocess_time} seconds")
                    node.preprocess_finished = True
                    node.preprocessed_data = preprocessed_data
                case _:
                    msg = "The preprocessing function must return a Result type"
                    raise TypeError(msg)

        results: list[_PipelineRunStatus] = []  # Will be returned later

        downstream_results = (
            (imp(child, preprocessed_data, depth + 1) for child in node.children)
            if node.children
            else iter([[_InProgressPipelineRun(downstream_data=None, metrics_up_to_now=[])]])
        )
        if node.data_stored_by_postprocess_interrupt is not None:
            downstream_results = chain(downstream_results, iter([node.data_stored_by_postprocess_interrupt]))

        for downstream_result in downstream_results:
            set_logging_depth(depth)
            for pipeline_run_status in downstream_result:
                match pipeline_run_status:
                    case _PausedPipelineRun():
                        results.append(pipeline_run_status)
                    case _InProgressPipelineRun(downstream_data, metrics_up_to_now):
                        logging.info(f"Running postprocess for module {node.module_info}")
                        t1 = perf_counter()
                        match node.module.postprocess(downstream_data):
                            case Sleep(stored_data):
                                # TODO
                                raise NotImplementedError
                            case Backtrack():
                                # TODO
                                raise NotImplementedError
                            case Data(postprocessed_data):
                                postprocess_time = perf_counter() - t1
                                logging.info(
                                    f"Postprocess for module {node.module_info} took {postprocess_time} seconds",
                                )
                                module_run_metrics = ModuleRunMetrics.create(
                                    module_info=node.module_info,
                                    module=node.module,
                                    preprocess_time=node.preprocess_time,  # type: ignore
                                    postprocess_time=postprocess_time,
                                )
                                results.append(
                                    _InProgressPipelineRun(
                                        downstream_data=postprocessed_data,
                                        metrics_up_to_now=[*metrics_up_to_now, module_run_metrics],
                                    ),
                                )
                            case _:
                                msg = "The postprocessing function must return a Result type"
                                raise TypeError(msg)

                        node.parent = None  # This node and all its descendents ran successfully and can be deleted
        return results

    results = imp(pipeline_tree, None, 0)

    finished_pipeline_runs = [
        FinishedPipelineRun(result=r.downstream_data, steps=r.metrics_up_to_now)
        for r in results
        if isinstance(r, _InProgressPipelineRun)
    ]

    if any(isinstance(r, _PausedPipelineRun) for r in results):
        return InterruptedTreeRun(
            finished_pipeline_runs=finished_pipeline_runs,
            rest_tree=pipeline_tree,
        )
    return FinishedTreeRun(finished_pipeline_runs=finished_pipeline_runs)
