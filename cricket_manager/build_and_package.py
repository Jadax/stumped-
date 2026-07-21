"""Test, build, smoke-check, checksum, and archive the Windows release."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
EXE = DIST / "Stumped.exe"
# Single source of truth: the shipped config, so releases can't go stale.
VERSION = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["version"]


def run(command: list[str], *, timeout: int = 600) -> None:
    print(">", subprocess.list2cmdline(command), flush=True)
    completed = subprocess.run(command, cwd=ROOT, timeout=timeout, check=False)
    if completed.returncode:
        raise RuntimeError(f"Command failed with exit code {completed.returncode}: {command[0]}")


def safe_remove(path: Path) -> None:
    resolved, root = path.resolve(), ROOT.resolve()
    if resolved.parent != root or resolved.name not in {"build"}:
        raise RuntimeError(f"Refusing to remove unexpected path: {resolved}")
    if resolved.exists(): shutil.rmtree(resolved)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""): digest.update(block)
    return digest.hexdigest()


def build(skip_build: bool = False) -> tuple[Path, Path]:
    print("[1/6] Running release tests")
    run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"], timeout=180)
    print("[2/6] Running performance benchmark")
    run([sys.executable, "-B", "profile_game.py"], timeout=120)
    if not skip_build:
        print("[3/6] Building one-file Windows executable")
        safe_remove(BUILD); DIST.mkdir(exist_ok=True)
        if EXE.exists(): EXE.unlink()
        run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "build.spec"], timeout=900)
    else:
        print("[3/6] Reusing existing executable")
    if not EXE.is_file() or EXE.stat().st_size < 1_000_000:
        raise RuntimeError("dist/Stumped.exe is missing or unexpectedly small")

    print("[4/6] Running packaged startup diagnostics")
    run([str(EXE), "--diagnostics"], timeout=60)
    print("[5/6] Writing release manifest")
    manifest = {"product": "Stumped!", "version": VERSION, "platform": "Windows x64",
                "executable": EXE.name, "bytes": EXE.stat().st_size, "sha256": sha256(EXE)}
    manifest_path = DIST / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print("[6/6] Creating distribution ZIP")
    archive = DIST / f"Stumped-Windows-x64-v{VERSION}.zip"
    if archive.exists(): archive.unlink()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        package.write(EXE, EXE.name)
        package.write(ROOT / "README.md", "README.md")
        package.write(manifest_path, manifest_path.name)
    print(f"Release ready: {archive}")
    return EXE, archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-build", action="store_true", help="package an existing dist/Stumped.exe")
    args = parser.parse_args()
    try:
        build(args.skip_build)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
