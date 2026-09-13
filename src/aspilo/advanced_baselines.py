from __future__ import annotations
import math
import numpy as np
import pandas as pd
from .packaging_optimizer import optimize_packaging
from .baseline import manual_packaging_baseline, direct_routes
from .routing import supplier_flow_stats, build_milk_runs, optimize_supplier_frequency
from .inventory import compute_inventory_policy, add_frequency_cycle_stock

FREQ_GRID=np.array([1,2,3,5,7.5,10,12.5,15,20,25,30,40],float)


def _round_feasible_frequency(minimum: float, preferred: float) -> float:
    target=max(float(minimum),float(preferred))
    feasible=FREQ_GRID[FREQ_GRID>=target-1e-12]
    return float(feasible[0] if len(feasible) else math.ceil(target))


def baseline_a(parts,suppliers,packaging,compatibility,daily_demand,vehicles,holding_rate=.22):
    """Current-style baseline: manual packaging, direct shipments, fixed/minimum-feasible frequency."""
    annual=daily_demand.drop(columns=['date']).sum()
    pack=manual_packaging_baseline(parts,packaging,compatibility,annual)
    flow=optimize_supplier_frequency(parts,suppliers,daily_demand,pack,packaging,vehicles,holding_rate)
    routes=direct_routes(suppliers,flow,vehicles)
    freq=routes[['suppliers','frequency_per_week']].rename(columns={'suppliers':'supplier_id'})
    inv=compute_inventory_policy(parts,suppliers,daily_demand,holding_rate)
    fpart=parts.set_index('part_id').supplier_id.map(freq.set_index('supplier_id').frequency_per_week)
    inv=add_frequency_cycle_stock(inv,fpart,holding_rate)
    return {'packaging':pack,'frequency':freq,'routes':routes,'inventory':inv}


def baseline_b(parts,suppliers,packaging,compatibility,daily_demand,vehicles,holding_rate=.22):
    """Reasonable planning heuristic: compatible packaging + policy frequencies + milk-runs + ROP.

    This intentionally avoids solving the joint MILP.  It approximates a competent planner who
    uses physically feasible packaging, distance/volume frequency rules and geographic milk-run
    consolidation.
    """
    annual=daily_demand.drop(columns=['date']).sum()
    # local packaging optimization is allowed, but remains blind to route-level consolidation.
    pack=optimize_packaging(parts,packaging,compatibility,annual)
    stats=supplier_flow_stats(parts,daily_demand,pack,packaging,suppliers)
    veh=vehicles.sort_values('max_payload_kg').iloc[-1]
    rows=[]
    sm=suppliers.set_index('supplier_id')
    for _,r in stats.iterrows():
        minf=max(r.annual_weight_kg/(50*.90*veh.max_payload_kg),r.annual_cube_m3/(50*.90*veh.usable_cube_m3),1.0)
        # Operationally credible rule: nearby/high-volume suppliers ship more often, distant/low-volume less often.
        cube_week=r.annual_cube_m3/50
        if cube_week>55: pref=10
        elif cube_week>30: pref=7.5
        elif cube_week>14: pref=5
        elif cube_week>6: pref=3
        else: pref=2
        if sm.loc[r.supplier_id].distance_km<70 and cube_week>18: pref=max(pref,5)
        if sm.loc[r.supplier_id].reliability_otif<.93: pref=max(pref,5)
        f=_round_feasible_frequency(minf,pref)
        rows.append((r.supplier_id,f,minf,r.annual_weight_kg,r.annual_cube_m3,r.annual_value,r.distance_km))
    freq=pd.DataFrame(rows,columns=['supplier_id','frequency_per_week','minimum_physical_frequency','annual_weight_kg','annual_cube_m3','annual_value','distance_km'])
    routes=build_milk_runs(suppliers,freq,vehicles)
    inv=compute_inventory_policy(parts,suppliers,daily_demand,holding_rate)
    fpart=parts.set_index('part_id').supplier_id.map(freq.set_index('supplier_id').frequency_per_week)
    inv=add_frequency_cycle_stock(inv,fpart,holding_rate)
    return {'packaging':pack,'frequency':freq,'routes':routes,'inventory':inv}


def sequential_policy(parts,suppliers,packaging,compatibility,daily_demand,vehicles,holding_rate=.22):
    """Sequential local optimization: package first, then frequency, then routing, then inventory."""
    annual=daily_demand.drop(columns=['date']).sum()
    pack=optimize_packaging(parts,packaging,compatibility,annual)
    freq=optimize_supplier_frequency(parts,suppliers,daily_demand,pack,packaging,vehicles,holding_rate)
    routes=build_milk_runs(suppliers,freq,vehicles)
    inv=compute_inventory_policy(parts,suppliers,daily_demand,holding_rate)
    fpart=parts.set_index('part_id').supplier_id.map(freq.set_index('supplier_id').frequency_per_week)
    inv=add_frequency_cycle_stock(inv,fpart,holding_rate)
    return {'packaging':pack,'frequency':freq,'routes':routes,'inventory':inv}
