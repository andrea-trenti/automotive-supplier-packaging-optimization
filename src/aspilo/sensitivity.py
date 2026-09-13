from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.stats import rankdata, pearsonr
from .advanced_simulation import monte_carlo_advanced
from .advanced_economics import total_cost_components


def lhs(n,d,seed=123):
    g=np.random.default_rng(seed); x=np.zeros((n,d))
    for j in range(d):
        perm=g.permutation(n); x[:,j]=(perm+g.random(n))/n
    return x


def _prcc(df,inputs,response):
    X=np.column_stack([rankdata(df[c]) for c in inputs]); y=rankdata(df[response]); out=[]
    for j,c in enumerate(inputs):
        others=np.delete(X,j,axis=1); A=np.column_stack([np.ones(len(df)),others])
        bx=np.linalg.lstsq(A,X[:,j],rcond=None)[0]; by=np.linalg.lstsq(A,y,rcond=None)[0]
        rx=X[:,j]-A@bx; ry=y-A@by; r,p=pearsonr(rx,ry); out.append((c,r,p))
    return pd.DataFrame(out,columns=['input','prcc','p_value']).sort_values('prcc',key=lambda s:s.abs(),ascending=False)


def sensitivity_experiment(parts,suppliers,packaging,daily_demand,vehicles,policy,cfg,returnable_part_ids,n=60,seed=777):
    names=['supplier_reliability','holding_rate','transport_cost','container_turnaround','demand_variability','damage_probability']
    lo=np.array([-.08,.16,.80,.80,.75,.70]); hi=np.array([.04,.30,1.30,1.35,1.50,1.50])
    X=lo+(hi-lo)*lhs(n,len(names),seed); rows=[]
    for i,x in enumerate(X):
        sup=suppliers.copy(); # x[0] is additive reliability perturbation, bounded
        sup['reliability_otif']=np.clip(sup.reliability_otif+x[0],.75,.9995)
        mc=monte_carlo_advanced(parts,sup,daily_demand,policy['inventory'],n=2,seed=seed+1000+i*3,days=150,
                                correlated_risk=True,demand_cv_multiplier=float(x[4]),returnable_part_ids=returnable_part_ids,
                                premium_freight_multiplier=cfg['premium_freight_multiplier'],line_stop_cost_per_hour=cfg['line_stop_cost_per_hour'])
        comp=total_cost_components(parts,packaging,policy['packaging'],daily_demand,policy['inventory'],policy['routes'],vehicles,policy['docks'],mc)
        # Apply explicit epistemic multipliers to the corresponding accounting components.
        base_h=cfg['holding_rate']; comp['inventory_eur']*=x[1]/base_h
        comp['transport_eur']*=x[2]
        comp['reverse_logistics_eur']*=x[3]
        comp['damage_eur']*=x[5]
        total=sum(v for k,v in comp.items() if k!='total_landed_logistics_cost_eur')
        rows.append((*x,total,float(mc.critical_fill_rate.mean()),float(mc.line_stop_events.mean())))
    df=pd.DataFrame(rows,columns=names+['total_cost_eur','critical_fill_rate','mean_line_stop_events'])
    prcc_cost=_prcc(df,names,'total_cost_eur'); prcc_cost['response']='total_cost_eur'
    prcc_service=_prcc(df,names,'critical_fill_rate'); prcc_service['response']='critical_fill_rate'
    return df,pd.concat([prcc_cost,prcc_service],ignore_index=True)
