from __future__ import annotations

import os
import sys
from pathlib import Path


def bootstrap_local_packages() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    site_packages = base_dir / ".venv" / "Lib" / "site-packages"

    if site_packages.exists():
        site_packages_str = str(site_packages)
        if site_packages_str not in sys.path:
            sys.path.insert(0, site_packages_str)

        current_pythonpath = os.environ.get("PYTHONPATH", "")
        paths = [part for part in current_pythonpath.split(os.pathsep) if part]
        if site_packages_str not in paths:
            os.environ["PYTHONPATH"] = os.pathsep.join([site_packages_str, *paths]) if paths else site_packages_str
