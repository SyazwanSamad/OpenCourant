# Parameter regression

Windows x64 DP SMP validation passed on 2026-10-28, using MSVC/Intel oneAPI 2025.2
and profile 2612. [The approved plan](../../../doc/OpenReader_parameter_fix_plan.md)
defines the bounded scope. Run from the repository root in the initialized
toolchain environment, with a fresh output directory:

```powershell
python qa-tests/reader/test_parameters.py --reader exec/open_reader_win64.dll --starter exec/starter_win64.exe --engine exec/engine_win64.exe --output cbuild_parameters_physics
```

Omit `--engine` for the standard-library Reader/Starter gate used in Windows CI.
NumPy and the existing `vortex_radioss` installation are required for histories.

The literal and parameterized decks have equal physical inputs. The latter uses
all five types in one model: `COUNT=2`, `FUNCID=COUNT-1=1`, `BASE=6000`,
`YOUNG=BASE*2+345=12345`, `NEG=-1`, and `ZEROV=BASE-BASE=0`. Global material values
before/after the submodel remain 6000; one local override supplies 24000. TEXT
supplies `test specimen` through `$` stitching, the fixed-width load axis `X`,
and a whole numeric PART card. The same integer expression supplies header and
load function IDs. `-&NEG` yields a positive unit force. No type/scope matrix or
additional solver simulations are needed.

| Check | Result |
| --- | --- |
| Literal and parameterized Reader/Starter | Correct IDs, numeric values, titles and global/local listings; exit 0; nonempty restarts |
| Missing direct reference, missing expression argument, malformed expression, cycle | Four separately generated failures; file/line diagnostics; Starter exit 2; no usable restart |
| Reload after every failed Reader load | Empty failed model, then correct values from a valid model in the same process |
| Shared-reader controls | LS-DYNA integer/real/expression node values, native Python bitwise `&`, standalone title ampersand preserved |
| Engine | Exactly two normal terminations; analytic mass/inertia/motion/energy and all paired histories pass |
| Existing focused regressions | 84 API/export checks, 2 query groups, 27 loading checks, 4 contact checks, 14 original conversion cases, 32 lifecycle/ownership cases and 30 Starter integration checks pass |

Both Engine runs produce mass 1 kg, center `[0.5,0.5,0.5]`, inertia diagonal
`[0.5,0.5,0.5]` and 100 history samples. Maximum position error is
`5.94e-8 m`, distance error `5.96e-8 m`, and energy error `4.16e-10 J`.
Existing tolerances are unchanged: position/distance `3e-5 m`, driven velocity
`3e-4 m/s`, energy `3e-5 J`, and paired histories `rtol=1e-5`, `atol=1e-6`.

[report.json](windows_x64/report.json) retains results and input/binary SHA-256
hashes; [run.txt](windows_x64/run.txt) and
[regressions.txt](windows_x64/regressions.txt) retain the passing runs.
[diagnostics.txt](windows_x64/diagnostics.txt) records the four failed-input
diagnostics. Full generated inputs, listings, restarts and histories are retained
locally under `cbuild_parameter_fix/validation-final/`.

The [pre-fix isolated probes](windows_x64/baseline.json) used source commit
`184be37ac10066237cc624dda44a41f5eb78f1a6`, reader SHA-256
`7bf1ce7e92340be7ccd6b90dfa0a72965b030b7abb26a71478c2cfab9d61785d`.
They showed INT_EXPR returning 0 instead of 1, TEXT remaining literal, an
undefined reference becoming 0, and REAL/REAL_EXPR Starter runs failing during
parameter printing with error 760. The compact equivalent pair now passes.

This covers the tested ExprTk expression syntax and RADIOSS field replacement,
not complete Templex compatibility. Starter's LS-DYNA conversion resolves values
to literals; parameter-preserving export and LS-DYNA CSV parameter syntax are
outside this repair. SP, MPI, Linux and ARM64 parameter validation and hosted CI
execution remain unchecked. Frozen Stage 1-7 evidence is unchanged; the existing
Stage 7 physics/reference and parallel-checksum failures still block release.
