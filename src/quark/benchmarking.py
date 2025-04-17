from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional
from time import perf_counter
import logging
import json

from anytree import NodeMixin

from quark.plugin_manager import factory
from quark.core import Core, AsyncWait, Backtrack, Interruption


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
    unique_name:str
# === Module Datatypes ===


@dataclass(frozen=True)
class PipelineRunResult:
    """
    The result of running one benchmarking pipeline
    """
    # TODO write about what this is and how to capture additional metrics in the json (additional_metrics)
    result: Any
    total_time: float
    steps: list[ModuleRunMetrics]


# === Tree Results ===
@dataclass(frozen=True)
class FinishedTreeRun:
    results: list[PipelineRunResult]

@dataclass(frozen=True)
class InterruptedTreeRun:
    intermediate_results: list[PipelineRunResult]
    rest_tree: ModuleNode

TreeRunResult = FinishedTreeRun | InterruptedTreeRun
# === Tree Results ===


@dataclass
class ModuleNode(NodeMixin):
    """
    A module node in the pipeline tree

    The module will provide the output of its preprocess step to every child node.
    Every child module will later provide their postprocess output back to this node.
    When first created, a module node only stores its module information and its parent node.
    The module itself is only crated shortly before it is used.
    The preprocess time is stored after the preprocess step is run.
    """

    module_info: ModuleInfo

    module: Optional[Core] = None
    # TODO rename to preprocess is finished
    finished: bool = False
    preprocessed_data: Optional[Any] = None
    preprocess_time: Optional[float] = None

    def __init__(self, module_info: ModuleInfo, parent: Optional[ModuleNode] = None):
        super(ModuleNode, self).__init__()
        self.module_info = module_info
        self.parent = parent


class PipelineRunResultEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if not isinstance(o, PipelineRunResult):
            # Let the base class default method raise the TypeError
            return super().default(o)
        d = o.__dict__.copy()
        d["steps"] = [step.__dict__ for step in o.steps]
        for step in d["steps"]:
            step["module_info"] = step["module_info"].__dict__
            # TODO can I remove this line?
            step["module_info"].pop("preprocessed_data", None)
        return d


def run_pipeline_tree(pipeline_tree: ModuleNode) -> TreeRunResult:
    """
    Runs pipelines by traversing the given pipeline tree

    The pipeline tree represents one or more pipelines, where each node is a module.
    A node can provide its output to any of its child nodes, each choice representing a distinct pipeline.
    The tree is traversed in a depth-first manner, storing the result from each preprocess step to re-use as input for each child node.
    When a leaf node is reached, the tree is traversed back up to the root node, running every postprocessing step along the way.

    :param pipeline_tree: Root nodes of a pipeline tree, representing one or more pipelines
    :return: A tuple of a list of BenchmarkRun objects, one for each leaf node, and an optional interruption that is set if an interruption happened
    """

    pipeline_run_results:list[PipelineRunResult] = []
    def imp(node: ModuleNode, depth:int, upstream_data: Any = None) -> Optional[Interruption]:
        # set_logger(depth)

        logging.info(f"Running preprocess for module {node.module_info}")
        if node.finished:
            logging.info(f"Module {node.module_info} already done, skipping")
            data = node.preprocessed_data
        else:
            # TODO is this if statement necessary?
            if node.module is None:
                logging.info(f"Creating module instance for {node.module_info}")
                node.module = factory.create(node.module_info.name, node.module_info.params)
            assert node.module is not None
            t1 = perf_counter()
            match node.module.preprocess(upstream_data):
                case AsyncWait():
                    logging.info(f"Async interrupt encountered, returning from {node.module_info}")
                    return AsyncWait()
                case Backtrack(data):
                    # TODO
                    return
                case data:
                    node.preprocess_time = perf_counter() - t1
                    logging.info(f"Preprocess for module {node.module_info} took {node.preprocess_time} seconds")
                    node.finished = True
                    node.preprocessed_data = data


        match node.children:
            case []: # Leaf node; Tail end of pipeline reached
                # Document somewhere why the postprocess chain is done in this way instead of returning a postprocess result from imp and going from there
                logging.info("Arrived at leaf node, starting postprocessing chain")
                next_node = node
                steps:list[ModuleRunMetrics] = []
                while next_node is not None:
                    # set_logger(depth)
                    assert next_node.module is not None # Otherwise Pylint complains
                    logging.info(f"Running postprocess for module {next_node.module_info}")
                    t1 = perf_counter()
                    match next_node.module.postprocess(data):
                        case AsyncWait(): # TODO
                            logging.info(f"Async interrupt encountered, returning from {node.module_info}")
                            return AsyncWait()
                        case Backtrack(data): # TODO
                            return
                        case data:
                            postprocess_time = perf_counter() - t1
                            unique_name:str
                            match next_node.module.get_unique_name():
                                case None:
                                    unique_name = f"{next_node.module_info.name}{str.join("_", (str(v) for v in next_node.module_info.params.values()))}"
                                case name:
                                    unique_name = name
                            assert next_node.preprocess_time is not None # Otherwise Pylint complains
                            steps.append(ModuleRunMetrics(
                                module_info=next_node.module_info,
                                preprocess_time=next_node.preprocess_time,
                                postprocess_time=postprocess_time,
                                additional_metrics=next_node.module.get_metrics(),
                                unique_name=unique_name
                            ))
                            logging.info(f"Postprocess for module {next_node.module_info} took {postprocess_time} seconds")
                            next_node = next_node.parent
                            depth -= 1
                steps.reverse()
                pipeline_run_results.append(PipelineRunResult(
                    result=data,
                    total_time=sum(step.preprocess_time + step.postprocess_time for step in steps),
                    steps=steps
                ))
                logging.info("Finished postprocessing chain")

            case children:
                encountered_async_wait: bool = False
                for child in children:
                    match imp(child, depth+1, data):
                        case None:
                            child.parent = None
                        case AsyncWait():
                            encountered_async_wait = True
                        case _:
                            raise Exception("Root nodes may not return any Interruption other than AsyncWait")
                if encountered_async_wait:
                    return AsyncWait()


    # logging.info("")
    # logging.info(f"Running pipeline tree:\n{RenderTree(pipeline_tree)}")
    match imp(pipeline_tree, 0):
        case None:
            return FinishedTreeRun(results=pipeline_run_results)
        case AsyncWait():
            return InterruptedTreeRun(intermediate_results=pipeline_run_results, rest_tree=pipeline_tree)
        case _:
            raise Exception("No other interrupt than AsyncWait is allowed to be returned from the root node")
