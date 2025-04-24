from __future__ import annotations

import json
import logging
import pickle
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from quark.argument_parsing import get_args
from quark.benchmarking import (
    FinishedTreeRun,
    InterruptedTreeRun,
    ModuleNode,
    PipelineRunResult,
    PipelineRunResultEncoder,
    run_pipeline_tree,
)
from quark.config_parsing import parse_config
from quark.plugin_manager import loader
from quark.quark_logging import set_logger

PICKLE_FILE_NAME: str = "intermediate_run_state.pkl"


@dataclass(frozen=True)
class BenchmarkingPickle:
    plugins: list[str]
    pipeline_trees: list[ModuleNode]
    pipeline_run_results: list[PipelineRunResult]


def start() -> None:
    """Start the benchmarking process."""
    args = get_args()
    base_path: Path
    plugins = list[str]
    pipeline_trees: list[ModuleNode] = []
    pipeline_run_results: list[PipelineRunResult] = []
    match args.resume_dir:
        case None:  # New run
            base_path = Path("benchmark_runs").joinpath(datetime.today().strftime("%Y-%m-%d-%H-%M-%S"))  # noqa: DTZ002
            base_path.mkdir(parents=True)
            set_logger(str(base_path.joinpath("logging.log")))
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
            # This is guaranteed to be set, as resume_dir and config are mutually exclusive and required
            config = parse_config(args.config)
            plugins = config.plugins
            pipeline_trees = config.pipeline_trees
        case path_str:  # Resumed run
            base_path = Path(path_str)
            if not base_path.is_absolute():
                base_path = Path("benchmark_runs").joinpath(base_path)
            pickle_file_path = base_path.joinpath(PICKLE_FILE_NAME)
            if not pickle_file_path.is_file():
                print("Error: No pickle file found in the specified resume_dir")  # noqa: T201
                exit(1)
            set_logger(str(base_path.joinpath("logging.log")))
            logging.info("")
            logging.info("Resuming benchmarking from data found in pickle file.")
            with Path.open(pickle_file_path, "rb") as f:
                benchmarking_pickle: BenchmarkingPickle = pickle.load(f)  # noqa: S301
            plugins = benchmarking_pickle.plugins
            pipeline_trees = benchmarking_pickle.pipeline_trees
            pipeline_run_results = benchmarking_pickle.pipeline_run_results

    loader.load_plugins(plugins)

    rest_trees: list[ModuleNode] = []
    for pipeline_tree in pipeline_trees:
        match run_pipeline_tree(pipeline_tree):
            case FinishedTreeRun(results):
                pipeline_run_results.extend(results)
            case InterruptedTreeRun(intermediate_results, rest_tree):
                pipeline_run_results.extend(intermediate_results)
                rest_trees.append(rest_tree)

    if rest_trees:
        logging.info(
            "Async interrupt: Some modules interrupted execution. Quark will save the current state and exit.",
        )
        with Path.open(base_path.joinpath(PICKLE_FILE_NAME), "wb") as f:
            pickle.dump(
                BenchmarkingPickle(
                    plugins=plugins,
                    pipeline_trees=rest_trees,
                    pipeline_run_results=pipeline_run_results,
                ),
                f,
            )
        return

    logging.info(" ======================== RESULTS =========================== ")
    pipelines_path = base_path.joinpath("pipelines")
    pipelines_path.mkdir()
    for result in pipeline_run_results:
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
        logging.info("-" * 60)

    logging.info(" ============================================================ ")
    logging.info(" ====================  QUARK finished!   ==================== ")
    logging.info(" ============================================================ ")


if __name__ == "__main__":
    start()
