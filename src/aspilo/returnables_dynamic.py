from __future__ import annotations
import math
import numpy as np
import pandas as pd


def fleet_requirements(parts,pack_choices,packaging,daily_demand,suppliers,safety_pct=.10,loss_rate_per_cycle=.0015):
    pm=packaging.set_index('packaging_id'); sm=suppliers.set_index('supplier_id'); mean=daily_demand.drop(columns=['date']).mean()
    m=parts[['part_id','supplier_id']].merge(pack_choices,on='part_id')
    rows=[]
    for _,r in m[m.returnable].iterrows():
        cpd=float(mean[r.part_id])/max(1,float(r.units_per_container))
        lead=float(sm.loc[r.supplier_id].lead_time_days)
        loop=max(2.0,2*lead+1.5)
        theoretical=max(1,math.ceil(cpd*loop))
        operational=math.ceil(theoretical*(1+safety_pct)+cpd*250*loss_rate_per_cycle)
        rows.append((r.part_id,r.packaging_id,cpd,loop,theoretical,operational,operational-theoretical,operational*pm.loc[r.packaging_id].purchase_cost_eur))
    return pd.DataFrame(rows,columns=['part_id','packaging_id','containers_per_day','loop_days','minimum_theoretical_fleet','operational_fleet','safety_allowance_units','container_asset_eur'])


def simulate_returnable_loop(parts,pack_choices,packaging,daily_demand,suppliers,seed=1,days=180,safety_pct=.10,loss_rate_per_cycle=.0015,repair_prob=.012,repair_days=3):
    """Part-level closed-loop state simulation with explicit conservation accounting."""
    g=np.random.default_rng(seed)
    req=fleet_requirements(parts,pack_choices,packaging,daily_demand,suppliers,safety_pct,loss_rate_per_cycle)
    if req.empty:
        return pd.DataFrame(),pd.DataFrame()
    meta=parts[['part_id','supplier_id']].merge(pack_choices[['part_id','packaging_id','units_per_container','returnable']],on='part_id')
    meta=meta[meta.returnable].merge(req,on=['part_id','packaging_id'])
    sm=suppliers.set_index('supplier_id')
    demand=daily_demand.set_index('date')
    state_rows=[]; summary=[]
    for _,r in meta.iterrows():
        pid=r.part_id; fleet=int(r.operational_fleet); supplier=fleet
        loaded_q=[0]*(days+20); empty_q=[0]*(days+20); repair_q=[0]*(days+20)
        plant=0; lost=0; shortages=0; shipped=0
        lead=max(1,int(round(float(sm.loc[r.supplier_id].lead_time_days))))
        for d in range(min(days,len(demand))):
            supplier+=empty_q[d]+repair_q[d]
            plant+=loaded_q[d]
            need=int(math.ceil(float(demand.iloc[d][pid])/max(1,float(r.units_per_container))))
            send=min(supplier,need); shortages+=max(0,need-send); shipped+=send; supplier-=send
            # loaded transport to plant
            loaded_q[min(d+lead,len(loaded_q)-1)]+=send
            # containers unloaded at plant on arrival and returned next day; represent plant dwell one day
            returns=plant; plant=0
            if returns:
                losses=int(g.binomial(returns,loss_rate_per_cycle)); lost+=losses; survivors=returns-losses
                repairs=int(g.binomial(survivors,repair_prob)); normal=survivors-repairs
                empty_q[min(d+lead,len(empty_q)-1)]+=normal
                repair_q[min(d+repair_days+lead,len(repair_q)-1)]+=repairs
            live=supplier+plant+sum(loaded_q[d+1:])+sum(empty_q[d+1:])+sum(repair_q[d+1:])
            conserved=(live+lost)==fleet
            state_rows.append((pid,d,supplier,plant,sum(loaded_q[d+1:]),sum(empty_q[d+1:]),sum(repair_q[d+1:]),lost,live,conserved))
        summary.append((pid,fleet,shipped,shortages,lost,shortages/max(shipped+shortages,1)))
    states=pd.DataFrame(state_rows,columns=['part_id','day','at_supplier','at_plant','loaded_transit','empty_transit','cleaning_repair','lost','live_fleet','conserved'])
    summ=pd.DataFrame(summary,columns=['part_id','operational_fleet','containers_shipped','container_shortages','containers_lost','container_shortage_rate'])
    return states,summ
