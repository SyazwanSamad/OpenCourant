# Dependency removal: Stage 5 H3D functionality removed

Stage 5 is implemented and validated on Windows x64, double precision, on
2026-10-28. Starter and Engine no longer contain H3D SDK bridges, loaders, writer
or reader integration. Native outputs and Python queries remain available.
This is a Windows validation result; the complete release gate remains open.

## Resulting behavior

- `/H3D` requests fail with a diagnostic before integration. The native reader
  reports file/line context for direct and included/embedded cards; Engine
  reports the input line and keyword. H3D report options, the STOP sensor output
  flag, positive FVMBAG H3D flags, TYPE21 `Pskid`, and H3D control-file requests
  also fail explicitly. Unrelated fields on these mixed cards remain intact.
- Use existing `/ANIM`, `/TFILE`/`/TH`, `/STATE`, and `/DYNAIN` outputs as
  appropriate. There is no automatic keyword translation or replacement H3D
  implementation. Skid-line and FVMBAG H3D-specific requests have no automatic
  equivalent. FVMBAG flags that disable the retired output remain accepted.
- Ordinary HTML reports and native MVW references remain. H3D viewer embeds,
  generated H3D links, file discovery, and checksum import are removed. Native
  animation and history checksums still work, even with an old `.h3d` file in
  the directory; that file is ignored.
- Old checkpoints continue without resuming H3D output. A checkpoint whose
  retired output count is nonzero prints that the output is not resumed.
  Remove H3D requests from its continuation input before running it.

## Implementation and compatibility

The residual `engine/source/output/h3d/` and `common_source/output/h3d/` trees,
`h3d_mod.F`, and `h3d_inc_mod.F` are deleted. All callers, parameters, compiler
include paths, and deleted-source flag entries follow the removal. Initialization,
scheduling, gathers, writes, finalization, and the checksum reader are removed;
no success-returning writer stub remains. OpenReader remains the sole model reader.

Shared allocation and collection predicates retain native animation, OUTP, time
history, sensor, reaction, failure, friction, and coupling demand. The native
contact-force maximum and its MPI reduction remain. Writer-only extrema, skid
buffers/arguments, normalized-friction results and their dedicated communication
are retired. Shared FVMBAG visualization counters have neutral names; SPH names
such as `ISPH3D` retain their independent meaning. Python quantity names and the
Stage 4 calculation bodies are unchanged.

Removing the Starter H3D parser also removes its incidental initialization of
generic element-buffer counters. `INI_OUTMAX_AUTO` now initializes those six
reserved counters directly to zero; nodal extrema counts have explicit zero
defaults. Fresh Starter runs therefore retain the original buffer layout without
allocating the parser's selection arrays. Native extra-cycle handling retains
the coupling stop condition after removal of the H3D state machine.

Restart writers retain numbered reserved slots and widths. Readers consume old
request counts and payloads before discarding retired output data. A bounded
`DISCARD_RESTART_REALS` helper uses the existing checked IEEE/gzip reader instead
of seeking over assumed record sizes. Old contact-pressure lengths use the
actual local/global nodal dimensions. Generic result-buffer layouts needed to
consume and rewrite old checkpoints remain compatible; the H3D database is not
renamed into a replacement type.

Slot `TABVINT(294)` preserves the animation tens digit and discards the retired
H3D units digit. The frozen pressure fixture starts at `11`; the new solver writes
`10` and retains `10` through another continuation. Native flag fields are not
shifted into the retired position.

The dependency archive and ignored SDK payload are still present locally. Their
filtering, replacement pin, cache cleanup, launch/package plumbing and release
artifact checks are Stage 6. Source integration removal does not establish a
clean delivery chain by itself.

## Verification

Starter, SMP Engine and Intel MPI Engine build with the existing Windows Release
configuration: Intel ifx/icx 2025.2, MKL 2025.2, VS 2022 and Intel MPI 2021.16.
OpenReader build ID is `or_20261028155058_d0a844f7`. Integration tests separately
recompile the five existing integration modules with bounds checking. Runtime
checks use one thread per process; MPI checks use two local ranks.

