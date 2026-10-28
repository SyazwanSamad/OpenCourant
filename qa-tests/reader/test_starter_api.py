# Copyright (C) 2026 OpenCourant contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Audit Starter's reader calls against the in-tree library exports."""

import argparse
import ctypes as ct
import json
import os
from pathlib import Path
import re

from rigid_parts.test_reader_contract import ROOT


def calls(text):
    text = '\n'.join(line for line in text.splitlines()
                     if not line.startswith(('C', 'c', '*', '!')) and not line.lstrip().startswith('!'))
    return {name.lower() for name in re.findall(r'(?i)\bcall\s+((?:cpp_|hm_reader_|open_reader_)[a-z0-9_]+)', text)} | {
        name.lower() for name in re.findall(r'(?i)bind\s*\(\s*c\s*,\s*name\s*=\s*[\'\"]([^\'\"]+)', text)}


def spellings(name):
    return [name, name + '_', name + '__', name.upper()]


def main():
    assert calls('C CALL CPP_COMMENT()\n      CALL CPP_READ(A)\n! CALL CPP_SKIP()\n'
                 'subroutine f() bind(C, name="cpp_bound")') == {'cpp_read', 'cpp_bound'}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reader', required=True, type=lambda p: Path(p).resolve())
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    directories = [os.add_dll_directory(str(path.parent)) for path in [args.reader]] if os.name == 'nt' else []
    opened = ct.CDLL(str(args.reader))
    source_calls = {}
    for path in sorted((ROOT / 'starter/source').rglob('*')):
        if path.suffix.lower() in ['.f', '.f90']:
            for name in calls(path.read_text(errors='replace')):
                source_calls.setdefault(name, []).append(str(path.relative_to(ROOT)))
    local = '\n'.join(path.read_text(errors='replace') for folder in ['starter/source', 'common_source']
                      for path in (ROOT / folder).rglob('*') if path.suffix.lower() in ['.c', '.cpp'])
    report = {'platform': os.name, 'reader_calls': {}, 'local_calls': [], 'guarded_missing': {},
              'missing_exports': {}, 'unresolved': []}
    for name, paths in sorted(source_calls.items()):
        if not any(hasattr(opened, symbol) for symbol in spellings(name)):
            if re.search(r'\b' + re.escape(name) + r'\s*\(', local, re.I):
                report['local_calls'].append(name)
            else:
                report['unresolved'].append({'name': name, 'callers': paths})
            continue
        missing = [symbol for symbol in spellings(name) if not hasattr(opened, symbol)]
        if missing:
            report['missing_exports'][name] = missing
        report['reader_calls'][name] = paths
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    assert not report['unresolved'], report['unresolved']
    assert not report['missing_exports'], report['missing_exports']
    print(f'PASS {len(report["reader_calls"])} reader APIs, all four export spellings; '
          f'{len(report["local_calls"])} local C/C++ calls; no external reader')


if __name__ == '__main__':
    main()
