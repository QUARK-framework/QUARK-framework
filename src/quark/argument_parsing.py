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
    argument_group.add_argument(
        "-ff",
        "--failfast",
        help="Flag whether a single failed benchmark run causes QUARK to fail",
        action="store_true",
    )


def get_args(args: list[str] | None) -> argparse.Namespace:
    """Parse the command line and return a dictionary storing the given parameters."""
    parser = argparse.ArgumentParser(description="QUARK: Framework for Quantum Computing Application Benchmarking")

    _config_argument_parsing(
        parser.add_argument_group("Mutually exclusive arguments, one is required").add_mutually_exclusive_group(
            required=True,
        ),
    )
    _other_argument_parsing(parser.add_argument_group("Other arguments"))
    return parser.parse_args(
        # Print help if no arguments are provided
        args=["--help"] if (not args) and (not sys.argv[1:]) else args,
    )
