from pathlib import Path
import sys,json,time
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from aspilo.final_pipeline import _oos,_stress,_resilience_envelope,_ablation,_runtime_benchmark
from aspilo.returnables_dynamic import fleet_requirements,simulate_returnable_loop
from aspilo.packaging_analysis import rationalization_curve,returnable_break_even_by_part
from aspilo.sensitivity import sensitivity_experiment
from aspilo.advanced_economics import probabilistic_npv

cfg=json.load(open(ROOT/'configs/base.json')); raw=ROOT/'data/raw'; proc=ROOT/'data/processed'; out=ROOT/'outputs'
load=lambda n: pd.read_csv(raw/f'{n}.csv')
parts,suppliers,packaging,vehicles,daily,compat=[load(k) for k in ['parts','suppliers','packaging','vehicles','daily_demand','compatibility']]

def pol(prefix):
    d={}
    for key in ['packaging','frequency','routes','inventory','docks','returnables','emissions']:
        p=proc/f'{prefix}_{key}.csv'
        if p.exists(): d[key]=pd.read_csv(p)
    if 'packaging' in d and 'returnable' in d['packaging']:
        d['packaging']['returnable']=d['packaging']['returnable'].astype(str).str.lower().eq('true')
    return d

nom=pol('nominal'); target=pol('target_plus'); B=pol('baseline_b')
T=time.time()
print('[2.1] oos',flush=True)
# Out-of-sample set B.
oos_nom=_oos(nom,parts,suppliers,packaging,daily,vehicles,cfg,seed=310000,n_each=25); oos_nom['policy']='Nominal joint'
oos_tar=_oos(target,parts,suppliers,packaging,daily,vehicles,cfg,seed=410000,n_each=25); oos_tar['policy']='Target+ robust'
oos=pd.concat([oos_nom,oos_tar],ignore_index=True); oos.to_csv(proc/'oos_results.csv',index=False)
oos_summary=oos.groupby(['policy','scenario']).agg(fill_rate=('fill_rate','mean'),critical_fill_rate=('critical_fill_rate','mean'),line_stop_probability=('line_stop_events',lambda x:float((x>0).mean())),mean_line_stop_events=('line_stop_events','mean'),premium_freight_events=('premium_freight_events','mean'),p95_shortage_duration_days=('p95_shortage_duration_days','max'),mean_disruption_cost_eur=('total_disruption_cost_eur','mean')).reset_index(); oos_summary.to_csv(proc/'oos_summary.csv',index=False)
print('[2.2] stress',flush=True)
# Stress and resilience.
sn,_=_stress(nom,parts,suppliers,packaging,daily,vehicles,cfg,seed=510000,n=30); sn['policy']='Nominal joint'
st,_=_stress(target,parts,suppliers,packaging,daily,vehicles,cfg,seed=610000,n=30); st['policy']='Target+ robust'
stress=pd.concat([sn,st],ignore_index=True); stress.to_csv(proc/'stress_suite.csv',index=False)
env=_resilience_envelope(target,parts,suppliers,daily,cfg); env.to_csv(proc/'resilience_envelope.csv',index=False)
abl=_ablation(target,parts,suppliers,daily,cfg); abl.to_csv(proc/'ablation_study.csv',index=False)
print('[2.3] returnables',flush=True)
# Returnable closed-loop and packaging analyses.
fleet=fleet_requirements(parts,target['packaging'],packaging,daily,suppliers,safety_pct=.10); fleet.to_csv(proc/'returnable_fleet_requirements.csv',index=False)
states,rs=simulate_returnable_loop(parts,target['packaging'],packaging,daily,suppliers,seed=20260913,days=180,safety_pct=.10); states.to_csv(proc/'returnable_state_history.csv',index=False); rs.to_csv(proc/'returnable_loop_summary.csv',index=False)
breaks=returnable_break_even_by_part(parts,packaging,compat,target['packaging'],daily); breaks.to_csv(proc/'returnable_break_even_parts.csv',index=False)
rat=rationalization_curve(parts,packaging,compat,daily); rat.to_csv(proc/'packaging_rationalization.csv',index=False)
print('[2.4] sensitivity',flush=True)
# Sensitivity and runtime.
sens,prcc=sensitivity_experiment(parts,suppliers,packaging,daily,vehicles,target,cfg,set(target['packaging'].loc[target['packaging'].returnable,'part_id']),n=48); sens.to_csv(proc/'sensitivity_samples.csv',index=False); prcc.to_csv(proc/'sensitivity_prcc.csv',index=False)
runtime=_runtime_benchmark(parts,suppliers,packaging,compat,daily,vehicles,cfg); runtime.to_csv(proc/'runtime_benchmark.csv',index=False)
print('[2.5] tts/econ',flush=True)
# TTS/TTR from inventory coverage vs synthetic recovery proxy.
pcover=target['inventory'][['part_id','mean_daily_demand','avg_inventory_units','criticality']].merge(parts[['part_id','supplier_id']],on='part_id'); pcover['tts_days']=pcover.avg_inventory_units/pcover.mean_daily_demand.clip(lower=1e-9)
tts=pcover.groupby('supplier_id').agg(tts_days=('tts_days','min'),critical_parts=('criticality',lambda x:int((x=='critical').sum()))).reset_index().merge(suppliers[['supplier_id','lead_time_days','risk_class','reliability_otif']],on='supplier_id'); tts['ttr_days']=tts.lead_time_days*(1+tts.risk_class.map({'A':2.4,'B':1.5,'C':1.1})); tts['resilience_gap_days']=tts.ttr_days-tts.tts_days; tts['vulnerable_tts_lt_ttr']=tts.tts_days<tts.ttr_days; tts.to_csv(proc/'tts_ttr.csv',index=False)
# Economics and NPV against smart baseline B.
comparison=pd.read_csv(proc/'policy_comparison.csv').set_index('policy'); b=comparison.loc['Baseline B']; t=comparison.loc['Target+ robust']
categories=['transport_eur','packaging_material_eur','packaging_cleaning_repair_eur','reverse_logistics_eur','inventory_eur','handling_eur','damage_eur','dock_wait_eur','dock_overtime_eur','premium_freight_eur','line_stop_exposure_eur']
bridge=pd.DataFrame({'cost_component':categories,'baseline_b_eur':[b[c] for c in categories],'target_plus_eur':[t[c] for c in categories]}); bridge['saving_eur']=bridge.baseline_b_eur-bridge.target_plus_eur; bridge.to_csv(proc/'cost_component_bridge.csv',index=False)
fleetB=fleet_requirements(parts,B['packaging'],packaging,daily,suppliers,safety_pct=.10)
capex=max(0,float(fleet.container_asset_eur.sum()-fleetB.container_asset_eur.sum()))+180000.0
annual_saving=float(b.total_landed_logistics_cost_eur-t.total_landed_logistics_cost_eur)
npv=probabilistic_npv(annual_saving,capex,seed=20260913,n=4096); npv.to_csv(proc/'probabilistic_npv.csv',index=False)
# Sensitivity-backed VOI priority.
costp=prcc[prcc.response=='total_cost_eur'].set_index('input').prcc.abs().to_dict(); servp=prcc[prcc.response=='critical_fill_rate'].set_index('input').prcc.abs().to_dict()
voi=pd.DataFrame([
('supplier lead-time / OTIF distributions','supplier_reliability',costp.get('supplier_reliability',0)+servp.get('supplier_reliability',0),'shortage and resilience calibration'),
('actual lane fill and carrier rates','transport_cost',costp.get('transport_cost',0),'transport savings and consolidation value'),
('returnable turnaround / loss history','container_turnaround',costp.get('container_turnaround',0),'returnable fleet and reverse-loop economics'),
('actual holding-rate / working-capital data','holding_rate',costp.get('holding_rate',0),'frequency versus inventory trade-off'),
('packaging damage history','damage_probability',costp.get('damage_probability',0),'packaging frontier and quality cost'),
('vehicle-mix / production schedule variability','demand_variability',costp.get('demand_variability',0)+servp.get('demand_variability',0),'robust stock and service requirements'),
],columns=['real_data_item','linked_parameter','priority_score','decision_use']).sort_values('priority_score',ascending=False); voi.to_csv(proc/'value_of_information.csv',index=False)
print(json.dumps({'runtime_s':time.time()-T,'oos_target_critical_fill':float(oos_tar.critical_fill_rate.mean()),'oos_target_line_stop_probability':float((oos_tar.line_stop_events>0).mean()),'returnable_fleet_operational':int(fleet.operational_fleet.sum()),'returnable_conservation':bool(states.conserved.all()),'vulnerable_suppliers':int(tts.vulnerable_tts_lt_ttr.sum()),'npv_p50':float(npv.npv_eur.median()),'npv_prob_positive':float((npv.npv_eur>0).mean())},indent=2))
