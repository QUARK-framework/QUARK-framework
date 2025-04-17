from __future__ import annotations
from dataclasses import dataclass
import json
from datetime import datetime
from pathlib import Path
import logging
import pickle


from quark.argument_parsing import get_args
from quark.config_parsing import parse_config
from quark.plugin_manager import loader
from quark.quark_logging import set_logger
from quark.benchmarking import ModuleNode, PipelineRunResult, FinishedTreeRun, InterruptedTreeRun, PipelineRunResultEncoder, run_pipeline_tree


@dataclass(frozen=True)
class BenchmarkingPickle:
    pipeline_trees: list[ModuleNode]
    pipeline_run_results: list[PipelineRunResult]


def start() -> None:
    """
    Main function that triggers the benchmarking process
    """

    set_logger()

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
    config = parse_config(args.config)
    loader.load_plugins(config.plugins)

    pipeline_trees:list[ModuleNode] = config.pipeline_trees
    pipeline_run_results:list[PipelineRunResult] = []

    # TODO document the fact that the pipeline trees are overwritten and that the run id could be read beforehand
    pickle_file_path = f"{config.run_id}.pkl"
    if Path(pickle_file_path).is_file(): # Override trees and intermediate results with pickled values
        logging.info(f"Pickle file matching run id found: {pickle_file_path}")
        logging.info("Continuing benchmarking from data found in pickle file.")
        benchmarking_pickle: BenchmarkingPickle = pickle.load(open(pickle_file_path, "rb"))
        pipeline_trees = benchmarking_pickle.pipeline_trees
        pipeline_run_results = benchmarking_pickle.pipeline_run_results

    rest_trees: list[ModuleNode] = []
    for pipeline_tree in pipeline_trees:
        match run_pipeline_tree(pipeline_tree):
            case FinishedTreeRun(results):
                pipeline_run_results.extend(results)
            case InterruptedTreeRun(intermediate_results, rest_tree):
                pipeline_run_results.extend(intermediate_results)
                rest_trees.append(rest_tree)

    if rest_trees:
        logging.info("Async interrupt: Some modules interrupted execution. Quark will save the current state and exit.")
        pickle.dump(
            BenchmarkingPickle(
                pipeline_trees=rest_trees,
                pipeline_run_results=pipeline_run_results
            ),
            open(pickle_file_path, "wb"))
        return


    logging.info(" ======================== RESULTS =========================== ")
    base_path = Path("benchmark_runs").joinpath(datetime.today().strftime('%Y-%m-%d-%H-%M-%S'))
    base_path.mkdir(parents=True)
    pipelines_path = base_path.joinpath("pipelines")
    pipelines_path.mkdir()
    for i, result in enumerate(pipeline_run_results):
        # dir_name = "benchmark_{i}"
        dir_name = str.join("-", (step.unique_name for step in result.steps))
        dir_path = pipelines_path.joinpath(dir_name)
        dir_path.mkdir()
        json_path = dir_path.joinpath("results.json")
        json_path.write_text(json.dumps(result, cls=PipelineRunResultEncoder, indent=4))
        logging.info([step.module_info for step in result.steps])
        logging.info(f"Result: {result.result}")
        logging.info(f"Total time: {result.total_time}")
        logging.info(f"Metrics: {[step.additional_metrics for step in result.steps]}")
        logging.info("-"*60)

    logging.info(" ============================================================ ")
    logging.info(" ====================  QUARK finished!   ==================== ")
    logging.info(" ============================================================ ")


if __name__ == '__main__':
    start()
