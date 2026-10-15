# build.py — cross-platform build entry. Run: uv run python build.py
import subprocess, sys

IS_LINUX = sys.platform.startswith("linux")

subprocess.run(
    [sys.executable, "manage.py", "collectstatic", "--noinput"],
    check=True,
)

cmd = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--noconsole",
    "--onefile",
    "--name",
    "djpos",
    "--collect-all",
    "webview",
]
# Packages Django loads BY STRING (MIDDLEWARE, INSTALLED_APPS, backends...).
# PyInstaller's static analysis can't see these — add one here whenever
# you add a string entry to settings.
DJANGO_STRING_LOADED = [
    "whitenoise",
]

for pkg in DJANGO_STRING_LOADED:
    cmd += ["--collect-all", pkg]

if IS_LINUX:
    cmd += ["--collect-all", "qtpy", "--collect-all", "PyQt6"]
else:
    cmd += ["--hidden-import", "clr_loader", "--hidden-import", "pythonnet"]

sep = ":" if IS_LINUX else ";"
cmd += ["--add-data", f"staticfiles{sep}staticfiles", "launcher.py"]

subprocess.run(cmd, check=True)
