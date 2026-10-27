# Start the local Hardware Model Viewer

Use two PowerShell terminals: one for the Python viewer and one for Caddy, which provides HTTPS. These steps reuse your existing installation and configuration after closing the terminals or rebooting Windows.

## 1. Start the viewer

Open PowerShell and run:

```powershell
Set-Location 'C:\Users\PatrickKnowles\OneDrive - Jama Software, Inc\Documents\Coding\Jama-Tool-Kit\Hardware-Model-Viewer'
.\.venv\Scripts\python.exe .\viewer.py serve --config .\config\local.json
```

Leave this terminal running. The viewer listens at `http://127.0.0.1:8090`.

Calling the Python executable inside `.venv` uses that environment directly; you do not need to activate it. Do not recreate the environment, reinstall dependencies, or copy the example configuration over your existing `local.json` for a normal restart.

## 2. Start Caddy

Open a **second PowerShell terminal** and run:

```powershell
Set-Location 'C:\Users\PatrickKnowles\OneDrive - Jama Software, Inc\Documents\Coding\Jama-Tool-Kit\Hardware-Model-Viewer'
& 'C:\Tools\Caddy\caddy.exe' run --config .\deploy\Caddyfile.local --adapter caddyfile
```

Leave this terminal running too. Caddy serves `https://localhost:8444` and forwards requests to the Python viewer on port 8090.

## Open the model in Jama

Open [the HTTPS health check](https://localhost:8444/health). It should return `{"status":"ok"}`.

Then sign in to Jama Connect, open the Implementation Summary containing your published model, and open or refresh its **OSLC Artifacts** view. Existing examples are REQHW-SUM-11 and REQHW-SUM-12.

Keep the registered OSLC URL as `https://localhost:8444/spa`. Opening that URL directly does not supply the selected item or delegated Jama session; use the OSLC view in Jama to load a real model.

## What survives closing the terminals or rebooting

- **Published models, GIFs, source downloads, and manifests:** stored as attachments on their Jama summary items. Their item associations survive restarting Python, Caddy, and Windows. You do not need to republish them.
- **Local settings:** saved in `config/local.json` and `deploy/Caddyfile.local`. Keep both files, the viewer application, `.venv`, and `C:\Tools\Caddy\caddy.exe`. The two local configuration files are gitignored; keep a separate backup when moving or reinstalling the application.
- **Original exports and publication records:** remain in your run folders. Keep these for future changes and publication recovery. Already published models load from Jama, so viewing them does not depend on the original export folder remaining open.
- **HTTPS trust:** normally persists for the same Windows account. Keep Caddy's local certificate data and the trusted local certificate.
- **Jama sessions and loaded previews:** temporary. Sign in again if needed and reopen or refresh the OSLC view after restarting.

Both local processes must be running, and the browser must be able to reach Jama, to view the published files. With the current `localhost` setup, use Jama in a browser on this same computer.

## Stop or troubleshoot

Press **Ctrl+C** in each terminal to stop its process. Repeat steps 1 and 2 whenever you want to start again.

- **Port already in use:** a previous process may still be running. Check `http://127.0.0.1:8090/health` for Python and `https://localhost:8444/health` for the complete connection before starting another copy. The existing `scripts/restart-local-viewer.ps1` helper runs Python in the background; closing its launching terminal may leave that process running.
- **502 from Caddy:** check that the Python viewer is running in terminal 1.
- **Certificate or local network block:** use the same browser profile and Windows account as before. Restore local certificate trust or the Jama site's local network permission if it was reset.
- **Page opens but the model does not:** reopen the summary's OSLC view to obtain a fresh Jama session. The current `local.json` allows project 53, where the REQHW demonstrations were published.
