# Hardware Model Viewer Feature and Requirement Implementation Plan

Prepared October 27, 2026 for JCTK-TXT-5. Proposed scope: **12 Draft features, 114 Draft requirements, and one Implementation Summary** in Jama Connect Tool Kit, project 56.

Review the complete feature and requirement list below before Jama creation. The user-requested application folders replace the prompt's stale TAF1APP destination references. No application behavior changes, new Test Cases, Defects, or standalone definition items are proposed.

## Current project comparison

The read-only project inventory contains no Feature (132) or Requirement (24) items. All proposed behaviors therefore need new items; there are no existing human-generated feature candidates to reuse. Existing prompts, sets, placeholder text items, and the Functional Requirements / Non-Functional Requirements folders remain unchanged.

The specification reflects the latest code and accepted chat changes: single-item expanders, nested expanders for multiple models/GIFs, free trackball and X/Y/Z controls, drawing UI removal, local HTTPS deployment, ZIP-backed Jama attachments, resumable publication, and the demonstrated summary integrations. It does not restore the original drawing UI or promise exact CAD geometry, decal recovery from STEP, arbitrary-format viewing, or unsaved Fusion synchronization.

## Jama destination hierarchy

```text
Features [JCTK-SET-1 / 10577]
  Hardware-Model-Viewer
    <12 feature items>
Requirements [JCTK-SET-2 / 10578]
  Hardware-Model-Viewer
    <folder matching each feature name>
      <requirements linked to that one feature>
Implementation Summaries [JCTK-SET-7 / 10596]
  Hardware-Model-Viewer
    Hardware-Model-Viewer Features and Requirements Generation 2026-10-27
```

Create **3 application folders and 12 feature-named requirement folders**. Create no folders or data in sets that are not used. New Features and Requirements use Draft status option 292 from picklist 63. Each requirement has exactly one upstream feature through Related to (4). The Implementation Summary has downstream Related to links to every created feature and requirement.

## Execution and approval sequence

1. Obtain approval of this concrete plan as required by JCTK-TXT-5.
2. Refresh project contents, item schemas, Draft options, and the mapped project relationship rule set; stop for reconciliation if scope changed.
3. Create a baseline from the **project 56 root**, including the full project, titled `Pre-Generate Features and Requirements <date> <time>` using America/Denver time.
4. Create or reconcile the application and feature folders under the exact sets listed above; record all returned IDs before dependent writes.
5. Create Draft features and requirements with the names, descriptions, and one-feature ownership listed below; verify saved content, status, and locations.
6. Create and verify Feature → Requirement Related to links, checking for existing matches before any create.
7. Finalize tasks.md and walkthrough.md with actual IDs, links, counts, verification, and limitations; copy the approved plan and both finalized files into the Implementation Summary.
8. Relate the summary to all generated features and requirements, and verify coverage and parent locations.
9. Create a second full-project baseline titled `Post-Generate Features and Requirements <date> <time>` and return direct baseline, folder, and summary links.

Record pending operations before POSTs, retain a resumable ledger, and reconcile unknown outcomes before retrying. Do not blindly recreate an item, relationship, folder, or baseline. Do not mark this plan implemented before read-back verification succeeds.

## Traceability and verification

The mapped Specification Driven Development rule set allows Feature (132) → Requirement (24), Summary (133) → Feature, and Summary → Requirement using Related to (4). These are the only proposed relationship types. The TIM also requires Requirement → Test Case coverage; this prompt does not generate Test Cases, so full project test coverage will not be claimed.

Code paths below identify implementation evidence, not independent proof of every requirement. Existing unit/browser checks and live REQHW-SUM-11/12 publication receipts support the walkthrough; do not populate compliance or verification fields as Passed solely because code exists. The source snapshot records actual working-tree hashes because this thread's changes include staged content beyond the recorded Git HEAD.

## Proposed features and requirements

### F01 Jama Item Launch and User Session

Open the hardware viewer in the context of the Jama item selected by the user. Validate the launching instance and project, obtain the active user's delegated session, and retain that session only for the current browser interaction. Clear protected content when Jama rejects access and prevent stale asynchronous responses from restoring data from a previous run or session.

