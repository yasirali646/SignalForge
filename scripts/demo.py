#!/usr/bin/env python3
"""
Hackathon demo script — SignalForge

Usage:
  1. Start API: python run_api.py
  2. Run demo:  python scripts/demo.py

With BRIGHTDATA_API_TOKEN in .env, collection uses live Bright Data APIs.
Without token, COLLECTOR_MODE=local uses direct HTTP + synthetic SERP.
"""

import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

API = "http://127.0.0.1:8000/api/v1"


def wait_for_api(retries: int = 15) -> None:
    for i in range(retries):
        try:
            r = requests.get(f"{API}/health", timeout=2)
            if r.ok:
                print("API ready.")
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    print("Start the API first: python run_api.py")
    sys.exit(1)


def main() -> None:
    wait_for_api()

    print("\n=== 1. List seeded competitors ===")
    competitors = requests.get(f"{API}/competitors", timeout=10).json()
    for c in competitors:
        print(f"  - {c['name']} ({c['domain']}) id={c['id']}")

    print("\n=== 2. Baseline collection (pass 1) ===")
    r1 = requests.post(f"{API}/collect", timeout=600)
    r1.raise_for_status()
    for row in r1.json():
        print(
            f"  {row['competitor_id']}: snapshots={row['snapshots_created']} "
            f"events={row['events_created']} errors={len(row.get('errors', []))}"
        )

    print("\n=== 3. Second collection (pass 2 — detect changes) ===")
    r2 = requests.post(f"{API}/collect", timeout=600)
    r2.raise_for_status()
    for row in r2.json():
        print(
            f"  {row['competitor_id']}: snapshots={row['snapshots_created']} "
            f"events={row['events_created']}"
        )

    print("\n=== 4. Simulate pricing change (demo) ===")
    for c in competitors[:1]:
        sim = requests.post(f"{API}/demo/simulate-change/{c['id']}", timeout=30)
        if sim.ok:
            for e in sim.json():
                print(f"  Simulated: [{e['severity']}] {e['title']}")
        else:
            print(f"  Skip simulate ({sim.status_code}): need pricing baseline")

    print("\n=== 5. Event feed ===")
    events = requests.get(f"{API}/events?limit=10", timeout=10).json()
    if not events:
        print("  (no diff events yet — run simulate-change after baseline)")
    for e in events[:10]:
        print(f"  [{e['severity']}] {e.get('competitor_name')}: {e['title']}")
        print(f"       {e['diff_summary'][:120]}...")
        print(f"       {e['evidence_url']}")

    print("\n=== 6. Daily brief ===")
    brief = requests.get(f"{API}/brief/daily", timeout=10).json()
    print(f"  {brief['summary']}")

    out = ROOT / "data" / "demo_output.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {"competitors": competitors, "events": events, "brief": brief},
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"\nSaved {out}")
    print("\nOpen UI: cd ../frontend && npm run dev")


if __name__ == "__main__":
    main()
