import argparse
import os
from dataclasses import dataclass
from typing import Iterable

from result import Result, ResultReader


@dataclass
class ReportSummary:
    python_version: str
    total: int = 0
    valid: int = 0
    success: int = 0
    no_change: int = 0
    size_increase: int = 0
    recursion_error: int = 0
    syntax_error: int = 0
    unstable_minification: int = 0
    exception: int = 0
    mean_time: float = 0
    mean_size_change: float = 0


def result_summary(results_dir: str, python_version: str, sha: str) -> ReportSummary:
    summary = ReportSummary(python_version)

    total_time = 0
    total_size_change = 0

    results_file_path = os.path.join(results_dir, 'results_' + python_version + '_' + sha + '.csv')
    with ResultReader(results_file_path) as result_reader:

        result: Result
        for result in result_reader:
            summary.total += 1

            if result.result == 'Success':
                summary.success += 1
            elif result.result == 'NoChange':
                summary.no_change += 1
            elif result.result == 'SizeIncrease':
                summary.size_increase += 1
            elif result.result == 'RecursionError':
                summary.recursion_error += 1
            elif result.result == 'SyntaxError':
                summary.syntax_error += 1
            elif result.result == 'UnstableMinification':
                summary.unstable_minification += 1
            elif result.result.startswith('Exception'):
                summary.exception += 1

            if result.result in ['Success', 'SizeIncrease', 'NoChange']:
                summary.valid += 1
                total_time += result.time

            if result.result in ['Success', 'SizeIncrease']:
                size_change = result.original_size - result.minified_size
                size_percent_change = size_change / result.original_size * 100

                total_size_change += size_percent_change

    if summary.valid:
        summary.mean_time = total_time / summary.valid
        summary.mean_size_change = total_size_change / summary.valid

    return summary


def report(results_dir: str, minifier_ref: str, minifier_sha: str) -> Iterable[str]:
    yield f'''
# Python Minifier Test Report

Git Ref: {minifier_ref}
Git Sha: {minifier_sha}

This report is generated by the `corpus_test/generate_report.py` script.

## Summary

| Python Version | Valid Corpus Entries | Average Time | Minified Size | Size Increased | Recursion Error | Unstable Minification | Exception |
|----------------|---------------------:|-------------:|--------------:|---------------:|----------------:|----------------------:|----------:|'''

    for python_version in ['2.7', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11']:
        try:
            summary = result_summary(results_dir, python_version, minifier_sha)
            yield f'| {python_version} | {summary.valid} | {summary.mean_time:.3f} | {summary.mean_size_change:.3f}% | {summary.size_increase} | {summary.recursion_error} | {summary.unstable_minification} | {summary.exception} |'
        except FileNotFoundError:
            yield f'| {python_version} | N/A | N/A | N/A | N/A | N/A | N/A | N/A |'


def main():
    parser = argparse.ArgumentParser(description='Generate a test report for a given python-minifier ref')
    parser.add_argument('results_dir', type=str, help='Path to results directory', default='results')
    parser.add_argument('minifier_ref', type=str, help='The python-minifier ref we are testing')
    parser.add_argument('minifier_sha', type=str, help='The python-minifier sha we are testing')
    args = parser.parse_args()

    for segment in report(args.results_dir, args.minifier_ref, args.minifier_sha):
        print(segment)


if __name__ == '__main__':
    main()