Evidence: `frontend/app.js`, `frontend/transport.js`, `src/jama_model_viewer/server.py`.

- **F01-R01 Launch context** — The application shall accept the artifact URL, projectId, optional name, and optional drawer handoff as its supported launcher parameters.
- **F01-R02 Duplicate parameter rejection** — The application shall reject launcher URLs containing an unknown parameter or repeated parameter name.
- **F01-R03 Trusted Jama origin** — The application shall reject a launcher artifact whose HTTPS origin differs from the configured Jama origin.
- **F01-R04 Allowed project launch** — The application shall reject a launcher project identifier that is not a safe integer in the configured project allowlist.
- **F01-R05 Delegated token handshake** — The application shall request the active user token from the Jama parent using the oslcLoadIframe message.
- **F01-R06 Parent message validation** — The application shall accept launcher token messages only from the configured Jama origin and the embedding parent window.
- **F01-R07 Session handshake timeout** — The application shall report a session timeout when the launcher token or drawer handoff is not received within 10 seconds.
- **F01-R08 Session memory** — The application shall retain the delegated token in browser memory rather than in launcher URLs or persistent browser storage.
- **F01-R09 Denied session cleanup** — The application shall clear the displayed protected content and in-memory token when an authenticated read returns HTTP 401 or 403.
- **F01-R10 Stale result rejection** — The application shall discard an artifact result when its selected run or session epoch has changed before the read completes.

### F02 Embedded Workspace and Appearance

Present the viewer inline in Jama and offer a larger view using the host's native drawer contract. Keep user-facing item and revision information visible, provide clear loading and error messages, and support a locally remembered light, dark, or system appearance without persisting Jama content.

Evidence: `frontend/index.html`, `frontend/app.js`, `frontend/viewer.css`.

- **F02-R01 Inline workspace** — The application shall display the hardware workspace inside the launching OSLC iframe.
- **F02-R02 Larger Jama view** — The application shall request the larger Jama drawer with the showDUI message when the user selects Open larger view.
- **F02-R03 Drawer token handoff** — The application shall transfer the session to the same-origin drawer through a random 128-bit BroadcastChannel handoff identifier.
- **F02-R04 Handoff completion** — The application shall close a launcher handoff channel after its token response or its 10-second expiry.
- **F02-R05 Item identification** — The application shall display the selected Jama item key and item name after context retrieval succeeds.
- **F02-R06 Revision identification** — The application shall display the selected run revision, publication time, units, and run identifier.
- **F02-R07 Appearance choices** — The application shall provide System, Light, and Dark appearance choices.
- **F02-R08 Appearance persistence** — The application shall persist only the selected appearance value under the viewer-specific browser theme key.
- **F02-R09 Iframe sizing** — The application shall request an inline iframe height between 400 and 1000 pixels based on the current content height.

### F03 Interactive Model Viewing

Display one or more published GLB or 3MF model previews with independent controls. Let the user freely rotate the camera and rotate each model explicitly around X, Y, and Z, while retaining fit/reset and standard viewpoints. Load models on demand and release renderer resources when the selected run changes.

Evidence: `frontend/model.js`, `frontend/app.js`, `frontend/transport.js`, `src/jama_model_viewer/core.py`.

- **F03-R01 Preview formats** — The application shall render published self-contained GLB and supported 3MF model previews in the browser.
- **F03-R02 Model count** — The application shall accept between 1 and 20 model previews in a published run.
- **F03-R03 Single model expander** — The application shall display a single model directly inside the model section without a nested model expander.
- **F03-R04 Multiple model expanders** — The application shall display an individual nested expander for each model when a run contains two or more models.
- **F03-R05 Free camera rotation** — The application shall provide trackball camera rotation without a fixed-up orbit restriction.
- **F03-R06 Three-axis model rotation** — The application shall provide independent X, Y, and Z model rotation sliders from minus 180 to plus 180 degrees in one-degree increments.
- **F03-R07 Standard viewpoints** — The application shall provide Isometric, Front, Top, and Right camera actions for each model.
- **F03-R08 Fit and reset** — The application shall reset the model rotation sliders to zero and restore the fitted isometric viewpoint when Fit / reset is selected.
- **F03-R09 Pan and zoom** — The application shall support right-button drag panning and scroll-based zoom within each model canvas.
- **F03-R10 Lazy model loading** — The application shall load a model preview only when its outer section and any applicable nested expander are open.
- **F03-R11 Hidden rendering suspension** — The application shall suspend model rendering while its section is closed or the browser document is hidden.
- **F03-R12 Model resource cleanup** — The application shall dispose the model geometry, materials, textures, controls, resize observer, and renderer when replacing its run.