| Check | Result |
| --- | --- |
| Existing reader/integration/numerical suites | All 148 checks pass, including six mode-2 Engine cases and same-build continuation |
| Repository decks against frozen Stage 1 | Five model comparisons; four Engine histories match exactly; both failed-input checks pass |
| Shared scalar source checks | Preserved arithmetic/helper/parser/Python bodies pass; SDK source trees/includes and integration symbols are absent |
| Binary and build-graph audit | Starter, SMP/MPI Engine and OpenReader have no SDK library names or SDK imports/exports; all three build graphs exclude H3D sources and include paths |
| Shell, triangle, quad and solid query-driven loads | Serial and two-rank MPI query samples and complete histories match their respective Stage 4 baselines exactly |
| Two-rank accelerometer and friction decks | Histories match exactly; decompressed native animation bytes match exactly, including added contact pressure, forces and nodal external-pressure output |
| Removed/native output behavior | 15 cases pass: direct, included, embedded, report, sensor, mixed-card and control-file diagnostics; native HTML/animation/history/checksums; termination without animation |
| Native STATE/DYNAIN | Output contents match Stage 4 after comment metadata is excluded; histories and invalid-keyword exit codes remain consistent |
| Old checkpoint continuation | Six old serial checkpoints pass with identical histories, including retired extrema payloads and packed pressure flags; both extended cases also pass a subsequent continuation from the new checkpoint |
| Discard helper | Compiled check passes for zero length, partial/multiple chunks, and negative-length rejection |

Every reported query/history maximum difference is zero. Comparisons retain the
existing tolerances (`rtol=1e-5`, history `atol=1e-6`, query `atol=1e-8`). Native
checksum digests are independently checked against Python MD5 of the animation
and history files. Input hashes, binary/build identities, reports, comparison
arrays and logs are retained in [the evidence manifest](stage5/windows_dp_smp/manifest.json).
Historical Stage 1-4 evidence is unchanged.

## Reproduction

Use the existing oneAPI/VS shell and Python 3.11 with the existing NumPy and
`vortex_radioss` packages. Set `RAD_CFG_PATH` and `RAD_PYTHON_PATH` as in the
[reader test instructions](../reader/README.md). Use fresh output directories.

```powershell
python qa-tests/dependency_removal/test_shared_result_sources.py
python qa-tests/dependency_removal/test_restart_discard.py --output cbuild_discard
python qa-tests/dependency_removal/test_removed_output.py --engine exec/engine_win64.exe --output cbuild_removed_output
python qa-tests/dependency_removal/test_old_checkpoints.py --engine exec/engine_win64.exe --output cbuild_old_checkpoints
python qa-tests/dependency_removal/test_shared_results.py --engine exec/engine_win64.exe --output cbuild_shared_smp
python qa-tests/dependency_removal/test_shared_results.py --engine exec/engine_win64_impi.exe --ranks 2 --output cbuild_shared_mpi
python qa-tests/dependency_removal/test_output_keywords.py --engine exec/engine_win64.exe --output cbuild_native_outputs
python qa-tests/dependency_removal/test_native_mpi.py --engine exec/engine_win64_impi.exe --output cbuild_native_mpi
```

For comparisons, unpack Stage 4 `query_values.zip` and pass its `queries-final`
or `queries-mpi-after` directory as `--baseline`. Stage 5 `native_mpi_values.zip`
contains `native-mpi-pressure-before` for `test_native_mpi.py --baseline`.
Stage 4 `native_outputs.zip` contains `outputs-final` for the native keyword
comparison. The checkpoint test reads frozen archives directly. The existing
reader instructions reproduce the 148-check suite and repository-deck checks.

## Remaining gates

Linux x64/ARM64, single precision, hosted CI, multiple OpenMP threads, broader
MPI/R2R and old multi-domain checkpoints, implicit/modal and coupled/user-library
workflows, all material/formulation branches, full miniqa, and large-model
performance remain unverified. The coupling stop branch has a control-flow
self-check; an actual coupled run was not exercised. Final package/container
absence and clean/stale dependency-cache behavior remain Stages 6-7 gates.
