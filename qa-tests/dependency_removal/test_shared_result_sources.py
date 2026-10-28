# Copyright (C) 2026 OpenCourant contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Enforce the arithmetic and dependency boundaries established by Stage 4."""

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def normalized(text):
    lines = [line.split('!', 1)[0].lower() for line in text.splitlines()
             if not line.startswith(('!', 'C', 'c'))]
    return re.sub(r'\s+', '', ''.join(lines).replace('result_valid', 'is_written_value')
                  .replace('zero_default', 'is_lighter'))


def main():
    reference = json.loads((Path(__file__).with_name('shared_results_reference.json')).read_text())
    assert normalized('C comment\n      A = B + C ! why') == 'a=b+c'
    for kind, expected in reference['calculations'].items():
        text = (ROOT / expected['path']).read_text(encoding='utf-8')
        start = re.search(r'''(?i)\bif\s*\(\s*keyword\s*==\s*["']MASS''', text).start()
        body = normalized(text[start:])[:expected['normalized_characters']]
        assert hashlib.sha256(body.encode()).hexdigest() == expected['sha256'], kind
        code = normalized(text)
        assert not re.search(r'h3d|called_from_python|shell_stack|id_elem|ity_elem|iok_part', code), kind
    print('PASS shared scalar arithmetic matches pre-refactor bodies; no H3D calculation dependencies')
    for name in reference.get('retired_in_stage5', {}):
        assert not (ROOT/name).exists(), name
    for name, expected in reference['unchanged_helpers'].items():
        text = (ROOT / name).read_text(encoding='utf-8')
        if 'python' in name:
            text = text.replace('%result', '%h3d').replace(':: result', ':: h3d')
        assert hashlib.sha256(normalized(text).encode()).hexdigest() == expected, name
    for expected in reference['unchanged_procedures']:
        text = (ROOT/expected['path']).read_text()
        start = re.search(r'(?im)^ +subroutine ' + expected['name'] + r'\(', text).start()
        end = start + re.search(r'(?m)^ +END[ \t]*$', text[start:]).end()
        assert hashlib.sha256(normalized(text[start:end]).encode()).hexdigest() == expected['sha256']
    print('PASS geometry/contact/reduction, parser, Python registration/packing/synchronization bodies preserved')
    text = (ROOT / 'engine/source/tools/curve/funct_python_update_elements.F90').read_text()
    code = normalized(text)
    assert not re.search(r'h3d|shell_stack|id_elem|ity_elem|ipart[csq]|iparttg|\bnpart\b', code)
    for kind in ['shell', 'solid', 'quad']:
        assert 'callresult_' + kind + '_scalar(' in code
    assert '%result' in text and '%h3d' not in text
    for name in ['redkey1_h3d.F', '../output/h3d/h3d_results/h3d_shell_scalar_1.F']:
        assert not (ROOT / 'engine/source/input' / name).exists()
    for name in ['engine/source/output/h3d', 'common_source/output/h3d',
                 'engine/share/modules/h3d_mod.F', 'engine/share/modules/h3d_inc_mod.F']:
        assert not (ROOT/name).exists(), name
    forbidden = re.compile(r'(?i)h3dpublic|Hyper3D|h3dwriter|h3dreader|\bUSE\s+H3D_(?:MOD|INC_MOD)\b')
    for folder in ['engine', 'starter', 'common_source']:
        for path in (ROOT/folder).rglob('*'):
            if path.suffix not in ['.F', '.F90', '.inc', '.c', '.cpp', '.h'] or any(part.startswith('cbuild') for part in path.parts):
                continue
            assert not forbidden.search(path.read_text(encoding='utf-8')), path
    for folder in ['engine', 'starter']:
        for path in (ROOT/folder/'CMake_Compilers').glob('cmake*.txt'):
            assert 'h3d' not in path.read_text(encoding='utf-8').lower(), path
    initialization = normalized((ROOT/'starter/source/elements/elbuf_init/ini_outmax_auto.F').read_text())
    assert 'ikeymax' not in initialization and 'ipart_ok' not in initialization
    for field in ['yield', 'seq', 'eint', 'dmg', 'sig', 'stra']:
        assert 'gbuf%g_tm_' + field + '=0' in initialization
    writer = (ROOT/'engine/source/output/restart/wrcomm.F').read_text()
    reader = (ROOT/'engine/source/output/restart/rdcomm.F').read_text()
    assert 'tabvint(294)=output%data%anim_has_noda_pext*10' in normalized(writer)
    assert 'TABVINT(294)/10' in reader
    resol = normalized((ROOT/'engine/source/engine/resol.F').read_text())
    assert 'if((state_anim==1).and..not.vipercoupling)then' in resol
    assert 'if((state_anim==1).and..not.vipercoupling)thencalltrace_out(3)goto100elsemstop=2goto500endif' in resol
    for last_animation in [0, 1, 2, 3]:
        for thermal_stop in [False, True]:
            for coupled in [False, True]:
                native_state = 1 if last_animation == 1 and not thermal_stop else 2
                old_extra = (native_state == 1 or False) and not coupled
                new_extra = native_state == 1 and not coupled
                assert old_extra == new_extra
                # The retired writer's disabled state selected stop in every other case.
                assert old_extra or native_state == 2 or coupled
    print('PASS Python uses neutral APIs; H3D SDK and writer source trees are absent')


if __name__ == '__main__':
    main()
