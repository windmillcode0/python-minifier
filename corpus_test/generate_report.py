import argparse
import os
import sys
from dataclasses import dataclass, field
from typing import Iterable

from result import Result, ResultReader


@dataclass
class ResultsSummary:
    python_version: str
    total: int = 0
    valid: int = 0
    success: int = 0
    no_change: int = 0
    syntax_error: int = 0
    mean_time: float = 0
    mean_size_change: float = 0

    size_increase: set = field(default_factory=set)
    recursion_error: set = field(default_factory=set)
    unstable_minification: set = field(default_factory=set)
    exception: set = field(default_factory=set)

def result_summary(results_dir: str, python_version: str, sha: str) -> ResultsSummary:
    summary = ResultsSummary(python_version)

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
                summary.size_increase.add(result.corpus_entry)
            elif result.result == 'RecursionError':
                summary.recursion_error.add(result.corpus_entry)
            elif result.result == 'SyntaxError':
                summary.syntax_error += 1
            elif result.result == 'UnstableMinification':
                summary.unstable_minification.add(result.corpus_entry)
            elif result.result.startswith('Exception'):
                summary.exception.add(result.corpus_entry)

            if result.result in ['Success', 'SizeIncrease', 'NoChange']:
                summary.valid += 1
                total_time += result.time

            if result.result in ['Success', 'SizeIncrease']:
                size_percent_change = (result.minified_size / result.original_size) * 100

                total_size_change += size_percent_change

    if summary.valid:
        summary.mean_time = total_time / summary.valid
        summary.mean_size_change = total_size_change / summary.valid

    return summary

def format_difference(compare: set, base: set) -> str:
    s = len(compare)

    detail = []

    if len(compare - base) > 0:
        detail.append(f'+{len(compare - base)}')

    if len(base - compare) > 0:
        detail.append(f'-{len(base - compare)}')

    if detail:
        return f'{s} ({", ".join(detail)})'
    else:
        return s


def report(results_dir: str, minifier_ref: str, minifier_sha: str, base_ref: str, base_sha: str) -> Iterable[str]:
    yield f'''
# Python Minifier Test Report

Git Ref: {minifier_ref}
Git Sha: {minifier_sha}
Base Ref: {base_ref}
Base Sha: {base_sha}

This report is generated by the `corpus_test/generate_report.py` script.

## Summary

| Python Version | Valid Corpus Entries | Average Time | Minified Size | Size Increased | Recursion Error | Unstable Minification | Exception |
|----------------|---------------------:|-------------:|--------------:|---------------:|----------------:|----------------------:|----------:|'''

    for python_version in ['2.7', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11']:
        try:
            summary = result_summary(results_dir, python_version, minifier_sha)
        except FileNotFoundError:
            yield f'| {python_version} | N/A | N/A | N/A | N/A | N/A | N/A | N/A |'
            continue

        try:
            base_summary = result_summary(results_dir, python_version, base_sha)
        except FileNotFoundError:
            base_summary = ResultsSummary(python_version)

        mean_time_change = summary.mean_time - base_summary.mean_time
        mean_size_change = summary.mean_size_change - base_summary.mean_size_change

        yield (
            f'| {python_version} ' +
            f'| {summary.valid} ' +
            f'| {summary.mean_time:.3f} ({mean_time_change:+.3f}) ' +
            f'| {summary.mean_size_change:.3f}% ({mean_size_change:+.3f}) ' +
            f'| {format_difference(summary.size_increase, base_summary.size_increase)} ' +
            f'| {format_difference(summary.recursion_error, base_summary.recursion_error)} ' +
            f'| {format_difference(summary.unstable_minification, base_summary.unstable_minification)} ' +
            f'| {format_difference(summary.exception, base_summary.exception)} '
        )

def main():
    parser = argparse.ArgumentParser(description='Generate a test report for a given python-minifier ref')
    parser.add_argument('results_dir', type=str, help='Path to results directory', default='results')
    parser.add_argument('minifier_ref', type=str, help='The python-minifier ref we are testing')
    parser.add_argument('minifier_sha', type=str, help='The python-minifier sha we are testing')
    parser.add_argument('base_ref', type=str, help='The python-minifier sha to compare with')
    parser.add_argument('base_sha', type=str, help='The python-minifier sha to compare with')
    args = parser.parse_args()

    sys.stderr.write(f'Generating report for {args.minifier_ref} ({args.minifier_sha})')

    for segment in report(args.results_dir, args.minifier_ref, args.minifier_sha, args.base_ref, args.base_sha):
        print(segment)


if __name__ == '__main__':
    main()
