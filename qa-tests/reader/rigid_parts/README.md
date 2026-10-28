# Irigid conversion contract and tests

Current status: OpenReader passes all 14 snapshots and implements both rigid-part
modes. Starter always builds/links OpenReader and conversion is enabled. See the
[Stage 3 report](../../dependency_removal/STAGE3.md) for Windows validation and limits.

Stage 1 reference observations for the bundled extlib v82 reader, build
`20260918_f907fe76`, on Windows x64. The DLL SHA-256 is recorded in `expected.json`.
These are reader-level fixtures; Stage 4 also runs the indicated subset through
Starter. They are not Engine validation models. Stage 4 corrected the element
headers to `/SHELL/<part ID>` and `/BRICK/<part ID>`; earlier fixtures incorrectly
put the part ID in the connectivity row. This correction changed the two mode-2
reference results below. The earlier conclusion that v82 ignores mode 2 was wrong.

## Observed contract

| Input | v82 conversion result |
| --- | --- |
| Missing or zero `IRIGID` | No generated body. |
| `IRIGID=1` | One body per part. |
| Disconnected shell regions in one part, `IRIGID=1` | One body, not one per connected region. |
| Empty part, `IRIGID=1` | One body with a part-based set. Physical validity remains a Starter check. |
| Two rigid parts sharing nodes | Two bodies; the reader does not merge them. Later Starter conflict/hierarchy handling still needs validation. |
| `IRIGID=2`, one connected shell | One generated body with a four-node NODE set. |
| `IRIGID=2`, two disconnected shells | Two generated bodies with separate four-node NODE sets. |
| Tested values `-1`, `3` | No generated bodies and no reader warning. This observation does not establish these as supported rigid modes. |
| Input parts ordered 30, 20, 10, with part 20 ordinary | Part iteration is 10, 20, 30; counts are `[1, 0, 1]`; generated mapping is `[10, 30]`. |
| Existing `/RBODY/100` and `/GRNOD/NODE/50` | Existing body is retained; generated bodies are 101 and 102, with generated sets 52 and 53 in this fixture. Do not infer a general set-ID allocation rule from this one example. |

Each mode-1 generated body references a `/SET/GENERAL` with one `PART` clause containing
the originating part ID. It does not store an explicit connectivity-node list.
The snapshots record that clause, the body order, generated IDs, and body-to-part
mapping returned by the creation API.

The reader copies `Node_ID`, `Skew_ID`, `Sens_ID`, `Mass`, and all six inertia
components from the part. `explicit_fields.rad` verifies node 9, skew 5, sensor 6,
mass 12.5, diagonal inertia `[11, 22, 33]`, and off-diagonal inertia `[1, 2, 3]`.
The defaults fixture produces zero for these fields. The generated objects do not
explicitly supply `ICoG` or `Ispher` through the queried reader API; the snapshot
uses JSON `null` for unavailable attributes, not for physical zero values.

Immediately after conversion, an unspecified main node is still zero. Calling the
existing main-node helper assigns nodes 10 and 11 after the fixture's existing
nodes 1-9. A specified node 9 remains unchanged. Center-of-gravity calculation and
physical mass/inertia initialization occur later in Starter; the numerical suites
now test those independently of these reader-only snapshots.

## Run

From the repository root with Python 3.9 or newer and OpenReader built:

```powershell
python qa-tests/reader/rigid_parts/test_reader_contract.py --reader exec/open_reader_win64.dll
```

The runner uses a fresh process per fixture, temporary output directories, and a
30-second timeout. Checked-in snapshots are never automatically rewritten. The
legacy compatibility guard and its driver/build option have been removed.

## Stage 3 implementation checks

Run the command above with `--reader exec/open_reader_win64.dll` to check all
fourteen v82 snapshots against OpenReader, including successful mode-2 conversion.

`test_openreader_conversion.py` adds nine lifecycle/error checks and five mode-1
frozen v82 comparisons: `solid`, `include_fields`, `submodel_units`, `different_offsets`,
and `two_submodels`, plus 18 mode-2 frozen comparisons. They check titles, ownership, references, generated IDs, and
raw mass/inertia values. The unit cases use kilograms, millimetres, and seconds;
different offsets exercise node, element, part, material, and property ID spaces.

v82 gives generated entities unit ID zero even when the originating part has an
explicit unit ID. OpenReader keeps that ID on both the body and its set. The test
asserts this difference explicitly before comparing all remaining queried data.
No second scaling is applied during conversion. Stage 5 verifies the physical
result against an explicitly unit-tagged v82 body and records the v82 generated
body's incorrect inertia when it loses that unit ID.

```powershell
python qa-tests/reader/rigid_parts/test_openreader_conversion.py --reader exec/open_reader_win64.dll
```

The lifecycle checks cover repeat evaluation/creation without duplication, current
selection preservation, model reload with different part counts, array canaries,
all eight exports, invalid call order, changed/deleted parts, changed rigid flags,
mode-2 repeat conversion, and missing references.
An invalid conversion exits with code 1 and a diagnostic; no C++ exception crosses
the native ABI. Creation validates sources before mutation and rolls back generated
entities if an SDI creation or assignment fails. Caller-provided array capacities
cannot be inspected through the existing signatures; callers must use the evaluated
counts. Canaries check valid-sized buffers rather than promising protection against
arbitrary undersized pointers.

## Solver validation and remaining limits

The current integration suite runs 30 helper, Fortran bounds/order, and complete
Starter checks using OpenReader only. Numerical validation runs 19 mode-1/explicit
Engine cases and ten structural/error cases, plus six mode-2 generated/explicit
Engine runs. Independent analytic controls and the frozen pre-removal evidence
remain the oracles. See [the commands](../README.md#numerical-validation-stage-5).

Mode-2 comparisons cover SHELL, SH3N, BRICK, TETRA4, BEAM, and TRUSS connectivity,
vertex/edge connections, reversed element order, empty/shared parts, existing
bodies, ownership, offsets, and units. NODE membership/order is compared in full.
Optional mode-1 mass/inertia fields are not copied for mode 2.

Broader Engine coverage, runtime R2R filtering, other element formulations,
Linux/ARM, SP, and MPI remain unverified. HM Reader is not a runtime test oracle.
