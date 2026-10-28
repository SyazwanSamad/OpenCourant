# Dependency removal: Stage 2 OpenReader coverage

Historical Stage 2 report. [Stage 3](STAGE3.md) retires the live vendor-reader
comparisons and legacy options below; use its commands for the current checkout.

Implemented and validated on Windows x64, double-precision SMP, on 2026-10-28.
The [removal plan](../../doc/Remove_HMReader_H3D_plan.md) retains cross-platform
cutover and release gates. Stage 3 has not started: the bundled reader and both
H3D libraries remain installed and available to the reference checks.
The [Stage 1 baseline](README.md) is unchanged.

## Changes and support decision

- OpenReader implements `IRIGID=2` using connected element-node regions, one
  body and explicit NODE set per region. Component/node order, generated IDs,
  mappings, titles, includes/submodels, and units are checked against v82.
  Mode 1 retains its PART sets and optional mass/inertia/main-node fields.
  Mode 2 does not copy those mode-1-only fields.
- Conversion retains evaluate-before-create, array bounds/range checks, repeat
  behavior, pre-mutation source validation, and rollback on creation failure.
  Evaluation and creation compare the saved mode and region membership.
  An empty element iterator now returns false safely; an unset optional RBODY
  main-node field is handled as zero, while invalid reference types still fail.
- Starter no longer forces the rigid-part bypass for OpenReader. The normal
  executable is tested with successful mode-1 and connected/disconnected mode-2
  inputs. Explicit legacy options remain for older external readers.
- Eight Starter-used API families gained missing canonical/underscore exports;
  existing aliases remain. No public signature was added or changed in Stage 2.
- Structured-ALE generation remains unsupported. There is no OpenReader
  `cpp_sale_mesh_create` implementation and no validated enabled-generator
  baseline here. Native loading now rejects `/ALE/STRUCTURED_MESH` with file/line
  context, including cards in includes, before an unrecognized card can be
  discarded. The reader returns failure through its ABI rather than allowing a
  C++ exception to cross into Fortran. Comment-only references still load.
  CMake also rejects OpenReader with `HM_READER_NO_STRUCTURED_ALE=OFF`.
  Ordinary ALE is separate; the existing 2D ALE comparison still passes.

## Validation

The reader and ordinary Starter were rebuilt with Intel oneAPI 2025.2.0,
MSVC tools 14.44.35215, and CMake 3.31.6-msvc6. OpenReader build ID:
`or_20261028093857_d0a844f7`; bundled v82: `20260918_f907fe76`.
The Engine binary and the 2,495-file configuration tree match Stage 1 hashes.
Integration pairs reuse the same Starter objects and recompile five affected
modules with bounds checking and conversion enabled.

| Suite | Passing checks |
| --- | ---: |
| v82 reference snapshots | 14 |
| OpenReader snapshots, both rigid modes successful | 14 |
| Include/part/model API groups | 5 |
| Loading, failures, unsupported ALE, default Starter | 27 |
| Contact groups and reload | 6 |
| Conversion lifecycle and reference comparisons | 32 |
| Bounds-checked Starter integration | 49 |
| Existing numerical/structural suite | 49 |
| **Total** | **196** |

Additional validation:

- The source-call/export audit passes **84 reader APIs, four spellings each**,
  with 11 local C/C++ calls resolved separately. The guarded structured-ALE
  generator is the sole excluded reader API.
- Conversion comparisons include 18 mode-2 cases: connected/disconnected parts,
  vertex/edge connectivity, reversed element order, empty/shared parts, explicit
  bodies, flags, includes/submodels, units, SHELL, SH3N, BRICK, TETRA4, BEAM,
  and TRUSS. Complete NODE lists are compared, not just counts.
- The existing numerical suite passes 28 Engine runs, 20 structural/error cases,
  and the known v82 unit-loss discrepancy. The unit-preserving OpenReader result
  is checked against an explicitly unit-tagged body.
- **Nine additional mode-2 Engine runs** compare translation, rotation, and
  independently translating disconnected cubes against v82 and explicit bodies.
  Mass, inertia, memberships, analytic motion/energy, and paired histories pass.
  Maximum position error is `1.1921e-7 m`; recorded energy error is zero.
- Five repository models pass paired Starter comparisons: accelerometer,
  TYPE7 friction, three-node shells, 2D ALE, and minimal LS-DYNA contact/include.
  The four native models also pass eight Engine runs with **zero absolute
  difference** between the paired recorded histories. LS-DYNA is Starter-only.
  Four missing-input/include checks exit with code 2 and no restart.
- Four H3D on/off cases, both readers, pass two-segment continuation to 0.1 s.
  H3D Reader still opens the generated files. These are current-build restart
  checks; old-format consumption after H3D removal remains a later-stage gate.
- Configuration with the missing structured-ALE generator enabled fails with the
  intended CMake diagnostic. Both native loader entry points reject root/include
  structured-ALE cards; the complete default Starter exits cleanly with code 2.

Existing tolerances and reference snapshot values were not loosened.
Numerical history decoding uses the existing validated packed-record helper to
avoid the installed history reader's group-offset issue.

## Evidence and reproduction

[Frozen evidence](stage2/windows_dp_smp/manifest.json) records source/binary hashes,
the full suite and numerical reports, paired-deck results, export audit, reader
snapshots, input manifests, logs, and mode-2 inputs/histories. The code changes
are in the working tree based on commit
`d0a844f7270ae3c0666c1360700be42708a7694b`; that commit alone predates Stage 2.
Raw local runs are in ignored `cbuild_dependency_stage2/`.

Use the [reader commands](../reader/README.md) to build integration pairs and run
the individual suites. To repeat the aggregate checks with fresh output paths:

```powershell
python qa-tests/dependency_removal/capture_baseline.py --binaries cbuild_reader_integration --output cbuild_reader_verified
python qa-tests/dependency_removal/compare_decks.py --binaries cbuild_reader_integration --output cbuild_reader_decks
python qa-tests/reader/test_starter_api.py --reader exec/open_reader_win64.dll --reference extlib/hm_reader/win64/hm_reader_win64.dll --output cbuild_reader_api.json
```

The aggregate runner retains its original name but now executes the current
positive mode-2 contracts. It does not rewrite the frozen Stage 1 evidence.
The separate mode-2 numerical command is in the reader README.
Windows CI includes the export audit and updated positive conversion checks;
hosted execution has not been run.

## Remaining gates

Linux x64/ARM64, SP, MPI/R2R, the full applicable miniqa matrix, every element
formulation, and large-model performance remain unverified. Windows results are
not evidence for those configurations. Enabling structured-ALE generation would
require implementation and coordinate/connectivity/ownership/Engine validation
before claiming support. HM Reader/H3D removal and clean-package dependency
absence checks belong to later stages.
