import argparse
import os
import re
from pathlib import Path

from zkay.config import cfg

from zkay import my_logging
from zkay.compiler.privacy.zkay_frontend import compile_zkay, package_zkay
from zkay.compiler.solidity.compiler import SolcException
from zkay.my_logging.log_context import log_context
from zkay.utils.helpers import read_file, lines_of_code
from zkay.utils.progress_printer import print_step, TermColor, colored_print
from zkay.utils.timer import time_measure
from zkay.zkay_ast.process_ast import get_processed_ast, TypeCheckException, PreprocessAstException, ParseExeception, \
    get_parsed_ast_and_fake_code
from zkay.zkay_ast.visitor.statement_counter import count_statements


def parse_arguments():
    # prepare parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-fake-solidity', action='store_true', help='Output fake solidity code (zkay code without privacy features and comments)')
    parser.add_argument('--type-check', action='store_true', help='Only type-check, do not compile.')
    msg = 'The directory to output the compiled contract to. Default: Current directory'
    parser.add_argument('--output', default=os.getcwd(), help=msg)
    parser.add_argument(
        '--count-statements',
        default=False,
        action='store_true',
        dest='count',
        help="Count the number of statements in the translated program")
    parser.add_argument('input', type=str, help='The source file')
    parser.add_argument('--config-overrides', default='', dest='overrides', help='semicolon separated list of config_val_name=config_val pairs')

    # parse
    a = parser.parse_args()

    return a


def compile(file_location: str, d, count, get_binaries=False):
    code = read_file(file_location)

    # log specific features of compiled program
    my_logging.data('originalLoc', lines_of_code(code))
    m = re.search(r'\/\/ Description: (.*)', code)
    if m:
        my_logging.data('description', m.group(1))
    m = re.search(r'\/\/ Domain: (.*)', code)
    if m:
        my_logging.data('domain', m.group(1))
    _, filename = os.path.split(file_location)

    # compile
    with time_measure('compileFull'):
        cg, _ = compile_zkay(code, d, filename)
        #package_zkay(file_location, cg)

    #if count:
    #    my_logging.data('nStatements', count_statements(ast))


if __name__ == '__main__':
    # parse arguments
    a = parse_arguments()

    # Support for overriding any config value via command line
    override_dict = {}
    if a.overrides:
        overrides = a.overrides.split(';')
        for o in overrides:
            key_val = o.split('=')
            if len(key_val) != 2:
                raise ValueError(f'Invalid override argument {key_val}')
            k, v = key_val
            v = v.strip().replace('\'', '\\\'')
            override_dict[k.strip()] = f"'{v}'"
    cfg.override_defaults(override_dict)

    input_file = Path(a.input)
    if not input_file.exists():
        with colored_print(TermColor.FAIL):
            print(f'Error: input file \'{input_file}\' does not exist')
        exit(1)

    # create output directory
    output_dir = Path(a.output).absolute()
    if not output_dir.exists():
        os.mkdir(output_dir)
    elif not output_dir.is_dir():
        with colored_print(TermColor.FAIL):
            print(f'Error: \'{output_dir}\' is not a directory')
        exit(2)

    # create log directory
    log_file = my_logging.get_log_file(filename='compile', parent_dir=str(output_dir), include_timestamp=False, label=None)
    my_logging.prepare_logger(log_file)

    # only type-check
    print(f'Processing file {input_file.name}:')

    if a.output_fake_solidity:
        _, fake_code = get_parsed_ast_and_fake_code(read_file(str(input_file)))
        with open(os.path.join(output_dir, f'{input_file.name}.fake.sol'), 'w') as f:
            f.write(fake_code)
    elif a.type_check:
        code = read_file(str(input_file))

        try:
            ast = get_processed_ast(code)
        except (ParseExeception, PreprocessAstException, TypeCheckException, SolcException):
            exit(3)
    else:
        # compile
        with log_context('inputfile', os.path.basename(a.input)):
            compile(str(input_file), str(output_dir), a.count)

    with colored_print(TermColor.OKGREEN):
        print("Finished successfully")