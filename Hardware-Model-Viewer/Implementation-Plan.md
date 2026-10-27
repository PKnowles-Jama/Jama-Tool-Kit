# Jama Hardware Model Viewer Implementation Plan

Implementation baseline — October 27, 2026

Build a separate Jama OSLC viewer that displays the model, animations, and drawings produced by the Requirements to Hardware workflow. Render models in the browser using bundled open-source libraries. First qualify a static deployment using Jama as the protected artifact store; retain a small customer-hosted adapter when Jama authentication or browser restrictions prevent direct attachment access. Neither mode needs a CAD rendering server.

The application and publishing workflow are now implemented in this folder, and REQHW-TXT-5 has a verified step-7 addition. The connected Cloud CORS probe rejected the illustrative static origin, so the supplied configuration uses the native Python adapter. See README.md and docs/validation.md for implemented commands, test evidence, and the customer HTTPS/OSLC qualification still required.

## Existing integration and scope

The source application is `Jama-Tool-Kit/INCOSE-Assessment-Script-main/INCOSE-Assessment-Script-main`. Its current OSLC architecture comprises:

- `/spa`, a compact launcher receiving `artifact`, `projectId`, and optional `name` from Jama.
- `oslcLoadIframe`, a parent-message handshake for an active user's delegated bearer token.
- `showDUI`, which opens `/spa/panel` in Jama's native right-side drawer.
- Python context validation and Jama REST access behind trusted HTTPS.
- Theme, progress, and session-expiry behavior that can be adapted for this viewer.

Relevant source files are `src/incose_assessor/oslc/static/oslc.js`, `static/page.html`, `static/oslc.css`, `static/oslc-theme.js`, `context.py`, `jama.py`, `security.py`, `application.py`, and `server.py`. The deployment contract is documented in `docs/oslc-deployment.md`. This is an existing implementation contract; compatibility must be qualified on each target Jama deployment.

REQHW-TXT-5 was read through **ad_jama**: item 9782, version 5, project 53. It gathers approved features and their requirements, creates the Fusion360 model and analysis, builds an Implementation Summary, and publishes included-only relationships. The supporting scripts already handle PNG attachment publication and resumable writes. `publish_summary.py` records the resulting numeric item ID as `summaryId` and sets `complete: true` in `publish-state.json` after verification.

The default display item should be that newly created Implementation Summary. The execution prompt remains the workflow entry point. A configurable explicit target item can be supported later, provided it is verified in the correct project and mapped to the same published run. Displaying a model does not alter feature or requirement scope.

## Deployment decision

| Mode | Components | Suitable use | Condition |
| --- | --- | --- | --- |
| Preferred static viewer | HTML, CSS, JavaScript, bundled libraries; assets and manifest attached to Jama | No new application backend or container; internal static hosting is sufficient | Browser can authenticate to Jama and fetch item metadata and binary attachments under an acceptable CORS and embedding policy |
| Customer-hosted adapter | Same viewer plus a small Python REST adapter behind HTTPS | Reliable fallback for restrictive Jama/browser deployments | Adapter forwards authorized reads to Jama using the current delegated user token |
| Managed serverless hosting | Static viewer plus optional function equivalent of the adapter | Connected demonstrations or customers permitting managed infrastructure | Hosting and access controls must be suitable for customer data; costs depend on provider and usage |

A static iframe still needs an HTTPS origin from an existing intranet web server or approved static host. A `file://` page is not a reliable Jama integration. “Serverless” here means no new application server to operate; it does not remove the need to serve the page and protected artifacts.

Do not select a public model-viewing SaaS as a required dependency. Ship identical viewer assets for connected and disconnected installations. A private static asset directory must have real access control; unguessable filenames do not preserve Jama permissions. Keeping model content in Jama is the preferred way to avoid that additional permission system.

