# Copyright (C) 2026 OpenCourant contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Compile a focused self-check of the production retired-record discard routine."""
import argparse
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=lambda p:Path(p).resolve())
    parser.add_argument('--compiler',default='ifx')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    source=(ROOT/'engine/source/output/restart/rdresb.F').read_text()
    routine=source[source.index('      SUBROUTINE DISCARD_RESTART_REALS'):]
    assert re.search(r'(?m)^      END\s*$',routine)
    routine=routine.replace('#include "implicit_f.inc"','      IMPLICIT NONE').replace('my_real','DOUBLE PRECISION')
    harness='''      MODULE TEST_STATE
      INTEGER TOTAL_READ,CALL_COUNT
      END MODULE
      PROGRAM CHECK_DISCARD
      USE TEST_STATE
      IMPLICIT NONE
      CHARACTER ARG
      TOTAL_READ=0
      CALL_COUNT=0
      CALL GET_COMMAND_ARGUMENT(1,ARG)
      IF(ARG=='-') CALL DISCARD_RESTART_REALS(-1)
      CALL DISCARD_RESTART_REALS(0)
      IF(CALL_COUNT/=0) STOP 1
      CALL DISCARD_RESTART_REALS(1001)
      CALL DISCARD_RESTART_REALS(2505)
      IF(TOTAL_READ/=3506.OR.CALL_COUNT/=5) STOP 1
      END
      SUBROUTINE READ_DB(BUFFER,N)
      USE TEST_STATE
      IMPLICIT NONE
      INTEGER N
      DOUBLE PRECISION BUFFER(*)
      IF(N<1.OR.N>1000) STOP 1
      TOTAL_READ=TOTAL_READ+N
      CALL_COUNT=CALL_COUNT+1
      END
      SUBROUTINE ARRET(N)
      IMPLICIT NONE
      INTEGER N
      IF(N/=2) STOP 1
      STOP 2
      END
'''+routine
    path=args.output/'check.F';path.write_text(harness)
    executable=args.output/'check.exe'
    compiled=subprocess.run([args.compiler,'/nologo','/fpp','/extend_source:132','/exe:'+str(executable),str(path)],
                            cwd=args.output,capture_output=True,text=True,timeout=60)
    (args.output/'compile.log').write_text(compiled.stdout+compiled.stderr)
    assert compiled.returncode==0,compiled.stdout+compiled.stderr
    for arg,expected in [('',0),('-',2)]:
        result=subprocess.run([str(executable),arg],capture_output=True,text=True,timeout=10)
        assert result.returncode==expected,(arg,result.returncode,result.stdout,result.stderr)
    print('PASS restart discard: zero length, partial/multiple chunks, negative-length rejection')


if __name__=='__main__':
    main()
