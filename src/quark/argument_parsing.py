import argparse


def _create_benchmark_parser(argument_group: argparse._ArgumentGroup) -> None:
    argument_group.add_argument("-c", "--config", help="Path to a yaml config file")
    argument_group.add_argument("-rd", "--resume-dir", help="Path to results directory of the job to be resumed")


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    group = parser.add_argument_group("Mutually exclusive, one is required").add_mutually_exclusive_group(
        required=True,
    )
    _create_benchmark_parser(group)
    return parser.parse_args()
