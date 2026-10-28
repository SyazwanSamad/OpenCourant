# Copyright (C) 2026 OpenCourant contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Verify removed-output diagnostics and retain native HTML/animation/history output."""
import argparse
import hashlib
import json
import os
import re

import numpy as np
from compare_decks import records
from pathlib import Path
import subprocess
import sys

from test_shared_results import ROOT, run
sys.path.insert(0, str(ROOT/'qa-tests/reader/rigid_parts'))
from test_numerical import make_deck, ints, reals


def mixed_requests():
    surf='/SURF/SEG/9002\nvalidation surface\n'+ints(1,1,2,3,4)+'\n'
    basecards=['/MONVOL/FVMBAG1/9001','removed flag',ints(9002)+' '*10+reals(0)+ints(1),reals(1,1,1,1,1),ints(1)+' '*30+reals(0,300)+ints(0,0),ints(0),ints(0,0),ints(0,1)+reals(0)+' '*10+ints(0)+reals(0),reals(1,1,1),ints(1,1,1,0,0,0),ints(0)+' '*10+reals(0,0,0),reals(0,0,0,0,0),ints(0,0,0,0,0)]
    basecards2=['/MONVOL/FVMBAG2/9001','removed flag',ints(9002,9002)+reals(0)+ints(1),ints(1)+' '*30+reals(0,300)+' '*10+ints(0),ints(0),ints(0,0),reals(0,0)+' '*10+ints(0)+reals(0),reals(0,0)]
    contact=['/INTER/TYPE21/9001','removed skid request',ints(9002,9002,0,0,0)+' '*20+ints(0,0,0),reals(0,0,0,0)+ints(0),reals(0,0)+' '*20+reals(1),reals(1,0,0,0,0),'0'.rjust(100),ints(0,0)+reals(0)+' '*10+ints(0,0)+reals(0)+ints(0),reals(0,0,0,0,0),reals(0),ints(0)+reals(0,0),reals(0)+ints(0)+reals(0,0)+ints(0),reals(0,0,0)+' '*10+ints(0)+reals(0),ints(0,0)+reals(0,0)]
    return surf, [('fvmbag1',basecards),('fvmbag2',basecards2),('pskid',contact)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', required=True, type=lambda p:Path(p).resolve())
    parser.add_argument('--starter', default=ROOT/'exec/starter_win64.exe', type=lambda p:Path(p).resolve())
    parser.add_argument('--output', required=True, type=lambda p:Path(p).resolve())
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy()
    env.update(RAD_CFG_PATH=str(ROOT/'hm_cfg_files'),OMP_NUM_THREADS='1',KMP_STACKSIZE='400m')
    report={'status':'running','engine_sha256':hashlib.sha256(args.engine.read_bytes()).hexdigest(),'cases':[]}
    try:
        folder=args.output/'engine';folder.mkdir()
        make_deck(folder,'force',True)
        run([args.starter,'-i','rigid_0000.rad','-np','1'],folder,env)
        path=folder/'rigid_0001.rad';original=path.read_text()
        requests={'schedule':'/H3D/DT\n0 0.025\n','scalar':'/H3D/SOLID/SIGEQ\n',
                  'report-html':'/REPORT/HTML/H3D/EXT\n','report-mvw':'/REPORT/MVW/H3D/TH\n',
                  'stop-sensor':'/STOP/LSENSOR\n1\n0 0 0 0 0 1 0\n'}
        for name,request in requests.items():
            path.write_text(original+'\n'+request)
            result=subprocess.run([str(args.engine),'-i',path.name,'-nt','1'],cwd=folder,env=env,capture_output=True,text=True,timeout=60)
            diagnostic=result.stdout+result.stderr
            (args.output/(name+'.log')).write_text(diagnostic)
            assert result.returncode==2,(name,result.returncode,diagnostic[-2000:])
            assert 'H3D' in diagnostic and any(x in diagnostic.lower() for x in ['removed','unsupported'])
            assert 'NORMAL TERMINATION' not in diagnostic and 'CYCLE    TIME' not in diagnostic
            assert 'Engine input line' in diagnostic or '/STOP/LSENSOR' in diagnostic
            report['cases'].append({'case':name,'exit_code':result.returncode})
        # Native and embedded/include parser paths must reject a real keyword, not comments or titles.
        for name in ['native','include','embedded-report']:
            case=args.output/name;case.mkdir();make_deck(case,'force',True)
            model=case/'rigid_0000.rad';text=model.read_text()
            if name=='include':
                (case/'removed.inc').write_text('/H3D/DT\n0 0.01\n')
                text=text.replace('/END','#include removed.inc\n/END')
            else:text=text.replace('/END',('/REPORT/HTML/H3D\n' if name=='embedded-report' else '/H3D/SHELL/SIGEQ\n')+'/END')
            model.write_text(text)
            result=subprocess.run([str(args.starter),'-i',model.name,'-np','1'],cwd=case,env=env,capture_output=True,text=True,timeout=60)
            diagnostic=result.stdout+result.stderr
            (case/'diagnostic.log').write_text(diagnostic)
            assert result.returncode==2 and 'removed H3D output' in diagnostic,(name,diagnostic[-2000:])
            assert '.rad:' in diagnostic or 'removed.inc:' in diagnostic
            report['cases'].append({'case':name,'exit_code':result.returncode})
        surface, requests = mixed_requests()
        for name, cards in requests:
            case=args.output/name;case.mkdir();make_deck(case,'force',True)
            model=case/'rigid_0000.rad'
            model.write_text(model.read_text().replace('/END',surface+'\n'.join(cards)+'\n/END'))
            result=subprocess.run([str(args.starter),'-i',model.name,'-np','1'],cwd=case,env=env,capture_output=True,text=True,timeout=60)
            diagnostic=result.stdout+result.stderr
            (case/'diagnostic.log').write_text(diagnostic)
            assert result.returncode==2 and 'H3D output has been removed' in diagnostic,(name,diagnostic[-2000:])
            report['cases'].append({'case':name,'exit_code':result.returncode})
        path.write_text(original+'\n# /H3D/DT is only a comment\n/REPORT/HTML\n')
        output=run([args.engine,'-i',path.name,'-nt','1'],folder,env)
        assert 'NORMAL TERMINATION' in output
        html=(folder/'rigid_report.html').read_text()
        assert '<html>' in html and 'h3d' not in html.lower() and 'HVPControl' not in html
        assert list(folder.glob('rigidA*')) and (folder/'rigidT01').stat().st_size>0
        assert not list(folder.glob('*.h3d'))
        report['cases'].append({'case':'native-report-animation-history','status':'passed'})
        retired=folder/'rigid.h3d';retired.write_bytes(b'retired output must be ignored')
        run([args.starter,'-checksum_report','rigid'],folder,env)
        checksums=(folder/'rigid.report').read_text()
        for filename in ['rigidA001','rigidT01']:
            assert filename in checksums
            assert hashlib.md5((folder/filename).read_bytes()).hexdigest() in checksums
        assert 'rigid.h3d' not in checksums and 'h3dreader' not in checksums.lower()
        retired.unlink()
        report['cases'].append({'case':'native-checksums-ignore-retired-file','status':'passed'})
        expected_widths, expected_values=records(folder/'rigidT01')
        plain=args.output/'without-animation';plain.mkdir();make_deck(plain,'force',True)
        run([args.starter,'-i','rigid_0000.rad','-np','1'],plain,env)
        schedule=plain/'rigid_0001.rad'
        text=re.sub(r'/ANIM/DT\n[^\n]*\n','',schedule.read_text()).replace('/ANIM/VECT/VEL\n','')
        schedule.write_text(text)
        output=run([args.engine,'-i',schedule.name,'-nt','1'],plain,env)
        assert 'NORMAL TERMINATION' in output
        assert not list(plain.glob('rigidA*')) and not list(plain.glob('*.h3d'))
        widths, values=records(plain/'rigidT01')
        np.testing.assert_array_equal(widths,expected_widths)
        np.testing.assert_allclose(values,expected_values,rtol=1e-5,atol=1e-6)
        report['cases'].append({'case':'without-animation','status':'passed',
            'max_history_difference':float(np.max(np.abs(values-expected_values)))})

        control=args.output/'control-file';control.mkdir();make_deck(control,'force',True)
        run([args.starter,'-i','rigid_0000.rad','-np','1'],control,env)
        (control/'rigid_0001.ctl').write_text('/H3D\n')
        result=subprocess.run([str(args.engine),'-i','rigid_0001.rad','-nt','1'],cwd=control,env=env,capture_output=True,text=True,timeout=60)
        diagnostic=result.stdout+result.stderr
        (control/'diagnostic.log').write_text(diagnostic)
        assert result.returncode==2 and 'H3D control-file output has been removed' in diagnostic,diagnostic[-2000:]
        assert 'NORMAL TERMINATION' not in diagnostic
        report['cases'].append({'case':'control-file','exit_code':result.returncode})
        report['status']='passed'
    except Exception as error:
        report['status'],report['error']='failed',repr(error)
        raise
    finally:
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"PASS removed output validation: {len(report['cases'])} cases")


if __name__=='__main__':
    main()