### F04 GIF Animation Playback

Show published GIF animations with an initial still poster and explicit playback controls. Keep the single-animation view compact, group multiple animations in independent nested sections, and stop playback when the relevant section is closed or the page is hidden.

Evidence: `frontend/app.js`, `src/jama_model_viewer/publisher.py`, `src/jama_model_viewer/core.py`.

- **F04-R01 Animation poster** — The application shall display the declared PNG or JPEG poster before starting a published GIF.
- **F04-R02 Explicit playback** — The application shall start a GIF only after the user selects its Play action.
- **F04-R03 Stop playback** — The application shall replace a playing GIF with its poster when the user selects Stop.
- **F04-R04 Single animation expander** — The application shall display a single GIF directly inside the Animations section without a nested animation expander.
- **F04-R05 Multiple animation expanders** — The application shall display an individual nested expander for each GIF when a run contains two or more animations.
- **F04-R06 Collapse playback stop** — The application shall stop a GIF when its own nested expander or the outer Animations section is closed.
- **F04-R07 Hidden page playback stop** — The application shall stop GIF playback when the browser document becomes hidden.
- **F04-R08 Missing animation message** — The application shall display an explicit no-animations message when the selected run declares no GIF assets.

### F05 Published Run Discovery and Downloads

Resolve complete publications belonging to the selected Jama item and let the user choose between retained runs. Retrieve the original asset bytes for rendering or download while preventing files from different instances, projects, items, or runs from being combined.

Evidence: `frontend/app.js`, `frontend/transport.js`, `src/jama_model_viewer/service.py`.

- **F05-R01 Manifest discovery** — The application shall discover viewer publications using item-associated attachments whose title starts with JHMV manifest v1 followed by the run identifier.
- **F05-R02 Complete run selection** — The application shall offer only manifests with the supported schema version and complete publication status.
- **F05-R03 Deterministic run order** — The application shall order discovered runs by descending UTC publication timestamp and then descending run identifier.
- **F05-R04 Run refresh** — The application shall reread the published run inventory on initial launch and when the user selects Refresh.
- **F05-R05 Run selector** — The application shall replace the displayed assets with those of the run selected in the Published run control.
- **F05-R06 Missing publication message** — The application shall instruct the user to complete step 7 when no complete viewer publication is found on the item.
- **F05-R07 Original file downloads** — The application shall provide download actions for each model preview, source CAD asset, and GIF using the original manifest filename.
- **F05-R08 Run isolation** — The application shall bind each requested asset to the selected manifest run identifier and exact asset name.

### F06 Artifact Package Preparation

Prepare a reproducible viewer package from exported model files and optional source CAD and GIFs after the existing summary publication has finished. Capture the source requirements snapshot and file hashes so changed inputs cannot be silently published as the prepared run. Produce posters automatically and validate local filenames and supported encodings before writes.

Evidence: `src/jama_model_viewer/publisher.py`, `src/jama_model_viewer/core.py`, `src/jama_model_viewer/cli.py`.

