import argparse
import sys


def _config_argument_parsing(argument_group: argparse._ArgumentGroup) -> None:
    argument_group.add_argument("-c", "--config", help="Path to a yaml config file")
    argument_group.add_argument("-rd", "--resume-dir", help="Path to results directory of the job to be resumed")


def _other_argument_parsing(argument_group: argparse._ArgumentGroup) -> None:
    argument_group.add_argument(
        "-kp",
        "--keep-pickle",
        help="Keep the pickled state of an interrupted QUARK run, even if all pipeline runs were completed",
        action="store_true",
    )


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="QUARK: Framework for Quantum Computing Application Benchmarking")

    _config_argument_parsing(
        parser.add_argument_group("Mutually exclusive arguments, one is required").add_mutually_exclusive_group(
            required=True,
        ),
    )
    _other_argument_parsing(parser.add_argument_group("Other arguments"))
    return parser.parse_args(args=None if sys.argv[1:] else ["--help"])  # Print help if no arguments are provided
