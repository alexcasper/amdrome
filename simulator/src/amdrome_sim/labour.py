"""Labour: worker roster, type affinities, absence, per-shift assignment.

Decision surface (charter skill 2): each shift the agent assigns present
workers to stations. A station's effective skill = mean contribution of
its assigned present workers (affinity match = full skill, mismatched =
80%); an unstaffed station runs 30% slower and its ops use a floor skill.
Default (no action): present workers spread evenly, ignoring affinity —
so the skill being tested is specialist-to-station matching under absence.
"""

ABSENT_P = 0.04          # per worker per shift
UNDERSTAFF_PROC_PENALTY = 1.3
DOUBLE_STAFF_BONUS = 0.9     # two assigned workers: mild speedup
MISMATCH_FACTOR = 0.8        # worker on non-affinity station


class Roster:
    def __init__(self, rng, station_types, size=10, n_techs=2):
        self.n_techs = n_techs
        self.types = list(station_types)
        self.workers = []
        for i in range(size):
            self.workers.append({
                "id": i,
                "skill": round(rng.uniform(0.7, 1.0), 3),
                "affinity": self.types[rng.randrange(len(self.types))],
                "absent": False,
            })
        self.assigned = {t: [] for t in self.types}

    def roll_shift(self, rng, assign_counts=None):
        """New shift: absence draws, then agent assignment (or default).

        assign_counts: {station_type: n} with sum <= present workers.
        Invalid totals fall back to the even spread.
        """
        burst = rng.random() < 0.15
        for w in self.workers:
            p = ABSENT_P * (3.0 if burst else 1.0)
            w["absent"] = rng.random() < p
        present = [w for w in self.workers if not w["absent"]]
        self.assigned = {t: [] for t in self.types}
        if assign_counts is None or assign_counts == {}:
            for i, w in enumerate(present):
                self.assigned[self.types[i % len(self.types)]].append(w)
            return sum(1 for w in self.workers if w["absent"])
        try:
            total = sum(assign_counts.values())
        except (TypeError, AttributeError):
            total = len(present) + 1          # force fallback
        if (total > len(present) or total == 0 or any(
                (not isinstance(n, int)) or n < 0 or t not in self.assigned
                for t, n in assign_counts.items())):
            for i, w in enumerate(present):
                self.assigned[self.types[i % len(self.types)]].append(w)
            return sum(1 for w in self.workers if w["absent"])
        pool = list(present)
        for t, n in assign_counts.items():
            self.assigned[t] = pool[:n]
            del pool[:n]
        return sum(1 for w in self.workers if w["absent"])

    def apply_assignment(self, assign_counts):
        """Re-spread present workers per agent's mid-shift assignment."""
        present = [w for w in self.workers if not w["absent"]]
        try:
            total = sum(assign_counts.values())
        except (TypeError, AttributeError):
            return False
        if (total > len(present) or total == 0 or any(
                (not isinstance(n, int)) or n < 0 or t not in self.assigned
                for t, n in assign_counts.items())):
            return False
        pool = list(present)
        self.assigned = {t: [] for t in self.types}
        for t, n in assign_counts.items():
            self.assigned[t] = pool[:n]
            del pool[:n]
        return True

    def card(self):
        """Kanban-visible roster card (skills/absence are knowable)."""
        return {
            "present": sum(1 for w in self.workers if not w["absent"]),
            "workers": [{"id": w["id"], "skill": w["skill"],
                         "affinity": w["affinity"],
                         "absent": w["absent"]} for w in self.workers],
            "assigned_counts": {t: len(ws) for t, ws in self.assigned.items()},
        }

    def staffing_multiplier(self, station_kind=None):
        """Proc-time multiplier for the station this shift."""
        if station_kind is None:
            return 1.0                     # legacy global call
        n = len(self.assigned.get(station_kind, []))
        if n == 0:
            return UNDERSTAFF_PROC_PENALTY
        if n >= 2:
            return DOUBLE_STAFF_BONUS
        return 1.0

    def effective_skill(self, station_kind):
        """Effective skill for ops at this station (defect scaling)."""
        ws = self.assigned.get(station_kind, [])
        if not ws:
            return 0.7                    # unstaffed: floor skill
        contrib = [w["skill"] if w["affinity"] == station_kind
                   else w["skill"] * MISMATCH_FACTOR for w in ws]
        return sum(contrib) / len(contrib)
