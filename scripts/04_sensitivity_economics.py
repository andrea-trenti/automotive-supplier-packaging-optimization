from _load_final_context import *
from aspilo.sensitivity import sensitivity_experiment
from aspilo.final_pipeline import _runtime_benchmark
from aspilo.returnables_dynamic import fleet_requirements
from aspilo.advanced_economics import probabilistic_npv
import pandas as pd,numpy as np,json,time
T=time.time(); target=pol('target_plus'); B=pol('baseline_b')
sens,prcc=sensitivity_experiment(parts,suppliers,packaging,daily,vehicles,target,cfg,set(target['packaging'].loc[target['packaging'].returnable,'part_id']),n=48); sens.to_csv(proc/'sensitivity_samples.csv',index=False); prcc.to_csv(proc/'sensitivity_prcc.csv',index=False)
runtime=_runtime_benchmark(parts,suppliers,packaging,compatibility,daily,vehicles,cfg); runtime.to_csv(proc/'runtime_benchmark.csv',index=False)
# TTS/TTR from part-level inventory coverage.
pcover=target['inventory'][['part_id','mean_daily_demand','avg_inventory_units','criticality']].merge(parts[['part_id','supplier_id']],on='part_id'); pcover['tts_days']=pcover.avg_inventory_units/pcover.mean_daily_demand.clip(lower=1e-9)
tts=pcover.groupby('supplier_id').agg(tts_days=('tts_days','min'),critical_parts=('criticality',lambda x:int((x=='critical').sum()))).reset_index().merge(suppliers[['supplier_id','lead_time_days','risk_class','reliability_otif']],on='supplier_id'); tts['ttr_days']=tts.lead_time_days*(1+tts.risk_class.map({'A':2.4,'B':1.5,'C':1.1})); tts['resilience_gap_days']=tts.ttr_days-tts.tts_days; tts['vulnerable_tts_lt_ttr']=tts.tts_days<tts.ttr_days; tts.to_csv(proc/'tts_ttr.csv',index=False)
comparison=pd.read_csv(proc/'policy_comparison.csv').set_index('policy'); b=comparison.loc['Baseline B']; t=comparison.loc['Target+ robust']
cats=['transport_eur','packaging_material_eur','packaging_cleaning_repair_eur','reverse_logistics_eur','inventory_eur','handling_eur','damage_eur','dock_wait_eur','dock_overtime_eur','premium_freight_eur','line_stop_exposure_eur']
bridge=pd.DataFrame({'cost_component':cats,'baseline_b_eur':[b[c] for c in cats],'target_plus_eur':[t[c] for c in cats]}); bridge['saving_eur']=bridge.baseline_b_eur-bridge.target_plus_eur; bridge.to_csv(proc/'cost_component_bridge.csv',index=False)
fleet=fleet_requirements(parts,target['packaging'],packaging,daily,suppliers,safety_pct=.10); fleetB=fleet_requirements(parts,B['packaging'],packaging,daily,suppliers,safety_pct=.10)
capex=max(0,float(fleet.container_asset_eur.sum()-fleetB.container_asset_eur.sum()))+180000.0; annual_saving=float(b.total_landed_logistics_cost_eur-t.total_landed_logistics_cost_eur)
npv=probabilistic_npv(annual_saving,capex,seed=20260913,n=4096); npv.to_csv(proc/'probabilistic_npv.csv',index=False)
# Sensitivity-backed value-of-information priority, not a monetary EVPI claim.
costp=prcc[prcc.response=='total_cost_eur'].set_index('input').prcc.abs().to_dict(); servp=prcc[prcc.response=='critical_fill_rate'].set_index('input').prcc.abs().to_dict()
voi=pd.DataFrame([
('supplier lead-time / OTIF distributions','supplier_reliability',costp.get('supplier_reliability',0)+servp.get('supplier_reliability',0),'shortage and resilience calibration'),
('actual lane fill and carrier rates','transport_cost',costp.get('transport_cost',0),'transport savings and consolidation value'),
('returnable turnaround / loss history','container_turnaround',costp.get('container_turnaround',0),'returnable fleet and reverse-loop economics'),
('actual holding-rate / working-capital data','holding_rate',costp.get('holding_rate',0),'frequency versus inventory trade-off'),
('packaging damage history','damage_probability',costp.get('damage_probability',0),'packaging frontier and quality cost'),
('vehicle-mix / production schedule variability','demand_variability',costp.get('demand_variability',0)+servp.get('demand_variability',0),'robust stock and service requirements')],columns=['real_data_item','linked_parameter','priority_score','decision_use']).sort_values('priority_score',ascending=False); voi.to_csv(proc/'value_of_information.csv',index=False)
print(json.dumps({'runtime_s':time.time()-T,'incremental_capex_eur':capex,'baseline_b_fleet_asset_eur':float(fleetB.container_asset_eur.sum()),'target_fleet_asset_eur':float(fleet.container_asset_eur.sum()),'annual_saving_vs_B_eur':annual_saving,'npv_p05':float(npv.npv_eur.quantile(.05)),'npv_p50':float(npv.npv_eur.quantile(.5)),'npv_p95':float(npv.npv_eur.quantile(.95)),'p_npv_positive':float((npv.npv_eur>0).mean()),'payback_p50_years':float(npv.payback_years.quantile(.5)),'vulnerable_suppliers':int(tts.vulnerable_tts_lt_ttr.sum()),'worst_gap_days':float(tts.resilience_gap_days.max())},indent=2)); print(prcc.to_string(index=False)); print(runtime.to_string(index=False)); print(voi.to_string(index=False))
