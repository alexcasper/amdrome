"""Floor: grid (config-parameterizable), entity placement, Manhattan transport."""

# Default grid (picked from the 8x6 / 12x8 / 16x12 sweep,
# research/2026-10-17-grid-sweep.md: 12x8 is the balanced point —
# policy/scenario/noise = 64/24/12). 16x12 is the challenge tier,
# reachable via factory expansion (DESIGN.md sec 10); larger grids are
# headroom for v1 multi-cell footprints and simultaneous lines.
GRID_W, GRID_H = 12, 8

STATION_TYPES = ["cut", "form", "weld", "paint", "inspect", "pack"]


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _snake_cells(w, h):
    """Row-major snake walk — the compact line follows it (wraps on
    narrow floors instead of overflowing)."""
    cells = []
    for y in range(h):
        row = [(x, y) for x in range(w)]
        cells.extend(row if y % 2 == 0 else reversed(row))
    return cells


def compact_layout(w=GRID_W, h=GRID_H):
    """Straight line along the snake walk: inbuf cut b form b weld ..."""
    cells = _snake_cells(w, h)
    ents, i = [], 0
    ents.append(("inbuf", cells[i])); i += 1
    for j, st in enumerate(STATION_TYPES):
        ents.append((st, cells[i])); i += 1
        if j < len(STATION_TYPES) - 1:
            ents.append(("buffer", cells[i])); i += 1
    return ents


def scattered_layout(rng, w=GRID_W, h=GRID_H):
    cells = [(x, y) for x in range(w) for y in range(h)]
    rng.shuffle(cells)
    picked = cells[:len(STATION_TYPES) * 2]
    ents = [("inbuf", picked[0])]
    for i, st in enumerate(STATION_TYPES):
        ents.append((st, picked[1 + 2 * i]))
        if i < len(STATION_TYPES) - 1:
            ents.append(("buffer", picked[2 + 2 * i]))
    return ents


def validate(ents, w=GRID_W, h=GRID_H):
    """Invariants: distinct cells, in-bounds, one of each station type."""
    cells = [p for _, p in ents]
    assert len(set(cells)) == len(cells), "overlapping entities"
    for x, y in cells:
        assert 0 <= x < w and 0 <= y < h, "out of bounds"
    kinds = [k for k, _ in ents]
    for st in STATION_TYPES:
        assert kinds.count(st) == 1, f"missing/dup station {st}"
    assert kinds.count("inbuf") == 1
    assert kinds[0] == "inbuf"
    return True
