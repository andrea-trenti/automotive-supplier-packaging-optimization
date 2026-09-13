# Mathematical Formulation

## Sets
- `i ∈ I`: parts
- `s ∈ S`: suppliers
- `p ∈ P`: packaging candidates
- `f ∈ F`: replenishment frequencies
- `r ∈ R`: routes
- `v ∈ V`: vehicle types

## Core binary decisions
`x_ip = 1` if part `i` uses package `p`.

`z_sf = 1` if supplier `s` uses replenishment frequency `f`.

In the reduced integrated MILP currently solved in code, routing is downstream of the packaging-frequency block. Therefore the repository calls the solved model **integrated packaging-frequency MILP**, not a full exact IRP/VRP MILP.

## Packaging capacity
For part `i` and package `p`:

`q_ip = min(q_volume, q_weight, q_geometry, q_manual)` where applicable.

`q_volume = floor(V_p / v_i)`

`q_weight = floor(W_p / w_i)`

`q_geometry = floor(L_p/l_i) floor(B_p/b_i) floor(H_p/h_i)`

The geometry term prevents a pure volume ratio from accepting physically impossible packing.

## Assignment
For every part:

`Σ_p x_ip = 1`

Only compatibility-approved `(i,p)` combinations exist in the decision vector.

For every supplier:

`Σ_f z_sf = 1`

## Shared supplier transport capacity
Annual gross packaging cube for supplier `s` must fit the selected annual transport capacity:

`Σ_{i∈I_s} Σ_p C_ip V_p x_ip ≤ 50 η_V V_truck Σ_f f z_sf`

where `C_ip` is annual container cycles and `η_V=0.90` is a synthetic planning utilization limit.

Annual material weight similarly satisfies:

`Σ_{i∈I_s} D_i w_i ≤ 50 η_W W_truck Σ_f f z_sf`.

These constraints are important: they prevent the frequency optimizer from selecting a cadence that cannot physically move a supplier's annual volume.

## Inventory
For demand mean `μ_d`, demand standard deviation `σ_d`, mean lead time `μ_L` and lead-time standard deviation `σ_L`, the current approximation uses:

`σ_LT = sqrt( μ_L σ_d² + μ_d² σ_L² )`

`SS = z σ_LT`

`ROP = μ_d μ_L + SS`

Cycle stock is frequency-dependent:

`CS = 0.5 μ_d (5/f)`.

Pipeline stock:

`PI = μ_d μ_L`.

The service target is criticality-dependent and is verified by stochastic simulation and out-of-sample evaluation rather than accepted analytically.

## Routing
After the integrated MILP, suppliers are grouped by frequency and angular sweep, then sequenced by nearest feasible next stop. Every route must respect both:

`Σ load_weight ≤ W_v`

`Σ load_cube ≤ V_v`

and a synthetic maximum route-duty duration. This is the final downstream routing heuristic used by the release; it is explicitly **not** presented as globally optimal CVRPTW/IRP routing.

## Dock scheduling
Routes compete for a finite set of receiving docks. List scheduling produces requested arrival, scheduled start, waiting and service times. Infinite dock capacity is explicitly disallowed.

## Returnable loop
For a returnable package:

`Fleet_i ≈ ceil( containers_per_day_i × loop_days_i × (1+buffer) / (1-loss_rate) )`.

The analytical fleet equation provides the theoretical sizing precursor. The final release also executes an explicit state-conservation simulation across supplier, loaded transit, plant, empty transit, repair/cleaning and lost-container states.

## Emissions
Final transport GHG accounting is activity based:

`CO2e = tonne-km × EF_WTW`.

The default HGV factor is parameterized and traceable to a GLEC starting-point value; it is not claimed to be fleet-specific measurement.

## Total landed logistics cost

`TLC = Transport + Packaging + Inventory + Handling + Damage + Reverse Logistics + Premium Freight + Expected Disruption`.

The objective intentionally exceeds isolated transport cost.

## Tail risk
For disruption cost random variable `C`, the repository reports `P95(C)` and:

`CVaR_0.95 = E[C | C ≥ VaR_0.95]`.

## Current solver status
The reduced packaging-frequency MILP is solved with SciPy/HiGHS. Solver status, objective, node count and MIP gap are exported and never replaced by an unsupported claim of global optimality for the full network problem.
