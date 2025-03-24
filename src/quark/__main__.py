from dataclasses import dataclass
import argparse
from typing import Any, Union, Tuple, Optional
from time import perf_counter
import logging

import yaml
from anytree import AnyNode, NodeMixin, RenderTree

from quark.plugin_manager import factory, loader
from quark.protocols import Core

def create_benchmark_parser(parser: argparse.ArgumentParser):
    parser.add_argument("-c", "--config", help="Provide valid config file instead of interactive mode")
    parser.add_argument('-cc', '--createconfig', help='If you want o create a config without executing it',
                        required=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('-s', '--summarize', nargs='+', help='If you want to summarize multiple experiments',
                        required=False)
    parser.add_argument('-m', '--modules', help="Provide a file listing the modules to be loaded")
    parser.add_argument('-rd', '--resume-dir', nargs='?', help='Provide results directory of the job to be resumed')
    parser.add_argument('-ff', '--failfast', help='Flag whether a single failed benchmark run causes QUARK to fail',
                        required=False, action=argparse.BooleanOptionalAction)

    parser.set_defaults(goal='benchmark')


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


# In the config file, a pipeline module can be specified in two ways:
# -A single string is interpreted as a single module without parameters
# -A dictionary with a single key-value pair is interpreted as a single module where the value is another dictionary containing the parameters
PipelineModule = Union[str, dict[str, dict[str, Any]]]

PipelineLayer = Union[PipelineModule, list[PipelineModule]]
ModuleInfo = Tuple[str, dict[str, Any]]


def _extract_module_info(module: PipelineModule) -> ModuleInfo:
    match module:
        case str():  # Single module
            return((module, {}))
        case dict():  # Single module with parameters
            name = next(iter(module))
            params = module[name]
            return ((name, params))

def _init_pipeline_tree(pipeline: list[PipelineLayer], parent: AnyNode) -> None:
    match pipeline:
        case []:
            return
        case [layer, *_]:
            if not isinstance(layer, list):
                layer = [layer]
            for module in layer:
                moduleInfo = _extract_module_info(module)
                node = AnyNode(parent, moduleInfo=moduleInfo)
                _init_pipeline_tree(pipeline[1:], parent=node)

@dataclass
class ModuleNode(NodeMixin):
    moduleInfo: ModuleInfo
    module: Optional[Core] = None
    preprocess_time: Optional[float] = None

@dataclass(frozen=True)
class RunInfo:
    moduleInfo: ModuleInfo
    preprocess_time: float
    postprocess_time: float

@dataclass(frozen=True)
class BenchmarkRun:
    result: Any
    steps: list[RunInfo]

def _run_pipeline_tree(root: AnyNode) -> list[BenchmarkRun]:
    benchmark_runs = []
    def _imp(node: ModuleNode, depth:int, upstream_data: Any = None) -> None:
        _set_logger(depth)
        node.module = factory.create(node.moduleInfo[0], node.moduleInfo[1])
        logging.info(f"Running preprocess for module {node.moduleInfo[0]}")
        t1 = perf_counter()
        data = node.module.preprocess(upstream_data)
        node.preprocess_time = perf_counter() - t1
        logging.info(f"Preprocess for module {node.moduleInfo[0]} took {node.preprocess_time} seconds\n")
        match node.children:
            case []: # Leaf node; End of pipeline
                logging.info("Arrived at leaf node, starting postprocessing chain")
                next_node = node
                benchmark_runs.append([])
                while(next_node.parent != None):
                    _set_logger(depth)
                    assert next_node.module is not None
                    logging.info(f"Running postprocess for module {next_node.moduleInfo[0]}")
                    t1 = perf_counter()
                    data = next_node.module.postprocess(data)
                    postprocess_time = perf_counter() - t1
                    assert next_node.preprocess_time is not None
                    benchmark_runs[-1].append(RunInfo(next_node.moduleInfo, next_node.preprocess_time, postprocess_time))
                    logging.info(f"Postprocess for module {next_node.moduleInfo[0]} took {postprocess_time} seconds")
                    next_node = next_node.parent
                    depth -= 1
                benchmark_runs[-1].reverse()
                benchmark_runs[-1] = BenchmarkRun(result=data, steps=benchmark_runs[-1])
                logging.info("Finished postprocessing chain\n")

            case children:
                for child in children:
                    _imp(child, depth+1, data)

    for child in root.children:
        _imp(child, 0)
    return benchmark_runs


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

    parser = argparse.ArgumentParser()
    create_benchmark_parser(parser)

    args = parser.parse_args()

    with open(args.config) as file:
        data = yaml.load(file, Loader=yaml.FullLoader)

    loader.load_plugins(data["plugins"])

    pipelines = {}
    label_found = False
    for label in ["pipeline", "pipelines"]:
        if label in data:
            pipelines = data[label]
            label_found = True
            break

    if not label_found:
        raise ValueError("No pipeline found in configuration file")

    if isinstance(pipelines, list):
        pipelines = {"pipeline": pipelines}

    pipeline_tree_root = AnyNode()

    for pipeline_group, pipeline in pipelines.items():
        _init_pipeline_tree(pipeline, parent=pipeline_tree_root)

    logging.info(RenderTree(pipeline_tree_root))

    benchmark_runs = _run_pipeline_tree(pipeline_tree_root)

    # logging.info(benchmark_runs)

    for run in benchmark_runs:
        logging.info(f"Result: {run.result}")
        logging.info([step.moduleInfo for step in run.steps])
        logging.info(f"Total time: {sum(step.preprocess_time + step.postprocess_time for step in run.steps)}")

    logging.info(" ============================================================ ")
    logging.info(" ====================  QUARK finished!   ==================== ")
    logging.info(" ============================================================ ")
    exit(0)



if __name__ == '__main__':
    start()
