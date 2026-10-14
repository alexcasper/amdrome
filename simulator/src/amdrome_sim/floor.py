"""Floor: 12x8 grid, entity placement, Manhattan transport."""

GRID_W, GRID_H = 12, 8

STATION_TYPES = ["cut", "form", "weld", "paint", "inspect", "pack"]


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def compact_layout():
    """Straight line along row 3: inbuf cut b form b weld b paint b insp b pack."""
    ents, x = [], 0
    ents.append(("inbuf", (x, 3)))
    x += 1
    for i, st in enumerate(STATION_TYPES):
        ents.append((st, (x, 3)))
        x += 1
        if i < len(STATION_TYPES) - 1:
            ents.append(("buffer", (x, 3)))
            x += 1
    return ents


def scattered_layout(rng):
    cells = [(x, y) for x in range(GRID_W) for y in range(GRID_H)]
    rng.shuffle(cells)
    picked = cells[:len(STATION_TYPES) * 2]
    ents = [("inbuf", picked[0])]
    for i, st in enumerate(STATION_TYPES):
        ents.append((st, picked[1 + 2 * i]))
        if i < len(STATION_TYPES) - 1:
            ents.append(("buffer", picked[2 + 2 * i]))
    return ents


def validate(ents):
    """Invariants: distinct cells, in-bounds, one of each station type."""
    cells = [p for _, p in ents]
    assert len(set(cells)) == len(cells), "overlapping entities"
    for x, y in cells:
        assert 0 <= x < GRID_W and 0 <= y < GRID_H, "out of bounds"
    kinds = [k for k, _ in ents]
    for st in STATION_TYPES:
        assert kinds.count(st) == 1, f"missing/dup station {st}"
    assert kinds.count("inbuf") == 1
    assert kinds[0] == "inbuf"
    return True
