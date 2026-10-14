#!/usr/bin/env python3
"""Interactive live console player for amdrome factory simulation (bead amdrome-g0s).

Usage:
  python3 demo/console/play.py [--agent shrewd|blind|eager|cautious|assistant]
                               [--seed 42] [--ticks 120] [--delay 0.05] [--step]
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "simulator" / "src"))
sys.path.insert(0, str(ROOT))

from amdrome_sim import Engine
import agents.blind as blind
import agents.shrewd as shrewd
import agents.eager as eager
import agents.cautious as cautious
from demo.assistant import OperatorAssistant
from demo.console.dashboard import render_dashboard

AGENTS = {
    "shrewd": shrewd,
    "blind": blind,
    "eager": eager,
    "cautious": cautious,
}


def main():
    parser = argparse.ArgumentParser(description="amdrome Live Factory Floor Console")
    parser.add_argument("--agent", default="shrewd", choices=["shrewd", "blind", "eager", "cautious", "assistant"],
                        help="Agent policy to run")
    parser.add_argument("--seed", type=int, default=42, help="Simulation seed")
    parser.add_argument("--ticks", type=int, default=120, help="Number of ticks to run")
    parser.add_argument("--delay", type=float, default=0.03, help="Delay between ticks in seconds (0 for instant)")
    parser.add_argument("--step", action="store_true", help="Step-by-step interactive mode (press Enter each tick)")
    args = parser.parse_args()

    assistant = OperatorAssistant(autonomous=True)
    if args.agent == "assistant":
        agent_obj = assistant
    else:
        agent_obj = AGENTS[args.agent]

    engine = Engine(seed=args.seed, agent=agent_obj, ticks=args.ticks)

    # ANSI clear screen & hide cursor
    print("\033[2J\033[H\033[?25l", end="", flush=True)

    try:
        for t in range(args.ticks):
            engine.t = t
            engine._tick(t)

            # Get assistant report for guidance overlay
            obs = engine.view.observe(t, engine.line, engine._wip(), engine.spot.p,
                                      engine.open_contracts, engine.results_log)
            report = assistant.process_tick(obs)

            # Render frame
            output = render_dashboard(t, args.ticks, engine, assistant_report=report)
            # Move cursor to top-left and overwrite
            print("\033[H" + output, flush=True)

            if args.step:
                input()
            elif args.delay > 0:
                time.sleep(args.delay)

    finally:
        # Restore cursor
        print("\033[?25h", flush=True)

    # Print final summary
    res = engine.result()
    print("\n" + "=" * 60)
    print("EPISODE COMPLETED")
    print(f"Final Net Profit:    ${res['net_profit']:,.2f}")
    print(f"Revenue Earned:      ${res['revenue']:,.2f}")
    print(f"Clean Units Made:    {res['completed_clean']}")
    print(f"Breakdowns:          {res['breakdowns']}")
    print(f"PMs Run:             {res['pm_count']}")
    print(f"Unplanned Downtime:  {res['unplanned_downtime']} ticks")
    print(f"Defect PPM:          {res['defect_ppm']:.1f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
