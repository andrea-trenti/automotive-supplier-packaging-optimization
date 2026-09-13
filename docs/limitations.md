# Limitations and Model-Risk Register

## Empirical validity
The largest limitation is not algorithm count; it is empirical validation. All suppliers, parts, costs, distances, demand, reliability and packaging parameters are synthetic. The model demonstrates an engineering workflow, not a plant-calibrated answer.

## Baseline sensitivity
The final headline uses **Smart Baseline B**, not the deliberately weak Baseline A. Baseline A is retained only as a falsification reference: the original ~40.2% saving does not survive the stronger benchmark. The final 9.33% saving remains a **within-synthetic-study comparison**, not a claim that an automotive OEM would save the same percentage.

## Routing optimality
The integrated MILP proves optimality only for the reduced packaging-frequency formulation. Milk-run construction is currently a capacity-feasible heuristic. No claim of global CVRPTW/IRP optimality is made.

## Time granularity
Inventory simulation is daily. High-frequency same-day milk runs are therefore aggregated. A sub-daily DES is needed before making claims about intra-shift line-side stockout risk.

## Packaging physics
The model checks dimensions, volume, weight and handling-class compatibility, but it does not solve a 3-D bin-packing problem with dunnage, orientation, center of gravity and load-securing rules.

## Ergonomics
Manual gross-weight limits are synthetic screening constraints. They are not RULA/REBA, ISO 11228 or legal compliance determinations.

## Emissions
GLEC/ISO methodology is used as the accounting frame. Default emission intensities are not carrier-specific measurements. Detailed fuel, vehicle, empty-running and lane data would materially change CO2e estimates.

## Supplier risk
The final stress and OOS layers include correlated/common-cause disruption scenarios, but the dependence structure is synthetic rather than estimated from observed supplier, carrier or Tier-2 histories. Real regional and shared-source dependencies could materially change tail risk.

## TTS/TTR
Current TTS/TTR values are exposure proxies derived from synthetic inventory/recovery assumptions. They must not be presented as measured supplier recovery performance.

## Returnables
The final release includes explicit state-conservation simulation and distinguishes theoretical from operational fleet requirements. Repair/cleaning capacity, supplier dwell distributions and loss/repair rates remain synthetic and are not calibrated from an industrial container pool.

## Business case
The final release includes implementation CAPEX assumptions and 4,096-draw probabilistic NPV/payback analysis with double-count reconciliation. The modeled uncertainty support remains synthetic: `P(NPV > 0) = 100%` means the selected synthetic distribution does not cross zero, **not** that an industrial implementation is certain to create value. Payer allocation, contractual terms and implementation delays remain simplified.
