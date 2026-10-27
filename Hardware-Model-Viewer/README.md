# Jama Hardware Model Viewer

An independent OSLC iframe and optional Jama drawer for browser-rendered models, GIF animations, and expandable isometric/three-view drawings. Assets stay attached to the Implementation Summary; the viewer uses the active Jama user's delegated access. The publishing CLI runs separately after REQHW-TXT-5 step 6.

No model-rendering server, Docker, viewing SaaS, or runtime CDN is required. The supplied adapter runs as a normal Python process behind HTTPS. A static mode is included for Jama installations that permit authenticated browser attachment access.

The current Cloud probe rejected the illustrative static origin's CORS preflight (403, no CORS headers), so **adapter mode is the default**. Static mode requires qualification against the actual customer origins. Cloud/self-hosted OSLC registration, trusted HTTPS, and real delegated-session/attachment upload qualification remain deployment steps. The repository includes automated local browser tests; these are not a claim of production Jama qualification.

## Start locally

Python 3.10+ is required. From this folder:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item config/viewer.example.json config/local.json
.venv\Scripts\python.exe viewer.py serve --config config/local.json --demo
```

Open `http://127.0.0.1:8090/spa?demo=1` for the clearly labeled synthetic example. Demo access is disabled unless `--demo` is supplied; omit that option in production. Original INCOSE application files and configuration are unchanged.

For Jama, set `publicOrigin`, `jamaOrigin`, and `allowedProjectIds` in `config/local.json`, put the service behind trusted HTTPS, and register `https://YOUR-VIEWER-ORIGIN/spa` as the OSLC launcher. Jama must append `artifact=<absolute Jama item URL>&projectId=<numeric project ID>` and provide the delegated token through `oslcLoadIframe`. The viewer supports the source application's `showDUI` drawer pattern. Tokens stay in memory and Authorization headers.

## Prepare a run

Finish the existing `publish_summary.py --apply` workflow first. Its `publish-state.json` must contain `complete: true`, a numeric `summaryId`, and `pending: null`. Keep `summary-plan.json` and `coverage.json` in the same run folder. The display target in this release is that verified Implementation Summary; arbitrary target-item mapping is not enabled.

Export a self-contained, uncompressed `.glb` without glTF extensions, or a `.3mf` mesh preview. Preserve original STEP/3MF CAD as a source download. A GLB uses meters and Y-up by specification; native 3MF exports may use Z-up. Explicitly record the actual preview units and orientation. Match all model, animation, and drawing files to the same CAD revision. Meshes are visualization evidence, not a replacement for the analysis report or original solid geometry.

```powershell
$run = 'C:\path\Requirements-to-Hardware-Run-2026-10-27'
python viewer.py prepare --run $run --model "$run\preview.glb" --source "$run\model.step" --gif "$run\motion.gif" --drawing "$run\four-view.png" --document "$run\drawing.pdf" --revision 'CAD revision 1' --units m --up-axis Y --projection third-angle --drawing-kind cad-drawing
python viewer.py validate --run $run
python viewer.py publish --run $run --credentials '..\..\Requirements-to-Hardware\Scripts\info.json' --preflight
python viewer.py publish --run $run --credentials '..\..\Requirements-to-Hardware\Scripts\info.json' --apply
```

`--source`, `--gif`, `--drawing`, and `--document` may repeat; omit absent artifacts. `prepare` creates a PNG poster for each GIF. Drawings accept PNG/JPEG previews, with optional PDF originals via `--document`. A sheet should contain isometric/front/top/right views and the correct first-angle or third-angle projection. Use `--drawing-kind undimensioned-visualization` for illustrations without CAD dimensions/tolerances. The browser's **Save four-view illustration** action produces a labeled undimensioned image for later publication. It does not update Jama automatically.

The package is saved under `<run>\viewer`. Preparation refuses to overwrite an existing package. Publication uses a separate `<run>\viewer-publish-state.json`, never recreates the summary, and never changes source features or requirements. `--preflight` makes authenticated reads only; actual upload permissions and accepted binary types are enforced by Jama during `--apply`. A preflight cannot prove write permission without writing.

For a different Jama instance, provide `--base-url https://YOUR-JAMA-ORIGIN` and collect the source workflow there. A package is bound to its original instance/project/summary; changing only the connection cannot redirect it. Use OAuth environment variables instead of a credential file if preferred: `JAMA_CLIENT_ID` and `JAMA_CLIENT_SECRET`. Never put publisher credentials in viewer configuration or browser files.

