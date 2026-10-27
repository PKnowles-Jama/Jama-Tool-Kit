"""Prepare a reviewable JCTK-TXT-5 specification; this script makes no Jama writes."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/jctk-2026-10-27'
FEATURES = []


def feature(name, description, evidence, rows):
    key = f'F{len(FEATURES)+1:02d}'
    requirements = []
    for line in rows.strip().splitlines():
        title, statement = line.strip().split('|', 1)
        requirements.append({'key': f'{key}-R{len(requirements)+1:02d}', 'name': title,
            'description': 'The application shall ' + statement, 'featureKey': key,
            'evidence': evidence})
    FEATURES.append({'key':key, 'name':name, 'description':description,
                     'evidence':evidence, 'requirements':requirements})


feature('Jama Item Launch and User Session',
    'Open the hardware viewer in the context of the Jama item selected by the user. Validate the launching instance and project, obtain the active user\'s delegated session, and retain that session only for the current browser interaction. Clear protected content when Jama rejects access and prevent stale asynchronous responses from restoring data from a previous run or session.',
    ['frontend/app.js', 'frontend/transport.js', 'src/jama_model_viewer/server.py'], '''
Launch context|accept the artifact URL, projectId, optional name, and optional drawer handoff as its supported launcher parameters.
Duplicate parameter rejection|reject launcher URLs containing an unknown parameter or repeated parameter name.
Trusted Jama origin|reject a launcher artifact whose HTTPS origin differs from the configured Jama origin.
Allowed project launch|reject a launcher project identifier that is not a safe integer in the configured project allowlist.
Delegated token handshake|request the active user token from the Jama parent using the oslcLoadIframe message.
Parent message validation|accept launcher token messages only from the configured Jama origin and the embedding parent window.
Session handshake timeout|report a session timeout when the launcher token or drawer handoff is not received within 10 seconds.
Session memory|retain the delegated token in browser memory rather than in launcher URLs or persistent browser storage.
Denied session cleanup|clear the displayed protected content and in-memory token when an authenticated read returns HTTP 401 or 403.
Stale result rejection|discard an artifact result when its selected run or session epoch has changed before the read completes.
''')

feature('Embedded Workspace and Appearance',
    'Present the viewer inline in Jama and offer a larger view using the host\'s native drawer contract. Keep user-facing item and revision information visible, provide clear loading and error messages, and support a locally remembered light, dark, or system appearance without persisting Jama content.',
    ['frontend/index.html', 'frontend/app.js', 'frontend/viewer.css'], '''
Inline workspace|display the hardware workspace inside the launching OSLC iframe.
Larger Jama view|request the larger Jama drawer with the showDUI message when the user selects Open larger view.
Drawer token handoff|transfer the session to the same-origin drawer through a random 128-bit BroadcastChannel handoff identifier.
Handoff completion|close a launcher handoff channel after its token response or its 10-second expiry.
Item identification|display the selected Jama item key and item name after context retrieval succeeds.
Revision identification|display the selected run revision, publication time, units, and run identifier.
Appearance choices|provide System, Light, and Dark appearance choices.
Appearance persistence|persist only the selected appearance value under the viewer-specific browser theme key.
Iframe sizing|request an inline iframe height between 400 and 1000 pixels based on the current content height.
''')

feature('Interactive Model Viewing',
    'Display one or more published GLB or 3MF model previews with independent controls. Let the user freely rotate the camera and rotate each model explicitly around X, Y, and Z, while retaining fit/reset and standard viewpoints. Load models on demand and release renderer resources when the selected run changes.',
    ['frontend/model.js', 'frontend/app.js', 'frontend/transport.js', 'src/jama_model_viewer/core.py'], '''
Preview formats|render published self-contained GLB and supported 3MF model previews in the browser.
Model count|accept between 1 and 20 model previews in a published run.
Single model expander|display a single model directly inside the model section without a nested model expander.
Multiple model expanders|display an individual nested expander for each model when a run contains two or more models.
Free camera rotation|provide trackball camera rotation without a fixed-up orbit restriction.
Three-axis model rotation|provide independent X, Y, and Z model rotation sliders from minus 180 to plus 180 degrees in one-degree increments.
Standard viewpoints|provide Isometric, Front, Top, and Right camera actions for each model.
Fit and reset|reset the model rotation sliders to zero and restore the fitted isometric viewpoint when Fit / reset is selected.
Pan and zoom|support right-button drag panning and scroll-based zoom within each model canvas.
Lazy model loading|load a model preview only when its outer section and any applicable nested expander are open.
Hidden rendering suspension|suspend model rendering while its section is closed or the browser document is hidden.
Model resource cleanup|dispose the model geometry, materials, textures, controls, resize observer, and renderer when replacing its run.
''')

feature('GIF Animation Playback',
    'Show published GIF animations with an initial still poster and explicit playback controls. Keep the single-animation view compact, group multiple animations in independent nested sections, and stop playback when the relevant section is closed or the page is hidden.',
    ['frontend/app.js', 'src/jama_model_viewer/publisher.py', 'src/jama_model_viewer/core.py'], '''
Animation poster|display the declared PNG or JPEG poster before starting a published GIF.
Explicit playback|start a GIF only after the user selects its Play action.
Stop playback|replace a playing GIF with its poster when the user selects Stop.
Single animation expander|display a single GIF directly inside the Animations section without a nested animation expander.
Multiple animation expanders|display an individual nested expander for each GIF when a run contains two or more animations.
Collapse playback stop|stop a GIF when its own nested expander or the outer Animations section is closed.
Hidden page playback stop|stop GIF playback when the browser document becomes hidden.
Missing animation message|display an explicit no-animations message when the selected run declares no GIF assets.
''')

feature('Published Run Discovery and Downloads',
    'Resolve complete publications belonging to the selected Jama item and let the user choose between retained runs. Retrieve the original asset bytes for rendering or download while preventing files from different instances, projects, items, or runs from being combined.',
    ['frontend/app.js', 'frontend/transport.js', 'src/jama_model_viewer/service.py'], '''
Manifest discovery|discover viewer publications using item-associated attachments whose title starts with JHMV manifest v1 followed by the run identifier.
Complete run selection|offer only manifests with the supported schema version and complete publication status.
Deterministic run order|order discovered runs by descending UTC publication timestamp and then descending run identifier.
Run refresh|reread the published run inventory on initial launch and when the user selects Refresh.
Run selector|replace the displayed assets with those of the run selected in the Published run control.
Missing publication message|instruct the user to complete step 7 when no complete viewer publication is found on the item.
Original file downloads|provide download actions for each model preview, source CAD asset, and GIF using the original manifest filename.
Run isolation|bind each requested asset to the selected manifest run identifier and exact asset name.
''')

feature('Artifact Package Preparation',
    'Prepare a reproducible viewer package from exported model files and optional source CAD and GIFs after the existing summary publication has finished. Capture the source requirements snapshot and file hashes so changed inputs cannot be silently published as the prepared run. Produce posters automatically and validate local filenames and supported encodings before writes.',
    ['src/jama_model_viewer/publisher.py', 'src/jama_model_viewer/core.py', 'src/jama_model_viewer/cli.py'], '''
Completed summary prerequisite|require a completed summary ledger with a positive numeric summaryId and no pending summary operation before preparing a viewer package.
Summary item binding|derive the package instance, project, and display item from the completed summary plan and ledger.
Repeated model inputs|accept repeated --model options when preparing multiple previews for one run.
Optional source and GIF inputs|accept repeated optional source CAD and GIF paths for package preparation.
Package identity|assign a UUID run identifier and record the model revision, creation timestamp, units, and up-axis in the prepared manifest.
Snapshot digest|record the SHA-256 of coverage.json as the prepared package source snapshot digest.
Artifact fingerprints|record each packaged asset's filename, role, MIME type, byte length, and SHA-256.
Poster generation|generate a PNG poster from the first frame of each input GIF and reference that poster from the GIF manifest entry.
Package overwrite prevention|refuse preparation when the run already contains manifest.prepared.json.
Filename safety|reject artifact paths that do not resolve to a simple filename within the viewer package directory.
Image and file bounds|reject a preparation input exceeding 50 MiB or a raster image exceeding 16777216 pixels.
Encoding validation|reject raster files whose detected encoding differs from the declared filename extension.
Changed input rejection|reject validation when a packaged file fingerprint or the coverage.json digest differs from its prepared value.
''')

feature('Resumable Jama Publication',
    'Publish viewer attachments onto the verified existing summary as a separate operation from model generation and summary creation. Support read-only preflight, resumable per-file state, verified uploads and associations, and a final manifest association that makes the complete run discoverable. Stop on unresolved write outcomes rather than duplicating Jama items.',
    ['src/jama_model_viewer/publisher.py', 'src/jama_model_viewer/cli.py', 'src/jama_model_viewer/jama_rest.py'], '''
Read-only preflight|validate the local package and read the live destination and attachment inventory without creating attachments when --preflight is selected.
Explicit apply mode|require the publish command to specify either --preflight or --apply.
Destination verification|reject publication when the connection origin or live destination project differs from the package binding.
Separate publication ledger|record viewer attachment operations in viewer-publish-state.json without replacing the existing summary ledger.
Package ledger binding|reject a publication ledger whose canonical prepared-manifest digest differs from the current package.
Confirmed upload reuse|reuse a confirmed attachment identifier and uploaded representation when resuming the same package.
Ambiguous creation stop|stop when an attachment creation remains pending without a confirmed attachment identifier.
Upload verification|read back each stored attachment and verify its filename, stored length, and SHA-256 before associating it.
Association recovery|check the current item attachment inventory before repeating a pending association operation.
Manifest publication order|associate the complete immutable manifest only after all declared assets have been uploaded and associated successfully.
Viewer failure isolation|leave the existing summary and its feature and requirement relationships intact when viewer publication fails.
Publisher concurrency lock|reject a second publisher using the same run while viewer-publish.lock exists.
Read retry policy|retry transient GET failures within the REST client's four-attempt limit without automatically retrying non-GET writes.
''')

feature('Protected Attachment Access',
    'Keep Jama user permissions authoritative for model and animation access. Restrict the adapter to bounded reads against the configured Jama instance, validate exact item and attachment bindings, and prevent the read endpoints from becoming a general proxy. Return useful access errors without logging user tokens or customer content.',
    ['src/jama_model_viewer/service.py', 'src/jama_model_viewer/server.py', 'frontend/transport.js'], '''
Authenticated API access|require a nonempty whitespace-free bearer token of at most 8192 characters on protected adapter requests.
Application origin check|reject adapter API requests whose Origin differs from the configured public origin.
API request bounds|reject protected API bodies exceeding 16384 bytes or using a non-JSON content type.
Fixed read endpoints|expose only /api/context and /api/asset as authenticated adapter operations.
Live item authorization|read the requested Jama item with the supplied user token before resolving its published assets.
Manifest item binding|reject a manifest whose Jama origin, project, display item, or summary identifier differs from the selected item context.
Attachment association check|reject a manifest or asset that refers to an attachment not currently associated with the selected item.
Attachment identity check|verify the asset's live project, stored file identifier, and exact stored filename against its manifest before returning bytes.
Content integrity check|reject asset bytes whose length or SHA-256 differs from the published manifest.
TLS and redirect policy|retain HTTPS certificate verification and reject redirects when the adapter reads Jama resources.
Bounded discovery|reject inventories exceeding the configured attachment limit or containing more than 30 viewer manifest associations.
Protected response headers|send no-store, nosniff, no-referrer, and a content security policy restricting embedding to the configured Jama origin on adapter responses.
Private process logging|suppress native adapter request logging of query strings, bearer headers, and customer content.
''')

feature('Jama ZIP Storage Compatibility',
    'Store model, source CAD, and manifest files in genuine ZIP containers when their original extensions are unsuitable for direct Jama attachment upload. Preserve original filenames and hashes for user downloads, validate the stored container separately, and bound extraction to the single declared file. Continue reading earlier direct-file publications.',
    ['src/jama_model_viewer/archive.py', 'src/jama_model_viewer/publisher.py', 'src/jama_model_viewer/service.py', 'frontend/archive.js', 'frontend/transport.js'], '''
ZIP publication formats|store new GLB, 3MF, STEP, STP, and manifest JSON uploads in ZIP containers while leaving ordinary GIF and image uploads direct.
Deterministic ZIP bytes|create identical ZIP bytes for identical original filenames and contents by using fixed archive metadata.
Container fingerprints|record the stored ZIP name, byte length, encoding, and SHA-256 alongside the original asset metadata.
Single-entry extraction|extract a ZIP only when it contains exactly the expected original filename.
ZIP expansion bound|reject encrypted ZIP content or an uncompressed entry exceeding the configured extraction limit.
Original asset restoration|verify both the stored ZIP hash and extracted original hash before rendering or downloading a container-backed asset.
Earlier publication compatibility|retain support for already-confirmed direct-file uploads when reading or resuming older publications.
''')

feature('Local STEP Preview Conversion',
    'Convert an exported STEP model into an embedded GLB mesh using the locally bundled OCCT importer. Keep conversion outside the viewing service, normalize coordinates for the viewer, and record the settings and limitations of the resulting visualization. Preserve the original source as the engineering reference.',
    ['scripts/convert-step.cjs', 'frontend/step-to-glb.cjs', 'README.md'], '''
Local STEP conversion|convert a local .step or .stp input into a self-contained GLB without an online conversion service.
Conversion input bounds|reject STEP conversion inputs larger than 50 MiB.
Conversion timeout|terminate the conversion process when it exceeds 120 seconds.
Triangle conversion budget|reject converted output exceeding one million triangles.
Conversion coordinates|write converted positions and normals in meters with a Y-up orientation.
Conversion output safety|refuse to overwrite an existing GLB output file.
Conversion provenance|write a companion conversion record identifying the source, output, converter version, units, axes, and tessellation settings.
Appearance fidelity scope|preserve supported mesh base colors during STEP conversion without claiming that omitted source image decals were recovered.
''')

feature('Offline Deployment and Release Packaging',
    'Provide the same viewer assets for a native customer-hosted adapter or a qualified static deployment. Bundle browser libraries and offline installation dependencies, expose local health checks, and package releases from selected source locations. Keep rendering in the browser and document the HTTPS, browser permission, and Jama registration prerequisites separately from model generation.',
    ['src/jama_model_viewer/server.py', 'src/jama_model_viewer/service.py', 'scripts/build_release.py', 'scripts/bundle_vendor.py', 'scripts/verify.py', 'docs/deployment.md'], '''
Deployment modes|support configured adapter mode and static mode using the same browser viewer.
Native service|serve the adapter as a Python process bound by default to 127.0.0.1 on port 8090.
Health endpoint|return a JSON ok status from /health while the native service is running.
Local browser libraries|load required browser libraries from the packaged application origin without a runtime CDN dependency.
Offline Python installation|supply pinned Python requirements and support installation from target-compatible local wheels without contacting a package index.
Native and static archives|produce separate native and static viewer release ZIP archives.
Release checksums|write SHA-256 checksum files for both release ZIP archives and a per-file checksum inventory in the native release.
Credential file exclusion|exclude config/local.json and files outside the release builder's selected source paths from the release archives.
Synthetic demo isolation|serve synthetic demo assets only when the native service is started with the explicit --demo option.
Regression command failure|stop the verification runner on the first failing unit-test or browser-test subprocess.
''')

feature('Legacy Package Compatibility',
    'Read previously published manifests without restoring the drawing user interface that was removed at the user\'s request. Preserve compatibility options needed by older automation while keeping the current viewer limited to models, source downloads, and GIF animations.',
    ['frontend/index.html', 'frontend/app.js', 'src/jama_model_viewer/core.py', 'src/jama_model_viewer/cli.py', 'src/jama_model_viewer/drawing.py'], '''
Drawing user interface removal|omit the Drawings section and the Save four-view illustration action from the embedded workspace.
Legacy manifest entries|accept supported drawing and document manifest entries without displaying them in the current viewer.
Legacy command compatibility|retain the existing offline draw command and drawing-related preparation options for older automation without reintroducing a drawing panel.
''')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items = json.loads((OUT/'items-before.json').read_text(encoding='utf-8'))
    assert not [i for i in items if i['itemType'] in (132, 24)], 'Reconcile existing feature/requirement items first'
    requirements = [r for f in FEATURES for r in f['requirements']]
    assert len({r['key'] for r in requirements}) == len(requirements)
    assert all(r['description'].startswith('The application shall ') and r['description'].endswith('.') for r in requirements)
    assert all((ROOT/p).is_file() for f in FEATURES for p in f['evidence'])
    files = set(p for f in FEATURES for p in f['evidence'])
    files.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'src/jama_model_viewer').glob('*.py'))
    files.update(['schemas/manifest.schema.json', 'config/viewer.example.json', 'third_party/vendor-lock.json'])
    snapshot = {'gitHead': subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
        'scope': 'Actual working-tree content, including staged chat-driven changes; not HEAD alone.',
        'files': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(files)}}
    (OUT/'code-snapshot.json').write_text(json.dumps(snapshot, indent=2), encoding='utf-8')
    data = {'projectId':56, 'promptItemId':10686, 'promptKey':'JCTK-TXT-5',
        'application':'Hardware-Model-Viewer', 'status':'awaiting-plan-approval',
        'draftStatusOptionId':292, 'sets':{'features':10577, 'requirements':10578, 'summaries':10596},
        'relationshipTypeId':4, 'features':FEATURES}
    (OUT/'specification-plan.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    total_f, total_r = len(FEATURES), len(requirements)
    plan = [
        '# Hardware Model Viewer Feature and Requirement Implementation Plan', '',
        f'Prepared October 27, 2026 for JCTK-TXT-5. Proposed scope: **{total_f} Draft features, {total_r} Draft requirements, and one Implementation Summary** in Jama Connect Tool Kit, project 56.', '',
        'Review the complete feature and requirement list below before Jama creation. The user-requested application folders replace the prompt\'s stale TAF1APP destination references. No application behavior changes, new Test Cases, Defects, or standalone definition items are proposed.', '',
        '## Current project comparison', '',
        'The read-only project inventory contains no Feature (132) or Requirement (24) items. All proposed behaviors therefore need new items; there are no existing human-generated feature candidates to reuse. Existing prompts, sets, placeholder text items, and the Functional Requirements / Non-Functional Requirements folders remain unchanged.', '',
        'The specification reflects the latest code and accepted chat changes: single-item expanders, nested expanders for multiple models/GIFs, free trackball and X/Y/Z controls, drawing UI removal, local HTTPS deployment, ZIP-backed Jama attachments, resumable publication, and the demonstrated summary integrations. It does not restore the original drawing UI or promise exact CAD geometry, decal recovery from STEP, arbitrary-format viewing, or unsaved Fusion synchronization.', '',
        '## Jama destination hierarchy', '', '```text',
        'Features [JCTK-SET-1 / 10577]', '  Hardware-Model-Viewer', '    <12 feature items>',
        'Requirements [JCTK-SET-2 / 10578]', '  Hardware-Model-Viewer', '    <folder matching each feature name>', '      <requirements linked to that one feature>',
        'Implementation Summaries [JCTK-SET-7 / 10596]', '  Hardware-Model-Viewer', '    Hardware-Model-Viewer Features and Requirements Generation 2026-10-27', '```', '',
        f'Create **3 application folders and {total_f} feature-named requirement folders**. Create no folders or data in sets that are not used. New Features and Requirements use Draft status option 292 from picklist 63. Each requirement has exactly one upstream feature through Related to (4). The Implementation Summary has downstream Related to links to every created feature and requirement.', '',
        '## Execution and approval sequence', '',
        '1. Obtain approval of this concrete plan as required by JCTK-TXT-5.',
        '2. Refresh project contents, item schemas, Draft options, and the mapped project relationship rule set; stop for reconciliation if scope changed.',
        '3. Create a baseline from the **project 56 root**, including the full project, titled `Pre-Generate Features and Requirements <date> <time>` using America/Denver time.',
        '4. Create or reconcile the application and feature folders under the exact sets listed above; record all returned IDs before dependent writes.',
        '5. Create Draft features and requirements with the names, descriptions, and one-feature ownership listed below; verify saved content, status, and locations.',
        '6. Create and verify Feature → Requirement Related to links, checking for existing matches before any create.',
        '7. Finalize tasks.md and walkthrough.md with actual IDs, links, counts, verification, and limitations; copy the approved plan and both finalized files into the Implementation Summary.',
        '8. Relate the summary to all generated features and requirements, and verify coverage and parent locations.',
        '9. Create a second full-project baseline titled `Post-Generate Features and Requirements <date> <time>` and return direct baseline, folder, and summary links.', '',
        'Record pending operations before POSTs, retain a resumable ledger, and reconcile unknown outcomes before retrying. Do not blindly recreate an item, relationship, folder, or baseline. Do not mark this plan implemented before read-back verification succeeds.', '',
        '## Traceability and verification', '',
        'The mapped Specification Driven Development rule set allows Feature (132) → Requirement (24), Summary (133) → Feature, and Summary → Requirement using Related to (4). These are the only proposed relationship types. The TIM also requires Requirement → Test Case coverage; this prompt does not generate Test Cases, so full project test coverage will not be claimed.', '',
        'Code paths below identify implementation evidence, not independent proof of every requirement. Existing unit/browser checks and live REQHW-SUM-11/12 publication receipts support the walkthrough; do not populate compliance or verification fields as Passed solely because code exists. The source snapshot records actual working-tree hashes because this thread\'s changes include staged content beyond the recorded Git HEAD.', '',
        '## Proposed features and requirements', '']
    for f in FEATURES:
        plan += [f"### {f['key']} {f['name']}", '', f['description'], '',
                 'Evidence: '+', '.join(f'`{p}`' for p in f['evidence'])+'.', '']
        for r in f['requirements']:
            plan += [f"- **{r['key']} {r['name']}** — {r['description']}"]
        plan += ['']
    plan += ['## Scope limits and review findings', '',
        '- Fusion model generation and MP4-to-GIF encoding are external run-preparation activities. The current viewer publisher accepts exported models and GIF inputs; it does not implement Fusion generation or a general MP4 conversion command.',
        '- The source run has a logo decal; its STEP-derived preview has zero images/textures. Texture-preserving GLB exports are supported, but recovering missing decals is outside this specification.',
        '- Local Network Access permission, trusted TLS, and Jama iframe permission delegation are browser/host prerequisites. They are not browser settings changed by the application.',
        '- Legacy draw utilities remain in the code for compatibility. The active UI has no drawings section or drawing-export action.',
        '- Customer-specific self-hosted and full airgap qualification remains deployment work. Local mocked browser tests do not establish every customer installation\'s compatibility.',
        '- The current release builder traverses deploy/. A locally created Caddyfile.local can therefore enter the native archive despite being Git-ignored; no requirement here claims that all local deployment files are excluded. Track this as a packaging gap for a separate code change.', '',
        '## Approval boundary', '',
        'JCTK-TXT-5 process steps 6 and 8 state "once approved to proceed by the user" before project baselining and item creation. This delivery stops at the reviewable plan. No Jama folder, item, relationship, or baseline has been created for this execution yet.', '']
    (OUT/'Implementation-Plan.md').write_text('\n'.join(plan), encoding='utf-8')
    tasks = ['# Hardware Model Viewer Specification Tasks', '',
        '- [x] Read JCTK-TXT-5 and reconcile its stale destination references with the user\'s application-folder instruction.',
        '- [x] Inventory project 56 and confirm that no Feature or Requirement items already exist.',
        '- [x] Review current viewer source, this conversation\'s changes, item schemas, Draft status, and mapped relationship rules.',
        f'- [x] Prepare the complete list of {total_f} features and {total_r} requirements with one-feature ownership.',
        '- [x] Record the code content hashes and local evidence paths.',
        '- [ ] Obtain approval of Implementation-Plan.md.',
        '- [ ] Refresh live project evidence and create the full-project pre-generation baseline.',
        '- [ ] Create/reconcile the three Hardware-Model-Viewer application folders and feature-named requirement folders.',
        '- [ ] Create Draft features and requirements; verify fields and locations.',
        '- [ ] Create and verify one upstream feature relationship for each generated requirement.',
        '- [ ] Finalize this task list and walkthrough with actual results.',
        '- [ ] Create the Implementation Summary containing the approved plan, tasks, and walkthrough; link it to generated items.',
        '- [ ] Create the full-project post-generation baseline and report the final links.', '']
    (OUT/'tasks.md').write_text('\n'.join(tasks), encoding='utf-8')
    walkthrough = ['# Hardware Model Viewer Specification Walkthrough', '',
        'Status: analysis and planning complete; approval pending. No Jama writes for this execution have occurred.', '',
        '## Evidence reviewed', '',
        '- JCTK-TXT-5: item 10686, version 1, project 56. The ad_jama transport was closed; the same authenticated Jama instance was read through the existing REST client.',
        '- Project inventory: 16 items, zero Features and zero Requirements, with destination sets 10577, 10578, and 10596.',
        '- Schemas: Feature 132, Requirement 24, Implementation Summary 133, Folder 32, and Set 31. Draft status is active option 292.',
        '- TIM: rule set 1 is mapped to project 56 and permits the three proposed Related to paths.',
        '- Current source behavior, bundled dependency inventory, prior 26-unit-test/browser validation, and the two live viewer-publication receipts.', '',
        '## User changes reflected', '',
        '- Separate viewer derived from the INCOSE OSLC pattern, retaining the original application independently.',
        '- Browser-rendered models and GIFs associated with the selected Jama summary, with local HTTPS and offline-capable deployment.',
        '- Single items use one section expander; multiple items use per-item nested expanders.',
        '- Trackball movement and independent X/Y/Z sliders replace the earlier constrained orbit behavior.',
        '- Drawing section and drawing export action are removed; older package metadata remains accepted.',
        '- Real ZIP storage resolves the connected Cloud instance\'s direct GLB attachment rejection.',
        '- Source logo loss is documented as a STEP export limitation, not a missing requirement to recover unavailable image data.', '',
        '## Pending publication', '',
        f'After approval, create {total_f} Draft features, {total_r} Draft requirements, {total_f+3} folders, one summary, and two full-project baselines. Verify {total_r} Feature → Requirement relationships and {total_f+total_r} Summary → generated-item relationships. Replace this section with actual IDs and saved read-back results before copying it into the summary.', '',
        'The scoped requirements do not imply full Requirement → Test Case coverage or customer-wide deployment qualification. Preserve the existing prompts and unrelated project items.', '']
    (OUT/'walkthrough.md').write_text('\n'.join(walkthrough), encoding='utf-8')
    print(json.dumps({'features':total_f, 'requirements':total_r, 'folders':total_f+3,
        'summaryItems':1, 'relationships':total_r+total_f+total_r, 'baselines':2,
        'plan':str(OUT/'Implementation-Plan.md'), 'jamaWrites':0}, indent=2))


if __name__ == '__main__': main()
