from __future__ import annotations
import math
import numpy as np
import pandas as pd
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import lil_matrix, csr_matrix
from .packaging_optimizer import units_per_container

FREQS=np.array([1,2,3,5,7.5,10,12.5,15,20,25,30],float)

def solve_packaging_frequency_milp(parts,suppliers,packaging,compatibility,daily_demand,vehicles,holding_rate=.22,weeks=50,time_limit=30):
    annual=daily_demand.drop(columns=['date']).sum(); feasible=set(zip(compatibility.part_id,compatibility.packaging_id)); pm=packaging.set_index('packaging_id'); sm=suppliers.set_index('supplier_id'); veh=vehicles.sort_values('max_payload_kg').iloc[-1]
    pidx={p:i for i,p in enumerate(parts.part_id)}; sids=suppliers.supplier_id.tolist(); sidx={s:i for i,s in enumerate(sids)}
    xvars=[]; xmeta=[]; c=[]
    # packaging variables and cost coefficients
    for _,p in parts.iterrows():
        for _,k in packaging.iterrows():
            if (p.part_id,k.packaging_id) not in feasible: continue
            q,*_=units_per_container(p,k); cycles=math.ceil(max(1,float(annual[p.part_id]))/q)
            pc=cycles*((k.purchase_cost_eur/max(k.lifetime_cycles,1)+k.cleaning_eur_cycle+k.repair_eur_cycle+k.reverse_logistics_eur_cycle) if k.returnable else k.purchase_cost_eur)
            handling=cycles*k.handling_cost_eur
            damage=float(annual[p.part_id])*p.unit_value_eur*p.damage_sensitivity*k.base_damage_rate*0.45
            idx=len(c); xvars.append(idx); xmeta.append((p.part_id,k.packaging_id,q,cycles,k.internal_l_m*k.internal_w_m*k.internal_h_m)); c.append(pc+handling+damage)
    zmeta=[]; zvars=[]
    # supplier-frequency variables
    pwork=parts.copy(); pwork['annual_units']=pwork.part_id.map(annual); pwork['annual_value']=pwork.annual_units*pwork.unit_value_eur
    sup_value=pwork.groupby('supplier_id').annual_value.sum()
    for sid in sids:
        dist=sm.loc[sid].distance_km; val=sup_value.get(sid,0); rel=sm.loc[sid].reliability_otif
        for f in FREQS:
            idx=len(c); zvars.append(idx); zmeta.append((sid,f)); trips=weeks*f
            transport=trips*(85+2*dist*1.05)
            cycle_inv=val/250*(5/f)/2*holding_rate
            risk=(1-rel)*(5/f)*val*0.003
            dock=max(0,f-10)*500
            c.append(transport+cycle_inv+risk+dock)
    n=len(c); lb=np.zeros(n); ub=np.ones(n); integrality=np.ones(n)
    rows=[]; lows=[]; highs=[]
    # exactly one packaging per part
    bypart={pid:[] for pid in parts.part_id}
    for idx,m in zip(xvars,xmeta): bypart[m[0]].append(idx)
    for pid,ids in bypart.items(): rows.append({j:1 for j in ids}); lows.append(1); highs.append(1)
    # exactly one frequency per supplier
    bysup={sid:[] for sid in sids}
    for idx,m in zip(zvars,zmeta): bysup[m[0]].append(idx)
    for sid,ids in bysup.items(): rows.append({j:1 for j in ids}); lows.append(1); highs.append(1)
    # annual cube capacity by supplier couples packaging and frequency
    parts_sid=parts.set_index('part_id').supplier_id.to_dict()
    for sid in sids:
        row={}
        for idx,m in zip(xvars,xmeta):
            pid,pk,q,cycles,cube=m
            if parts_sid[pid]==sid: row[idx]=cycles*cube
        for idx,(ss,f) in zip(zvars,zmeta):
            if ss==sid: row[idx]=row.get(idx,0)-weeks*f*0.90*veh.usable_cube_m3
        rows.append(row); lows.append(-np.inf); highs.append(0)
        # weight capacity; weight is packaging-independent but frequency-dependent
        annual_w=float((pwork.loc[pwork.supplier_id==sid,'annual_units']*pwork.loc[pwork.supplier_id==sid,'unit_weight_kg']).sum())
        row2={}
        for idx,(ss,f) in zip(zvars,zmeta):
            if ss==sid: row2[idx]=-weeks*f*0.90*veh.max_payload_kg
        rows.append(row2); lows.append(-np.inf); highs.append(-annual_w)
    A=lil_matrix((len(rows),n),dtype=float)
    for i,row in enumerate(rows):
        for j,v in row.items(): A[i,j]=v
    res=milp(c=np.asarray(c),integrality=integrality,bounds=Bounds(lb,ub),constraints=LinearConstraint(csr_matrix(A),np.asarray(lows),np.asarray(highs)),options={'time_limit':time_limit,'mip_rel_gap':0.002})
    if res.x is None: raise RuntimeError(f'MILP failed: {res.message}')
    x=res.x; pack_rows=[]
    for idx,m in zip(xvars,xmeta):
        if x[idx]>.5:
            pid,pk,q,cycles,cube=m; pack_rows.append((pid,pk,q,cycles,cube))
    freq_rows=[]
    for idx,(sid,f) in zip(zvars,zmeta):
        if x[idx]>.5: freq_rows.append((sid,f))
    return pd.DataFrame(pack_rows,columns=['part_id','packaging_id','units_per_container','annual_container_cycles','gross_container_cube_m3']),pd.DataFrame(freq_rows,columns=['supplier_id','frequency_per_week']),{'success':bool(res.success),'status':int(res.status),'message':res.message,'objective_eur':float(res.fun),'mip_gap':float(getattr(res,'mip_gap',np.nan)),'mip_node_count':int(getattr(res,'mip_node_count',0))}
