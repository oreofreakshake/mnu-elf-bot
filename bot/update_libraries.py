from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REQUIREMENTS_FILE = Path("requirements.txt")


def ensure_virtualenv() -> None:
    in_virtualenv = (
        hasattr(sys, "real_prefix")
        or sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    )

    if not in_virtualenv:
        raise SystemExit(
            "Error: No virtual environment is active.\n"
            "Activate your venv before running this script."
        )


def run(
    *args: str,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", *args],
        check=True,
        text=True,
        capture_output=capture_output,
    )


def main() -> None:
    ensure_virtualenv()

    print(f"Using virtual environment: {sys.prefix}")
    print("Checking outdated packages...")

    result = run(
        "pip",
        "list",
        "--outdated",
        "--format=json",
        capture_output=True,
    )

    outdated_packages = json.loads(result.stdout)

    if outdated_packages:
        print(f"Found {len(outdated_packages)} outdated package(s).\n")

        for package in outdated_packages:
            name = package["name"]
            current = package["version"]
            latest = package["latest_version"]

            print(f"Upgrading {name}: {current} -> {latest}")
            run("pip", "install", "--upgrade", name)
    else:
        print("All packages are already up to date.")

    print("\nFreezing dependencies...")

    result = run(
        "pip",
        "freeze",
        capture_output=True,
    )

    REQUIREMENTS_FILE.write_text(
        result.stdout,
        encoding="utf-8",
    )

    print(f"Updated: {REQUIREMENTS_FILE.resolve()}")


if __name__ == "__main__":
    main()
