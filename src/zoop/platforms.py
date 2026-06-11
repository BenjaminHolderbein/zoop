"""Platform-specific knowledge: where Blip stores its data and how to make it
create a transfer.

The two send mechanisms differ by OS:

* Windows/Linux use Blip's Compose/Conveyor launcher: invoking the binary with
  ``--peer <user_id>:<device_id> --file <path>`` forwards the request to the
  already-running single instance. See :func:`build_send_argv`.
* macOS has no such CLI. Its background core instead serves a DRPC socket in the
  App Group container; we talk to it directly (see :mod:`zoop.macsend`).
  :func:`find_socket` locates that socket.

Per-OS knowledge is isolated here:

* :func:`state_dat_candidates` -- candidate paths to ``state.dat``;
* :func:`launcher_prefix` -- the argv prefix used to invoke Blip (win/linux);
* :func:`socket_candidates` / :func:`find_socket` -- the DRPC socket (macOS).

Windows and macOS are verified. Linux ships best-effort candidates. If Blip
lives somewhere else, add the path here (PRs welcome) or override with the
``BLIP_STATE`` / ``BLIP_BIN`` / ``BLIP_SOCK`` environment variables.
"""

from __future__ import annotations

import glob
import os
import shutil
import sys
from pathlib import Path

# MSIX package family name for the Microsoft Store build of Blip.
_WIN_PKG = "BlipStudioInc.BlipApp_eydxbjyejh39j"
_APP_DIR = "net.blip.desktop"  # Blip's data-dir name on all platforms


def _expand(p: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(p)))


def state_dat_candidates() -> list[Path]:
    """Return candidate ``state.dat`` locations for the current OS, most likely
    first. Callers should use the first one that exists."""
    env = os.environ.get("BLIP_STATE")
    if env:
        return [_expand(env)]

    if sys.platform.startswith("win"):
        local = os.environ.get("LOCALAPPDATA", "")
        return [
            Path(local) / "Packages" / _WIN_PKG / "LocalCache" / "Local" / _APP_DIR / "state.dat",
            Path(local) / _APP_DIR / "state.dat",  # non-packaged fallback
        ]

    if sys.platform == "darwin":
        home = Path.home()
        gc = home / "Library" / "Group Containers"
        cands = [
            # The shipping Mac app (bundle id net.blip.macos) is sandboxed and
            # keeps state.dat in its App Group container, e.g.
            #   ~/Library/Group Containers/AY8UB8KTUX.blip/state.dat
            # The leading element is Blip's Apple Developer Team ID; glob it so
            # we don't hard-code a team that could change between signings.
            Path(p) for p in sorted(glob.glob(str(gc / "*.blip" / "state.dat")))
        ]
        cands += [
            # Non-sandboxed / older fallback.
            home / "Library" / "Application Support" / _APP_DIR / "state.dat",
        ]
        # Per-app sandbox container (Mac App Store style), just in case.
        cands += [
            Path(p)
            for p in glob.glob(
                str(home / "Library" / "Containers" / "*" / "Data" / "Library"
                    / "Application Support" / _APP_DIR / "state.dat")
            )
        ]
        return cands

    # Linux / other unix
    xdg = os.environ.get("XDG_DATA_HOME")
    home = Path.home()
    cands = []
    if xdg:
        cands.append(Path(xdg) / _APP_DIR / "state.dat")
    cands += [
        home / ".local" / "share" / _APP_DIR / "state.dat",
        home / ".config" / _APP_DIR / "state.dat",
    ]
    return cands


def find_state_dat() -> Path:
    for c in state_dat_candidates():
        if c.is_file():
            return c
    searched = "\n  ".join(str(c) for c in state_dat_candidates())
    raise FileNotFoundError(
        "Could not find Blip's state.dat. Searched:\n  " + searched +
        "\nIs Blip installed and signed in? You can also set BLIP_STATE=<path>."
    )


def launcher_prefix() -> list[str]:
    """Return the argv prefix that launches Blip (without --peer/--file)."""
    env = os.environ.get("BLIP_BIN")
    if env:
        return [env]

    if sys.platform.startswith("win"):
        # App execution alias, resolved via PATH (WindowsApps), with a fallback.
        alias = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WindowsApps" / "blip.exe"
        if shutil.which("blip.exe"):
            return ["blip.exe"]
        if alias.is_file():
            return [str(alias)]
        return ["blip.exe"]  # let it fail loudly if truly missing

    if sys.platform == "darwin":
        for app in ("/Applications/Blip.app", str(Path.home() / "Applications" / "Blip.app")):
            binary = Path(app) / "Contents" / "MacOS" / "Blip"
            if binary.is_file():
                return [str(binary)]
        # Fallback: hand args to the registered app via `open`.
        return ["open", "-a", "Blip", "--args"]

    # Linux / other unix
    for name in ("blip", "Blip"):
        found = shutil.which(name)
        if found:
            return [found]
    for cand in ("/opt/Blip/bin/Blip", "/opt/blip/bin/blip", "/usr/lib/blip/bin/Blip"):
        if Path(cand).is_file():
            return [cand]
    return ["blip"]  # let it fail loudly if truly missing


def build_send_argv(peer: str, files: list[str]) -> list[str]:
    argv = launcher_prefix() + ["--peer", peer]
    for f in files:
        argv += ["--file", f]
    return argv


# --- macOS native send transport -------------------------------------------
# The Mac app has no --peer/--file CLI; instead its background core serves a
# DRPC socket in the App Group container (see macsend.py). These helpers locate
# that socket and make sure the core is running.

def socket_candidates() -> list[Path]:
    env = os.environ.get("BLIP_SOCK")
    if env:
        return [_expand(env)]
    if sys.platform == "darwin":
        # Glob the App Group container dir (not the sock itself) so we report the
        # expected path even when Blip is closed and the socket doesn't exist yet.
        gc = Path.home() / "Library" / "Group Containers"
        return [Path(d) / "Library" / "Caches" / "sock"
                for d in sorted(glob.glob(str(gc / "*.blip")))]
    return []


def find_socket(launch: bool = True, timeout: float = 20.0) -> Path:
    """Return the core's DRPC socket, launching Blip and waiting if needed."""
    for c in socket_candidates():
        if c.exists():
            return c
    if launch and sys.platform == "darwin":
        import subprocess
        import time
        subprocess.run(["open", "-a", "Blip"], check=False)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for c in socket_candidates():
                if c.exists():
                    return c
            time.sleep(0.5)
    raise FileNotFoundError(
        "Could not find Blip's RPC socket. Is Blip installed and signed in? "
        "Searched: " + (", ".join(str(c) for c in socket_candidates()) or "(no candidates)")
    )
