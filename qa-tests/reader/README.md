# Reader regression tests

## Converted contact groups

```powershell
python qa-tests/reader/test_contact_groups.py --reader exec/open_reader_win64.dll --reference extlib/hm_reader/win64/hm_reader_win64.dll --starter exec/starter_win64.exe
```

Six checks cover the small LS-DYNA `SSTYP=6` (all parts minus a part set) contact,
generic sets used as both surfaces and lines, explicitly typed node groups,
selection preservation, reload, and a complete TYPE25 Starter restart. The native
and converted group-use results match v82. The fixtures need only Python's
standard library and are included in Windows CI. The production-model failure,
fix, and comparison with the default Starter are recorded in
[the R66 benchmark](../../doc/OpenReader_R66_benchmark.md).

## Configuration and model loading (Stage 2)

`test_model_loading.py` checks the actual OpenReader library in a fresh subprocess
per case. Python's standard library is sufficient. Build OpenReader first and
run from the repository root:

```powershell
python qa-tests/reader/test_model_loading.py --reader exec/open_reader_win64.dll
```

To include the complete Starter checks, initialize the Intel/MSVC runtime
environment, rebuild Starter, and add its path:

```powershell
python qa-tests/reader/test_model_loading.py --reader exec/open_reader_win64.dll --starter exec/starter_win64.exe
```

On Windows x64, all 18 checks pass:

- `cpp_build_model` and `cpp_build_model_inc` both load ordinary and rigid-part
  fixtures using profile 2612. Native loading and entity output preserve `IRIGID`.
- Both entry points return failure for an unregistered profile, incomplete
  configuration, missing configuration, and a nonexistent input file.
- LS-DYNA initialization succeeds for a minimal keyword deck and reports failure
  for an unsupported Radioss target profile or missing keyword file.
- The accelerometer Starter case exits successfully, reports zero errors, and
  writes a nonempty restart. Its existing shell-formulation warning 680 remains.
- A complete Starter run with broken configuration exits with code 2 and a readable
  reader diagnostic instead of a native exception or a query of a null model.
- A complete Starter run requesting `IRIGID=1` exits with code 2 and the Stage 1
  part diagnostic while conversion remains disabled.

The runner creates isolated temporary configuration/input directories and limits
each subprocess to 30 seconds (60 seconds for the accelerometer smoke test).
It leaves the repository's inputs and configuration unchanged. The configuration
failure cases supply just the units/messages needed to reach the intended failure.

The profile enum, maps, inheritance, descriptor fallback, and entity writer now
recognize 2612. Failure results are checked before Starter performs model queries.
The bundled external reader ABI is retained; Irigid conversion is still bypassed
and guarded for OpenReader pending mode-2 implementation and validation.

These checks do not validate Engine results, production LS-DYNA conversion,
or Linux/ARM builds. Stage 3 adds focused successful-reload coverage below.

## Irigid conversion reference (Stage 1)

See [rigid_parts/README.md](rigid_parts/README.md) for the 14 v82 reference fixtures,
recorded conversion contract, and isolated bounds-checked guard driver. Those
reference snapshots can now also be checked against OpenReader using the same
runner and `--reader exec/open_reader_win64.dll --openreader`. This checks twelve
matching snapshots and explicit rejection of the two unimplemented mode-2 cases.

## Irigid conversion implementation (Stage 3)

```powershell
python qa-tests/reader/rigid_parts/test_reader_contract.py --reader exec/open_reader_win64.dll --openreader
python qa-tests/reader/rigid_parts/test_openreader_conversion.py --reader exec/open_reader_win64.dll --reference extlib/hm_reader/win64/hm_reader_win64.dll
```

The first command checks twelve recorded v82 snapshots and two mode-2 rejections.
The second checks seven
lifecycle/error scenarios and compares five additional ownership, units, offset,
and solid-part fixtures against v82. It verifies all exported symbol spellings and
puts canaries around arrays used for evaluation, creation, repeat calls, and reload.
The additional comparisons require the pinned v82 library. OpenReader deliberately
preserves an explicit source unit ID where v82 generates unit ID zero; values are
copied without rescaling. Other queried data must match.

The conversion APIs require evaluation before creation on each loaded model.
Invalid call order, changed/deleted parts, and missing references fail with a native
diagnostic and exit code 1. This prevents use of an incomplete conversion through
the existing void ABI. The ABI has no array-capacity argument, so callers must
allocate the evaluated sizes. Successful repeat calls return the original mapping
and IDs without creating more entities.

The default Starter bypass remains active. These checks do not enable production
rigid-part simulation or establish physical mass/inertia behavior.

## Starter integration (Stage 4)

Build OpenReader and Starter first. With an initialized Windows Intel/MSVC command
prompt and Starter's CMake compile database enabled, run:

```powershell
python qa-tests/reader/rigid_parts/build_integration.py --starter-build starter/cbuild_starter_win64_ninja --output cbuild_openreader_stage4
python qa-tests/reader/rigid_parts/test_starter_integration.py --reader exec/open_reader_win64.dll --binaries cbuild_openreader_stage4
```

The builder reuses the existing object files, recompiles the five affected modules
with bounds checking and conversion enabled, and links separate OpenReader/v82 test
executables. It writes into the requested output folder, leaving the default
Starter executable and its bypass intact. The integration runner performs 39 checks
covering native helper behavior, shell connectivity/owners, Fortran array canaries,
body ordering, invalid calls, and sixteen successful complete Starter runs.

