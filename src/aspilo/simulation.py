from __future__ import annotations
import numpy as np
import pandas as pd
from .utils import rng

CRIT_COST={'critical':1.0,'high':0.35,'medium':0.08,'low':0.015}

def simulate(parts,suppliers,daily_demand,inventory_policy,seed=1,premium_multiplier=4.5,line_stop_cost_per_hour=18000,line_stop_hours=0.75,days=250,shock=None,returnable_part_ids=None):
    g=rng(seed)
    part_ids=parts.part_id.to_numpy(); n=len(part_ids)
    pm=parts.set_index('part_id').loc[part_ids]
    sm=suppliers.set_index('supplier_id')
    pol=inventory_policy.set_index('part_id').loc[part_ids]
    demand=daily_demand.set_index('date').reindex(columns=part_ids).iloc[:days].to_numpy(float)
    if shock=='demand20': demand=demand*1.20
    sid=pm.supplier_id.to_numpy()
    rel=sm.loc[sid].reliability_otif.to_numpy(float)
    risk_class=sm.loc[sid].risk_class.to_numpy()
    if shock=='supplier_disruption': rel=np.where(risk_class=='A',rel*0.45,rel)
    lead_mean=sm.loc[sid].lead_time_days.to_numpy(float)
    if shock=='container_shortage' and returnable_part_ids is not None:
        mask=np.isin(part_ids,np.asarray(list(returnable_part_ids)))
        rel=np.where(mask,rel*0.82,rel); lead_mean=np.where(mask,lead_mean*1.35,lead_mean)
    lead_cv=sm.loc[sid].lead_time_cv.to_numpy(float)
    sigma=np.sqrt(np.log1p(lead_cv**2)); mu=np.log(np.maximum(.2,lead_mean))-0.5*sigma**2
    unit_value=pm.unit_value_eur.to_numpy(float)
    unit_weight=pm.unit_weight_kg.to_numpy(float)
    distance=sm.loc[sid].distance_km.to_numpy(float)
    crit=np.array([CRIT_COST[x] for x in pm.criticality])
    rop=pol.reorder_point_units.to_numpy(float)
    ss=pol.safety_stock_units.to_numpy(float)
    order_qty=np.maximum(1.0,(pol.mean_daily_demand*np.maximum(1.0,pol.delivery_interval_days)).to_numpy(float))
    stock=rop+ss
    max_horizon=days+30
    receipts=np.zeros((max_horizon,n),dtype=float)
    in_transit=np.zeros(n,dtype=float)
    stockouts=premium=line_stops=0; premium_cost=line_stop_cost=0.0; fill_demand=fill_served=0.0
    for day in range(min(days,len(demand))):
        rec=receipts[day]; stock+=rec; in_transit-=rec
        d=demand[day]; fill_demand+=d.sum(); shortage=np.maximum(0,d-stock); served=d-shortage; fill_served+=served.sum(); stock=np.maximum(0,stock-d)
        idx=np.flatnonzero(shortage>0)
        if idx.size:
            stockouts+=idx.size
            success=g.random(idx.size) < np.minimum(.995,0.75+0.24*rel[idx])
            if success.any():
                j=idx[success]; premium+=j.size; premium_cost+=float(np.sum(220.0 + 2.6*distance[j] + 0.35*shortage[j]*unit_weight[j])*premium_multiplier/4.5); fill_served+=float(np.sum(shortage[j]))
            if (~success).any():
                j=idx[~success]; line_stops+=int(np.sum(crit[j]>=0.35)); line_stop_cost+=float(np.sum(line_stop_cost_per_hour*line_stop_hours*crit[j]))
        reorder=(stock+in_transit)<=rop
        ridx=np.flatnonzero(reorder)
        if ridx.size:
            leads=g.lognormal(mu[ridx],sigma[ridx]); due=day+np.maximum(1,np.rint(leads).astype(int)); due=np.minimum(due,max_horizon-1)
            q=order_qty[ridx]
            np.add.at(receipts,(due,ridx),q); in_transit[ridx]+=q
    service=fill_served/max(fill_demand,1)
    return {'fill_rate':service,'stockout_events':stockouts,'premium_freight_events':premium,'premium_freight_cost_eur':premium_cost,'line_stop_events':line_stops,'line_stop_cost_eur':line_stop_cost,'total_disruption_cost_eur':premium_cost+line_stop_cost}

def monte_carlo(parts,suppliers,daily_demand,policy,n=300,seed=1000,**kwargs):
    return pd.DataFrame([simulate(parts,suppliers,daily_demand,policy,seed+i,**kwargs) for i in range(n)])
