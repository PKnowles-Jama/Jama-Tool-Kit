# Hardware viewer validation

Validated on October 27, 2026 in the Windows workspace. The viewer is implemented; installation into a customer Jama OSLC configuration is a separate deployment step.

## Automated checks

- All 22 Python unit tests passed. They exercise complete-summary prerequisites, source/artifact changes, exact item binding, manifest-last publication, resumable identical uploads, unknown POST outcomes, association read-back, read-only preflight, traversal rejection, unsupported GLB references, 3MF entity rejection, item/project mismatch, counted pagination, HTTP origin/token restrictions, response headers, and four-view illustration generation.
- Real Chrome checks render a synthetic GLB with all external requests blocked, play/stop a GIF using its poster, zoom drawings, change cameras, collapse sections, and inspect narrow dark-mode layout. Screenshots and the browser result record are in `tests/output` after running the tests.
- Browser integration tests use simulated Jama and viewer origins to exercise delegated-token parent messages, authenticated binary retrieval, both static and adapter modes, the native drawer/BroadcastChannel handoff, and clearing content after 401 responses. They also render a synthetic 3MF. These tests simulate the host and API; they do not assert compatibility with a customer's live OSLC implementation.
- The optional local converter was executed against the existing `REQHW-Rocket-Porta-Pad-II-Assembly-2026-10-12.step` without changing the source. It produced a 394,356-byte GLB, rendered it through the authenticated browser test, and generated a four-view illustration. Verify exact engineering dimensions/materials against the CAD source for each production run.
- Python compilation and JavaScript syntax checks were run on the new code. Vendored dependency archives were checked against npm SHA-512 integrity metadata, with resulting file hashes recorded in `third_party/vendor-lock.json`.
- A fresh Python 3.13 virtual environment installed the pinned dependencies using only the bundled Windows wheels (`--no-index`); unit and browser checks were run from that environment. A full customer airgapped installation and target-specific Linux wheels remain separate qualification activities.

## Live read-only Jama probe

`scripts/qualify_jama.py` authenticated to the connected Cloud instance using the existing Requirements-to-Hardware credential file and verified read access to REQHW-TXT-5 in project 53. The CORS OPTIONS request for the illustrative origin `https://models.example.internal` returned 403 with no CORS allowance. The supplied configuration therefore selects the adapter. Evidence is in `jama-read-qualification.json`; the probe performed no writes.

REQHW-TXT-5 was read through ad_jama, and its editable description field was validated there. The connector transport closed during the update attempt. A REST read-back confirmed the description was unchanged, then the authorized addition was applied using a description-only JSON PATCH through the existing Requirements-to-Hardware REST client. A final read verified the saved HTML exactly; original steps 1 through 6 and Ground Rules were preserved. Before/prepared/saved HTML is retained in this folder for audit and excluded from release packages. No live test summary or model attachment was created by the automated checks. The existing INCOSE application and all source requirements/features remain unchanged.

## Customer qualification still required

Provide the actual HTTPS hostname/certificate and register `/spa` with the target Jama OSLC adapter. Verify delegated-token capability, user permissions and expiry, inline sizing, drawer behavior, real file upload/association/download for each enabled type, allowlists/limits, and proxy headers. A read-only preflight cannot establish write permission.

Run the same checks on each supported self-hosted version. Install the airgap package with target-specific Python wheels and optional Node runtime, an empty browser cache, and external network blocked. Benchmark representative models on customer hardware and adjust file/triangle/texture limits. Production upload, live OSLC embedding, self-hosted compatibility, native service supervision, TLS configuration, and full disconnected installation have not been qualified by a simulated browser test.
