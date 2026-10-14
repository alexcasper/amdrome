"""Labour: worker roster, skills, absence, technician contention.

v1: fixed-size roster; one worker per station (default assignment),
skill per station type; techs shared between repairs and PM support.
Absence = Bernoulli per shift with sickness bursts (hyperprior-free).
"""

ABSENT_P = 0.04          # per worker per shift
TECH_REPAIR_SLOWDOWN = 1.5   # repair takes 1.5x when no tech assigned


class Roster:
    def __init__(self, rng, size=10, n_techs=2):
        self.n_techs = n_techs
        self.workers = [
            {"id": i, "skill": round(rng.uniform(0.7, 1.0), 3),
             "absent": False} for i in range(size)]

    def roll_shift(self, rng):
        """New shift: absence draws (sickness burst = neighbor correlation)."""
        burst = rng.random() < 0.15
        for w in self.workers:
            p = ABSENT_P * (3.0 if burst else 1.0)
            w["absent"] = rng.random() < p
        return sum(1 for w in self.workers if w["absent"])

    def staffing_multiplier(self):
        """Fraction of workers present — scales station processing."""
        present = sum(1 for w in self.workers if not w["absent"])
        return 0.5 + 0.5 * present / len(self.workers)
