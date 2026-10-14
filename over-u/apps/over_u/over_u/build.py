"""Standard Frappe after_build extension; no upstream source modification."""

import os
import subprocess
from pathlib import Path


def after_build():
	# Package lives under repo/over-u/apps/over_u/over_u.
	repo = Path(__file__).resolve().parents[4]
	env = dict(os.environ)
	env.setdefault("NODE_OPTIONS", "--max-old-space-size=6144")
	env.setdefault(
		"OVER_U_LMS_FRONTEND",
		str(Path.home() / "frappe-bench/apps/lms/frontend"),
	)
	subprocess.run(
		["node", str(repo / "over-u/dev/build-localized-frontend.mjs")],
		check=True,
		env=env,
	)
