from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from atis_clean.release.manifest import _release_fingerprint, release_manifest_path


def main() -> int:
    path = release_manifest_path()
    if not path.exists():
        print(f"FAIL: Missing release manifest at {path}")
        return 1

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError, UnicodeDecodeError) as exc:
        print(f"FAIL: Could not parse release manifest: {exc}")
        return 1

    if not isinstance(payload, dict):
        print("FAIL: Release manifest must be a JSON object.")
        return 1

    expected = _release_fingerprint()
    mismatches = [key for key, value in expected.items() if payload.get(key) != value]
    if mismatches:
        print("FAIL: Release manifest content drift detected.")
        print(f"Mismatched keys: {', '.join(mismatches)}")
        return 1

    build_time = payload.get("build_time")
    if not isinstance(build_time, str) or not build_time.strip():
        print("FAIL: build_time must be a non-empty string.")
        return 1

    # CI guard: build_time is allowed to vary, but semantic manifest fields must match code.
    print("PASS: Release manifest semantic fields are clean (build_time variance ignored).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
