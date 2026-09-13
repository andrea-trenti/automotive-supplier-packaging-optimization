from __future__ import annotations
import itertools
import math
import numpy as np
import pandas as pd
from .packaging_optimizer import optimize_packaging


def rationalization_curve(parts,packaging,compatibility,daily_demand):
    annual=daily_demand.drop(columns=['date']).sum(); ids=packaging.packaging_id.tolist(); rows=[]
    for k in range(2,len(ids)+1):
        best=None
        for subset in itertools.combinations(ids,k):
            comp=compatibility[compatibility.packaging_id.isin(subset)]
            if comp.part_id.nunique()<parts.part_id.nunique(): continue
            pk=packaging[packaging.packaging_id.isin(subset)]
            try: choice=optimize_packaging(parts,pk,comp,annual)
            except Exception: continue
            cost=float(choice.total_packaging_system_cost_eur.sum())
            cand=(cost,subset,choice)
            if best is None or cost<best[0]: best=cand
        if best is not None:
            rows.append((k,'|'.join(best[1]),best[0]))
    return pd.DataFrame(rows,columns=['packaging_sku_count','packaging_ids','annual_packaging_system_cost_eur'])


def returnable_break_even_by_part(parts,packaging,compatibility,pack_choices,daily_demand,discount_rate=.085,years=5):
    annual=daily_demand.drop(columns=['date']).sum(); pm=packaging.set_index('packaging_id'); feasible={p:set(g.packaging_id) for p,g in compatibility.groupby('part_id')}; partm=parts.set_index('part_id'); rows=[]
    expendable=set(packaging.loc[~packaging.returnable,'packaging_id'])
    for _,r in pack_choices[pack_choices.returnable].iterrows():
        pid=r.part_id; k=pm.loc[r.packaging_id]; exp_ids=list(feasible.get(pid,set())&expendable)
        if not exp_ids: continue
        # Compare container-level cash cost; geometry/capacity differences are reflected in units/container.
        exp=min(exp_ids,key=lambda x:pm.loc[x].purchase_cost_eur)
        e=pm.loc[exp]
        ret_var=float(k.cleaning_eur_cycle+k.repair_eur_cycle+k.reverse_logistics_eur_cycle)
        exp_cycle=float(e.purchase_cost_eur)
        denom=exp_cycle-ret_var
        be=float(k.purchase_cost_eur/denom) if denom>0 else np.inf
        annual_cycles=float(math.ceil(max(1,float(annual[pid]))/max(1,float(r.units_per_container))))
        yearly_ret=annual_cycles*ret_var; yearly_exp=annual_cycles*exp_cycle
        npv_ret=-float(k.purchase_cost_eur)+sum(-yearly_ret/(1+discount_rate)**y for y in range(1,years+1))
        npv_exp=sum(-yearly_exp/(1+discount_rate)**y for y in range(1,years+1))
        rows.append((pid,partm.loc[pid].line_family,r.packaging_id,exp,be,annual_cycles,npv_ret-npv_exp))
    return pd.DataFrame(rows,columns=['part_id','line_family','returnable_packaging','expendable_alternative','break_even_cycles','annual_container_cycles','npv_advantage_returnable_eur_5y'])
