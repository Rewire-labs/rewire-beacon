"""Dump the OpenAPI spec to docs/api/openapi.yaml.

Run locally:
  cd apps/control-plane
  python ../../scripts/dump_openapi.py > ../../docs/api/openapi.yaml

CI compares git diff --exit-code to detect drift.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Make package importable when running from repo root.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "apps" / "control-plane" / "src"))


def main() -> None:
    from beacon.main import app  # type: ignore

    spec = app.openapi()
    try:
        import yaml  # type: ignore

        out = yaml.safe_dump(spec, sort_keys=False)
    except ImportError:
        out = json.dumps(spec, indent=2)
    sys.stdout.write(out)


if __name__ == "__main__":  # pragma: no cover
    main()
