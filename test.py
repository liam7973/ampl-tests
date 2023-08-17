"""
Test Script for AMPL compiler.

Usage:
    test.py (--scanner | --hashtable | --symboltable | --all) [<tests>...]
    test.py --save=<dir> (--scanner | --hashtable | --symboltable | --all) [<tests>...]
    test.py (-h | --help)
    test.py --version
    
Options:
    -h, --help        Display this help screen
    --version         Show version information
    --scanner         Run scanner test suite
    --hashtable       Run hashtable test suite
    --symboltable     Run symbol table test suite
    --all             Run all test suites
    --save=<dir>      Save test output to the specified directory

Examples:
    test.py --scanner 1 2 3       # Run scanner tests 1, 2, 3
    test.py --hashtable 0..5      # Run hashtable tests 0 through 5
    
There are a total of 30 tests. If no specific tests are provided, tests [0..10] will be executed by default.
The differences will be displayed on the console.

Author: Dylan Kirby - 25853805
Date: 2023-08-13
"""
from __future__ import annotations

import os
from subprocess import Popen, TimeoutExpired

from docopt import docopt
from termcolor import cprint
from utils import compile_test_module


def execute_test(
        module,
        test_number: int,
        bin_dir: str,
        test_dir: str = f'{os.getcwd()}/tests',
        timeout:float=10
    ) -> bool:
    """
    Executes the test for the specified module and test number.

    :param module: The module to test (scanner, hashtable, symboltable)
    :param test_number: The test number to execute
    :param bin_dir: The directory containing the test executables
    :param test_dir: The directory containing the test files (default: tests)
    :param timeout: The timeout in seconds (default: 10)
    :return: True if the test executed, False otherwise
    """

    with open(f'temp/{test_number}.out', 'w') as f_out, open(f'temp/{test_number}.err', 'w') as f_err:
        
        process = Popen(
            [f'{bin_dir}/test{module} {test_dir}/{test_number}.ampl'],
            shell=True,
            stdout=f_out,
            stderr=f_err,
        )
        
        try:
            process.wait(timeout=timeout)
            return True
        except TimeoutExpired:
            cprint(f'Test {test_number} timed out after {timeout} seconds.', 'red')
            handle_timeout(process, module)
            return False
        

def handle_timeout(
        process: Popen,
        module: str,
    ):
    
    process.terminate()

    # Wait for SIGTERM to be handled
    # Q: What is a good timeout value here?
    try:
        process.wait(timeout=1)
        return
    except TimeoutExpired:
        cprint(f'WARNING: The test{module} executable could not be terminated using SIGTERM, attempting SIGKILL.', 'red')
        process.kill()

    # Wait for SIGKILL to be handled
    try:
        process.wait(timeout=1)
        return
    except TimeoutExpired:
        cprint(f'CRITICAL: The test{module} executable could not be terminated using SIGKILL, manual intervention required.', 'red')
        exit(1)


def run_test(
        module,
        test_numbers: range | list[int] = range(0, 10+1)
    ) -> bool:
    """
    Runs the tests for the specified module and test numbers.

    :param module: The module to test (scanner, hashtable, symboltable)
    :param test_numbers: The test numbers to execute (default: [0..10])
    :return: True if all tests passed, False otherwise
    """

    # Run: bin/{module} tests/{number}.ampl
    # Diff the output with {module}/{number}.out
    # If diff is empty, test passes

    cprint(f'Running tests for {module}...', 'blue')

    failed = []
    for i in test_numbers:
        
        res = execute_test(module, i, f'{os.getcwd()}/../bin')
        if not res:
            failed.append(i)
            continue
        
        out_diff_proc = Popen(
            [f'diff temp/{i}.out {module}/{i}.out'],
            shell=True,
            cwd=f'{os.getcwd()}'
        )

        err_diff_proc = Popen(
            [f'diff temp/{i}.err {module}/{i}.err'],
            shell=True,
            cwd=f'{os.getcwd()}'
        )

        out_diff_proc.wait()
        err_diff_proc.wait()

        if out_diff_proc.returncode != 0 or err_diff_proc.returncode != 0:
            cprint(f'Test {i} failed.', 'red')
            failed.append(i)
        else:
            cprint(f'Test {i} passed.', 'green')

    if len(failed) == 0:
        cprint(f'All tests passed for {module}!', 'green')
        return True
    else:
        cprint(f'Tests {failed} failed for {module}.', 'red')
        return False
    
def rm_temp():
    temp_dir_proc = Popen(
        ['rm -rf temp'],
        shell=True,
        cwd=f'{os.getcwd()}'
    )
    temp_dir_proc.wait()

    if temp_dir_proc.returncode == 0:
        return
    
    cprint('Warning: Could not remove temp directory.', 'yellow')
    cprint('The temp directory may contain .nfs files, this is expected behaviour.', 'yellow')


        
MODULE_MAPPING = {
    '--scanner': ['scanner'],
    '--hashtable': ['hashtable'],
    '--symboltable': ['symboltable'],
    '--all': ['scanner', 'hashtable', 'symboltable']
}

if __name__ == '__main__':
    args = docopt(__doc__)

    modules = []
    test_cases = range(0, 50+1)

    # Get the module to test
    for module in MODULE_MAPPING.keys():
        if args[module]:
            modules = MODULE_MAPPING[module]
            break

    # Parse the test cases
    if len(args['<tests>']) != 0:
        temp = args['<tests>']
        if ".." in temp[0]:
            temp = temp[0].split("..")
            test_cases = range(int(temp[0]), int(temp[1])+1)
        else:
            test_cases = [int(i) for i in temp]      

    # Create temp directory
    cprint('Executing Setup', 'yellow')
    if os.path.exists('temp'):
        rm_temp()
    os.mkdir('temp') if not os.path.exists('temp') else None

    # Compile and run the tests
    for module in modules:
        try:
            if compile_test_module(module):
                run_test(module, test_cases)
        except Exception as e:
            cprint(f'Error: {e}', 'red')
            break

    # Clean up and save the results
    if args['--save'] is not None:
        mv_proc = Popen(
            [f'mv temp {args["--save"]}'],
            shell=True,
            cwd=f'{os.getcwd()}'
        )
        cprint(f'Saving test results to {args["--save"]}...', 'blue')
        mv_proc.wait()
    else:
        cprint('Cleaning up...', 'yellow')
        rm_temp()

    cprint('Done.', 'blue')