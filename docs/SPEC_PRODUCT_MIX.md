# SPEC: Product Mix — multiple manufacturing chains (v0, 2026-10-17)

**Status:** design refined from alex's feature sketch (2026-10-17), bead
`amdrome-product-mix` (P2). Sequenced AFTER amdrome-x4i lands the training
harness on a stable engine (feature-flagged off until then). v2 (BOM
trees, multi-level assembly) is explicitly out of scope.

## 1. Products catalog (engine config)

`PRODUCTS` in `simulator/src/amdrome_sim/products.py` (loaded via engine
config; default catalog):

| id | route | rationale |
|---|---|---|
| `A_core` | cut → form → weld → paint → inspect → pack | today's full route; premium price |
| `B_bare` | cut → form → weld → pack | skips paint+inspect: cheap, fast, but escapes flow to the customer (high penalty exposure) — the quality-vs-speed trade made physical |
| `C_double` | cut → form → weld → weld → inspect → pack | revisits weld (two passes): longer route, wear concentrated on weld, higher price |

Each product: `{route, unit_price_range, penalty profile, quality_floor}`.
Route length is a first-class economic axis: the layout calibration
(research/2026-10-13-layout-variance.md) showed transport dominates
cycle-time variance — short-route products tolerate scattered layouts,
long-route demand punishes them, so **bidding IS layout strategy**.

## 2. Jobs & flow

- Job carries `product_id`; routing follows `PRODUCTS[p].route`
  (station-type sequence, may skip/revisit — `buf_after` becomes
  route-dependent per job, resolved at release time).
- Buffers stay SHARED with product tags (v0): queue entries tagged;
  kanban cards report per-product depth (partial observability kept).
- Uniform job size in v0 (no buffer-slot multipliers).

## 3. Demand & market (anti-tape lever #2)

- Per-product arrival λ_p drawn from the hyperprior per episode —
  **the mix itself varies per episode** (beyond today's global λ).
- Contracts arrive per product (price/penalty drawn per-product);
  bidding on contracts = choosing the product mix. Settlement,
  escapes and PPM attribute per product.
- Spot-sales fallback stays (uncontracted units sell at 0.75×input spot
  regardless of product in v0; per-product spot is a v2 lever).

## 4. Monitoring/quality

SPC probes, CUSUM, PM stay per-station (unchanged). Inspection catches
defects only for products whose route includes `inspect` — B_bare ships
unverified (escape risk priced by its penalty profile).

## 5. Acceptance gates (bead closure criteria)

1. Mix-scheduling skill: an oracle/reactive mix bidder beats the best
   single-product bidder (paired, n≥200, p<0.01).
2. Layout-variance re-measured under the mixed catalog (the 53–64%
   single-route number must be re-established or re-scoped).
3. Anti-tape gate re-run (per-product λ hyperprior should strengthen it).
4. Determinism/golden re-pinned; 13+ tests green incl. per-product
   routing invariants (job never visits a station not in its route).

## 6. Sequencing & risk

- Feature flag `product_mix` (default False) — engine behaves exactly as
  today when off; x4i training harness lands on the stable single-route
  engine first.
- Main risk: route-dependent routing invalidates `Line.buf_after`
  wiring assumptions — jobs resolve their next hop from their own route,
  stations/buffers unchanged.
