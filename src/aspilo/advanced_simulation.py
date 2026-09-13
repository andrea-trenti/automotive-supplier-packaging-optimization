from __future__ import annotations
import numpy as np
import pandas as pd
from .utils import rng

CRIT_WEIGHT={'critical':1.0,'high':0.45,'medium':0.10,'low':0.02}
CRIT_MASK_LEVEL={'critical':True,'high':False,'medium':False,'low':False}


def _supplier_groups(suppliers: pd.DataFrame):
    sid=suppliers.supplier_id.str.extract(r'(\d+)')[0].astype(int).to_numpy()
    angle=np.arctan2(suppliers.y_km.to_numpy(float),suppliers.x_km.to_numpy(float))
    region=((angle+np.pi)/(np.pi/2)).astype(int)%4
    carrier=sid%6
    tier2=sid%12
    return dict(zip(suppliers.supplier_id,region)),dict(zip(suppliers.supplier_id,carrier)),dict(zip(suppliers.supplier_id,tier2))


def simulate_advanced(
    parts: pd.DataFrame,
    suppliers: pd.DataFrame,
    daily_demand: pd.DataFrame,
    inventory_policy: pd.DataFrame,
    seed: int=1,
    days: int=180,
    demand_multiplier: float=1.0,
    lead_time_multiplier: float=1.0,
    demand_cv_multiplier: float=1.0,
    correlated_risk: bool=True,
    supplier_outage_days: int=0,
    carrier_capacity_multiplier: float=1.0,
    container_availability: float=1.0,
    returnable_part_ids: set[str]|None=None,
    safety_stock_multiplier: float=1.0,
    critical_safety_multiplier: float=1.0,
    premium_trigger_fraction: float=.35,
    premium_success_base: float=.92,
    premium_freight_multiplier: float=4.5,
    line_stop_cost_per_hour: float=18000,
) -> dict:
    """Discrete-day inventory simulation with correlated demand and supply shocks.

    Existing BOM-driven daily demand provides structural correlation.  This layer adds
    common production shocks plus regional/carrier/Tier-2 supplier dependence.  It is a
    synthetic resilience experiment, not a calibrated plant simulation.
    """
    g=rng(seed)
    pids=parts.part_id.to_numpy(); n=len(pids)
    p=parts.set_index('part_id').loc[pids]
    s=suppliers.set_index('supplier_id')
    pol=inventory_policy.set_index('part_id').loc[pids].copy()
    demand_base=daily_demand.drop(columns=['date']).reindex(columns=pids).to_numpy(float)
    horizon=min(days,len(demand_base))
    demand=demand_base[:horizon].copy()*demand_multiplier
    # Common production/mix shock preserves BOM correlation rather than iid part noise.
    common=g.lognormal(mean=-.5*(.055*demand_cv_multiplier)**2,sigma=.055*demand_cv_multiplier,size=horizon)
    family_map={f:i for i,f in enumerate(sorted(parts.line_family.unique()))}
    fam_idx=np.array([family_map[x] for x in p.line_family])
    fam_shocks=g.lognormal(mean=-.5*(.035*demand_cv_multiplier)**2,sigma=.035*demand_cv_multiplier,size=(horizon,len(family_map)))
    demand=demand*common[:,None]*fam_shocks[:,fam_idx]

    sid=p.supplier_id.to_numpy(); sm=s.loc[sid]
    rel=sm.reliability_otif.to_numpy(float)
    lead_mean=sm.lead_time_days.to_numpy(float)*lead_time_multiplier
    lead_cv=sm.lead_time_cv.to_numpy(float)
    region_map,carrier_map,tier_map=_supplier_groups(suppliers)
    region=np.array([region_map[x] for x in sid]); carrier=np.array([carrier_map[x] for x in sid]); tier=np.array([tier_map[x] for x in sid])
    crit=p.criticality.to_numpy(); critical=(crit=='critical')
    crit_w=np.array([CRIT_WEIGHT[x] for x in crit])
    value=p.unit_value_eur.to_numpy(float); weight=p.unit_weight_kg.to_numpy(float); dist=sm.distance_km.to_numpy(float)

    rop=pol.reorder_point_units.to_numpy(float).copy()
    ss=pol.safety_stock_units.to_numpy(float)*safety_stock_multiplier
    ss[critical]*=critical_safety_multiplier
    cycle=pol.cycle_stock_units.to_numpy(float) if 'cycle_stock_units' in pol else pol.mean_daily_demand.to_numpy(float)
    rop=np.maximum(rop,pol.mean_daily_demand.to_numpy(float)*pol.mean_lead_time_days.to_numpy(float)+ss)
    # Daily time-step cannot represent more than one regular order per part/day; enforce at least one
    # average day of demand in each replenishment lot to avoid an artificial under-ordering bias at
    # high nominal shipment frequencies.
    order_qty=np.maximum.reduce([np.ones(n),2.0*cycle,1.25*pol.mean_daily_demand.to_numpy(float)])
    stock=rop+cycle
    maxh=horizon+60
    receipts=np.zeros((maxh,n),float); in_transit=np.zeros(n,float)
    shortage_run=np.zeros(n,int); shortage_durations=[]
    total_demand=served_total=critical_demand=critical_served=0.0
    stockout_events=premium_events=line_stop_events=0
    premium_cost=line_stop_cost=0.0; line_stop_hours_total=0.0
    critical_stockout_days=0

    returnable_mask_all = np.isin(pids, np.asarray(list(returnable_part_ids))) if (returnable_part_ids and container_availability < .999999) else None

    outage_supplier=None
    if supplier_outage_days>0:
        risk_score=(1-suppliers.reliability_otif.to_numpy(float))*suppliers.lead_time_days.to_numpy(float)
        outage_supplier=suppliers.iloc[int(np.argmax(risk_score))].supplier_id
    outage_start=max(10,horizon//3)

    for day in range(horizon):
        rec=receipts[day]; stock+=rec; in_transit=np.maximum(0,in_transit-rec)
        d=demand[day]
        total_demand+=d.sum(); critical_demand+=d[critical].sum()
        shortage=np.maximum(0,d-stock); base_served=d-shortage
        stock=np.maximum(0,stock-d)
        served=base_served.copy()
        idx=np.flatnonzero(shortage>1e-9)
        if idx.size:
            stockout_events+=idx.size
            critical_stockout_days+=int(np.any(shortage[critical]>0))
            shortage_run[idx]+=1
            ended=np.flatnonzero((shortage<=1e-9)&(shortage_run>0))
            for j in ended: shortage_durations.append(int(shortage_run[j])); shortage_run[j]=0
            # premium freight is triggered for larger shortages and critical material
            threshold=np.maximum(1.0,premium_trigger_fraction*pol.mean_daily_demand.to_numpy(float)[idx])
            trigger=(shortage[idx]>=threshold)|(critical[idx])
            tr=idx[trigger]
            if tr.size:
                success_prob=np.clip(premium_success_base*(.75+.25*rel[tr])*carrier_capacity_multiplier,.2,.995)
                if outage_supplier is not None and outage_start<=day<outage_start+supplier_outage_days:
                    success_prob=np.where(sid[tr]==outage_supplier,success_prob*.20,success_prob)
                success=g.random(tr.size)<success_prob
                if success.any():
                    j=tr[success]; premium_events+=j.size; served[j]+=shortage[j]
                    premium_cost+=float(np.sum((190+2.4*dist[j]+.30*shortage[j]*weight[j])*premium_freight_multiplier/4.5))
                fail=tr[~success]
                if fail.size:
                    j=fail[critical[fail]]
                    if j.size:
                        hours=np.minimum(6.0,0.25+2.5*shortage[j]/np.maximum(pol.mean_daily_demand.to_numpy(float)[j],1.0))
                        line_stop_events+=j.size; line_stop_hours_total+=float(hours.sum())
                        line_stop_cost+=float(np.sum(hours*line_stop_cost_per_hour*crit_w[j]))
        else:
            ended=np.flatnonzero(shortage_run>0)
            for j in ended: shortage_durations.append(int(shortage_run[j])); shortage_run[j]=0
        served_total+=served.sum(); critical_served+=served[critical].sum()

        inv_position=stock+in_transit
        reorder=inv_position<=rop
        ridx=np.flatnonzero(reorder)
        if ridx.size:
            # lognormal lead time with supplier-level variability
            sigma=np.sqrt(np.log1p(lead_cv[ridx]**2)); mu=np.log(np.maximum(.15,lead_mean[ridx]))-.5*sigma**2
            leads=g.lognormal(mu,sigma)
            if correlated_risk:
                # Common-cause shocks: rare regional disruption, carrier shortage and Tier-2 issue.
                reg_bad=g.random(4)<.012; carrier_bad=g.random(6)<.010; tier_bad=g.random(12)<.006
                leads*=1+1.25*reg_bad[region[ridx]]+0.85*carrier_bad[carrier[ridx]]+1.65*tier_bad[tier[ridx]]
            if outage_supplier is not None and outage_start<=day<outage_start+supplier_outage_days:
                leads=np.where(sid[ridx]==outage_supplier,leads+supplier_outage_days,leads)
            # container shortage affects returnable-part release and carrier shortage affects all replenishment.
            release=np.ones(ridx.size,bool)
            if returnable_mask_all is not None:
                mask=returnable_mask_all[ridx]
                release &= ~(mask & (g.random(ridx.size)>container_availability))
            release &= g.random(ridx.size)<np.clip(carrier_capacity_multiplier,.25,1.0)
            rr=ridx[release]
            if rr.size:
                l=leads[release]; due=day+np.maximum(1,np.rint(l).astype(int)); due=np.minimum(due,maxh-1)
                q=order_qty[rr]; np.add.at(receipts,(due,rr),q); in_transit[rr]+=q

    for j in np.flatnonzero(shortage_run>0): shortage_durations.append(int(shortage_run[j]))
    fill=served_total/max(total_demand,1.0); cfill=critical_served/max(critical_demand,1.0)
    p95dur=float(np.quantile(shortage_durations,.95)) if shortage_durations else 0.0
    return {
        'fill_rate':float(np.clip(fill,0,1)),
        'critical_fill_rate':float(np.clip(cfill,0,1)),
        'stockout_events':int(stockout_events),
        'critical_stockout_days':int(critical_stockout_days),
        'premium_freight_events':int(premium_events),
        'premium_freight_cost_eur':float(premium_cost),
        'line_stop_events':int(line_stop_events),
        'line_stop_hours':float(line_stop_hours_total),
        'line_stop_cost_eur':float(line_stop_cost),
        'p95_shortage_duration_days':p95dur,
        'total_disruption_cost_eur':float(premium_cost+line_stop_cost),
    }


def monte_carlo_advanced(parts,suppliers,daily_demand,inventory_policy,n=100,seed=1000,**kwargs):
    return pd.DataFrame([simulate_advanced(parts,suppliers,daily_demand,inventory_policy,seed=seed+i,**kwargs) for i in range(n)])
