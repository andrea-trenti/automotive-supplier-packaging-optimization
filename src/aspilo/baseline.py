from __future__ import annotations
import math
import pandas as pd
from .packaging_optimizer import units_per_container

PREF=['PK04','PK01','PK03','PK02','PK05','PK06']

def manual_packaging_baseline(parts,packaging,compatibility,annual_demand):
    pm=packaging.set_index('packaging_id'); feasible={pid:set(g.packaging_id) for pid,g in compatibility.groupby('part_id')}; rows=[]
    for _,p in parts.iterrows():
        chosen=next((k for k in PREF if k in feasible[p.part_id]),next(iter(feasible[p.part_id])))
        k=pm.loc[chosen]; q,qv,qw,qg=units_per_container(p,k); cycles=math.ceil(max(1,float(annual_demand[p.part_id]))/q)
        pack_cost=cycles*((k.purchase_cost_eur/max(k.lifetime_cycles,1)+k.cleaning_eur_cycle+k.repair_eur_cycle+k.reverse_logistics_eur_cycle) if k.returnable else k.purchase_cost_eur)
        damage=float(annual_demand[p.part_id])*p.unit_value_eur*p.damage_sensitivity*k.base_damage_rate
        rows.append(dict(part_id=p.part_id,packaging_id=chosen,units_per_container=q,q_volume=qv,q_weight=qw,q_geometry=qg,cube_utilization=min(1,q*p.unit_volume_m3/k.internal_volume_m3),gross_weight_kg=k.tare_kg+q*p.unit_weight_kg,annual_packaging_cost_eur=pack_cost,annual_handling_cost_eur=cycles*k.handling_cost_eur,annual_damage_cost_eur=damage,annual_packaging_transport_proxy_eur=0,total_packaging_system_cost_eur=pack_cost+cycles*k.handling_cost_eur+damage,returnable=bool(k.returnable)))
    return pd.DataFrame(rows)

def direct_routes(suppliers,frequency,vehicles,weeks=50):
    veh=vehicles.sort_values('max_payload_kg').iloc[-1]; rows=[]
    for i,r in frequency.iterrows():
        f=max(3.0,float(r.minimum_physical_frequency)); f=next((x for x in [3,5,7.5,10,12.5,15,20,25,30,40] if x>=f),math.ceil(f))
        w=r.annual_weight_kg/(weeks*f); v=r.annual_cube_m3/(weeks*f); s=suppliers.set_index('supplier_id').loc[r.supplier_id]
        km=2*s.distance_km; duration=km/55+s.service_min/60
        positions=int(math.ceil(v / max(veh.usable_cube_m3 / veh.pallet_positions, 1e-9))); rows.append(dict(route_id=f'B{i:03d}',frequency_per_week=f,suppliers=r.supplier_id,n_stops=1,route_km=km,load_weight_kg=w,load_cube_m3=v,pallet_positions_used=positions,weight_utilization=w/veh.max_payload_kg,cube_utilization=v/veh.usable_cube_m3,pallet_position_utilization=positions/veh.pallet_positions,route_duration_h=duration,vehicle_id=veh.vehicle_id,feasible=(w<=veh.max_payload_kg and v<=veh.usable_cube_m3 and positions<=veh.pallet_positions and duration<=11.5)))
    return pd.DataFrame(rows)
