"""Stations & buffers: nodes of the production line, wear state."""

STATION_ORDER = ["cut", "form", "weld", "paint", "inspect", "pack"]
PROC_NOMINAL = 7        # nominal processing ticks per op
SIGMA_PROC = 0.15       # lognormal cycle-time noise
DRIFT_SLOPE = 0.35      # cycle inflation at wear=1.0
BUFFER_CAP_DEFAULT = 4  # per-buffer capacity (reallocatable, total fixed)
T_UNIT = 1.0            # transport ticks per manhattan cell


class Buffer:
    __slots__ = ("kind", "pos", "queue", "cap")

    def __init__(self, kind, pos, cap=BUFFER_CAP_DEFAULT):
        self.kind = kind
        self.pos = pos
        self.queue = []
        self.cap = cap


class Station:
    __slots__ = ("kind", "pos", "job", "remaining", "wear", "state",
                 "downtime_rem", "last_proc_actual", "ops_done",
                 "pm_schedule_tick")

    def __init__(self, kind, pos):
        self.kind = kind
        self.pos = pos
        self.job = None
        self.remaining = 0
        self.wear = 0.0
        self.state = "idle"          # idle | proc | pm | broken | blocked
        self.downtime_rem = 0
        self.last_proc_actual = PROC_NOMINAL
        self.ops_done = 0
        self.pm_schedule_tick = None

    def proc_time(self, proc_scale, wear_rate_unused, rng):
        import math
        base = PROC_NOMINAL * proc_scale
        dur = max(1, round(base * math.exp(rng.gauss(0, SIGMA_PROC))
                           * (1.0 + DRIFT_SLOPE * self.wear)))
        self.last_proc_actual = dur
        return dur


class Line:
    """Ordered nodes: inbuf, st0, buf, st1, ..., st5(pack)."""

    def __init__(self, ents, buffer_total=18):
        self.nodes = []
        self.inbuf = None
        self.stations = []
        for kind, pos in ents:
            if kind in ("inbuf", "buffer"):
                b = Buffer(kind, pos)
                self.nodes.append(b)
                if kind == "inbuf":
                    self.inbuf = b
            else:
                s = Station(kind, pos)
                self.nodes.append(s)
                self.stations.append(s)
        self.buffer_total = buffer_total
        self.buffers = [n for n in self.nodes if isinstance(n, Buffer)]
        # inter-station buffers in route order (excludes inbuf)
        self.inter = [b for b in self.buffers if b.kind == "buffer"]
        self.buf_after = {}
        self.buf_before = {}
        for i, n in enumerate(self.nodes):
            if isinstance(n, Station):
                self.buf_before[n] = self.nodes[i - 1]
                if n.kind != "pack":
                    self.buf_after[n] = self.nodes[i + 1]

    def set_caps(self, caps):
        """caps = [inbuf, b1..b5]; total preserved (capacity reallocation)."""
        assert len(caps) == 1 + len(self.inter), "need 6 caps"
        assert sum(caps) == self.buffer_total, "buffer slot total is fixed"
        self.inbuf.cap = caps[0]
        for b, c in zip(self.inter, caps[1:]):
            b.cap = c
