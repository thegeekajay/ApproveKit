#!/usr/bin/env python3
"""Release helper for ApproveKit.

One-command maintainer flow:
1) bump version (patch/minor/major)
2) update CHANGELOG links and scaffold a new release section
3) run tests + build + twine checks
4) commit, tag, push
5) create a GitHub release (requires gh auth)
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import subprocess
import sys
from typing import Tuple

ROOT = pathlib.Path(__file__).resolve().parent
PYPROJECT = ROOT / "pyproject.toml"
INIT_FILE = ROOT / "approvekit" / "__init__.py"
CHANGELOG = ROOT / "CHANGELOG.md"


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def capture(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, cwd=ROOT, text=True).strip()


def ensure_clean_git() -> None:
    status = capture(["git", "status", "--porcelain"])
    if status:
        print("Git tree is not clean. Commit or stash your changes first.")
        sys.exit(1)


def parse_version(text: str) -> Tuple[int, int, int]:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", text)
    if not m:
        raise ValueError(f"Invalid semver: {text}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def bump(version: str, level: str) -> str:
    major, minor, patch = parse_version(version)
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def read_current_version() -> str:
    content = PYPROJECT.read_text()
    m = re.search(r'^version\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"\s*$', content, re.M)
    if not m:
        raise RuntimeError("Could not find project version in pyproject.toml")
    return m.group(1)


def update_pyproject_version(new_version: str) -> None:
    content = PYPROJECT.read_text()
    updated, count = re.subn(
        r'(^version\s*=\s*)"[0-9]+\.[0-9]+\.[0-9]+"(\s*$)',
        rf'\g<1>"{new_version}"\g<2>',
        content,
        flags=re.M,
    )
    if count != 1:
        raise RuntimeError("Expected exactly one version field in pyproject.toml")
    PYPROJECT.write_text(updated)


def update_init_version(new_version: str) -> None:
    content = INIT_FILE.read_text()
    if '__version__ = ' in content:
        updated, count = re.subn(
            r'^__version__\s*=\s*"[0-9]+\.[0-9]+\.[0-9]+"\s*$',
            f'__version__ = "{new_version}"',
            content,
            flags=re.M,
        )
        if count != 1:
            raise RuntimeError("Expected exactly one __version__ assignment")
        INIT_FILE.write_text(updated)
        return

    marker = "from approvekit.storage import Storage\n"
    if marker not in content:
        raise RuntimeError("Could not find import anchor in __init__.py")
    updated = content.replace(marker, marker + f"\n__version__ = \"{new_version}\"\n")
    if '"__version__"' not in updated:
        updated = updated.replace('    "Storage",\n', '    "Storage",\n    "__version__",\n')
    INIT_FILE.write_text(updated)


def update_changelog(current_version: str, new_version: str) -> None:
    content = CHANGELOG.read_text()
    header = "## [Unreleased]"
    if header not in content:
        raise RuntimeError("CHANGELOG.md is missing the [Unreleased] header")

    new_section = (
        f"## [{new_version}] - {dt.date.today().isoformat()}\n\n"
        "### Added\n\n"
        "- \n\n"
        "### Changed\n\n"
        "- \n\n"
        "### Fixed\n\n"
        "- \n\n"
    )

    if f"## [{new_version}]" in content:
        raise RuntimeError(f"CHANGELOG.md already has a section for {new_version}")

    content = content.replace(header + "\n\n", header + "\n\n" + new_section, 1)

    unreleased_line = f"[Unreleased]: https://github.com/thegeekajay/ApproveKit/compare/v{new_version}...HEAD"
    content, n = re.subn(
        r'^\[Unreleased\]:\s+https://github\.com/thegeekajay/ApproveKit/compare/v[^\n]+\.\.\.HEAD\s*$',
        unreleased_line,
        content,
        flags=re.M,
    )
    if n != 1:
        raise RuntimeError("Could not update [Unreleased] link in CHANGELOG.md")

    new_link = f"[{new_version}]: https://github.com/thegeekajay/ApproveKit/compare/v{current_version}...v{new_version}"
    prev_link_pattern = rf'^\[{re.escape(current_version)}\]:\s+https://github\.com/thegeekajay/ApproveKit/releases/tag/v{re.escape(current_version)}\s*$'
    if re.search(prev_link_pattern, content, re.M):
        content = re.sub(prev_link_pattern, new_link + "\n" + r"\g<0>", content, flags=re.M)
    else:
        content = content.rstrip() + "\n" + new_link + "\n"

    CHANGELOG.write_text(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare and publish a new release")
    parser.add_argument("level", choices=["patch", "minor", "major"], nargs="?", default="patch")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest run")
    parser.add_argument("--skip-build", action="store_true", help="Skip build/twine check")
    parser.add_argument("--skip-release", action="store_true", help="Skip GitHub release creation")
    args = parser.parse_args()

    ensure_clean_git()
    current_version = read_current_version()
    new_version = bump(current_version, args.level)

    print(f"Bumping version: {current_version} -> {new_version}")
    update_pyproject_version(new_version)
    update_init_version(new_version)
    update_changelog(current_version, new_version)

    if not args.skip_tests:
        run([sys.executable, "-m", "pytest", "-q"])

    if not args.skip_build:
        run([sys.executable, "-m", "build"])
        run([sys.executable, "-m", "twine", "check", "dist/*"])

    run(["git", "add", "pyproject.toml", "approvekit/__init__.py", "CHANGELOG.md"])
    run(["git", "commit", "-m", f"chore(release): v{new_version}"])
    run(["git", "tag", f"v{new_version}"])
    run(["git", "push", "origin", "main", f"v{new_version}"])

    if not args.skip_release:
        run(
            [
                "gh",
                "release",
                "create",
                f"v{new_version}",
                "--title",
                f"ApproveKit v{new_version}",
                "--generate-notes",
            ]
        )

    print("Release flow complete.")


if __name__ == "__main__":
    main()
