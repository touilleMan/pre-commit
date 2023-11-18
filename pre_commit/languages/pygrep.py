from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from re import Pattern
from typing import NamedTuple

from pre_commit import lang_base
from pre_commit import output
from pre_commit.prefix import Prefix
from pre_commit.xargs import xargs

ENVIRONMENT_DIR = None
get_default_version = lang_base.basic_get_default_version
health_check = lang_base.basic_health_check
install_environment = lang_base.no_install
in_env = lang_base.no_env


def _process_filename_by_line(pattern: Pattern[bytes], filename: str) -> int:
    retv = 0
    with open(filename, 'rb') as f:
        for line_no, line in enumerate(f, start=1):
            if pattern.search(line):
                retv = 1
                output.write(f'{filename}:{line_no}:')
                output.write_line_b(line.rstrip(b'\r\n'))
    return retv


def _process_filename_at_once(pattern: Pattern[bytes], filename: str) -> int:
    retv = 0
    with open(filename, 'rb') as f:
        contents = f.read()
        match = pattern.search(contents)
        if match:
            retv = 1
            line_no = contents[:match.start()].count(b'\n')
            output.write(f'{filename}:{line_no + 1}:')

            matched_lines = match[0].split(b'\n')
            matched_lines[0] = contents.split(b'\n')[line_no]

            output.write_line_b(b'\n'.join(matched_lines))
    return retv


def _process_filename_by_line_negated(
        pattern: Pattern[bytes],
        filename: str,
) -> int:
    with open(filename, 'rb') as f:
        for line in f:
            if pattern.search(line):
                return 0
        else:
            output.write_line(filename)
            return 1


def _process_filename_at_once_negated(
        pattern: Pattern[bytes],
        filename: str,
) -> int:
    with open(filename, 'rb') as f:
        contents = f.read()
    match = pattern.search(contents)
    if match:
        return 0
    else:
        output.write_line(filename)
        return 1


class Choice(NamedTuple):
    multiline: bool
    negate: bool


FNS = {
    Choice(multiline=True, negate=True): _process_filename_at_once_negated,
    Choice(multiline=True, negate=False): _process_filename_at_once,
    Choice(multiline=False, negate=True): _process_filename_by_line_negated,
    Choice(multiline=False, negate=False): _process_filename_by_line,
}


def run_hook(
        prefix: Prefix,
        entry: str,
        args: Sequence[str],
        file_args: Sequence[str],
        *,
        is_local: bool,
        require_serial: bool,
        color: bool,
        dry_run: bool,
) -> tuple[int, bytes]:
    cmd = (sys.executable, '-m', __name__, *args, entry)
    return xargs(cmd, file_args, color=color, dry_run=dry_run)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            'grep-like finder using python regexes.  Unlike grep, this tool '
            'returns nonzero when it finds a match and zero otherwise.  The '
            'idea here being that matches are "problems".'
        ),
    )
    parser.add_argument('-i', '--ignore-case', action='store_true')
    parser.add_argument('--multiline', action='store_true')
    parser.add_argument('--negate', action='store_true')
    parser.add_argument('pattern', help='python regex pattern.')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)

    flags = re.IGNORECASE if args.ignore_case else 0
    if args.multiline:
        flags |= re.MULTILINE | re.DOTALL

    pattern = re.compile(args.pattern.encode(), flags)

    retv = 0
    process_fn = FNS[Choice(multiline=args.multiline, negate=args.negate)]
    for filename in args.filenames:
        retv |= process_fn(pattern, filename)
    return retv


if __name__ == '__main__':
    raise SystemExit(main())
