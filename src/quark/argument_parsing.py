import argparse

def _create_benchmark_parser(argument_group: argparse._ArgumentGroup):
    argument_group.add_argument("-c", "--config", help="Path to a yaml config file")
    # parser.add_argument('-cc', '--createconfig', help='If you want o create a config without executing it',
    #                     required=False, action=argparse.BooleanOptionalAction)
    # parser.add_argument('-s', '--summarize', nargs='+', help='If you want to summarize multiple experiments',
    #                     required=False)
    # parser.add_argument('-m', '--modules', help="Provide a file listing the modules to be loaded")
    argument_group.add_argument('-rd', '--resume-dir', help='Path to results directory of the job to be resumed')
    # parser.add_argument('-ff', '--failfast', help='Flag whether a single failed benchmark run causes QUARK to fail',
    #                     required=False, action=argparse.BooleanOptionalAction)

    # parser.set_defaults(goal='benchmark')

def get_args():
    parser = argparse.ArgumentParser()

    group = parser.add_argument_group('Mutually exclusive, one is required').add_mutually_exclusive_group(required=True)
    _create_benchmark_parser(group)
    return parser.parse_args()
