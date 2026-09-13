from pathlib import Path
import sys,json,time
import pandas as pd
import gc
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from aspilo.final_pipeline import _oos,_stress,_resilience_envelope,_ablation
cfg=json.load(open(ROOT/'configs/base.json')); raw=ROOT/'data/raw'; proc=ROOT/'data/processed'
parts=pd.read_csv(raw/'parts.csv'); suppliers=pd.read_csv(raw/'suppliers.csv'); packaging=pd.read_csv(raw/'packaging.csv'); daily=pd.read_csv(raw/'daily_demand.csv'); vehicles=pd.read_csv(raw/'vehicles.csv')
def pol(prefix):
 d={}
 for key in ['packaging','frequency','routes','inventory','docks','returnables','emissions']:
  p=proc/f'{prefix}_{key}.csv'
  if p.exists(): d[key]=pd.read_csv(p)
 d['packaging']['returnable']=d['packaging'].returnable.astype(str).str.lower().eq('true'); return d
nom,target=pol('nominal'),pol('target_plus'); T=time.time()
print('oos nominal',flush=True); o1=_oos(nom,parts,suppliers,packaging,daily,vehicles,cfg,seed=310000,n_each=25); o1['policy']='Nominal joint'
print('oos target',flush=True); o2=_oos(target,parts,suppliers,packaging,daily,vehicles,cfg,seed=410000,n_each=25); o2['policy']='Target+ robust'
oos=pd.concat([o1,o2],ignore_index=True); oos.to_csv(proc/'oos_results.csv',index=False)
oos.groupby(['policy','scenario']).agg(fill_rate=('fill_rate','mean'),critical_fill_rate=('critical_fill_rate','mean'),line_stop_probability=('line_stop_events',lambda x:float((x>0).mean())),mean_line_stop_events=('line_stop_events','mean'),premium_freight_events=('premium_freight_events','mean'),p95_shortage_duration_days=('p95_shortage_duration_days','max'),mean_disruption_cost_eur=('total_disruption_cost_eur','mean')).reset_index().to_csv(proc/'oos_summary.csv',index=False)
o2_crit=float(o2.critical_fill_rate.mean()); o2_ls=float((o2.line_stop_events>0).mean()); o1_ls=float((o1.line_stop_events>0).mean()); del o1,o2,oos; gc.collect()
print('stress nominal',flush=True); sn,_=_stress(nom,parts,suppliers,packaging,daily,vehicles,cfg,seed=510000,n=30); sn['policy']='Nominal joint'
print('stress target',flush=True); st,_=_stress(target,parts,suppliers,packaging,daily,vehicles,cfg,seed=610000,n=30); st['policy']='Target+ robust'
pd.concat([sn,st],ignore_index=True).to_csv(proc/'stress_suite.csv',index=False)
del sn,st; gc.collect()
print('envelope',flush=True); env=_resilience_envelope(target,parts,suppliers,daily,cfg); env.to_csv(proc/'resilience_envelope.csv',index=False); del env; gc.collect()
print('ablation',flush=True); abl=_ablation(target,parts,suppliers,daily,cfg); abl.to_csv(proc/'ablation_study.csv',index=False); del abl; gc.collect()
print(json.dumps({'runtime_s':time.time()-T,'oos_target_critical_fill':o2_crit,'oos_target_line_stop_probability':o2_ls,'oos_nominal_line_stop_probability':o1_ls},indent=2))
