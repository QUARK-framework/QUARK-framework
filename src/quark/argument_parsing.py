import argparse

def _create_benchmark_parser(parser: argparse.ArgumentParser):
    parser.add_argument("-c", "--config", help="Provide valid config file instead of interactive mode")
    # parser.add_argument('-cc', '--createconfig', help='If you want o create a config without executing it',
    #                     required=False, action=argparse.BooleanOptionalAction)
    # parser.add_argument('-s', '--summarize', nargs='+', help='If you want to summarize multiple experiments',
    #                     required=False)
    # parser.add_argument('-m', '--modules', help="Provide a file listing the modules to be loaded")
    # parser.add_argument('-rd', '--resume-dir', nargs='?', help='Provide results directory of the job to be resumed')
    # parser.add_argument('-ff', '--failfast', help='Flag whether a single failed benchmark run causes QUARK to fail',
    #                     required=False, action=argparse.BooleanOptionalAction)

    # parser.set_defaults(goal='benchmark')

def get_args():
    parser = argparse.ArgumentParser()
    _create_benchmark_parser(parser)
    return parser.parse_args()
