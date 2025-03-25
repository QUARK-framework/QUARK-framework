from __future__ import annotations
from dataclasses import dataclass
from itertools import chain
from typing import Any, Union, Tuple, Optional
from time import perf_counter
import logging

import yaml
from anytree import NodeMixin, RenderTree

from quark.parsing import get_args
from quark.plugin_manager import factory, loader
from quark.protocols import Core


# In the config file, a pipeline module can be specified in two ways:
# -A single string is interpreted as a single module without parameters
# -A dictionary with a single key-value pair is interpreted as a single module where the value is another dictionary containing the parameters
PipelineModule = Union[str, dict[str, dict[str, Any]]]

PipelineLayer = Union[PipelineModule, list[PipelineModule]]
ModuleInfo = Tuple[str, dict[str, Any]]


@dataclass
class ModuleNode(NodeMixin):
    moduleInfo: ModuleInfo
    module: Optional[Core] = None
    preprocess_time: Optional[float] = None

    def __init__(self, moduleInfo: ModuleInfo, parent: Optional[ModuleNode] = None):
        super(ModuleNode, self).__init__()
        self.moduleInfo = moduleInfo
        self.parent = parent

@dataclass(frozen=True)
class RunInfo:
    moduleInfo: ModuleInfo
    preprocess_time: float
    postprocess_time: float

@dataclass(frozen=True)
class BenchmarkRun:
    result: Any
    steps: list[RunInfo]


def start() -> None:
    """
    Main function that triggers the benchmarking process
    """

    _set_logger()

    logging.info(" ============================================================ ")
    logging.info(r"             ___    _   _      _      ____    _  __           ")
    logging.info(r"            / _ \  | | | |    / \    |  _ \  | |/ /           ")
    logging.info(r"           | | | | | | | |   / _ \   | |_) | | ' /            ")
    logging.info(r"           | |_| | | |_| |  / ___ \  |  _ <  | . \            ")
    logging.info(r"            \__\_\  \___/  /_/   \_\ |_| \_\ |_|\_\           ")
    logging.info("                                                              ")
    logging.info(" ============================================================ ")
    logging.info("  A Framework for Quantum Computing Application Benchmarking  ")
    logging.info("                                                              ")
    logging.info("        Licensed under the Apache License, Version 2.0        ")
    logging.info(" ============================================================ ")


    args = get_args()

    with open(args.config) as file:
        data = yaml.load(file, Loader=yaml.FullLoader)

    loader.load_plugins(data["plugins"])

    pipelines = []
    if "pipelines" in data:
        pipelines = data["pipelines"]
    elif "pipeline" in data:
        pipelines = [data["pipeline"]]
    else:
        raise ValueError("No pipeline found in configuration file")

    # Initialize all pipelines into trees and collect them
    pipeline_trees = chain.from_iterable(_init_pipeline_tree(pipeline) for pipeline in pipelines)
    # Run all pipelines and collect the resulting lists of BenchmarkRun objects
    benchmark_runs = chain.from_iterable(_run_pipeline_tree(pipeline_tree) for pipeline_tree in pipeline_trees)

    benchmark_runs = list(benchmark_runs)
    logging.info(" ======================== RESULTS ====================--===== ")
    for run in benchmark_runs:
        logging.info([step.moduleInfo for step in run.steps])
        logging.info(f"Result: {run.result}")
        logging.info(f"Total time: {sum(step.preprocess_time + step.postprocess_time for step in run.steps)}")

    logging.info(" ============================================================ ")
    logging.info(" ====================  QUARK finished!   ==================== ")
    logging.info(" ============================================================ ")
    exit(0)


def _set_logger(depth: int = 0) -> None:
    """
    Sets up the logger to also write to a file in the store directory.
    """
    logging.getLogger().handlers = []
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s [%(levelname)s] {' '*4*depth}%(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("logging.log")]
    )

def _extract_module_info(module: PipelineModule) -> ModuleInfo:
    match module:
        case str():  # Single module
            return((module, {}))
        case dict():  # Single module with parameters
            name = next(iter(module))
            params = module[name]
            return ((name, params))

def _init_pipeline_tree(pipeline: list[PipelineLayer]) -> list[ModuleNode]:
    pipeline = [layer if isinstance(layer, list) else [layer] for layer in pipeline]
    pipeline_trees = [ModuleNode(_extract_module_info(layer)) for layer in pipeline[0]]
    def imp(pipeline: list[list[PipelineModule]], parent: ModuleNode) -> None:
        match pipeline:
            case []:
                return
            case [layer, *_]:
                for module in layer:
                    moduleInfo = _extract_module_info(module)
                    node = ModuleNode(moduleInfo, parent)
                    imp(pipeline[1:], parent=node)
    for node in pipeline_trees:
        imp(pipeline[1:], parent=node) # type: ignore
    return pipeline_trees


def _run_pipeline_tree(pipeline_tree: ModuleNode) -> list[BenchmarkRun]:
    """
    Runs pipelines by traversing the given pipeline tree

    The pipeline tree represents one or more pipelines, where each node is a module.
    A node can provide its output to any of its child nodes, each choice representing a distinct pipeline.
    The tree is traversed in a depth-first manner, storing the result from each preprocess step to re-use as input for each child node.
    When a leaf node is reached, the tree is traversed back up to the root node, running every postprocessing step along the way.

    :param pipeline_tree: Root nodes of a pipeline tree, representing one or more pipelines
    :return: A list of BenchmarkRun objects, one for each leaf node
    """

    benchmark_runs = [] # List of BenchmarkRun objects
    def imp(node: ModuleNode, depth:int, upstream_data: Any = None) -> None:
        _set_logger(depth)
        node.module = factory.create(node.moduleInfo[0], node.moduleInfo[1])
        logging.info(f"Running preprocess for module {node.moduleInfo}")
        t1 = perf_counter()
        data = node.module.preprocess(upstream_data)
        node.preprocess_time = perf_counter() - t1
        logging.info(f"Preprocess for module {node.moduleInfo} took {node.preprocess_time} seconds")
        match node.children:
            case []: # Leaf node; End of pipeline
                logging.info("Arrived at leaf node, starting postprocessing chain")
                next_node = node
                benchmark_runs.append([])
                while(next_node != None):
                    _set_logger(depth)
                    assert next_node.module is not None
                    logging.info(f"Running postprocess for module {next_node.moduleInfo}")
                    t1 = perf_counter()
                    data = next_node.module.postprocess(data)
                    postprocess_time = perf_counter() - t1
                    assert next_node.preprocess_time is not None
                    benchmark_runs[-1].append(RunInfo(next_node.moduleInfo, next_node.preprocess_time, postprocess_time))
                    logging.info(f"Postprocess for module {next_node.moduleInfo} took {postprocess_time} seconds")
                    next_node = next_node.parent
                    depth -= 1
                benchmark_runs[-1].reverse()
                benchmark_runs[-1] = BenchmarkRun(result=data, steps=benchmark_runs[-1])
                logging.info("Finished postprocessing chain")

            case children:
                for child in children:
                    imp(child, depth+1, data)

    logging.info("")
    logging.info(f"Running pipeline tree:\n{RenderTree(pipeline_tree)}")
    imp(pipeline_tree, 0)
    return benchmark_runs


if __name__ == '__main__':
    start()
