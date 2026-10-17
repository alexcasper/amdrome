#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "simulator" / "src"))
sys.path.insert(0, str(ROOT))

from amdrome_sim import Engine
import agents.shrewd as shrewd

e = Engine(seed=42, agent=shrewd, ticks=120)
for t in range(120):
    e.t = t
    e._tick(t)
    if t in (20, 40, 60, 80, 100, 119):
        print(f"\n{'='*70}")
        print(f" TICK {t:03d} | Spot Price: ${e.spot.p:.2f} | WIP: {len(e.jobs)} units")
        print(f" Clean Delivered: {e.completed_clean} | Defective Escapes: {e.completed_defective} | Scrapped: {e.scrapped}")
        print(f" Unplanned Downtime: {e.unplanned_downtime}t | Breakdowns: {e.breakdowns} | PMs Run: {e.pm_count}")
        print(f" Net Profit So Far: ${e.result()['net_profit']:.2f}")
        print(f"{'-'*70}")
        print(" LINE FLOW & STATIONS:")
        for s in e.line.stations:
            buf = e.line.buf_before[s]
            status_symbol = "🟢" if s.state == "proc" else ("🟡" if s.state == "blocked" else ("🔴" if s.state == "broken" else "⚪"))
            print(f"  [Buffer: {len(buf.queue):>2}/{buf.cap}] ──► {status_symbol} [{s.kind.upper():<7}] {s.state:<7} "
                  f"| wear: {s.wear:5.1%} | remaining: {s.remaining:>2}t | ops done: {s.ops_done:>2}")
        print(f"{'-'*70}")
        won_list = []
        for cid, v in e.won.items():
            won_list.append(f"#{cid}: {v['filled_clean']}/{v['contract'].size} delivered (deadline: t={v['contract'].deadline})")
        print(f" Active Contracts Won: {won_list if won_list else 'None'}")