The adapter is an authorization and byte-delivery component, not a model renderer. It can run as a normal Python service behind existing HTTPS ingress. Containers are optional. An OCI package can support Linux Docker Engine or Podman. Docker Desktop has paid enterprise/government licensing conditions, so it cannot be assumed to satisfy a universally free deployment requirement. [Docker licensing](https://docs.docker.com/subscription-billing/desktop-license/), [Podman documentation](https://docs.podman.io/en/latest/).

## Viewer experience

The launcher should show a compact version of the viewer inside the OSLC iframe. Offer an **Open larger view** action that uses Jama's existing drawer pattern. Both surfaces use the same section components, preserving the requested inline display rather than requiring the drawer for basic viewing.

```text
Jama item key and model title       Run time / Refresh / Open larger view
▼ Interactive model
  [Orbit, pan, zoom, fit, reset, standard views]
  [3D canvas]
▶ Animations (2)
  [GIF poster, title, Play/Stop, animation]
▶ Drawings (1)
  [Expandable isometric + front/top/right sheet]
```

Each section expands independently with keyboard-accessible controls. Open the model initially; collapse animations and drawings initially. Allow each GIF and each drawing sheet to expand separately when multiple artifacts exist. Drawings support zoom, pan, fit, and a larger in-tool view; a download link preserves the original sheet.

Use a poster until a GIF is played. Stopping or collapsing a GIF replaces it with the poster to stop playback; an ordinary GIF image has no dependable native pause/resume control. Pause rendering when the model is hidden and release graphics resources when a run is replaced. Load expensive assets only when needed. Respect reduced-motion preferences and resize the canvas with its container.

Show the bound Jama item, model revision, run ID, publication time, units, and status. “Live” means an interactive view of the latest completely published run, refreshed on open or on user request. Optional bounded polling may check the small manifest while the page is visible. It does not mean editing CAD or streaming unsaved Fusion changes. A run selector may expose older published runs without silently combining their artifacts.

If WebGL is unavailable, show a poster and the original-file links. A failed GIF or drawing should not prevent the model from loading. Missing artifacts receive an explicit “not generated” status; do not fabricate an animation or drawing to fill the section.

## Model formats and drawings

Use Three.js with locally bundled controls and loaders. It is MIT licensed. [Three.js license](https://github.com/mrdoob/three.js/blob/dev/LICENSE).

| Format | Planned treatment | Limits |
| --- | --- | --- |
| GLB / glTF 2.0 | Preferred published preview; normalize to a self-contained GLB | Mesh preview; does not retain the CAD feature history or exact solid geometry |
| 3MF | Supported input and optional direct viewer path with ThreeMFLoader | Qualify assembly placement, units, colors, and unsupported extensions using real exports |
| STEP / STP | Preserve source; produce a preview during packaging through a local importer | Tessellation is required; large assemblies can exceed browser memory |
| STL | Optional mesh input after the core path works | Units and material information may be missing |
| Native CAD and other formats | Preserve as downloads; add converters only when individually qualified | No promise of arbitrary-format viewing |

Three.js provides a glTF loader, 3MF loader, and glTF exporter. Its 3MF extension support is partial. [GLTFLoader](https://threejs.org/docs/pages/GLTFLoader.html), [ThreeMFLoader](https://threejs.org/docs/pages/ThreeMFLoader.html), [GLTFExporter](https://threejs.org/docs/pages/GLTFExporter.html).

Prefer exporting a mesh from the completed CAD workflow and packaging it once, rather than converting CAD on every page load. Where needed, use `occt-import-js` locally to tessellate STEP, then construct and export a GLB. It supports browser and Node.js use. Treat that converter as an optional dependency with its LGPL/OCCT notices and applicable source distribution obligations. Optional direct browser STEP import belongs after the core release and should run in a bounded worker with cancellation. [occt-import-js documentation and license](https://github.com/kovacsv/occt-import-js).

Record input/output units and axis transformations explicitly. Preview preparation should validate bounding dimensions, component transforms, visible geometry, and color preservation against the source. Apply configurable mesh simplification with recorded tolerances; label the result as a visualization preview. Retain the original STEP/3MF for engineering use.

Generate the isometric and three orthographic views from the same model revision. The initial release should accept a CAD-produced PNG sheet and optional PDF containing isometric, front, top, and right views, with first-angle or third-angle projection explicitly stated. If CAD drawing export is unavailable, a local rendering task can generate a labeled four-view illustration, clearly identified as an undimensioned visualization. A dimensioned engineering drawing requires the CAD drawing workflow; camera screenshots cannot establish its dimensions or tolerances.

## Artifact manifest and item binding

Create a versioned manifest describing one complete publication. Store the authoritative manifest as an attachment on the display item, with a reserved attachment title or configured writable pointer field for discovery. Verify that a pointer field exists before selecting that option. Do not parse human report prose or match files by date alone.

The manifest should include:

- Schema version, immutable run UUID, model revision, source snapshot digest, creation/publication timestamps, and publication sequence.
- Jama instance identity, numeric project ID, numeric display item ID, and source summary ID when different.
- Preview and source-model entries with attachment IDs, resolved file identifiers, exact filenames, MIME types, byte sizes, SHA-256 hashes, units, axes, and conversion settings.
- Animation entries with GIF/poster pairs and captions; drawing entries with sheet preview, optional PDF, view labels, and projection convention.
- Per-artifact status and a final publication status indicating whether all declared assets were verified.

Reuse the existing image helper's distinction between attachment item ID and stored file ID. Do not assume its PNG-only uploader already supports GIF, GLB, STEP, or PDF. Those types need generalization and qualification against the target Jama version, upload limits, retrieval behavior, and permissions.

Publish verified assets first and the final manifest/pointer last. The reader selects only a fully published run for its exact instance/project/item tuple. Deterministic ordering must handle repeated runs on the same date and concurrent publication; a pointer update should detect competing updates or use a serialized publisher. The UI keeps the previous complete run until the next run is ready and identifies that older revision visibly.

## Changes to the Requirements to Hardware workflow

Add a proposed final step after REQHW-TXT-5 step 6. Keep model export, animation production, and drawing production available during model generation, but bind and publish their viewer package only after the summary and relationships are verified.

1. Complete existing collection, CAD generation, analysis, summary creation, and included-only relationships.
2. Read `publish-state.json`; require `complete: true`, a resolved `summaryId`, and no unresolved operation. Verify the live destination item/project. Never infer its ID from the summary title or create a second summary.
3. Prepare a package in a dedicated `viewer/` run subfolder. Accept explicit artifact paths, create the lightweight preview and drawing previews where supported, hash the files, and validate the package offline.
4. Execute a read-only preflight for destination permissions, artifact types/sizes, bindings, and expected existing publication.
5. Upload and associate artifacts using a separate `viewer-publish-state.json` ledger. Read back and verify the files, then publish the final manifest. Reconcile ambiguous writes before retrying and reuse confirmed uploads.
6. Verify manifest discovery and artifact access for the target item. Report its Jama link and viewer status. If viewer publication fails, retain the successfully published summary and resume only the viewer stage.

Proposed commands in the new tool: `prepare`, `validate`, `publish --preflight`, and `publish --apply`. Keep this packaging/publishing CLI separate from the viewer's read-only runtime. Reuse selected REST helpers through a defined adapter or copied, attributed module; avoid Python imports that depend on a developer's absolute workspace path.

Prepare a reviewable addition to REQHW-TXT-5 and its README as part of implementation. The final viewer step should describe artifact creation, the completed-summary prerequisite, optional explicit target binding, validation, publication recovery, and the returned item link. Preserve all existing inclusion rules and the prohibition on modifying requirements or features.

## Repository copy and proposed structure

Create the new application in `Jama-Tool-Kit/Hardware-Model-Viewer`. Start from a selective copy of the OSLC integration and its relevant tests, with a source inventory and file hashes recording provenance. The parent Jama-Tool-Kit checkout currently has no resolvable HEAD, so capture hashes rather than relying on a commit reference until repository history is established.

Do not copy credentials, customer configuration, virtual environments, generated runs, AI weights, logs, or source `.git` directories. Rename the application package, CLI, headers, theme storage key, and channel namespace. Preserve source notices. The source package declares a proprietary license; confirm redistribution rights for copied code separately from the open-source viewer libraries. Do not carry over assessment engines, local AI services, PyQt desktop UI, test generation, or their deployment dependencies.

```text
Hardware-Model-Viewer/
  Implementation-Plan.md
  README.md
  frontend/                 # Shared iframe/drawer UI and browser renderer
  src/jama_model_viewer/     # Optional auth/attachment adapter, OSLC validation
  publisher/                # Prepare, validate, preflight, resumable publication
  schemas/                  # Manifest and non-secret configuration schemas
  config/                   # Illustrative customer mappings
  deploy/                   # Static hosting and native service; optional OCI
  docs/                     # Jama setup, artifact export, offline installation
  tests/                    # Binding, permissions, publication, browser checks
  third_party/              # Licenses and bundled dependency inventory
```

This tree was the implementation baseline; see README.md for the final source layout and commands.

## Implementation sequence and acceptance

| Phase | Deliverable | Exit condition |
| --- | --- | --- |
| 1 — Qualify static access | Small launcher spike and deployment decision record | On representative Cloud and self-hosted Jama versions, verify handshake, origin checks, inline resizing/drawer, attachment fetches, CORS preflight, binary responses, and denied/expired access. Select static or adapter per deployment. |
| 2 — Create isolated copy | Renamed integration shell and dependency inventory | Existing tool still works; new tool opens on the correct item; copied source is recorded; no secrets or assessment/AI runtime remains. |
| 3 — Build viewer | GLB/3MF rendering, GIF controls, drawing viewer | Three independent collapsible sections work inline and in the drawer, with resize, keyboard access, loading errors, and WebGL fallback. |
| 4 — Build artifact publisher | Versioned manifest, preparation CLI, separate ledger | Publish to a designated test summary; verify hashes, item associations, repeated invocation, partial failure, ambiguous-write recovery, and manifest-last selection. |
| 5 — Extend execution workflow | Final-step instructions and export contract | A REQHW run produces one summary and one discoverable viewer publication without changing source features/requirements. |
| 6 — Qualify offline deployment | Static bundle and native adapter package; optional OCI archive | Fresh installation and viewing succeed with external network access blocked, using bundled libraries and internal certificate trust. |

Phase 1 is a deployment gate. A failed static-access qualification should switch to the small adapter without changing the renderer, manifest, or publisher architecture. Record a per-customer compatibility matrix rather than requiring customer-wide CORS changes just to retain a static deployment.

Additional acceptance scenarios:

- Two items, two projects, or two Jama instances cannot resolve each other's artifacts through a modified URL or manifest.
- The adapter verifies item access and attachment association on every protected fetch; it cannot proxy arbitrary URLs or redirect credentials to another host. Browser mode uses an explicit configured Jama origin and independently validates fetched item metadata.
- Tokens remain in memory, never in URLs, manifests, persistent browser storage, or logs. Authenticated bytes are fetched into bounded buffers/blob URLs as needed for image and model rendering; release those URLs when hidden or replaced. No bearer token is attached to an untrusted model dependency URL.
- Self-contained previews avoid external texture references. Enforce file, expanded archive, triangle, texture, conversion-time, and memory budgets; malformed or oversized inputs fail with a useful message. Apply the same limits to 3MF archives and optional STEP conversion.
- Restricted or expired access clears rendered content and requires reopening from Jama. Sensitive responses use appropriate no-store policies. Embedding/CSP settings allow only the intended Jama hosts and locally supplied scripts/workers.
- A representative assembly preserves component positions, units, and expected bounding dimensions. Front/top/right views match the stated projection convention and CAD reference images.
- Multiple GIFs and sheets remain independently usable; collapsed content stops consuming continuous rendering/animation resources.
- Agree initial performance budgets during phase 1 using a named customer workstation, browser, and assembly. Measure package size, first useful display, peak memory, and interaction responsiveness; set package limits from those results rather than promising universal load times.

## Airgapped operation and review defaults

Bundle JavaScript, CSS, fonts, WebAssembly, conversion tools if selected, Python wheels for the adapter/publisher, licenses, checksums, and installation instructions. Build the release in a controlled environment and transfer it through the customer's approved process. Runtime must require no npm/pip downloads, CDN calls, analytics, external identity provider, or online conversion service. Test it with an empty browser cache and blocked external network access.

This makes the **display and artifact-publication portion** self-hostable offline. REQHW-TXT-5 currently calls Fusion360 through MCP; replacing that model-generation chain for an airgapped customer is a separate integration. The viewer should accept artifacts from whichever locally available CAD workflow the customer uses.

The proposed defaults for review are: display on the newly created Implementation Summary; render inline with an optional larger Jama drawer; use GLB as the preferred preview while retaining original CAD; publish assets into Jama; attempt static deployment first with a native Python adapter fallback; and defer continuous CAD synchronization, model editing, and arbitrary-format conversion. No paid viewing service is required by this design.
