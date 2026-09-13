from __future__ import annotations
import math
import numpy as np
import pandas as pd


def units_per_container(part: pd.Series, pack: pd.Series) -> tuple[int,int,int,int]:
    q_volume=int(pack.internal_volume_m3 // max(part.unit_volume_m3,1e-12))
    q_weight=int(pack.max_payload_kg // max(part.unit_weight_kg,1e-12))
    q_geom=max(0,int(pack.internal_l_m//part.part_length_m)*int(pack.internal_w_m//part.part_width_m)*int(pack.internal_h_m//part.part_height_m))
    q=max(1,min(q_volume,q_weight,q_geom))
    if part.handling_class=='manual':
        q_manual=max(1,int((pack.max_manual_gross_kg-pack.tare_kg)//max(part.unit_weight_kg,1e-12)))
        q=min(q,q_manual)
    return q,q_volume,q_weight,q_geom


def optimize_packaging(parts:pd.DataFrame, packaging:pd.DataFrame, compatibility:pd.DataFrame, annual_demand:pd.Series, transport_volume_rate:float=42.0)->pd.DataFrame:
    comp=set(zip(compatibility.part_id,compatibility.packaging_id))
    results=[]
    for _,p in parts.iterrows():
        best=None
        for _,k in packaging.iterrows():
            if (p.part_id,k.packaging_id) not in comp: continue
            q,qv,qw,qg=units_per_container(p,k)
            cycles=math.ceil(max(1,float(annual_demand.get(p.part_id,0)))/q)
            if k.returnable:
                pack_cost=cycles*(k.purchase_cost_eur/max(k.lifetime_cycles,1)+k.cleaning_eur_cycle+k.repair_eur_cycle+k.reverse_logistics_eur_cycle)
            else:
                pack_cost=cycles*k.purchase_cost_eur
            gross_volume=cycles*(k.internal_l_m*k.internal_w_m*k.internal_h_m)
            cube_cost=gross_volume*transport_volume_rate
            touches=cycles*k.handling_cost_eur
            protection=max(0.18,1-9*k.base_damage_rate)
            expected_damage=float(annual_demand.get(p.part_id,0))*p.unit_value_eur*p.damage_sensitivity*(1-protection)*0.018
            total=pack_cost+cube_cost+touches+expected_damage
            used=min(1.0,q*p.unit_volume_m3/k.internal_volume_m3)
            gross_w=k.tare_kg+q*p.unit_weight_kg
            row=dict(part_id=p.part_id,packaging_id=k.packaging_id,units_per_container=q,q_volume=qv,q_weight=qw,q_geometry=qg,cube_utilization=used,gross_weight_kg=gross_w,annual_packaging_cost_eur=pack_cost,annual_handling_cost_eur=touches,annual_damage_cost_eur=expected_damage,annual_packaging_transport_proxy_eur=cube_cost,total_packaging_system_cost_eur=total,returnable=bool(k.returnable))
            if best is None or total<best['total_packaging_system_cost_eur']: best=row
        if best is None: raise ValueError(f'No feasible packaging for {p.part_id}')
        results.append(best)
    return pd.DataFrame(results)

def evaluate_packaging_selection(parts:pd.DataFrame, packaging:pd.DataFrame, annual_demand:pd.Series, selection:pd.DataFrame, transport_volume_rate:float=42.0)->pd.DataFrame:
    sel=selection.set_index('part_id'); pm=packaging.set_index('packaging_id'); rows=[]
    for _,p in parts.iterrows():
        k=pm.loc[sel.loc[p.part_id,'packaging_id']]
        q,qv,qw,qg=units_per_container(p,k); cycles=math.ceil(max(1,float(annual_demand.get(p.part_id,0)))/q)
        if k.returnable: pack_cost=cycles*(k.purchase_cost_eur/max(k.lifetime_cycles,1)+k.cleaning_eur_cycle+k.repair_eur_cycle+k.reverse_logistics_eur_cycle)
        else: pack_cost=cycles*k.purchase_cost_eur
        gross_volume=cycles*(k.internal_l_m*k.internal_w_m*k.internal_h_m); cube_cost=gross_volume*transport_volume_rate; touches=cycles*k.handling_cost_eur
        protection=max(0.18,1-9*k.base_damage_rate); expected_damage=float(annual_demand.get(p.part_id,0))*p.unit_value_eur*p.damage_sensitivity*(1-protection)*0.018
        total=pack_cost+cube_cost+touches+expected_damage
        rows.append(dict(part_id=p.part_id,packaging_id=k.name,units_per_container=q,q_volume=qv,q_weight=qw,q_geometry=qg,cube_utilization=min(1.0,q*p.unit_volume_m3/k.internal_volume_m3),gross_weight_kg=k.tare_kg+q*p.unit_weight_kg,annual_packaging_cost_eur=pack_cost,annual_handling_cost_eur=touches,annual_damage_cost_eur=expected_damage,annual_packaging_transport_proxy_eur=cube_cost,total_packaging_system_cost_eur=total,returnable=bool(k.returnable)))
    return pd.DataFrame(rows)
