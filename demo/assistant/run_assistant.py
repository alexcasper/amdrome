#!/usr/bin/env python3
"""CLI runner for the Operator Assistant demonstration (bead amdrome-a3j).

Runs an episode of amdrome_sim.Engine with the Operator Assistant,
streaming alerts, station health assessments, and prescriptive recommendations.

Usage:
  python3 demo/assistant/run_assistant.py [--seed 42] [--ticks 336] [--autonomous] [--verbose]
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "simulator" / "src"))
sys.path.insert(0, str(ROOT))

from amdrome_sim import Engine
from demo.assistant import OperatorAssistant, Severity


def main():
    parser = argparse.ArgumentParser(description="amdrome Operator Assistant Streaming CLI")
    parser.add_argument("--seed", type=int, default=42, help="Episode random seed")
    parser.add_argument("--ticks", type=int, default=336, help="Episode duration in ticks")
    parser.add_argument("--autonomous", action="store_true", help="Assistant executes actions autonomously")
    parser.add_argument("--verbose", action="store_true", help="Print live alerts per tick")
    args = parser.parse_args()

    assistant = OperatorAssistant(autonomous=args.autonomous)

    class CopilotAgent:
        def act(self, obs):
            report = assistant.process_tick(obs)
            if args.verbose and report.active_alerts:
                print(f"[Tick {obs['t']:>3}] Alerts ({len(report.active_alerts)}):", file=sys.stderr)
                for a in report.active_alerts:
                    icon = "🚨" if a.severity == Severity.CRITICAL else "⚠️"
                    print(f"  {icon} [{a.severity.value}] {a.code}: {a.message}", file=sys.stderr)
                if report.ranked_recommendations:
                    top = report.ranked_recommendations[0]
                    print(f"  💡 TOP RECOMMENDATION: [{top.action_type.value}] on {top.target} "
                          f"(Est. Savings: ${top.expected_savings:,.2f})", file=sys.stderr)

            if args.autonomous:
                return report.suggested_actions
            # By default in copilot mode, dispatch recommended probes to maintain telemetry
            return {"probes": report.suggested_actions.get("probes", [])}

    engine = Engine(seed=args.seed, agent=CopilotAgent(), ticks=args.ticks)
    res = engine.run()
    summary = assistant.get_summary()

    output = {
        "engine_results": res,
        "assistant_summary": summary,
        "autonomous_mode": args.autonomous,
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