## Convert STEP locally

Node.js is required only for the optional local converter:

```powershell
node scripts/convert-step.cjs 'C:\path\model.step' 'C:\path\preview.glb'
```

The bundled `occt-import-js` converter runs offline, outputs meters/Y-up, preserves per-mesh base colors, and writes a conversion record beside the GLB. It limits input to 50 MiB, conversion to 120 seconds, and output to one million triangles. The output directory must exist; existing output files are not overwritten. Verify component positions, dimensions, colors, and orientation against CAD before publishing. Face-level styling and CAD feature history are not preserved. The original STEP remains downloadable via `--source`.

If a CAD drawing export is unavailable, create the fallback illustration before `prepare`:

```powershell
python viewer.py draw --model "$run\preview.glb" --output "$run\four-view.png" --up-axis Y --projection third-angle
```

Then prepare with `--drawing-kind undimensioned-visualization`. This local Pillow renderer handles baseline triangle GLB geometry and node placements, with a 100,000-triangle drawing limit. It produces labeled orthographic views without dimensions/tolerances or CAD hidden-line removal; use CAD-produced drawings when those properties matter.

## Viewer behavior

The model, animations, and drawings have independent collapsible sections. The model supports orbit, pan, zoom, fit, and standard camera views. GIFs use generated posters, explicit Play/Stop buttons, and stop when collapsed or when the page is hidden. Drawings support zoom and drag-to-pan. The viewer loads the latest complete run on open or Refresh and provides a run selector. There is no unsaved CAD synchronization or in-browser CAD editing.

Artifacts are fetched with the user's delegated token, bounded, verified against their SHA-256, and kept in temporary browser memory. Expired/denied reads clear content. Model rendering runs only on changes while visible; no continuous render loop is used. A lack of WebGL displays an error while keeping source downloads usable.

## Recover interrupted publication

Keep the prepared package, original snapshot, and both publication ledgers. Rerun the same `publish --apply` command to reuse confirmed uploads. Unknown POST outcomes stop publication.

- For unresolved **create**, find the attachment by the exact run UUID/hash title recorded by the publisher (`JHMV asset <runId> <sha256>`, or `JHMV manifest v1 <runId>`). Verify project, title, and file bytes if already uploaded. Enter its confirmed numeric attachment item ID as `attachmentId` for that filename in `viewer-publish-state.json`, retaining its hash. Clear `pending` only after reconciliation. If creation did not commit, confirm absence before clearing `pending` to allow a new POST.
- For **upload**, the same bytes may be PUT again to the known attachment ID. Uploaded bytes are read back and hashed before association.
- For **associate**, retry first checks current item attachments. A committed association is reused. If no association exists, confirm absence before clearing that entry's `pending` to permit another POST.
- A stale `viewer-publish.lock` may be removed only after confirming no publisher process is active. Never remove the publication ledger to force retries.

The final manifest is associated last and defines a complete run. A failed viewer publication leaves the Implementation Summary intact. Parallel distinct runs are selected deterministically by immutable UTC publication time then run UUID; files from different runs are never combined. Keep at most 30 manifest associations per item; archive older associations according to the customer's retention process. Source attachments remain controlled by Jama permissions.

## Deploy and package offline

See [Deployment](docs/deployment.md) for static hosting, native HTTPS ingress, optional OCI packaging, and airgapped installation. Dependencies are pinned in `requirements.txt` and `third_party/vendor-lock.json`; browser code is already bundled. `scripts/bundle_vendor.py` is a build-time refresh tool, not a runtime dependency. Rebuild and review the inventory if vendored files change.

```powershell
python -m pip download --dest wheelhouse -r requirements.txt
python scripts/build_release.py
```

Transfer `dist/hardware-model-viewer.zip` and a Python runtime appropriate for the destination. Generate wheels for the destination OS/Python; this workspace's wheels target Windows/Python 3.13. No Fusion360 replacement is included: customers in airgapped environments can publish exports from their locally available CAD system.

## Verify

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
python -m pip install --target .test-deps playwright==1.55.0
python tests/browser_check.py
python tests/browser_integration.py
```

Browser checks use installed Chrome with software WebGL, block external requests, and produce screenshots in `tests/output`. Integration tests simulate Jama to exercise both transports, the token handshake, drawer handoff, and session expiry. See [Validation](docs/validation.md) for the distinction between automated checks, live read-only probes, and outstanding customer qualification.
