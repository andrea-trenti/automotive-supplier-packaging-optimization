from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from .utils import rng

PACKAGING = [
    ("PK01","small_tote",0.40,0.30,0.22,1.8,18,18.0,True,120.0,220,0.004,2.2),
    ("PK02","large_tote",0.60,0.40,0.32,3.4,35,35.0,True,185.0,220,0.005,2.8),
    ("PK03","klt_like",0.60,0.40,0.28,2.7,30,30.0,True,150.0,250,0.0035,2.4),
    ("PK04","carton",0.55,0.38,0.30,0.8,24,20.0,False,2.8,1,0.012,2.0),
    ("PK05","pallet",1.20,0.80,1.00,24,650,999.0,False,16.0,1,0.010,4.5),
    ("PK06","returnable_rack",1.45,1.05,1.25,95,900,999.0,True,1250.0,350,0.002,5.5),
]

VEHICLES = [
    ("V01","rigid_18t",9000,42,14,1.55,0.78,195.0),
    ("V02","hgv_26t",15000,68,24,1.95,0.92,115.0),
    ("V03","tractor_40t",24000,90,33,2.25,1.04,115.0),
]


def _supplier_coords(g: np.random.Generator, n: int):
    # synthetic northern-Italy-like geometry in km around a plant at (0,0)
    angles = g.uniform(0, 2*np.pi, n)
    radii = g.gamma(2.2, 55.0, n) + 20
    radii = np.clip(radii, 20, 260)
    return radii*np.cos(angles), radii*np.sin(angles), radii


