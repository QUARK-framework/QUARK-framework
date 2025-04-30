from __future__ import annotations

import json
import logging
import pickle
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from quark.argument_parsing import get_args
from quark.benchmarking import (
    FinishedPipelineRun,
    FinishedTreeRun,
    InterruptedTreeRun,
    ModuleNode,
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
    finished_pipeline_runs: list[FinishedPipelineRun]


def start() -> None:
    """Start the benchmarking process."""
    args = get_args()
    base_path: Path
    plugins = list[str]
    pipeline_trees: list[ModuleNode] = []
    already_finished_pipeline_runs: list[FinishedPipelineRun] = []
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
        case resume_dir_path:  # Resumed run
            base_path = Path(resume_dir_path)
            # if not base_path.is_absolute():
            #     base_path = Path("benchmark_runs").joinpath(base_path)
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
            already_finished_pipeline_runs = benchmarking_pickle.finished_pipeline_runs

    pickle_file_path = base_path.joinpath(PICKLE_FILE_NAME)
    pipelines_path = base_path.joinpath("pipelines")

    loader.load_plugins(plugins)

    rest_trees: list[ModuleNode] = []
    for pipeline_tree in pipeline_trees:
        match run_pipeline_tree(pipeline_tree):
            case FinishedTreeRun(finished_pipeline_runs):
                already_finished_pipeline_runs.extend(finished_pipeline_runs)
            case InterruptedTreeRun(finished_pipeline_runs, paused_pipeline_runs, rest_tree):
                already_finished_pipeline_runs.extend(finished_pipeline_runs)
                rest_trees.append(rest_tree)

    if rest_trees:
        logging.info(
            "Some modules interrupted execution. Quark will store the current program state and exit.",
        )
        with Path.open(pickle_file_path, "wb") as f:
            pickle.dump(
                BenchmarkingPickle(
                    plugins=plugins,
                    pipeline_trees=rest_trees,
                    finished_pipeline_runs=already_finished_pipeline_runs,
                ),
                f,
            )
        logging.info(f"To resume from this state, start QUARK with '--resume-dir {base_path}'")
        return

    logging.info(" ======================== RESULTS =========================== ")

    pipelines_path.mkdir()
    for result in already_finished_pipeline_runs:
        dir_name = str.join("-", (step.unique_name for step in result.steps))
        dir_path = pipelines_path.joinpath(dir_name)
        dir_path.mkdir()
        json_path = dir_path.joinpath("results.json")
        json_path.write_text(json.dumps(result, cls=PipelineRunResultEncoder, indent=4))
        logging.info([step.module_info for step in result.steps])
        logging.info(f"Result: {result.result}")
        logging.info(f"Total time: {sum(step.preprocess_time + step.postprocess_time for step in result.steps)}")
        logging.info(f"Metrics: {[step.additional_metrics for step in result.steps]}")
        logging.info("-" * 60)

    if not args.keep_pickle:
        pickle_file_path.unlink(missing_ok=True)

    logging.info(" ============================================================ ")
    logging.info(" ====================  QUARK finished!   ==================== ")
    logging.info(" ============================================================ ")


if __name__ == "__main__":
    start()
