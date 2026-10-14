"""Quality: defect injection, inspection modes, rework/scrap/escape."""

SCRAP_COST = 300.0
ESCAPE_PENALTY = 850.0
DEFECT_WEAR_COEFF = 0.08   # p_def = base + coeff * wear^2
SKILL_COEFF = 0.5          # skill factor scales defect prob down

# inspection catch probabilities by mode
CATCH_PROB = {"skip": 0.10, "sample": 0.65, "full": 0.97}


def defect_prob(wear, p_defect_base, skill=1.0):
    """Defect probability per op: base + wear^2 term, scaled by skill."""
    base = min(0.40, p_defect_base + DEFECT_WEAR_COEFF * (wear ** 2))
    return base * (1.0 - SKILL_COEFF * (1.0 - skill))


def inject(job, station, p_defect_base, rng):
    if rng.random() < defect_prob(station.wear, p_defect_base):
        job["has_defect"] = True


def inspect(job, mode, rng):
    """Returns True if a defect (if present) is caught."""
    if not job.get("has_defect"):
        return False
    return rng.random() < CATCH_PROB[mode]