def generate_network(cfg: dict, out_dir: str | Path) -> dict[str, pd.DataFrame]:
    g = rng(cfg['seed'])
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    ns, nparts, ndays = cfg['n_suppliers'], cfg['n_parts'], cfg['n_days']
    x, y, dist = _supplier_coords(g, ns)
    suppliers = pd.DataFrame({
        'supplier_id':[f'S{i:03d}' for i in range(ns)],
        'x_km':x.round(2),'y_km':y.round(2),'distance_km':dist.round(1),
        'lead_time_days':g.uniform(0.6,4.5,ns).round(2),
        'lead_time_cv':g.uniform(0.08,0.45,ns).round(3),
        'reliability_otif':g.beta(45,3,ns).clip(0.82,0.999).round(4),
        'moq_units':g.choice([20,40,60,100,200],ns,p=[.1,.2,.25,.25,.2]),
        'dock_open_h':g.choice([6,7,8],ns),
        'dock_close_h':g.choice([15,16,17,18],ns),
        'risk_class':g.choice(['A','B','C'],ns,p=[.18,.47,.35]),
        'service_min':g.integers(12,38,ns),
        'calendar_days_per_week':g.choice([5,6],ns,p=[.85,.15]),
    })
    # parts distributed unevenly across suppliers
    supplier_idx = g.choice(np.arange(ns), nparts, p=g.dirichlet(np.ones(ns)*2.2))
    unit_weight = np.exp(g.normal(np.log(3.0),1.0,nparts)).clip(.03,180)
    # volume correlated with mass but with density dispersion
    density = np.exp(g.normal(np.log(220),0.65,nparts)).clip(25,1500) # kg/m3
    unit_volume = (unit_weight/density).clip(0.00005,0.75)
    dims_ratio = g.dirichlet([2,1.5,1.2],nparts)
    cube_root = np.cbrt(unit_volume)
    part_l = cube_root*(1.3+1.3*dims_ratio[:,0]); part_w = cube_root*(1.0+0.8*dims_ratio[:,1]);
    part_h = unit_volume/(part_l*part_w)
    values = np.exp(g.normal(np.log(18),1.2,nparts)).clip(0.4,4500)
    criticality = g.choice(['critical','high','medium','low'],nparts,p=[.07,.18,.45,.30])
    damage_sens = g.beta(2.2,5,nparts)
    line_family = g.choice(['powertrain','chassis','interior','electronics','body','thermal'],nparts)
    # BOM quantities by 4 mixed-model variants; structural zeros induce correlation
    variants=['A','B','C','D']
    bom = np.zeros((nparts,4),dtype=int)
    for i in range(nparts):
        base = g.choice([1,1,1,2,2,4,6,8,12],p=[.2,.08,.08,.18,.1,.12,.08,.08,.08])
        mask = g.random(4) < g.uniform(.55,1.0)
        if not mask.any(): mask[g.integers(0,4)] = True
        bom[i] = np.where(mask, np.maximum(1,np.rint(base*g.uniform(.75,1.25,4))).astype(int),0)
    parts = pd.DataFrame({
        'part_id':[f'P{i:04d}' for i in range(nparts)],
        'supplier_id':[f'S{i:03d}' for i in supplier_idx],
        'description':[f'Synthetic automotive component {i:04d}' for i in range(nparts)],
        'unit_weight_kg':unit_weight.round(4),'unit_volume_m3':unit_volume.round(6),
        'part_length_m':part_l.round(4),'part_width_m':part_w.round(4),'part_height_m':part_h.round(4),
        'unit_value_eur':values.round(2),'criticality':criticality,'damage_sensitivity':damage_sens.round(4),
        'handling_class':np.where((unit_weight<=8)&(unit_volume<=0.06),'manual',np.where((unit_weight<=25)&(unit_volume<=0.18),'assisted','mechanical')),
        'stackable':g.random(nparts)>.16,'returnable_eligible':g.random(nparts)>.11,'line_family':line_family,
        **{f'bom_{v}':bom[:,j] for j,v in enumerate(variants)}
    })
    packaging = pd.DataFrame(PACKAGING, columns=['packaging_id','packaging_type','internal_l_m','internal_w_m','internal_h_m','tare_kg','max_payload_kg','max_manual_gross_kg','returnable','purchase_cost_eur','lifetime_cycles','base_damage_rate','handling_cost_eur'])
    packaging['internal_volume_m3']=(packaging.internal_l_m*packaging.internal_w_m*packaging.internal_h_m).round(5)
    packaging['stackability']= [4,3,4,2,2,2]
    packaging['cleaning_eur_cycle']=[.14,.18,.16,0,0,.75]
    packaging['repair_eur_cycle']=[.08,.12,.10,0,0,1.6]
    packaging['reverse_logistics_eur_cycle']=[.30,.45,.38,0,0,2.1]
    vehicles = pd.DataFrame(VEHICLES,columns=['vehicle_id','vehicle_type','max_payload_kg','usable_cube_m3','pallet_positions','fixed_cost_eur_trip','variable_eur_km','glec_wtw_gco2e_tkm'])
    # production schedule with seasonality and correlated variant demand
    dates=pd.date_range('2026-01-01',periods=ndays,freq='D')
    dow=dates.dayofweek
    is_workday=(dow<5).astype(int)
    season=1+0.08*np.sin(2*np.pi*np.arange(ndays)/91)+0.04*np.sin(2*np.pi*np.arange(ndays)/30)
    total=np.where(is_workday, g.poisson(np.maximum(5,cfg['mean_vehicles_per_day']*season)),0)
    mix=np.zeros((ndays,4),dtype=int)
    base_mix=np.array([.34,.28,.23,.15])
    for d in range(ndays):
        drift=np.array([.03*np.sin(d/45),-.02*np.sin(d/45),.01*np.cos(d/60),-.02*np.cos(d/60)])
        p=np.maximum(.03,base_mix+drift); p=p/p.sum()
        mix[d]=g.multinomial(int(total[d]),p) if total[d]>0 else 0
    schedule=pd.DataFrame({'date':dates,'vehicles_total':total,**{f'veh_{v}':mix[:,j] for j,v in enumerate(variants)}})
    # BOM explosion: daily part demand
    demand = mix @ bom.T
    # modest independent scrap/service variance on workdays
    noise=g.normal(0,0.035,demand.shape)
    demand=np.maximum(0,np.rint(demand*(1+noise))).astype(int)
    daily=pd.DataFrame(demand,columns=parts.part_id)
    daily.insert(0,'date',dates)
    # compatibility table determined by dimensions/payload/handling/returnability
    rows=[]
    for pi,r in parts.iterrows():
        for _,pk in packaging.iterrows():
            compatible = (r.unit_weight_kg <= pk.max_payload_kg) and (r.unit_volume_m3 <= pk.internal_volume_m3)
            if r.handling_class=='manual': compatible &= (pk.tare_kg+r.unit_weight_kg <= pk.max_manual_gross_kg)
            if pk.returnable and not r.returnable_eligible: compatible=False
            if pk.packaging_type=='returnable_rack' and (r.unit_weight_kg<12 and r.unit_volume_m3<0.025): compatible=False
            if pk.packaging_type=='pallet' and (r.unit_weight_kg<6 and r.unit_volume_m3<0.010): compatible=False
            if pk.packaging_type in ['small_tote','klt_like'] and r.unit_weight_kg>20: compatible=False
            if pk.packaging_type=='carton' and r.unit_weight_kg>35: compatible=False
            if r.handling_class=='manual' and pk.packaging_type in ['pallet','returnable_rack']: compatible=False
            if compatible: rows.append((r.part_id,pk.packaging_id,True))
    compatibility=pd.DataFrame(rows,columns=['part_id','packaging_id','compatible'])
    datasets={'suppliers':suppliers,'parts':parts,'packaging':packaging,'vehicles':vehicles,'production_schedule':schedule,'daily_demand':daily,'compatibility':compatibility}
    for name,df in datasets.items(): df.to_csv(out/f'{name}.csv',index=False)
    return datasets
