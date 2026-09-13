from _load_final_context import *
from aspilo.final_pipeline import _resilience_envelope,_ablation
import json,time
T=time.time(); target=pol('target_plus')
env=_resilience_envelope(target,parts,suppliers,daily,cfg); env.to_csv(proc/'resilience_envelope.csv',index=False)
abl=_ablation(target,parts,suppliers,daily,cfg); abl.to_csv(proc/'ablation_study.csv',index=False)
print(env.to_string(index=False)); print(abl.to_string(index=False)); print(json.dumps({'runtime_s':time.time()-T},indent=2))