Stage 4 corrected malformed element headers in the earlier reader-only fixtures.
With valid connectivity, v82 converts `IRIGID=2` by connected region; it does not
ignore that flag. OpenReader rejects it explicitly pending implementation. The
two reference snapshots were updated from reviewed v82 results; the other twelve
remain unchanged. Mode 1 is validated through Starter, including the existing
explicit RBODY/ROTA model. Engine motion/energy tests, runtime R2R filtering, and
cross-platform builds remain outside these checks.

## Numerical validation (Stage 5)

Build the serial double-precision Engine from the current checkout with the
initialized Intel/MSVC/MKL environment. For a direct CMake/Ninja build, set
`arch=win64`, `precision=dp`, `MPI=smp`, `EXEC_NAME=engine_win64`, and `debug=0`,
and use the installed `ifx`/`icx` compilers. Build the Stage 4 isolated Starter
executables using the commands above, then run:

```powershell
python qa-tests/reader/rigid_parts/test_numerical.py --binaries cbuild_openreader_stage4 --engine exec/engine_win64.exe --output cbuild_openreader_stage5
```

The runner uses the existing NumPy and `vortex_radioss.animtod3plot.RadiossTHReader`
modules. It needs no CSV converter. The installed history reader misplaces group
offsets for the current Engine's 23-global-variable output, so the runner uses its
packed data with checked record lengths for these fixed test layouts. It does
not change the installed package. The JSON report records the reader's source hash.

All 49 checks pass on Windows: 28 Engine runs, twenty structural/error cases, and
one documented v82 unit-loss discrepancy. The Engine cases compare generated
OpenReader/v82 bodies with explicit v82 controls and analytic motion/energy, with
an additional comparison against the existing RBODY/ROTA model. The nine cube
cases exercise translation, automatic main nodes, rotation, force, submodel
offsets, sensor release, delayed loads, added inertia/skew, and alternate units.
The units case uses an explicitly unit-tagged v82 body as the physical reference;
the v82 generated body is known to drop that unit ID.

Each Engine run lasts 0.1 seconds with maximum time step `1e-4` seconds. Position
and distance tolerance is `3e-5` m, driven velocity tolerance is `3e-4` m/s, and
energy tolerance is `3e-5` J. The recorded maxima are `6.68e-8` m distance error,
`2.45e-6` m position error, and `2.46e-6` J energy error. Model geometry and the
eight lumped nodal masses give independent mass, center, and inertia expectations.
Empty-part rejection is checked under Starter bounds checking and leaves no
restart. An empty group now produces a readable error instead of indexing an
empty secondary-node array.

The output folder retains generated inputs, logs, histories, restart files, and
`report.json`; each run uses fresh case directories. `--case` selects one numerical
case during investigation. The default bypass is unchanged. Mode 2, MPI/R2R,
Linux/ARM, and broader production-model validation remain outstanding.

## API alignment and rollout (Stage 6)

```powershell
python qa-tests/reader/test_model_queries.py --reader exec/open_reader_win64.dll --reference extlib/hm_reader/win64/hm_reader_win64.dll
```

This standard-library runner checks all four export spellings for the include
count, indexed include lookup, and part-element query. Native nested includes,
long names, submodel placeholders and offsets, and empty/filled parts are checked
against v82. It checks resolved paths, space padding, truncation, array canaries,
and preservation of the active entity and iterator. OpenReader-only checks cover
invalid IDs/indices, zero-sized buffers, the legacy bulk-list allocation, successful
reload, original nested LS-DYNA include paths (including `*INCLUDE_TRANSFORM`),
and failure without stale entities.
The v82 converter does not return success for this minimal keyword fixture, so
keyword paths use known fixture paths as their oracle; no v82 keyword comparison
is claimed.

The include-count ABI is now
`cpp_get_number_of_include_files(int *is_dyna, int *count)`, matching Starter and
the bundled reader. It assigns the count and leaves the input flag unchanged.
Callers of OpenReader's former one-argument export must update their declaration;
all in-tree callers already use two arguments. Indexed lookup is one-based,
writes a space-padded fixed-width buffer, truncates to its capacity, and returns
blanks for invalid indices. Synthetic submodel entries retain v82's count/order
and empty filename. LS-DYNA lookup selects the original keyword include model;
native lookup selects the current Radioss model. Reload/failure clears that source.

Starter no longer automatically enables the legacy include/part fallbacks.
Their explicit CMake options remain available for older external readers.
The rigid-part bypass remains automatic because mode 2 has not been implemented;
Stage 5 validates mode 1, and cannot satisfy that remaining rollout gate.
The structured-ALE restriction is unchanged.

[OpenReader Windows CI](../../.github/workflows/openreader_ci.yml) builds the
in-tree reader and Starter on relevant pull requests and manual dispatch. It runs
this export/API check, loading and Starter smoke checks, both reader conversion
suites, and bounds-checked Starter integration against v82. These steps require
only Python's standard library. The Stage 5 numerical runner remains a separate
local check using the installed history reader. CI YAML is checked locally, but
the hosted job must run after submission; Linux x64 and ARM builds are not yet
validated.