- **F06-R01 Completed summary prerequisite** — The application shall require a completed summary ledger with a positive numeric summaryId and no pending summary operation before preparing a viewer package.
- **F06-R02 Summary item binding** — The application shall derive the package instance, project, and display item from the completed summary plan and ledger.
- **F06-R03 Repeated model inputs** — The application shall accept repeated --model options when preparing multiple previews for one run.
- **F06-R04 Optional source and GIF inputs** — The application shall accept repeated optional source CAD and GIF paths for package preparation.
- **F06-R05 Package identity** — The application shall assign a UUID run identifier and record the model revision, creation timestamp, units, and up-axis in the prepared manifest.
- **F06-R06 Snapshot digest** — The application shall record the SHA-256 of coverage.json as the prepared package source snapshot digest.
- **F06-R07 Artifact fingerprints** — The application shall record each packaged asset's filename, role, MIME type, byte length, and SHA-256.
- **F06-R08 Poster generation** — The application shall generate a PNG poster from the first frame of each input GIF and reference that poster from the GIF manifest entry.
- **F06-R09 Package overwrite prevention** — The application shall refuse preparation when the run already contains manifest.prepared.json.
- **F06-R10 Filename safety** — The application shall reject artifact paths that do not resolve to a simple filename within the viewer package directory.
- **F06-R11 Image and file bounds** — The application shall reject a preparation input exceeding 50 MiB or a raster image exceeding 16777216 pixels.
- **F06-R12 Encoding validation** — The application shall reject raster files whose detected encoding differs from the declared filename extension.
- **F06-R13 Changed input rejection** — The application shall reject validation when a packaged file fingerprint or the coverage.json digest differs from its prepared value.

### F07 Resumable Jama Publication

Publish viewer attachments onto the verified existing summary as a separate operation from model generation and summary creation. Support read-only preflight, resumable per-file state, verified uploads and associations, and a final manifest association that makes the complete run discoverable. Stop on unresolved write outcomes rather than duplicating Jama items.

Evidence: `src/jama_model_viewer/publisher.py`, `src/jama_model_viewer/cli.py`, `src/jama_model_viewer/jama_rest.py`.

- **F07-R01 Read-only preflight** — The application shall validate the local package and read the live destination and attachment inventory without creating attachments when --preflight is selected.
- **F07-R02 Explicit apply mode** — The application shall require the publish command to specify either --preflight or --apply.
- **F07-R03 Destination verification** — The application shall reject publication when the connection origin or live destination project differs from the package binding.
- **F07-R04 Separate publication ledger** — The application shall record viewer attachment operations in viewer-publish-state.json without replacing the existing summary ledger.
- **F07-R05 Package ledger binding** — The application shall reject a publication ledger whose canonical prepared-manifest digest differs from the current package.
- **F07-R06 Confirmed upload reuse** — The application shall reuse a confirmed attachment identifier and uploaded representation when resuming the same package.
- **F07-R07 Ambiguous creation stop** — The application shall stop when an attachment creation remains pending without a confirmed attachment identifier.
- **F07-R08 Upload verification** — The application shall read back each stored attachment and verify its filename, stored length, and SHA-256 before associating it.
- **F07-R09 Association recovery** — The application shall check the current item attachment inventory before repeating a pending association operation.
- **F07-R10 Manifest publication order** — The application shall associate the complete immutable manifest only after all declared assets have been uploaded and associated successfully.
- **F07-R11 Viewer failure isolation** — The application shall leave the existing summary and its feature and requirement relationships intact when viewer publication fails.
- **F07-R12 Publisher concurrency lock** — The application shall reject a second publisher using the same run while viewer-publish.lock exists.
- **F07-R13 Read retry policy** — The application shall retry transient GET failures within the REST client's four-attempt limit without automatically retrying non-GET writes.

### F08 Protected Attachment Access

Keep Jama user permissions authoritative for model and animation access. Restrict the adapter to bounded reads against the configured Jama instance, validate exact item and attachment bindings, and prevent the read endpoints from becoming a general proxy. Return useful access errors without logging user tokens or customer content.

Evidence: `src/jama_model_viewer/service.py`, `src/jama_model_viewer/server.py`, `frontend/transport.js`.

