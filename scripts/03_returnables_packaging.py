from _load_final_context import *
from aspilo.returnables_dynamic import fleet_requirements,simulate_returnable_loop
from aspilo.packaging_analysis import rationalization_curve,returnable_break_even_by_part
import json,time
T=time.time(); target=pol('target_plus')
fleet=fleet_requirements(parts,target['packaging'],packaging,daily,suppliers,safety_pct=.10); fleet.to_csv(proc/'returnable_fleet_requirements.csv',index=False)
states,summary=simulate_returnable_loop(parts,target['packaging'],packaging,daily,suppliers,seed=20260913,days=180,safety_pct=.10); states.to_csv(proc/'returnable_state_history.csv',index=False); summary.to_csv(proc/'returnable_loop_summary.csv',index=False)
b=returnable_break_even_by_part(parts,packaging,compatibility,target['packaging'],daily); b.to_csv(proc/'returnable_break_even_parts.csv',index=False)
r=rationalization_curve(parts,packaging,compatibility,daily); r.to_csv(proc/'packaging_rationalization.csv',index=False)
print(json.dumps({'runtime_s':time.time()-T,'returnable_parts':len(fleet),'minimum_theoretical_fleet':int(fleet.minimum_theoretical_fleet.sum()),'operational_fleet':int(fleet.operational_fleet.sum()),'fleet_asset_eur':float(fleet.container_asset_eur.sum()),'state_conservation':bool(states.conserved.all()),'mean_container_shortage_rate':float(summary.container_shortage_rate.mean()),'median_break_even_cycles':float(b.break_even_cycles.replace([float('inf')],float('nan')).median())},indent=2)); print(r.to_string(index=False))
