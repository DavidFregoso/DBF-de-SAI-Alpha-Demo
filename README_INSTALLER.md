# Windows Installer (Streamlit Demo, Phase 1)

This guide explains how to build a Windows installer that bundles the Streamlit demo app with an embedded Python 3.11 runtime. The installer is offline-ready for clients (no Python, pip, or build tools required).

## 1) Developer build steps

**Prerequisites (developer machine only)**
- Windows 10/11
- PowerShell 5.1+ (or PowerShell 7)
- Internet access to download the Python embeddable runtime and Python wheels
- Python 3.11.14 x64 installed and available via `py -3.11` (builder check enforced by `build_staging.ps1`)
- Inno Setup 6 installed (ISCC.exe)

**Build the staging folder**
1. Open PowerShell in the repo root.
2. Run:
   ```powershell
   .\scripts\build_staging.ps1
   ```
   This will:
   - Download the Python 3.11.14 embeddable zip.
   - Enable `site-packages` in the embedded runtime.
   - Install pip and required wheels into `build\staging\runtime`.
   - Copy the app into `build\staging\app` and create `StartDemo.cmd`.

**Build the installer**
1. Ensure Inno Setup is installed.
2. Run:
   ```powershell
   .\scripts\build_installer.ps1
   ```
   This calls the Inno Setup compiler against `build\installer.iss` and produces the installer exe in the default Inno output directory.

## 2) Client install + start steps

1. Download the installer exe.
2. Run the installer and click **Next → Next → Finish**.
3. Use the **Start Demo** shortcut (Start Menu or Desktop).
4. The dashboard opens at `http://127.0.0.1:<port>` in the default browser.

## 3) Firewall note

The demo runs locally and binds to `127.0.0.1`. If Windows Firewall prompts you, allow **private network** access only. No internet access is required at runtime.

## 4) Troubleshooting

- **“Embedded Python not found”**
  - Reinstall the demo; this indicates missing runtime files.
- **Port already in use**
  - The launcher tries ports 8501–8510. If all are taken, close other local web servers and try again.
- **Blank page or error on first launch**
  - Wait a few seconds and refresh; initial DBF mock data generation can take a moment.
- **Installer build fails**
  - Confirm `ISCC.exe` is installed and accessible. You can set the `INNO_SETUP_PATH` environment variable to the full path.
