from _load_final_context import *
from aspilo.final_pipeline import _oos
import pandas as pd,json,time
nom,target=pol('nominal'),pol('target_plus'); T=time.time()
a=_oos(nom,parts,suppliers,packaging,daily,vehicles,cfg,seed=310000,n_each=25); a['policy']='Nominal joint'
b=_oos(target,parts,suppliers,packaging,daily,vehicles,cfg,seed=410000,n_each=25); b['policy']='Target+ robust'
o=pd.concat([a,b],ignore_index=True); o.to_csv(proc/'oos_results.csv',index=False)
s=o.groupby(['policy','scenario']).agg(fill_rate=('fill_rate','mean'),critical_fill_rate=('critical_fill_rate','mean'),line_stop_probability=('line_stop_events',lambda x:float((x>0).mean())),mean_line_stop_events=('line_stop_events','mean'),premium_freight_events=('premium_freight_events','mean'),p95_shortage_duration_days=('p95_shortage_duration_days','max'),mean_disruption_cost_eur=('total_disruption_cost_eur','mean')).reset_index(); s.to_csv(proc/'oos_summary.csv',index=False)
print(json.dumps({'runtime_s':time.time()-T,'target_critical_fill':float(b.critical_fill_rate.mean()),'target_line_stop_probability':float((b.line_stop_events>0).mean()),'nominal_line_stop_probability':float((a.line_stop_events>0).mean())},indent=2))
