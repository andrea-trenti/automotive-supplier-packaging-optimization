from _load_final_context import *
from aspilo.final_pipeline import _stress
import pandas as pd,json,time
nom,target=pol('nominal'),pol('target_plus'); T=time.time()
a,_=_stress(nom,parts,suppliers,packaging,daily,vehicles,cfg,seed=510000,n=30); a['policy']='Nominal joint'
b,_=_stress(target,parts,suppliers,packaging,daily,vehicles,cfg,seed=610000,n=30); b['policy']='Target+ robust'
s=pd.concat([a,b],ignore_index=True); s.to_csv(proc/'stress_suite.csv',index=False)
print(s[['policy','scenario','critical_fill_rate','line_stop_probability','annual_cost_eur']].to_string(index=False)); print(json.dumps({'runtime_s':time.time()-T},indent=2))
