from __future__ import annotations
import math
import pandas as pd

def size_returnable_fleet(parts,pack_choices,packaging,daily_demand,suppliers,loss_rate_per_cycle=0.0015,buffer_pct=.08):
    pk=packaging.set_index('packaging_id'); sm=suppliers.set_index('supplier_id'); dd=daily_demand.drop(columns=['date']).mean()
    m=parts[['part_id','supplier_id']].merge(pack_choices,on='part_id')
    rows=[]
    for _,r in m[m.returnable].iterrows():
        cpd=dd[r.part_id]/r.units_per_container
        loop=2*sm.loc[r.supplier_id].lead_time_days+1.0
        base=cpd*loop
        fleet=math.ceil(base*(1+buffer_pct)/(1-loss_rate_per_cycle))
        asset=fleet*pk.loc[r.packaging_id].purchase_cost_eur
        rows.append((r.part_id,r.packaging_id,cpd,loop,fleet,asset))
    return pd.DataFrame(rows,columns=['part_id','packaging_id','containers_per_day','loop_days','required_fleet','container_asset_eur'])

def lifecycle_break_even(packaging:pd.DataFrame)->pd.DataFrame:
    carton=packaging[packaging.packaging_type=='carton'].iloc[0]
    rows=[]
    for _,k in packaging[packaging.returnable].iterrows():
        var=k.cleaning_eur_cycle+k.repair_eur_cycle+k.reverse_logistics_eur_cycle
        denom=max(1e-9,carton.purchase_cost_eur-var)
        cycles=k.purchase_cost_eur/denom
        rows.append((k.packaging_id,cycles,var,carton.purchase_cost_eur))
    return pd.DataFrame(rows,columns=['packaging_id','break_even_cycles_vs_carton','returnable_variable_eur_cycle','carton_eur_cycle'])
