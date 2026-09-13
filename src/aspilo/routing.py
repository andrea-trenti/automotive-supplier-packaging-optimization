from __future__ import annotations
import math
import numpy as np
import pandas as pd

def euclid(a,b): return float(math.hypot(a[0]-b[0],a[1]-b[1]))

def optimize_supplier_frequency(parts,suppliers,daily_demand,pack_choices,packaging,vehicles,holding_rate=0.22,weeks=50):
    p=parts[['part_id','supplier_id','unit_weight_kg','unit_value_eur']].merge(pack_choices[['part_id','packaging_id','units_per_container']],on='part_id')
    pk=packaging.set_index('packaging_id'); veh=vehicles.sort_values('max_payload_kg').iloc[-1]
    dd=daily_demand.drop(columns=['date']); ann=dd.sum()
    p['annual_units']=p.part_id.map(ann); p['annual_weight_kg']=p.annual_units*p.unit_weight_kg
    p['annual_cube_m3']=[math.ceil(max(1,a)/q)*(pk.loc[k].internal_l_m*pk.loc[k].internal_w_m*pk.loc[k].internal_h_m) for a,q,k in zip(p.annual_units,p.units_per_container,p.packaging_id)]
    agg=p.groupby('supplier_id').agg(annual_weight_kg=('annual_weight_kg','sum'),annual_cube_m3=('annual_cube_m3','sum')).reset_index()
    value=(p.annual_units*p.unit_value_eur).groupby(p.supplier_id).sum(); agg['annual_value']=agg.supplier_id.map(value)
    agg=agg.merge(suppliers[['supplier_id','distance_km','reliability_otif']],on='supplier_id')
    candidate_freqs=np.array([1,2,3,5,7.5,10,12.5,15,20,25,30],float)
    rows=[]
    for _,r in agg.iterrows():
        min_f=max(r.annual_weight_kg/(weeks*0.90*veh.max_payload_kg),r.annual_cube_m3/(weeks*0.90*veh.usable_cube_m3),0.5)
        feasible_freqs=candidate_freqs[candidate_freqs>=min_f-1e-12]
        if not len(feasible_freqs): feasible_freqs=np.array([math.ceil(min_f)])
        best=None
        for f in feasible_freqs:
            trips=weeks*f
            transport=trips*(85+2*r.distance_km*1.05)
            cycle_days=5/f; cycle_inv_value=r.annual_value/250*cycle_days/2; inventory=cycle_inv_value*holding_rate
            risk=(1-r.reliability_otif)*cycle_days*r.annual_value*0.003
            dock_penalty=max(0,f-10)*500
            total=transport+inventory+risk+dock_penalty
            cand=(total,f,transport,inventory,risk,min_f)
            if best is None or cand[0]<best[0]: best=cand
        rows.append((r.supplier_id,best[1],best[2],best[3],best[4],r.annual_weight_kg,r.annual_cube_m3,r.distance_km,best[5]))
    return pd.DataFrame(rows,columns=['supplier_id','frequency_per_week','annual_transport_proxy_eur','annual_cycle_inventory_proxy_eur','annual_service_risk_proxy_eur','annual_weight_kg','annual_cube_m3','distance_km','minimum_physical_frequency'])

def build_milk_runs(suppliers,frequency,vehicles,working_weeks=50):
    s=suppliers.merge(frequency,on='supplier_id'); s['angle']=np.arctan2(s.y_km,s.x_km)
    veh=vehicles.sort_values('max_payload_kg').iloc[-1]; routes=[]; route_id=0
    # high frequency suppliers can still share a route if their per-pickup loads fit jointly
    for f,grp in s.groupby('frequency_per_week'):
        g=grp.sort_values('angle').copy(); current=[]; w=v=0.0
        for _,r in g.iterrows():
            pw=r.annual_weight_kg/(working_weeks*f); pv=r.annual_cube_m3/(working_weeks*f)
            # physical feasibility must already hold supplier-by-supplier
            if pw>0.92*veh.max_payload_kg+1e-9 or pv>0.92*veh.usable_cube_m3+1e-9:
                raise ValueError(f'Frequency infeasible for {r.supplier_id}: {pw:.1f} kg, {pv:.1f} m3')
            trial=current+[(r.supplier_id,pw,pv)]
            cand=_finalize_route(route_id,f,trial,suppliers,veh)
            if current and (cand['weight_utilization']>0.92 or cand['cube_utilization']>0.92 or cand['route_duration_h']>11.5):
                routes.append(_finalize_route(route_id,f,current,suppliers,veh)); route_id+=1; current=[(r.supplier_id,pw,pv)]
            else:
                current=trial
        if current: routes.append(_finalize_route(route_id,f,current,suppliers,veh)); route_id+=1
    return pd.DataFrame(routes)

def _finalize_route(route_id,f,current,suppliers,veh):
    sm=suppliers.set_index('supplier_id'); unvisited=[x[0] for x in current]; seq=[]; loc=(0,0); km=0
    while unvisited:
        nxt=min(unvisited,key=lambda sid:euclid(loc,(sm.loc[sid].x_km,sm.loc[sid].y_km)))
        pt=(sm.loc[nxt].x_km,sm.loc[nxt].y_km); km+=euclid(loc,pt); seq.append(nxt); loc=pt; unvisited.remove(nxt)
    km+=euclid(loc,(0,0)); w=sum(x[1] for x in current); v=sum(x[2] for x in current)
    service=sum(sm.loc[sid].service_min for sid in seq)/60; drive=km/55; duration=drive+service
    positions=int(math.ceil(v / max(veh.usable_cube_m3 / veh.pallet_positions, 1e-9))); return dict(route_id=f'R{route_id:03d}',frequency_per_week=f,suppliers='|'.join(seq),n_stops=len(seq),route_km=km,load_weight_kg=w,load_cube_m3=v,pallet_positions_used=positions,weight_utilization=w/veh.max_payload_kg,cube_utilization=v/veh.usable_cube_m3,pallet_position_utilization=positions/veh.pallet_positions,route_duration_h=duration,vehicle_id=veh.vehicle_id,feasible=bool(duration<=11.5 and w<=veh.max_payload_kg and v<=veh.usable_cube_m3 and positions<=veh.pallet_positions))

def supplier_flow_stats(parts,daily_demand,pack_choices,packaging,suppliers,weeks=50):
    p=parts[['part_id','supplier_id','unit_weight_kg','unit_value_eur']].merge(pack_choices[['part_id','packaging_id','units_per_container']],on='part_id')
    pk=packaging.set_index('packaging_id'); ann=daily_demand.drop(columns=['date']).sum(); p['annual_units']=p.part_id.map(ann); p['annual_weight_kg']=p.annual_units*p.unit_weight_kg
    p['annual_cube_m3']=[math.ceil(max(1,a)/q)*(pk.loc[k].internal_l_m*pk.loc[k].internal_w_m*pk.loc[k].internal_h_m) for a,q,k in zip(p.annual_units,p.units_per_container,p.packaging_id)]
    agg=p.groupby('supplier_id').agg(annual_weight_kg=('annual_weight_kg','sum'),annual_cube_m3=('annual_cube_m3','sum')).reset_index()
    value=(p.annual_units*p.unit_value_eur).groupby(p.supplier_id).sum(); agg['annual_value']=agg.supplier_id.map(value)
    return agg.merge(suppliers[['supplier_id','distance_km','reliability_otif']],on='supplier_id')
