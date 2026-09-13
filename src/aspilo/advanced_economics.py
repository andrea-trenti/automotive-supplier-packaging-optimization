from __future__ import annotations
import math
import numpy as np
import pandas as pd


def packaging_cost_breakdown(parts, packaging, pack_choices, daily_demand):
    annual=daily_demand.drop(columns=['date']).sum()
    pm=packaging.set_index('packaging_id'); partm=parts.set_index('part_id'); rows=[]
    for _,r in pack_choices.iterrows():
        p=partm.loc[r.part_id]; k=pm.loc[r.packaging_id]
        cycles=math.ceil(max(1.0,float(annual[r.part_id]))/max(1,float(r.units_per_container)))
        if bool(k.returnable):
            material=cycles*k.purchase_cost_eur/max(k.lifetime_cycles,1)
            cleaning=cycles*k.cleaning_eur_cycle; repair=cycles*k.repair_eur_cycle; reverse=cycles*k.reverse_logistics_eur_cycle
        else:
            material=cycles*k.purchase_cost_eur; cleaning=repair=reverse=0.0
        handling=cycles*k.handling_cost_eur
        damage=float(r.annual_damage_cost_eur)
        rows.append((r.part_id,cycles,material,cleaning,repair,reverse,handling,damage))
    return pd.DataFrame(rows,columns=['part_id','annual_container_cycles','packaging_material_eur','cleaning_eur','repair_eur','reverse_logistics_eur','handling_eur','damage_eur'])


def transport_cost(routes, vehicles, weeks=50):
    vm=vehicles.set_index('vehicle_id')
    trips=routes.frequency_per_week.to_numpy(float)*weeks
    fixed=routes.vehicle_id.map(vm.fixed_cost_eur_trip).to_numpy(float)
    variable=routes.vehicle_id.map(vm.variable_eur_km).to_numpy(float)
    return float(np.sum(trips*(fixed+variable*routes.route_km.to_numpy(float))))


def dock_cost(docks, routes, wait_cost_per_truck_hour=58.0, overtime_cost_per_dock_hour=95.0, weeks=50):
    f=routes.set_index('route_id').frequency_per_week
    d=docks.copy(); annual_trips=d.route_id.map(f).fillna(0)*weeks
    wait=float(np.sum(d.waiting_h*annual_trips)*wait_cost_per_truck_hour)
    overtime=float(np.sum(d.overtime_h*annual_trips)*overtime_cost_per_dock_hour) if 'overtime_h' in d else 0.0
    return wait,overtime


def packaging_emissions_proxy(parts, packaging, pack_choices, daily_demand):
    """Synthetic packaging lifecycle proxy, kept separate from transport ISO/GLEC accounting.

    Factors are explicit scenario assumptions rather than measured EPD values.  They are
    intended only for internal trade-off sensitivity and are not reported as verified LCA.
    """
    annual=daily_demand.drop(columns=['date']).sum(); pm=packaging.set_index('packaging_id')
    # kgCO2e per kg packaging material manufactured; intentionally rounded scenario factors.
    embodied={'small_tote':2.4,'large_tote':2.4,'klt_like':2.4,'carton':0.85,'pallet':0.55,'returnable_rack':2.0}
    total=0.0
    for _,r in pack_choices.iterrows():
        k=pm.loc[r.packaging_id]; cycles=math.ceil(max(1,float(annual[r.part_id]))/max(1,float(r.units_per_container)))
        manufactured_units=cycles/max(float(k.lifetime_cycles),1.0) if bool(k.returnable) else cycles
        total+=manufactured_units*float(k.tare_kg)*embodied[k.packaging_type]
        if bool(k.returnable): total+=cycles*0.04  # cleaning/repair energy proxy per cycle
    return float(total)


def total_cost_components(parts,packaging,pack_choices,daily_demand,inventory,routes,vehicles,docks,mc,weeks=50):
    pk=packaging_cost_breakdown(parts,packaging,pack_choices,daily_demand)
    transport=transport_cost(routes,vehicles,weeks)
    wait,overtime=dock_cost(docks,routes,weeks=weeks)
    premium=float(mc.premium_freight_cost_eur.mean()); line=float(mc.line_stop_cost_eur.mean())
    comp={
        'transport_eur':transport,
        'packaging_material_eur':float(pk.packaging_material_eur.sum()),
        'packaging_cleaning_repair_eur':float(pk.cleaning_eur.sum()+pk.repair_eur.sum()),
        'reverse_logistics_eur':float(pk.reverse_logistics_eur.sum()),
        'inventory_eur':float(inventory.annual_inventory_holding_eur.sum()),
        'handling_eur':float(pk.handling_eur.sum()),
        'damage_eur':float(pk.damage_eur.sum()),
        'dock_wait_eur':wait,
        'dock_overtime_eur':overtime,
        'premium_freight_eur':premium,
        'line_stop_exposure_eur':line,
    }
    comp['total_landed_logistics_cost_eur']=float(sum(comp.values()))
    return comp


def probabilistic_npv(annual_saving, capex, seed=42, n=4096, discount_rate=.085, years=5):
    g=np.random.default_rng(seed)
    # Epistemic/implementation uncertainty: savings realization, capex, discount rate and ramp-up.
    save=annual_saving*g.triangular(.55,.82,1.05,n)
    cap=capex*g.triangular(.90,1.00,1.25,n)
    dr=np.clip(g.normal(discount_rate,.012,n),.03,.18)
    ramp=np.vstack([np.full(n,.65),np.full(n,.88),np.ones((years-2,n))])
    cash=save[None,:]*ramp
    npv=-cap.copy()
    for y in range(years): npv+=cash[y]/(1+dr)**(y+1)
    # simple interpolated payback with ramped undiscounted flows
    cum=-cap.copy(); payback=np.full(n,np.nan)
    for y in range(years):
        prev=cum.copy(); cum+=cash[y]
        hit=np.isnan(payback)&(cum>=0)
        payback[hit]=y+np.clip((-prev[hit])/np.maximum(cash[y,hit],1e-9),0,1)
    return pd.DataFrame({'npv_eur':npv,'annual_saving_realized_eur':save,'capex_eur':cap,'discount_rate':dr,'payback_years':payback})
