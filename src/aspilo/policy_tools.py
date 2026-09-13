from __future__ import annotations
import math
import numpy as np
import pandas as pd
from .routing import supplier_flow_stats, build_milk_runs
from .inventory import compute_inventory_policy, add_frequency_cycle_stock
from .dock_scheduling import schedule_receiving
from .returnables import size_returnable_fleet
from .emissions import route_emissions

FREQ_GRID=np.array([1,2,3,5,7.5,10,12.5,15,20,25,30,40],float)


def adjusted_frequency(base_freq, flow, suppliers, vehicles, scale=1.0, risk_boost=0.0):
    veh=vehicles.sort_values('max_payload_kg').iloc[-1]
    fm=base_freq.set_index('supplier_id').frequency_per_week.to_dict(); sm=suppliers.set_index('supplier_id')
    rows=[]
    for _,r in flow.iterrows():
        minf=max(r.annual_weight_kg/(50*.90*veh.max_payload_kg),r.annual_cube_m3/(50*.90*veh.usable_cube_m3),1.0)
        risk=(1-sm.loc[r.supplier_id].reliability_otif)/max(1e-6,1-.90)
        target=max(minf,fm.get(r.supplier_id,5)*scale*(1+risk_boost*min(1.5,risk)))
        feasible=FREQ_GRID[FREQ_GRID>=target-1e-12]; f=float(feasible[0] if len(feasible) else math.ceil(target))
        rows.append((r.supplier_id,f,minf,r.annual_weight_kg,r.annual_cube_m3,r.annual_value,r.distance_km))
    return pd.DataFrame(rows,columns=['supplier_id','frequency_per_week','minimum_physical_frequency','annual_weight_kg','annual_cube_m3','annual_value','distance_km'])


def build_policy(parts,suppliers,packaging,daily_demand,vehicles,pack_choices,base_freq,holding_rate=.22,
                 freq_scale=1.0,risk_freq_boost=0.0,safety_mult=1.0,critical_safety_mult=1.0,
                 n_docks=5,returnable_buffer=.10):
    flow=supplier_flow_stats(parts,daily_demand,pack_choices,packaging,suppliers)
    freq=adjusted_frequency(base_freq,flow,suppliers,vehicles,freq_scale,risk_freq_boost)
    routes=build_milk_runs(suppliers,freq,vehicles)
    inv=compute_inventory_policy(parts,suppliers,daily_demand,holding_rate)
    fpart=parts.set_index('part_id').supplier_id.map(freq.set_index('supplier_id').frequency_per_week)
    inv=add_frequency_cycle_stock(inv,fpart,holding_rate)
    inv['safety_stock_units']*=safety_mult
    crit=inv.criticality.eq('critical')
    inv.loc[crit,'safety_stock_units']*=critical_safety_mult
    inv['reorder_point_units']=inv.mean_daily_demand*inv.mean_lead_time_days+inv.safety_stock_units
    inv['avg_inventory_units']=inv.safety_stock_units+inv.cycle_stock_units+inv.pipeline_inventory_units
    inv['annual_inventory_holding_eur']=inv.avg_inventory_units*inv.unit_value_eur*holding_rate
    docks=schedule_receiving(routes,n_docks=n_docks,stagger=True)
    ret=size_returnable_fleet(parts,pack_choices,packaging,daily_demand,suppliers,buffer_pct=returnable_buffer)
    em=route_emissions(routes,vehicles)
    return {'packaging':pack_choices,'frequency':freq,'routes':routes,'inventory':inv,'docks':docks,'returnables':ret,'emissions':em}
