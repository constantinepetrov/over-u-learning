"""Standard Frappe after_build extension; no upstream source modification."""
from pathlib import Path
import subprocess
import os


def after_build():
    # Package lives under repo/over-u/apps/over_u/over_u.
    repo = Path(__file__).resolve().parents[4]
    env = dict(os.environ)
    env.setdefault("NODE_OPTIONS", "--max-old-space-size=6144")
    subprocess.run(["node", str(repo / "over-u/dev/build-localized-frontend.mjs")], check=True, env=env)
