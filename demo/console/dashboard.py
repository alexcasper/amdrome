"""Terminal dashboard renderer for amdrome factory simulation (bead amdrome-g0s).

Renders the complete game state: material flow, station status, wear gauges,
market contracts, and operator alerts using standard ANSI formatting.
"""

import sys
from typing import Any, Dict, List, Optional

# ANSI Color codes
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_RED = "\033[31m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_BLUE = "\033[34m"
C_MAGENTA = "\033[35m"
C_CYAN = "\033[36m"
C_WHITE = "\033[37m"
C_BG_DARK = "\033[40m"


def render_dashboard(t: int, max_ticks: int, engine: Any, assistant_report: Optional[Any] = None) -> str:
    """Renders a single frame of the factory floor console."""
    spot = engine.spot.p
    res = engine.result()
    net_profit = res["net_profit"]
    rev = res["revenue"]
    wip = len(engine.jobs)

    profit_color = C_GREEN if net_profit >= 0 else C_RED

    lines = []
    w = 96
    lines.append(f"{C_BLUE}╔{'═' * (w - 2)}╗{C_RESET}")
    title = f"  AMDROME FACTORY FLOOR CONSOLE  │  Tick {t:03d}/{max_ticks}  │  Spot: ${spot:.2f}  │  WIP: {wip} units  "
    pnl = f"Net Profit: {profit_color}${net_profit:,.2f}{C_RESET}  "
    header_content = f"{C_BOLD}{title}{C_RESET}"
    lines.append(f"{C_BLUE}║{C_RESET}{header_content:<{w - 2 + len(C_BOLD) + len(C_RESET)}}{C_BLUE}║{C_RESET}")
    lines.append(f"{C_BLUE}╠{'═' * (w - 2)}╣{C_RESET}")

    # Section 1: Financial & Production KPI Ticker
    kpi_bar = (f"  Revenue: {C_GREEN}${rev:,.2f}{C_RESET} │ "
               f"Scrapped: {C_RED}{engine.scrapped}{C_RESET} │ "
               f"Breakdowns: {C_RED}{engine.breakdowns}{C_RESET} │ "
               f"Downtime: {C_YELLOW}{engine.unplanned_downtime}t{C_RESET} │ "
               f"Clean Delivered: {C_GREEN}{engine.completed_clean}{C_RESET} │ "
               f"PMs: {C_CYAN}{engine.pm_count}{C_RESET}")
    lines.append(f"{C_BLUE}║{C_RESET} {kpi_bar:<{w - 4 + 7 * 9}} {C_BLUE}║{C_RESET}")
    lines.append(f"{C_BLUE}╠{'═' * (w - 2)}╣{C_RESET}")

    # Section 2: Factory Floor Topology & Conveyor Lines
    lines.append(f"{C_BLUE}║{C_RESET} {C_BOLD}FACTORY FLOOR & MATERIAL CONVEYOR FLOW:{C_RESET}{' ' * (w - 43)} {C_BLUE}║{C_RESET}")
    lines.append(f"{C_BLUE}║{C_RESET}{' ' * (w - 2)}{C_BLUE}║{C_RESET}")

    # Station nodes & states
    st_kinds = [s.kind for s in engine.line.stations]
    
    # Render Station Nodes
    st_boxes = []
    for s in engine.line.stations:
        buf = engine.line.buf_before[s]
        q_len = len(buf.queue)
        q_cap = buf.cap
        q_color = C_RED if q_len >= q_cap else (C_YELLOW if q_len > 0 else C_DIM)
        buf_str = f"{q_color}[B:{q_len}/{q_cap}]{C_RESET}"

        if s.state == "proc":
            st_color = C_GREEN
            icon = "🟢"
        elif s.state == "blocked":
            st_color = C_YELLOW
            icon = "🟡"
        elif s.state == "broken":
            st_color = C_RED
            icon = "🔴"
        elif s.state == "pm":
            st_color = C_CYAN
            icon = "🔧"
        else:
            st_color = C_WHITE
            icon = "⚪"

        st_str = f"{st_color}{s.kind.upper()[:4]}{C_RESET}"
        st_boxes.append(f"{buf_str}─►[{st_str}]")

    flow_line = " ─► ".join(st_boxes) + f" ─► {C_GREEN}[DELIVERY]{C_RESET}"
    lines.append(f"{C_BLUE}║{C_RESET}  {flow_line:<{w - 4 + 10 * 8}} {C_BLUE}║{C_RESET}")

    # Detail line: Wear and Remaining time
    details = []
    for s in engine.line.stations:
        wear_pct = int(s.wear * 100)
        w_color = C_RED if wear_pct >= 50 else (C_YELLOW if wear_pct >= 25 else C_GREEN)
        rem_str = f"{s.downtime_rem}t" if s.downtime_rem > 0 else f"{s.remaining}t"
        details.append(f"{s.kind[:3]}:{w_color}{wear_pct}%{C_RESET}({rem_str})")
    detail_str = " │ ".join(details)
    lines.append(f"{C_BLUE}║{C_RESET}  Telemetry: {detail_str:<{w - 15 + 6 * 8}} {C_BLUE}║{C_RESET}")
    lines.append(f"{C_BLUE}║{C_RESET}{' ' * (w - 2)}{C_BLUE}║{C_RESET}")

    # Section 3: Market & Customer Order Book
    lines.append(f"{C_BLUE}╠{'═' * (w - 2)}╣{C_RESET}")
    lines.append(f"{C_BLUE}║{C_RESET} {C_BOLD}SHARED MARKET & CONTRACT ORDER BOOK:{C_RESET}{' ' * (w - 39)} {C_BLUE}║{C_RESET}")

    if engine.won:
        for cid, v in list(engine.won.items())[:2]:
            c = v["contract"]
            filled = v["filled_clean"]
            due = c.deadline
            c_line = f"  • Contract #{cid}: {filled}/{c.size} delivered @ ${c.unit_price:.2f}/ea (Due tick {due}, max price ${c.max_price:.2f})"
            lines.append(f"{C_BLUE}║{C_RESET} {c_line:<{w - 4}} {C_BLUE}║{C_RESET}")
    else:
        no_c = "  • No active won contracts (relying on spot sales floor @ 75% spot price)"
        lines.append(f"{C_BLUE}║{C_RESET} {no_c:<{w - 4}} {C_BLUE}║{C_RESET}")

    if engine.open_contracts:
        open_c = engine.open_contracts[0]
        oc_line = f"  • Open for Bidding: Contract #{open_c.id} ({open_c.size} units, max bid ${open_c.max_price:.2f}, close tick {open_c.close_tick})"
        lines.append(f"{C_BLUE}║{C_RESET} {C_DIM}{oc_line}{C_RESET}{' ' * max(0, w - 4 - len(oc_line))} {C_BLUE}║{C_RESET}")

    # Section 4: Operator Assistant Telemetry & Prescriptive Guidance
    lines.append(f"{C_BLUE}╠{'═' * (w - 2)}╣{C_RESET}")
    lines.append(f"{C_BLUE}║{C_RESET} {C_BOLD}OPERATOR ASSISTANT GUIDANCE (Live Kanban Stream):{C_RESET}{' ' * (w - 52)} {C_BLUE}║{C_RESET}")

    if assistant_report and assistant_report.active_alerts:
        top_alert = assistant_report.active_alerts[0]
        a_icon = "🚨" if top_alert.severity.value == "CRITICAL" else "⚠️"
        a_line = f"  {a_icon} [{top_alert.severity.value}] {top_alert.code}: {top_alert.message}"
        lines.append(f"{C_BLUE}║{C_RESET} {a_line:<{w - 4}} {C_BLUE}║{C_RESET}")
    else:
        lines.append(f"{C_BLUE}║{C_RESET}  All systems nominal. No critical drift alerts on monitored stations.{' ' * (w - 74)} {C_BLUE}║{C_RESET}")

    if assistant_report and assistant_report.ranked_recommendations:
        top_rec = assistant_report.ranked_recommendations[0]
        r_line = f"  💡 REC: [{top_rec.action_type.value}] on {str(top_rec.target).upper()} (Est. Savings: ${top_rec.expected_savings:,.2f}) — {top_rec.rationale}"
        if len(r_line) > w - 4:
            r_line = r_line[:w - 7] + "..."
        lines.append(f"{C_BLUE}║{C_RESET} {r_line:<{w - 4}} {C_BLUE}║{C_RESET}")

    lines.append(f"{C_BLUE}╚{'═' * (w - 2)}╝{C_RESET}")
    return "\n".join(lines)
