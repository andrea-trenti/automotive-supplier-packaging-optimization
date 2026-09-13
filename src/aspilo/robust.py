from __future__ import annotations
import itertools
import numpy as np
import pandas as pd
from .policy_tools import build_policy
from .advanced_simulation import monte_carlo_advanced
from .advanced_economics import total_cost_components


def candidate_grid():
    # Pruned design: 12 materially distinct policies.  The second stock setting raises both
    # general and critical buffers, avoiding a 24-cell grid with many operationally redundant
    # combinations.
    rows=[]
    stock_settings=[(1.0,1.0),(1.15,1.35)]
    for fs,rb,(sm,cm) in itertools.product([.90,1.00,1.10],[0.0,.18],stock_settings):
        rows.append((fs,rb,sm,cm))
    return rows


def _scenario_kwargs(name):
    if name=='nominal': return {}
    if name=='correlated': return {'correlated_risk':True,'demand_cv_multiplier':1.15}
    if name=='demand10': return {'demand_multiplier':1.10,'demand_cv_multiplier':1.15}
    if name=='carrier': return {'carrier_capacity_multiplier':.92,'correlated_risk':True}
    if name=='container': return {'container_availability':.94,'correlated_risk':True}
    raise KeyError(name)


def screen_candidates(parts,suppliers,packaging,daily_demand,vehicles,pack_choices,base_freq,holding_rate,
                      cfg,returnable_part_ids,n_rep=16,seed=80000):
    rows=[]; policies={}
    scenarios=['nominal','correlated','demand10','carrier','container']
    for idx,(fs,rb,sm,cm) in enumerate(candidate_grid()):
        pol=build_policy(parts,suppliers,packaging,daily_demand,vehicles,pack_choices,base_freq,holding_rate,
                         freq_scale=fs,risk_freq_boost=rb,safety_mult=sm,critical_safety_mult=cm,
                         n_docks=cfg['n_receiving_docks'],returnable_buffer=.10)
        policies[idx]=pol
        all_mc=[]
        for j,sc in enumerate(scenarios):
            kw=_scenario_kwargs(sc)
            mc=monte_carlo_advanced(parts,suppliers,daily_demand,pol['inventory'],n=n_rep,seed=seed+idx*1000+j*100,
                                    days=180,returnable_part_ids=returnable_part_ids,
                                    premium_freight_multiplier=cfg['premium_freight_multiplier'],
                                    line_stop_cost_per_hour=cfg['line_stop_cost_per_hour'],**kw)
            mc['scenario']=sc; all_mc.append(mc)
        m=pd.concat(all_mc,ignore_index=True)
        comp=total_cost_components(parts,packaging,pack_choices,daily_demand,pol['inventory'],pol['routes'],vehicles,pol['docks'],m)
        critical_threshold=.9990
        chance=float((m.critical_fill_rate>=critical_threshold).mean())
        lsprob=float((m.line_stop_events>0).mean())
        tail=float(m.total_disruption_cost_eur[m.total_disruption_cost_eur>=m.total_disruption_cost_eur.quantile(.95)].mean())
        rows.append((idx,fs,rb,sm,cm,comp['total_landed_logistics_cost_eur'],float(pol['emissions'].annual_co2e_kg.sum()),float(pol['inventory'].avg_inventory_units.mul(pol['inventory'].unit_value_eur).sum()),m.fill_rate.mean(),m.critical_fill_rate.mean(),chance,lsprob,m.line_stop_events.mean(),m.p95_shortage_duration_days.quantile(.95),tail,pol['routes'].cube_utilization.mean(),pol['routes'].weight_utilization.mean()))
    df=pd.DataFrame(rows,columns=['candidate_id','frequency_scale','risk_frequency_boost','safety_multiplier','critical_safety_multiplier','annual_cost_eur','annual_co2e_kg','inventory_value_eur','fill_rate','critical_fill_rate','chance_critical_ge_999','line_stop_probability','mean_line_stop_events','p95_shortage_duration_days','cvar95_disruption_eur','mean_cube_utilization','mean_weight_utilization'])
    # Scenario-based chance constraint. If multiple feasible, select minimum annual cost + small tail-risk penalty.
    feasible=df[(df.chance_critical_ge_999>=.95)&(df.line_stop_probability<=.55)].copy()
    if feasible.empty:
        # Transparent fallback: choose lexicographically on service then cost; caller documents infeasibility.
        feasible=df.sort_values(['chance_critical_ge_999','line_stop_probability','annual_cost_eur'],ascending=[False,True,True]).head(5).copy()
    feasible['robust_score']=feasible.annual_cost_eur+.15*feasible.cvar95_disruption_eur
    best=feasible.sort_values('robust_score').iloc[0]
    return df,policies[int(best.candidate_id)],best


def pareto_front(df,cost='annual_cost_eur',emissions='annual_co2e_kg'):
    x=df.sort_values(cost).copy(); keep=[]; best=np.inf
    for i,r in x.iterrows():
        if r[emissions]<best-1e-9:
            keep.append(i); best=r[emissions]
    return x.loc[keep].sort_values(cost).reset_index(drop=True)
