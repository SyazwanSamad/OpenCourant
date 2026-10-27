# R66 Starter comparison and contact-group fix

Validated on Windows x64 on 2026-10-27 with the supplied `Main_0000.rad` and
`Main_combine.key`. The original project was left unchanged. Separate copies in
`cbuild_openreader_diagnosis/r66_benchmark/` retain console logs, listings,
restart files, input hashes, `benchmark.json`, and `comparison.json`.

## Failure and cause

The default Starter in `C:/OpenRadioss` succeeds. OpenReader initially exits with
code 2 and error 2087: contact 1 (`Single Surface`) references undefined group 20.
The model's LS-DYNA contact uses `SSTYP=6`: all parts except part set 10. Conversion
correctly creates `/SET/GENERAL/20` containing `ALL` minus that set.

The error occurs later in group-use classification, not rigid-part conversion.
`/INTER/TYPE25` accepts both `/SETS/LINE` and `/SETS/SURF` for its contact group.
The in-tree `P_SDIGetGroupType` stopped after the first allowed subtype and left
the group classified only as a line. `FILL_IGR` therefore omitted its surface,
and interface reading could not resolve group 20.

`RadiossblkIsGroupUsed` now records every allowed subtype for a generic reference,
while preserving explicitly typed references and unknown-type handling. Its
cached group-use data is cleared on model read/creation, so reload does not reuse
the previous model's references. No contact, set, geometry, or material input was
changed; the rigid-part bypass remains unchanged.

## Starter benchmark

Each invocation used `starter_win64.exe -i Main_0000.rad -np 8`,
`OMP_NUM_THREADS=1`, and `KMP_STACKSIZE=400m`, with the installation's configuration
and library paths. Times are single-run wall-clock observations, not statistical
performance measurements. No Engine simulation was run.

| Starter / reader | Time | Exit | Errors | Warnings | Restart files |
| --- | ---: | ---: | ---: | ---: | ---: |
| `C:/OpenRadioss`, default reader | 9.62 s | 0 | 0 | 6 | 8 |
| OpenCourant, OpenReader before fix | 17.28 s | 2 | 2 | 2 | 0 |
| OpenCourant, OpenReader after fix | 18.41 s | 0 | 0 | 5 | 8 |
| Current Starter integration build, bundled v82 | 9.69 s | 0 | 0 | 6 | 8 |

The current-Starter v82 control uses the isolated integration executable, with
bounds checking in the five rigid-body integration modules. It confirms that
the result is not specific to the older `C:/OpenRadioss` Starter. OpenReader is
about 1.9 times slower in these observations; performance tuning is separate work.
The final installed binaries were checked again in `openreader-verified/` with
eight restarts and zero errors. That verification ran alongside other QA and took
28.27 seconds, so it is excluded from the timing comparison above. Its artifact
hashes and comparison assertions are retained in the JSON records.

## Initialization comparison

OpenReader and both default-reader controls report the same model counts:

| Quantity | Count |
| --- | ---: |
| Parts | 10 |
| Materials / properties | 3 / 3 |
| Nodes | 667,479 |
| Four-node shells | 667,262 |
| Three-node shells | 3,529 |
| Interfaces | 1 |
| Input rigid bodies | 4 |

All printed rigid-body initializations (IDs 1, 2, and 4 after body merging) match
the reference masses, centers, inertia tensors, and sorted secondary-node lists.
The eight generated restart files are nonempty. This checks initialization and
connectivity, not restart byte identity or subsequent Engine dynamics.

OpenReader's remaining warnings are the same material/integration and initial
contact-penetration warnings present in the controls: 1084 (twice), 1167, 1633,
and 343. The default reader additionally warns about an unsupported `/IOFLAG`
field (100214). Initial contact penetrations remain a model condition to review.

## Regression

The small two-shell fixture in `qa-tests/reader/contact_groups/` reproduces the
same `SSTYP=6` contact and requires both surface and line usage, while leaving node
and part group usage false. The regression also checks an explicitly typed node
group, selection preservation, model reload, and a complete Starter restart:

```powershell
python qa-tests/reader/test_contact_groups.py --reader exec/open_reader_win64.dll --reference extlib/hm_reader/win64/hm_reader_win64.dll --starter exec/starter_win64.exe
```

All six focused checks pass. The test is included in OpenReader Windows CI.
The earlier suites also pass after rebuilding: five API groups, 14 v82 reference
snapshots, 14 OpenReader contract checks, 12 lifecycle/comparison checks, 18 loading
and Starter smoke/guard checks, 39 Starter integration checks, and all 49
numerical/structural checks. The hosted workflow enables compile-database output
before the initial build, avoiding a second CMake configure that could trigger
the observed compiler-path cache reset.
Engine dynamics, MPI execution, Linux/ARM, and hosted CI are outside this benchmark.
