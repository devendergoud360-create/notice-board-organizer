"""Cross-language parity check for the NRPS algorithm (Python vs JavaScript).

Generates a deterministic fixture in both languages' native JSON shape,
computes risk scores with risk.py and web/parity/risk.js, and asserts exact
equality (6-decimal ROUND_HALF_UP) for every record. Exit 0 on parity.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from risk import compute_risk  # noqa: E402
from seed_data import generate  # noqa: E402


def build_fixture() -> dict:
    today = date(2026, 11, 22)
    records = []
    for i, n in enumerate(generate(40, seed=99), start=1):
        rec = n.to_dict()
        rec["status"] = n.status
        records.append(rec)
    return {"today": today.isoformat(), "records": records}


def python_scores(fixture: dict) -> dict:
    today = date.fromisoformat(fixture["today"])
    return {
        r["id"]: compute_risk(
            type("R", (), {
                "id": r["id"], "category": r["category"],
                "expiry_date": date.fromisoformat(r["expiry_date"]),
                "date_posted": date.fromisoformat(r["date_posted"]),
                "status": r["status"],
            })(),
            [type("R", (), {
                "id": x["id"], "category": x["category"],
                "expiry_date": date.fromisoformat(x["expiry_date"]),
                "date_posted": date.fromisoformat(x["date_posted"]),
                "status": x["status"],
            })() for x in fixture["records"]],
            today,
        )
        for r in fixture["records"]
    }


def js_scores(fixture: dict) -> dict:
    js = os.path.join(ROOT, "web", "parity", "risk.js")
    result = subprocess.run(
        ["node", js], input=json.dumps(fixture), text=True,
        capture_output=True, cwd=ROOT, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"node failed: {result.stderr}")
    return {int(r["id"]): r["score"] for r in json.loads(result.stdout)}


def main() -> int:
    fixture = build_fixture()
    py = python_scores(fixture)
    js = js_scores(fixture)
    mismatches = [
        (nid, py[nid], js.get(nid)) for nid in py
        if js.get(nid) != py[nid]
    ]
    if mismatches:
        print(f"PARITY FAILED: {len(mismatches)} mismatch(es)")
        for m in mismatches[:10]:
            print("  id=%s python=%s javascript=%s" % m)
        return 1
    print(f"PARITY OK: {len(py)} records identical across Python and JavaScript "
          f"(6-decimal ROUND_HALF_UP)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
