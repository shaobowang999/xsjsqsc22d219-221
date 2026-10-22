"""Package a built desktop app after checking its version and update notes."""
import argparse
import hashlib
import json
import ssl
from pathlib import Path
import zipfile


def package_release(app_dir, output_dir):
    app = Path(app_dir).resolve()
    internal = app / "_internal"
    version = (internal / "VERSION").read_text(encoding="utf-8").strip()
    notes = json.loads((internal / "static/update-notes.json").read_text(encoding="utf-8"))
    if notes.get("version") != version or not notes.get("items"):
        raise RuntimeError("Package VERSION and release notes must match")
    compile((internal / "main.py").read_bytes(), "main.py", "exec")
    ssl_policy = Path(ssl.__file__).with_name("codex-rejected-cas.pem")
    if ssl_policy.is_file() and (internal / "python312.dll").is_file() and not (internal / ssl_policy.name).is_file():
        raise RuntimeError("Missing SSL runtime certificate policy data")
    manifest = (app / "uninstall-files.txt").read_text(encoding="utf-8-sig").splitlines()
    for name in ["三千思创无线画布.exe", "uninstall.exe", "_internal/main.py", "_internal/VERSION", "_internal/static/index.html"]:
        if name.replace("/", "\\") not in manifest and name not in manifest:
            raise RuntimeError("Missing release manifest entry: " + name)
    files = []
    for rel in manifest:
        rel = rel.replace("\\", "/")
        target = (app / rel).resolve()
        if not target.is_relative_to(app) or not target.is_file():
            raise RuntimeError("Invalid package file: " + rel)
        if any(part in {"用户数据", "API密钥", ".env", "history.json"} for part in target.relative_to(app).parts):
            raise RuntimeError("User data must not enter the release package")
        files.append((target, rel))
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"三千思创无线画布-{version}-win-x64-with-uninstall.zip"
    if archive.exists():
        raise RuntimeError("Release package already exists: " + str(archive))
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for target, rel in files:
            bundle.write(target, "三千思创无线画布/" + rel)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(checksum + "  " + archive.name + "\n", encoding="utf-8")
    print(archive)
    print("SHA256:", checksum)
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-directory", required=True)
    parser.add_argument("--output-directory", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    package_release(args.app_directory, args.output_directory)
