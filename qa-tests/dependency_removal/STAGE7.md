# Dependency removal: Stage 7 Windows regression gate

**Gate: failed. No solver release is approved.** Windows x64 verification was
performed on 2026-10-28. Linux x64 and ARM64 verification is deferred at the
user's explicit request. This report supplements [Stage 6](STAGE6.md), rather
than changing its frozen evidence.

The working branch is `openreader`, based on
`2fef8dac61deaec2367d12a1bf0f35f188a16ad1`, with the Stage 6/7 changes still
uncommitted. No solver release, hosted workflow, commit or push was performed
in Stage 7. The clean dependency pin remains the published
`v82-openreader-1` artifact recorded in Stage 6.

## Regression results

All 81 cases from the existing legacy MiniQA list are registered with CTest.
The omitted Python-function and two TYPE25 cases were added; the TYPE25 local
tolerance rules were copied verbatim from `or_QA.files_1miniqa` into their JSON
configurations. Reference values and existing tolerance values were not changed.

| Windows configuration | Passed | Skipped | Failed |
| --- | ---: | ---: | ---: |
| DP SMP, two OpenMP threads | 79 | 0 | 2 |
| DP Intel MPI, two ranks and two threads per rank | 79 | 0 | 2 |
| SP SMP, two OpenMP threads | 72 | 3 | 6 |
| SP Intel MPI, two ranks and two threads per rank | 72 | 3 | 6 |
| DP parallel arithmetic, layouts `1x4`, `2x2`, `4x1` | 63 | 3 | 15 |

CTest counts the runner's configured skips as successes. The table subtracts
them: SP skips are `1.01`, `1.42`, `1.87`; parallel-arithmetic skips are
`1.80`, `1.87`, `1.88`. The parallel-arithmetic result combines the original
78-case run and the three added cases. Each executed case compares the last
checksum across all three layouts.

### Regression findings