- **F08-R01 Authenticated API access** — The application shall require a nonempty whitespace-free bearer token of at most 8192 characters on protected adapter requests.
- **F08-R02 Application origin check** — The application shall reject adapter API requests whose Origin differs from the configured public origin.
- **F08-R03 API request bounds** — The application shall reject protected API bodies exceeding 16384 bytes or using a non-JSON content type.
- **F08-R04 Fixed read endpoints** — The application shall expose only /api/context and /api/asset as authenticated adapter operations.
- **F08-R05 Live item authorization** — The application shall read the requested Jama item with the supplied user token before resolving its published assets.
- **F08-R06 Manifest item binding** — The application shall reject a manifest whose Jama origin, project, display item, or summary identifier differs from the selected item context.
- **F08-R07 Attachment association check** — The application shall reject a manifest or asset that refers to an attachment not currently associated with the selected item.
- **F08-R08 Attachment identity check** — The application shall verify the asset's live project, stored file identifier, and exact stored filename against its manifest before returning bytes.
- **F08-R09 Content integrity check** — The application shall reject asset bytes whose length or SHA-256 differs from the published manifest.
- **F08-R10 TLS and redirect policy** — The application shall retain HTTPS certificate verification and reject redirects when the adapter reads Jama resources.
- **F08-R11 Bounded discovery** — The application shall reject inventories exceeding the configured attachment limit or containing more than 30 viewer manifest associations.
- **F08-R12 Protected response headers** — The application shall send no-store, nosniff, no-referrer, and a content security policy restricting embedding to the configured Jama origin on adapter responses.
- **F08-R13 Private process logging** — The application shall suppress native adapter request logging of query strings, bearer headers, and customer content.

### F09 Jama ZIP Storage Compatibility

Store model, source CAD, and manifest files in genuine ZIP containers when their original extensions are unsuitable for direct Jama attachment upload. Preserve original filenames and hashes for user downloads, validate the stored container separately, and bound extraction to the single declared file. Continue reading earlier direct-file publications.

Evidence: `src/jama_model_viewer/archive.py`, `src/jama_model_viewer/publisher.py`, `src/jama_model_viewer/service.py`, `frontend/archive.js`, `frontend/transport.js`.

- **F09-R01 ZIP publication formats** — The application shall store new GLB, 3MF, STEP, STP, and manifest JSON uploads in ZIP containers while leaving ordinary GIF and image uploads direct.
- **F09-R02 Deterministic ZIP bytes** — The application shall create identical ZIP bytes for identical original filenames and contents by using fixed archive metadata.
- **F09-R03 Container fingerprints** — The application shall record the stored ZIP name, byte length, encoding, and SHA-256 alongside the original asset metadata.
- **F09-R04 Single-entry extraction** — The application shall extract a ZIP only when it contains exactly the expected original filename.
- **F09-R05 ZIP expansion bound** — The application shall reject encrypted ZIP content or an uncompressed entry exceeding the configured extraction limit.
- **F09-R06 Original asset restoration** — The application shall verify both the stored ZIP hash and extracted original hash before rendering or downloading a container-backed asset.
- **F09-R07 Earlier publication compatibility** — The application shall retain support for already-confirmed direct-file uploads when reading or resuming older publications.

### F10 Local STEP Preview Conversion

Convert an exported STEP model into an embedded GLB mesh using the locally bundled OCCT importer. Keep conversion outside the viewing service, normalize coordinates for the viewer, and record the settings and limitations of the resulting visualization. Preserve the original source as the engineering reference.

Evidence: `scripts/convert-step.cjs`, `frontend/step-to-glb.cjs`, `README.md`.

- **F10-R01 Local STEP conversion** — The application shall convert a local .step or .stp input into a self-contained GLB without an online conversion service.
- **F10-R02 Conversion input bounds** — The application shall reject STEP conversion inputs larger than 50 MiB.
- **F10-R03 Conversion timeout** — The application shall terminate the conversion process when it exceeds 120 seconds.
- **F10-R04 Triangle conversion budget** — The application shall reject converted output exceeding one million triangles.
- **F10-R05 Conversion coordinates** — The application shall write converted positions and normals in meters with a Y-up orientation.
- **F10-R06 Conversion output safety** — The application shall refuse to overwrite an existing GLB output file.
- **F10-R07 Conversion provenance** — The application shall write a companion conversion record identifying the source, output, converter version, units, axes, and tessellation settings.
- **F10-R08 Appearance fidelity scope** — The application shall preserve supported mesh base colors during STEP conversion without claiming that omitted source image decals were recovered.

