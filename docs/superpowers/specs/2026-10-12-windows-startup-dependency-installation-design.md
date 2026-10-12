# Windows Startup Dependency Installation Design

## Goal

Make the existing Windows startup flow easier for non-technical users by detecting required system tools and offering to install missing tools before ClipGIF starts. Keep existing behavior for users whose dependencies are already available.

## Scope

- Extend `scripts/start_windows.bat`, which is invoked by the project-root `start.bat`.
- Update the Windows installation and startup instructions in `README.md`.
- Do not change the experimental macOS/Linux startup scripts or application runtime behavior.

## User flow

1. Check whether a Python interpreter at version 3.11 or newer is available.
2. Check whether both `ffmpeg` and `ffprobe` are available on `PATH`.
3. For each missing dependency group, clearly explain what is missing and ask the user before invoking Windows Package Manager (`winget`).
4. Install a supported Python 3 release or the FFmpeg package when approved. Python and FFmpeg are separate install steps so the user can approve each independently.
5. Recheck availability and versions before continuing. If the install was cancelled, failed, or the new tools are not visible in the current process, stop with actionable manual instructions; do not continue as if installation succeeded.
6. After system prerequisites pass, preserve the current virtual-environment creation, requirements installation, server startup, and browser-opening flow.

## Design choice

Use `winget` rather than downloading portable tools into the project. This reuses the Windows package manager and avoids embedding large third-party binaries in the repository. Installation must not be silent: the user explicitly approves each package installation, and normal `winget` package/source prompts remain enabled.

If `winget` is missing, unavailable, or returns an error, the script will report that automatic installation could not be completed and give the official/manual installation path. It will not elevate privileges or attempt an alternate package manager.

## Validation and errors

- Treat Python versions below 3.11 as missing/unsupported, including when an existing `.venv` is present.
- Require both FFmpeg executables. Finding one but not the other must trigger the FFmpeg remediation path.
- Re-run checks after installation rather than assuming the installer succeeded or that PATH was updated.
- Any decline, installer error, or failed recheck ends startup with a nonzero exit code and a specific next step.
- Do not modify user PATH or other system settings directly from the batch script.

## Documentation

Explain that `start.bat` checks for Python 3.11+ and FFmpeg, offers `winget` installation for missing prerequisites, and may require a new terminal/start attempt if Windows has not refreshed PATH. Retain manual installation instructions for systems without `winget`, and distinguish system prerequisites from Python packages installed into `.venv`.

## Tests

Validate the batch control flow for: all prerequisites already installed; missing Python and accepted/rejected/failed installation; missing either FFmpeg executable; absent `winget`; and a successful install that is not yet visible on PATH. Also run the existing Python test suite to ensure application behavior remains unchanged.
