from __future__ import annotations

import json
import logging
import pickle
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from quark.argument_parsing import get_args
from quark.benchmarking import (
    FailedPipelineRun,
    FinishedPipelineRun,
    FinishedTreeRun,
    InterruptedTreeRun,
    ModuleNode,
    run_pipeline_tree,
)
from quark.config_parsing import parse_config
from quark.plugin_manager import loader
from quark.quark_logging import set_logger

PICKLE_FILE_NAME: str = "intermediate_run_state.pkl"


@dataclass(frozen=True)
class BenchmarkingPickle:
    """Encapsulates all data needed when the program state is stored as a pickle file."""

    plugins: list[str]
    pipeline_trees: list[ModuleNode]
    finished_pipeline_runs: list[FinishedPipelineRun]
    failed_pipeline_runs: list[FailedPipelineRun]


class FinishedPipelineRunResultEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:  # noqa: ANN401
        if not isinstance(o, FinishedPipelineRun):
            # Let the base class default method raise the TypeError
            return super().default(o)
        # TODO Handle error if no string representation of data is available
        d = o.__dict__.copy()
        del d["result"]
        d["steps"] = [step.__dict__ for step in o.steps]
        for step in d["steps"]:
            step["module_info"] = step["module_info"].__dict__
        return d


class FailedPipelineRunResultEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:  # noqa: ANN401
        if not isinstance(o, FailedPipelineRun):
            # Let the base class default method raise the TypeError
            return super().default(o)
        d = o.__dict__.copy()
        d["exception"] = str(d["exception"])
        d["metrics_up_to_now"] = [step.__dict__ for step in o.metrics_up_to_now]
        for step in d["metrics_up_to_now"]:
            step["module_info"] = step["module_info"].__dict__
        return d


def start() -> None:
    """Start the benchmarking process."""
    args = get_args()
    base_path: Path
    plugins = list[str]
    pipeline_trees: list[ModuleNode] = []
    all_finished_pipeline_runs: list[FinishedPipelineRun] = []
    all_failed_pipeline_runs: list[FailedPipelineRun] = []
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
            all_finished_pipeline_runs = benchmarking_pickle.finished_pipeline_runs
            all_failed_pipeline_runs = benchmarking_pickle.failed_pipeline_runs

    pickle_file_path = base_path.joinpath(PICKLE_FILE_NAME)
    pipelines_path = base_path.joinpath("pipelines")
    failed_pipelines_path = base_path.joinpath("failed_pipelines")

    loader.load_plugins(plugins)

    rest_trees: list[ModuleNode] = []
    for pipeline_tree in pipeline_trees:
        match run_pipeline_tree(pipeline_tree):
            case FinishedTreeRun(finished_pipeline_runs):
                all_finished_pipeline_runs.extend(finished_pipeline_runs)
            case InterruptedTreeRun(finished_pipeline_runs, failed_pipeline_runs, rest_tree):
                all_finished_pipeline_runs.extend(finished_pipeline_runs)
                all_failed_pipeline_runs.extend(failed_pipeline_runs)
                if rest_tree:
                    rest_trees.append(rest_tree)

    if rest_trees:
        logging.info(
            "Some modules interrupted execution. QUARK will store the current program state and exit.",
        )
        # TODO write already finished runs to dirs
        with Path.open(pickle_file_path, "wb") as f:
            pickle.dump(
                BenchmarkingPickle(
                    plugins=plugins,
                    pipeline_trees=rest_trees,
                    finished_pipeline_runs=all_finished_pipeline_runs,
                    failed_pipeline_runs=all_failed_pipeline_runs,
                ),
                f,  # IDE throws warning: Expected type 'SupportsWrite[bytes]', got 'BufferedWriter' instead
            )
        logging.info(f"To resume from this state, start QUARK with '--resume-dir {base_path}'.")
        return

    logging.info(" ======================== RESULTS =========================== ")

    if all_finished_pipeline_runs:
        pipelines_path.mkdir()
    for finished_run in all_finished_pipeline_runs:
        dir_name = str.join("-", (step.unique_name for step in finished_run.steps))
        dir_path = pipelines_path.joinpath(dir_name)
        dir_path.mkdir()
        json_path = dir_path.joinpath("results.json")
        json_path.write_text(json.dumps(finished_run, cls=FinishedPipelineRunResultEncoder, indent=4))
        logging.info([step.module_info for step in finished_run.steps])
        logging.info(f"Result: {finished_run.result}")
        logging.info(f"Total time: {sum(step.preprocess_time + step.postprocess_time for step in finished_run.steps)}")
        logging.info(f"Metrics: {[step.additional_metrics for step in finished_run.steps]}")
        logging.info("-" * 60)

    if all_failed_pipeline_runs:
        failed_pipelines_path.mkdir()
    for i, failed_run in enumerate(all_failed_pipeline_runs):
        dir_name = str(i) + str.join("-", (step.unique_name for step in failed_run.metrics_up_to_now))
        dir_path = failed_pipelines_path.joinpath(dir_name)
        dir_path.mkdir()
        json_path = dir_path.joinpath("results.json")
        json_path.write_text(json.dumps(failed_run, cls=FailedPipelineRunResultEncoder, indent=4))
        logging.info([step.module_info for step in failed_run.metrics_up_to_now])
        logging.info(f"Exception: {failed_run.exception}")
        logging.info(f"Metrics: {[step.additional_metrics for step in failed_run.metrics_up_to_now]}")
        logging.info("-" * 60)

    if not args.keep_pickle:
        pickle_file_path.unlink(missing_ok=True)

    logging.info(" ============================================================ ")
    logging.info(" ====================  QUARK finished!   ==================== ")
    logging.info(" ============================================================ ")


if __name__ == "__main__":
    start()