### F11 Offline Deployment and Release Packaging

Provide the same viewer assets for a native customer-hosted adapter or a qualified static deployment. Bundle browser libraries and offline installation dependencies, expose local health checks, and package releases from selected source locations. Keep rendering in the browser and document the HTTPS, browser permission, and Jama registration prerequisites separately from model generation.

Evidence: `src/jama_model_viewer/server.py`, `src/jama_model_viewer/service.py`, `scripts/build_release.py`, `scripts/bundle_vendor.py`, `scripts/verify.py`, `docs/deployment.md`.

- **F11-R01 Deployment modes** — The application shall support configured adapter mode and static mode using the same browser viewer.
- **F11-R02 Native service** — The application shall serve the adapter as a Python process bound by default to 127.0.0.1 on port 8090.
- **F11-R03 Health endpoint** — The application shall return a JSON ok status from /health while the native service is running.
- **F11-R04 Local browser libraries** — The application shall load required browser libraries from the packaged application origin without a runtime CDN dependency.
- **F11-R05 Offline Python installation** — The application shall supply pinned Python requirements and support installation from target-compatible local wheels without contacting a package index.
- **F11-R06 Native and static archives** — The application shall produce separate native and static viewer release ZIP archives.
- **F11-R07 Release checksums** — The application shall write SHA-256 checksum files for both release ZIP archives and a per-file checksum inventory in the native release.
- **F11-R08 Credential file exclusion** — The application shall exclude config/local.json and files outside the release builder's selected source paths from the release archives.
- **F11-R09 Synthetic demo isolation** — The application shall serve synthetic demo assets only when the native service is started with the explicit --demo option.
- **F11-R10 Regression command failure** — The application shall stop the verification runner on the first failing unit-test or browser-test subprocess.

### F12 Legacy Package Compatibility

Read previously published manifests without restoring the drawing user interface that was removed at the user's request. Preserve compatibility options needed by older automation while keeping the current viewer limited to models, source downloads, and GIF animations.

Evidence: `frontend/index.html`, `frontend/app.js`, `src/jama_model_viewer/core.py`, `src/jama_model_viewer/cli.py`, `src/jama_model_viewer/drawing.py`.

- **F12-R01 Drawing user interface removal** — The application shall omit the Drawings section and the Save four-view illustration action from the embedded workspace.
- **F12-R02 Legacy manifest entries** — The application shall accept supported drawing and document manifest entries without displaying them in the current viewer.
- **F12-R03 Legacy command compatibility** — The application shall retain the existing offline draw command and drawing-related preparation options for older automation without reintroducing a drawing panel.

## Scope limits and review findings

- Fusion model generation and MP4-to-GIF encoding are external run-preparation activities. The current viewer publisher accepts exported models and GIF inputs; it does not implement Fusion generation or a general MP4 conversion command.
- The source run has a logo decal; its STEP-derived preview has zero images/textures. Texture-preserving GLB exports are supported, but recovering missing decals is outside this specification.
- Local Network Access permission, trusted TLS, and Jama iframe permission delegation are browser/host prerequisites. They are not browser settings changed by the application.
- Legacy draw utilities remain in the code for compatibility. The active UI has no drawings section or drawing-export action.
- Customer-specific self-hosted and full airgap qualification remains deployment work. Local mocked browser tests do not establish every customer installation's compatibility.
- The current release builder traverses deploy/. A locally created Caddyfile.local can therefore enter the native archive despite being Git-ignored; no requirement here claims that all local deployment files are excluded. Track this as a packaging gap for a separate code change.

## Approval boundary

JCTK-TXT-5 process steps 6 and 8 state "once approved to proceed by the user" before project baselining and item creation. This delivery stops at the reviewable plan. No Jama folder, item, relationship, or baseline has been created for this execution yet.
