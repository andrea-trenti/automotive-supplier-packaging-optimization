from pathlib import Path
import sys,json,time
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from aspilo.synthetic_data import generate_network
from aspilo.advanced_baselines import baseline_a,baseline_b,sequential_policy
from aspilo.final_pipeline import _complete_policy,_evaluate_policy
from aspilo.joint_milp import solve_packaging_frequency_milp
from aspilo.packaging_optimizer import evaluate_packaging_selection
from aspilo.policy_tools import build_policy
from aspilo.robust import screen_candidates,pareto_front
from aspilo.validation import validate_data,validate_routes

cfg=json.load(open(ROOT/'configs/base.json')); raw=ROOT/'data/raw'; proc=ROOT/'data/processed'; out=ROOT/'outputs'; proc.mkdir(parents=True,exist_ok=True)
T=time.time(); ds=generate_network(cfg,raw)
parts,suppliers,packaging,vehicles,daily,compat=[ds[k] for k in ['parts','suppliers','packaging','vehicles','daily_demand','compatibility']]
issues=validate_data(parts,suppliers,packaging,compat); assert not issues,issues
pols={}
for name,fn in [('baseline_a',baseline_a),('baseline_b',baseline_b),('sequential',sequential_policy)]:
    pols[name]=_complete_policy(fn(parts,suppliers,packaging,compat,daily,vehicles,cfg['holding_rate']),parts,suppliers,packaging,daily,vehicles,cfg['n_receiving_docks'])
sel,freq,info=solve_packaging_frequency_milp(parts,suppliers,packaging,compat,daily,vehicles,cfg['holding_rate'],time_limit=30)
pack=evaluate_packaging_selection(parts,packaging,daily.drop(columns=['date']).sum(),sel)
nom=build_policy(parts,suppliers,packaging,daily,vehicles,pack,freq,cfg['holding_rate'],n_docks=cfg['n_receiving_docks']); pols['nominal']=nom
assert not validate_routes(nom['routes'],vehicles)
retids=set(pack.loc[pack.returnable,'part_id'])
screen,target,best=screen_candidates(parts,suppliers,packaging,daily,vehicles,pack,freq,cfg['holding_rate'],cfg,retids,n_rep=6,seed=80000); pols['target_plus']=target
# Persist all decision policies.
for name,pol in pols.items():
    for key in ['packaging','frequency','routes','inventory','docks','returnables','emissions']:
        if key in pol: pol[key].to_csv(proc/f'{name}_{key}.csv',index=False)
screen.to_csv(proc/'robust_candidate_screen.csv',index=False)
pf=pareto_front(screen)
if len(pf):
    import numpy as np
    cn=(pf.annual_cost_eur-pf.annual_cost_eur.min())/max(pf.annual_cost_eur.max()-pf.annual_cost_eur.min(),1)
    en=(pf.annual_co2e_kg-pf.annual_co2e_kg.min())/max(pf.annual_co2e_kg.max()-pf.annual_co2e_kg.min(),1)
    pf['distance_to_ideal']=(cn**2+en**2)**.5; pf['knee_point']=False; pf.loc[pf.distance_to_ideal.idxmin(),'knee_point']=True
pf.to_csv(proc/'pareto_frontier.csv',index=False)
# Common-draw core evaluation.
rows=[]
for nm,key in [('Baseline A','baseline_a'),('Baseline B','baseline_b'),('Sequential','sequential'),('Nominal joint','nominal'),('Target+ robust','target_plus')]:
    met,_=_evaluate_policy(nm,pols[key],parts,suppliers,packaging,daily,vehicles,cfg,seed=210000,n=60,correlated_risk=True); rows.append(met)
comparison=pd.DataFrame(rows); comparison.to_csv(proc/'policy_comparison.csv',index=False)
(out/'final_milp_info.json').write_text(json.dumps(info,indent=2)); (out/'robust_selected_candidate.json').write_text(json.dumps(best.to_dict(),indent=2))
print(json.dumps({'runtime_s':time.time()-T,'selected_candidate':best.to_dict(),'comparison':comparison[['policy','total_landed_logistics_cost_eur','critical_fill_rate','line_stop_probability','transport_co2e_kg']].to_dict('records')},indent=2))