- **LAW13, `1.19`:** internal energy is NaN from the first printed cycle, despite
  normal termination. Time step, energy and external work also miss the reference.
  Both precisions and both launch modes fail. All four current/pre-Stage-5 DP
  Starter/Engine pairings reproduce the NaN. It predates Stage 5 and is recorded
  as a legacy compatibility failure. Altair lists LAW13 as obsolete since v13.0
  and defines obsolete keywords as supported but no longer maintained; see
  [the obsolete-keyword list](https://help.altair.com/hwsolvers/rad/topics/solvers/rad/obsolete_overview_starter_r.htm)
  and [LAW13 reference](https://help.altair.com/hwsolvers/rad/topics/solvers/rad/mat_law13_rigid_starter_obsolete_r.htm).
  This does not establish OpenCourant's support policy or authorize accepting NaN.
  The test and its recorded result are retained; no solver change is made here.
- **EBCS/INIV, `1.59`:** DP mass error is `-1.85e-16` in SMP and `-3.701e-16`
  in MPI, against reference `-0.9946e-12`. The existing Python zero tolerance
  `5e-14` sends this near-zero comparison through its relative rule, which fails.
  The legacy Perl zero rule differs. Neither rule nor the reference was widened
  to turn the test green.
- **Additional SP reference failures:** `1.09` (INT7 element deletion, rotational
  kinetic energy), `1.10` (INT7 small ball, time step), `1.64` (SPH compression,
  kinetic energy), `1.68` (EOS_PUFF_2, error/internal energy/external work), and
  `1.71` (LAW58 quads, error/internal energy). SMP and MPI fail the same cases.
  No pre-removal SP executable was available for a valid comparison.
- **Parallel checksums:** `1.03`, `1.05`, `1.06`, `1.16`, `1.19`, `1.32`, `1.34`,
  `1.38`, `1.44`, `1.48`, `1.51`, `1.55`, `1.71`, `1.90`, `1.91` differ between
  layouts. Every failing checksum triplet exactly matches the corresponding
  pre-Stage-5 binary triplet. All compared runs terminate normally. These failures
  predate H3D output removal; some affected decks explicitly contain `/PARITH/ON`.

The runner now reports integer mismatches without crashing, rejects missing
checksums instead of treating them as zero, uses the local Windows MPI launcher,
and reports layout mismatches without falsely asserting that the deck lacks
`/PARITH/ON`. Small regression checks cover the changed helpers and the copied
legacy rules; the Windows reader workflow includes those checks.

## Checks that passed

- The existing **149-check DP OpenReader suite**, including API/query/loading,
  rigid conversion, affected Fortran bounds checks, analytic motion/energy and
  same-build continuation. The SP Starter separately passes **31 loading/contact
  checks**.
- Native animation/history, STATE and DYNAIN comparisons; invalid native-output
  diagnostics; native animation/history MD5 reporting. **15 removed-output cases
  pass in each precision**, including embedded/include, mixed-card and control-file
  requests, with nonzero rejection before integration.
- **Eight old serial checkpoint continuations**, including retired output payloads
  and packed-pressure record alignment. **Four old MPI continuations**, two/four
  ranks and two successive segments, match the pre-Stage-5 histories with maximum
  difference **zero**. The second segment reads a checkpoint written by the current
  Engine. The MPI fixtures have retired output disabled; the serial fixtures cover
  retired nonzero payloads. MPI continuation is not an R2R coupling test.
- Fresh Windows **SP Starter, SMP Engine and Intel MPI Engine** release builds.
  Together with the Stage 6 DP builds, **seven binaries and six compile graphs**
  pass SDK-name, PE import/export and include/source inspection. The toolchain is
  VS 2022, ifx/icx 2025.2, MKL 2025.2 and Intel MPI 2021.16. Engine release commands
  use `O3`, precise floating-point behavior and disabled FMA contraction; exact
  commands/settings are frozen with the evidence.
- A local SP/DP Windows package with **2,568 files**, OpenReader, native converters,
  CFG/messages, retained notices and the published pin passes the package guard.
  **Eight isolated SMP/MPI runs** have finite histories and maximum comparison
  difference **zero**. DP uses the frozen physical references; SP checks packaging
  invariance against the in-tree SP executables. SP package checks do not change
  the MiniQA SP exclusions or approve their physics. Two-rank animation bytes,
  native converters and removed-output rejection also pass.
- Loaded-module inspection for **22 packaged commands** finds no retired SDK.
  Their runtime path contains only packaged executables/runtime files and Windows
  system directories. Compiler/SDK installation paths are excluded. This is PATH
  and loaded-module isolation on the current host, not a fresh operating system.

Clean/stale/public-download cache validation remains the frozen Stage 6 evidence;
Stage 7 does not republish or change the dependency archive. Final payload scans
cover tracked/ignored workspace files and ZIP contents.

## Evidence and reproduction

The [gate report](stage7/windows_x64/gate_report.json) contains the suite counts,
and the [manifest](stage7/windows_x64/manifest.json) hashes the reports, JUnit files,
logs, commands, input/source snapshots, build settings and numerical arrays.
The new [old-MPI fixture](stage7/windows_x64/old_multidomain_checkpoints.zip)
contains genuine pre-Stage-5 checkpoints, reference arrays and binary provenance;
it contains no reader/SDK executable.

In an initialized Windows compiler/MPI environment, use the existing CMake/CTest
runner with `arch=win64`, `PREC=dp` or `sp`, `MPI=smp` or `impi`, `NT=2`, and `NP=1`
or `2`. Use `type=default` for reference comparisons; use `type=pon` and
`pon_run=1x4,2x2,4x1` for parallel arithmetic. Keep `I_MPI_FABRICS=shm` and the
existing Python runtime path for local execution. The frozen reproduction
commands give the exact configurations; failing suites correctly return nonzero.

```powershell
python qa-tests/dependency_removal/test_qa_comparison.py
python qa-tests/dependency_removal/test_old_multidomain.py --engine exec/engine_win64_impi.exe --output cbuild_old_mpi_check
```

The intermediate tracked repository copyright audit reports **1,018 header
problems**. Five changed QA files were subsequently corrected; the remaining
**1,013 findings** are in files unchanged from HEAD during this stage and were
not mass-rewritten. Notices for the changed QA files preserve the original
copyright and add the OpenCourant modification block; the nine-file changed-source
audit passes.

## Remaining release gates

Resolve the active reference and parallel-checksum failures using the existing
physical assertions, and record the compatibility decision for obsolete LAW13.
Verify R2R external coupling, implicit/modal execution,
external coupled/user-library execution and large-model performance. Hosted CI
was not dispatched. Linux x64/ARM64 package/container/runtime checks remain
deferred at the user's request. These outstanding checks and the failures above
prevent a complete Stage 7 release sign-off.
