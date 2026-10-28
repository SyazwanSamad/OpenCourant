# Dependency removal: Stage 4 shared solver behavior

Historical Stage 4 capture. [Stage 5](STAGE5.md) removes H3D functionality and
records current commands and limits. The H3D-positive commands below describe
the old test interface; they are no longer supported by the current scripts.

Stage 4 is implemented and validated on Windows x64, double precision, on
2026-10-28. Shared scalar calculations, Python queries, native output parsing,
and shared helpers no longer depend on the H3D writer implementation. H3D output
and its SDK remain active until Stage 5. This is not a cross-platform release
sign-off.

## Changes and affected surfaces

- The shell/triangle, solid, and quad calculations move from the three
  `h3d_*_scalar_1` routines into `engine/source/tools/element_results/` as
  `RESULT_SHELL_SCALAR`, `RESULT_SOLID_SCALAR`, and `RESULT_QUAD_SCALAR`.
  Existing arithmetic, material/layer/integration selectors, validation, and
  ordering are preserved. The routines return values and validity metadata;
  writer part selection, element IDs, light filtering, stack writes, and scalar
  storage stay in the existing H3D callers. No duplicate calculation path is
  introduced.
- `funct_python_update_elements.F90` calls the neutral routines directly. Its
  writer scratch buffers and unused part arguments are removed, including both
  callers in `resol.F` and `resol_alloc.F90`. The internal Python keyword field
  becomes `%result`; public quantity names and packing widths/order remain
  unchanged in registration, the element module, and MPI synchronization.
- `redkey1_h3d.F` becomes `redkey1_output.F`, called by `freform.F`. Its executable
  parser body is unchanged. `/ANIM`, `/STATE`, `/DYNAIN`, `/DAMP`, and the live
  H3D dispatch remain available; Stage 5 will remove H3D dispatch with explicit
  unsupported-feature diagnostics.
- Five contact extrema helpers move to native animation's `generate/` directory.
  The thick-shell coordinate transform `CLSYS3` moves to element tools, and
  `SPMD_SUM_R_NODAL_21` moves to MPI output. Their bodies and all callers are
  preserved, including native contact output and interface-21 contributions.
  Compiler lists, GNU legacy flags, and caller metadata follow these moves.
- The H3D database audit records 67 original members and 2,652 direct component
  references. Only the unreferenced root fields `SH_IEPSDOT` and `IS_CORNER_DATA`
  are deleted, leaving 65 members with the same references. Active corner-data
  fields on keyword/output types remain. Active writer state is retired with
  the writer in Stage 5; shared buffers keep their existing owners. Collection
  predicates, friction/contact demand, and restart record widths are unchanged,
  including the animation/H3D digits sharing `TABVINT(294)`.
- A standard-library source check is added to Windows build CI. It checks the
  preserved arithmetic/helpers/parser/Python bodies and the dependency boundary.
  Numerical and SDK checks remain local tests. No dependency is added.

## Verification

The final Starter, SMP Engine, and Intel MPI Engine build successfully with Intel
ifx/icx 2025.2, MKL 2025.2, VS 2022, and Intel MPI 2021.16. Production builds use
the existing release settings. The reader integration helper separately rebuilds
five integration modules with bounds checking. OpenReader build ID is
`or_20261028121134_d0a844f7`. Binary hashes, settings, source hashes, inputs, logs,
and reports are frozen in [the evidence manifest](stage4/windows_dp_smp/manifest.json).

| Check | Result |
| --- | --- |
| Existing reader/integration/numerical regression | 148 passing checks, including six mode-2 Engine cases and same-build restarts |
| Repository decks against frozen Stage 1 | Five model comparisons, four Engine runs with identical histories, two failed-input checks |
| Python query feedback into loads, SMP | Shell, triangle, quad, solid; all query samples and packed histories exactly match pre-refactor results |
| Python query feedback into loads, two Intel MPI ranks | Same four families; query samples and packed histories exactly match the pre-refactor MPI executable |
| Shared source preservation | Three check groups pass, including unchanged scalar arithmetic and MPI reduction/synchronization bodies |
| Native parser/output | STATE for solids and DYNAIN for shells produce the same output contents after comment metadata is removed; histories match; animation files exist; invalid requests retain exit code 2 |
| Retained H3D scalar writer | Four families run with DENS/MASS/SIGEQ requests; generated files import, string tables match, and query/history comparisons remain exact |
| Frozen pre-removal checkpoints | Four continuations from both original reader origins, with H3D off/on; all 50-sample histories match exactly and final checkpoints are written |

Python traces include time, density, masses and equivalent stresses for two
elements, and plastic strain. The solid case also checks independent element and
total mass. Comparisons use the existing history tolerances (`rtol=1e-5`,
`atol=1e-6`) and query tolerances (`rtol=1e-5`, `atol=1e-8`); every reported maximum
difference is zero. SMP and MPI are each compared with their own old executable,
not with each other. Non-H3D runs point the H3D loader at an absent directory;
source checks establish that shared calculations contain no H3D calls.

The H3D check covers writing/import and string tables, not complete numerical
comparison of SDK dataset payloads. Python packing helpers retain their old
layout; their inactive serialization callers were not enabled or given a new
format. Checkpoint compatibility is established by the actual continuation
tests, not a claim that those inactive helpers were exercised.

## Reproduction

Use a configured oneAPI/VS shell with Python 3.11, NumPy and the existing
`vortex_radioss` history reader. Set `RAD_PYTHON_PATH` to `python311.dll` and
`RAD_CFG_PATH` to the repository's `hm_cfg_files`. Use fresh output directories.

```powershell
python qa-tests/dependency_removal/test_shared_result_sources.py
python qa-tests/dependency_removal/audit_h3d_shared_state.py --output cbuild_state_audit.json
python qa-tests/dependency_removal/test_shared_results.py --engine exec/engine_win64.exe --output cbuild_shared_smp
python qa-tests/dependency_removal/test_shared_results.py --engine exec/engine_win64_impi.exe --ranks 2 --output cbuild_shared_mpi
python qa-tests/dependency_removal/test_shared_results.py --engine exec/engine_win64.exe --h3d --output cbuild_shared_h3d
python qa-tests/dependency_removal/test_output_keywords.py --engine exec/engine_win64.exe --output cbuild_native_outputs
python qa-tests/dependency_removal/test_old_checkpoints.py --engine exec/engine_win64.exe --output cbuild_old_checkpoints
```

To repeat comparisons, unpack `query_values.zip` from the evidence directory
into a temporary directory and pass its `queries-before-verified`,
`queries-mpi-before-verified`, or `h3d-before` subdirectory as `--baseline`.
The native comparison baselines are in `native_outputs.zip` under `outputs-before`.
The existing [reader commands](../reader/README.md) reproduce the 148-check
suite and repository-deck comparisons. The old checkpoints already live in
the frozen Stage 1 archive; no external HM Reader binary is loaded by current
tests.

## Remaining gates

Linux x64/ARM64, single precision, hosted CI, broader MPI/R2R behavior, the full
miniqa collection, all material/formulation branches, and large-model performance
remain unverified. Runtime query coverage uses the four listed element families;
source hashes cover preservation of the other calculation branches, not their
runtime correctness. H3D removal and shared demand/restart cleanup are Stage 5.
The filtered dependency artifact, release packages, and cross-platform release
gates remain Stages 6-7. Structured-ALE mesh generation remains unsupported.
