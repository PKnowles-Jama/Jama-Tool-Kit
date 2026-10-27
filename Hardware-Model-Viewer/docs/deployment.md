# Hardware viewer deployment

## Native adapter

Use `config/viewer.example.json` as the non-secret template. Set the exact browser-visible HTTPS origin and Jama origin, allowed projects, bounded resource limits, and the supported REST root. Do not expose the loopback Python HTTP port directly to untrusted networks. Start `python viewer.py serve --config config/local.json`; no Docker is necessary. Use an organization-managed service supervisor for restart and a trusted reverse proxy for TLS, request timeouts, concurrency/rate limits, and a 16 KiB API request-body limit. An example Caddy configuration is in `deploy/Caddyfile.example`.

Register `/spa` in Jama's OSLC configuration. The launching item must be the Implementation Summary that owns the manifest and assets. Registration does not cause an already-open prompt item to navigate automatically: open the newly returned summary and its OSLC artifact tab to view the result. The tool can open a larger native drawer through the existing host contract when supported.

The adapter exposes only two authenticated POST operations: `/api/context` and `/api/asset`. It verifies application Origin, configured project, live item access, attachment associations, manifest binding, metadata, bounds, and hashes. Requests cannot select arbitrary upstream URLs. TLS validation stays enabled and Jama redirects are rejected. Responses are no-store; logs do not include tokens, queries, or customer content. Configure proxy logs to omit Authorization headers and request bodies.

Resource defaults: 50 MiB/file, one million rendered triangles, 16 megapixels/texture/image, 200 MiB expanded 3MF archive, 500 item attachments, 30 published runs. These are initial safeguards, not a customer performance guarantee. Lower limits for constrained clients. The adapter buffers a validated artifact; size/rate/concurrency limits at ingress should reflect available memory. STEP conversion runs separately during preparation, never inside a viewer request.

## Static mode

Build `dist/static-viewer.zip` using `scripts/build_release.py`. Serve its contents from an existing HTTPS static host, retain `viewer-config.json`, and register `/spa` with a static rewrite to `index.html` (also for `/spa/panel`). Use `mode: static`, the exact Jama origin, allowed projects, and actual public origin. No backend API is called in this mode.

The customer must qualify browser GET and OPTIONS requests with the Authorization header to Jama REST metadata and `/files`. Do not weaken Jama policies globally to satisfy this integration. Test native token delegation, CORS headers, CSP, embedding, binary MIME/download behavior, denial/expiry, and both iframe/drawer surfaces. Where any required policy cannot be satisfied, use the adapter.

Configure security headers on the static host, equivalent to the adapter: `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, and CSP restricting scripts to self, styles to self, images to self/blob/data, workers to self/blob, connections to self and the configured Jama origin, and `frame-ancestors` to the Jama origin. Do not set `X-Frame-Options: SAMEORIGIN`, which would block Jama embedding. There is no service worker or persistent asset cache containing Jama files.

The read-only probe on October 27, 2026 returned 403 without CORS allowance for `https://models.example.internal` on the connected Cloud instance. This does not establish the policy for other registered customer origins or self-hosted versions. The included config therefore defaults to the adapter.

## Optional containers

The supplied Dockerfile uses a predownloaded `wheelhouse`; it does not fetch pip packages at build time. Obtain and transfer the pinned base-image digest for the customer's approved Python image before building offline. Build using a customer-selected pinned base image:

```text
docker build --build-arg PYTHON_IMAGE=<approved-image@sha256:digest> -f deploy/Dockerfile -t jama-hardware-viewer:local .
docker run --rm -p 127.0.0.1:8090:8090 -v <absolute-config-path>:/run/config.json:ro jama-hardware-viewer:local
```

The same image can be run under Podman. Keep HTTPS at the existing ingress. Do not assume Docker Desktop is free for enterprise or government use. The native service remains the simplest deployment with no container platform.

## Airgapped installation

Create wheels for the target OS and Python version, bundle the release, review its checksum inventory and included third-party licenses, and transfer it using the customer's approved process. On the destination:

```text
python -m venv .venv
.venv/Scripts/python.exe -m pip install --no-index --find-links=wheelhouse -r requirements.txt
.venv/Scripts/python.exe viewer.py serve --config config/local.json
```

Use `.venv/bin/python` on Linux. Install internal TLS trust on server and browser; never disable certificate verification. The browser libraries require no package manager or CDN on the target. Node.js is needed only on the machine performing optional STEP conversion. Retain the converter's source/license obligations when redistributing it; see `third_party/NOTICE.md`.

Qualify installation from an empty cache with all external traffic blocked, using real customer files and a representative assembly/workstation. Test uploads of GLB, 3MF, GIF, PNG/JPEG, PDF, and source STEP against the actual Jama allowlist and attachment size limits. The viewer can run offline; the current Fusion360/MCP model-generation chain is a separate customer integration.
