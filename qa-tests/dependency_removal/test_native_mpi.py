# Copyright (C) 2026 OpenCourant contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Compare two-rank native contact/sensor histories with the pre-removal MPI build."""
import argparse
import hashlib
import gzip
import json
import os
from pathlib import Path
import shutil
import numpy as np
from test_shared_results import ROOT, run
from compare_decks import records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine',required=True,type=lambda p:Path(p).resolve())
    parser.add_argument('--starter',default=ROOT/'exec/starter_win64.exe',type=lambda p:Path(p).resolve())
    parser.add_argument('--output',required=True,type=lambda p:Path(p).resolve())
    parser.add_argument('--baseline',type=lambda p:Path(p).resolve())
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy();env.update(RAD_CFG_PATH=str(ROOT/'hm_cfg_files'),OMP_NUM_THREADS='1',KMP_STACKSIZE='400m',I_MPI_FABRICS='shm')
    report={'status':'running','ranks':2,'engine_sha256':hashlib.sha256(args.engine.read_bytes()).hexdigest(),'cases':[]}
    try:
        for name,relative in [('accelerometer','ACCELEROMETRES/data/ACCELERO_0000.rad'),('friction','INTERF/INT_7/friction/data/FRICT41_0000.rad')]:
            source=ROOT/'qa-tests/miniqa'/relative;folder=args.output/name
            shutil.copytree(source.parent,folder)
            if name=='friction':
                schedule=folder/(source.stem[:-1]+'1.rad')
                schedule.write_text(schedule.read_text()+'\n'+''.join('/ANIM/'+key+'\n' for key in
                    ['VECT/CONT','VECT/PCONT','VECT/FINT','VECT/FEXT','NODA/PEXT']))
            hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.suffix in ['.rad','.inc']}
            run([args.starter,'-i',source.name,'-np','2'],folder,env)
            output=run(['mpiexec','-localonly','-n','2',args.engine,'-i',source.stem[:-1]+'1.rad','-nt','1'],folder,env)
            assert 'NORMAL TERMINATION' in output
            history=next(folder.glob('*T01'));widths,values=records(history)
            assert len(values)>=2 and values[-1,0]>0 and np.isfinite(values).all()
            assert not list(folder.glob('*.h3d'))
            np.savez_compressed(folder/'values.npz',widths=widths,histories=values)
            animations=sorted(folder.glob(source.stem[:-5]+'A*.gz'))
            assert animations
            row={'case':name,'inputs':hashes,'samples':len(values)}
            row['animation_files']=len(animations)
            if args.baseline:
                old=np.load(args.baseline/name/'values.npz')
                np.testing.assert_array_equal(widths,old['widths'])
                np.testing.assert_allclose(values,old['histories'],rtol=1e-5,atol=1e-6)
                row['max_history_difference']=float(np.max(np.abs(values-old['histories'])))
                for path in animations:
                    assert gzip.decompress(path.read_bytes())==gzip.decompress((args.baseline/name/path.name).read_bytes()),path.name
                row['animation_bytes_match']=True

            report['cases'].append(row)
            print(f'PASS native MPI {name}: {len(values)} history samples',flush=True)
        report['status']='passed'
    except Exception as error:
        report['status'],report['error']='failed',repr(error)
        raise
    finally:
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
