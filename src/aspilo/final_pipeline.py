from __future__ import annotations
from pathlib import Path
import json, time, math
import numpy as np
import pandas as pd

from .synthetic_data import generate_network
from .advanced_baselines import baseline_a, baseline_b, sequential_policy
from .joint_milp import solve_packaging_frequency_milp
from .packaging_optimizer import evaluate_packaging_selection
from .policy_tools import build_policy
from .dock_scheduling import schedule_receiving
from .returnables import size_returnable_fleet
from .returnables_dynamic import fleet_requirements, simulate_returnable_loop
from .emissions import route_emissions
from .advanced_simulation import monte_carlo_advanced
from .advanced_economics import total_cost_components, probabilistic_npv, packaging_emissions_proxy
from .robust import screen_candidates, pareto_front
from .packaging_analysis import rationalization_curve, returnable_break_even_by_part
from .sensitivity import sensitivity_experiment
from .validation import validate_data, validate_routes
from .utils import load_config


def _complete_policy(pol, parts, suppliers, packaging, daily, vehicles, n_docks=5):
    if 'docks' not in pol: pol['docks']=schedule_receiving(pol['routes'],n_docks=n_docks,stagger=True)
    if 'returnables' not in pol: pol['returnables']=size_returnable_fleet(parts,pol['packaging'],packaging,daily,suppliers,buffer_pct=.10)
    if 'emissions' not in pol: pol['emissions']=route_emissions(pol['routes'],vehicles)
    return pol


def _evaluate_policy(name,pol,parts,suppliers,packaging,daily,vehicles,cfg,seed=200000,n=100,**sim_kw):
    retids=set(pol['packaging'].loc[pol['packaging'].returnable,'part_id'])
    mc=monte_carlo_advanced(parts,suppliers,daily,pol['inventory'],n=n,seed=seed,days=180,
                            returnable_part_ids=retids,premium_freight_multiplier=cfg['premium_freight_multiplier'],
                            line_stop_cost_per_hour=cfg['line_stop_cost_per_hour'],**sim_kw)
    comp=total_cost_components(parts,packaging,pol['packaging'],daily,pol['inventory'],pol['routes'],vehicles,pol['docks'],mc)
    return {
        'policy':name,
        **comp,
        'transport_co2e_kg':float(pol['emissions'].annual_co2e_kg.sum()),
        'packaging_co2e_proxy_kg':packaging_emissions_proxy(parts,packaging,pol['packaging'],daily),
        'routes':len(pol['routes']),
        'mean_cube_utilization':float(pol['routes'].cube_utilization.mean()),
        'mean_weight_utilization':float(pol['routes'].weight_utilization.mean()),
        'mean_pallet_utilization':float(pol['routes'].pallet_position_utilization.mean()) if 'pallet_position_utilization' in pol['routes'] else np.nan,
        'mean_fill_rate':float(mc.fill_rate.mean()),
        'critical_fill_rate':float(mc.critical_fill_rate.mean()),
        'line_stop_probability':float((mc.line_stop_events>0).mean()),
        'mean_line_stop_events':float(mc.line_stop_events.mean()),
        'mean_line_stop_hours':float(mc.line_stop_hours.mean()),
        'premium_freight_events_mean':float(mc.premium_freight_events.mean()),
        'p95_shortage_duration_days':float(mc.p95_shortage_duration_days.quantile(.95)),
        'disruption_cost_p95_eur':float(mc.total_disruption_cost_eur.quantile(.95)),
    },mc


def _oos(policy,parts,suppliers,packaging,daily,vehicles,cfg,seed=300000,n_each=40):
    retids=set(policy['packaging'].loc[policy['packaging'].returnable,'part_id'])
    scenarios={
        'nominal':{},
        'correlated':{'correlated_risk':True,'demand_cv_multiplier':1.20},
        'demand10':{'demand_multiplier':1.10,'demand_cv_multiplier':1.20},
        'carrier':{'carrier_capacity_multiplier':.90,'correlated_risk':True},
        'container':{'container_availability':.93,'correlated_risk':True},
        'combined':{'demand_multiplier':1.10,'lead_time_multiplier':1.20,'carrier_capacity_multiplier':.90,'container_availability':.94,'correlated_risk':True,'supplier_outage_days':2},
    }
    arr=[]
    for j,(sc,kw) in enumerate(scenarios.items()):
        m=monte_carlo_advanced(parts,suppliers,daily,policy['inventory'],n=n_each,seed=seed+j*500,days=180,
                               returnable_part_ids=retids,premium_freight_multiplier=cfg['premium_freight_multiplier'],
                               line_stop_cost_per_hour=cfg['line_stop_cost_per_hour'],**kw)
        m['scenario']=sc; arr.append(m)
    return pd.concat(arr,ignore_index=True)


def _stress(policy,parts,suppliers,packaging,daily,vehicles,cfg,seed=400000,n=50):
    retids=set(policy['packaging'].loc[policy['packaging'].returnable,'part_id'])
    scenarios={
        'nominal':{},
        'demand_plus_20pct':{'demand_multiplier':1.20,'demand_cv_multiplier':1.25},
        'critical_supplier_disruption':{'supplier_outage_days':5,'correlated_risk':True},
        'container_shortage':{'container_availability':.88,'correlated_risk':True},
        'carrier_capacity_shortage':{'carrier_capacity_multiplier':.82,'correlated_risk':True},
        'combined_shock':{'demand_multiplier':1.15,'lead_time_multiplier':1.35,'carrier_capacity_multiplier':.85,'container_availability':.90,'correlated_risk':True,'supplier_outage_days':3},
    }
    base_transport=None; rows=[]; allmc=[]
    for j,(sc,kw) in enumerate(scenarios.items()):
        m=monte_carlo_advanced(parts,suppliers,daily,policy['inventory'],n=n,seed=seed+j*700,days=180,
                               returnable_part_ids=retids,premium_freight_multiplier=cfg['premium_freight_multiplier'],
                               line_stop_cost_per_hour=cfg['line_stop_cost_per_hour'],**kw)
        m['scenario']=sc; allmc.append(m)
        comp=total_cost_components(parts,packaging,policy['packaging'],daily,policy['inventory'],policy['routes'],vehicles,policy['docks'],m)
        if base_transport is None: base_transport=comp['transport_eur']
        rows.append((sc,comp['total_landed_logistics_cost_eur'],m.fill_rate.mean(),m.critical_fill_rate.mean(),(m.line_stop_events>0).mean(),m.line_stop_events.mean(),m.premium_freight_events.mean(),m.p95_shortage_duration_days.quantile(.95)))
    # Fuel stress leaves service physics unchanged but changes operating economics.
    nominal=rows[0]
    rows.append(('fuel_plus_50pct',nominal[1]+.50*base_transport,nominal[2],nominal[3],nominal[4],nominal[5],nominal[6],nominal[7]))
    return pd.DataFrame(rows,columns=['scenario','annual_cost_eur','fill_rate','critical_fill_rate','line_stop_probability','mean_line_stop_events','premium_freight_events_mean','p95_shortage_duration_days']),pd.concat(allmc,ignore_index=True)


def _resilience_envelope(policy,parts,suppliers,daily,cfg,seed=500000):
    retids=set(policy['packaging'].loc[policy['packaging'].returnable,'part_id']); rows=[]; k=0
    experiments=[]
    for d in [0,2,4,6,8,10]: experiments.append(('supplier_outage_days',d,dict(supplier_outage_days=d,correlated_risk=True)))
    for x in [1.0,1.10,1.20,1.30,1.40]: experiments.append(('demand_multiplier',x,dict(demand_multiplier=x,correlated_risk=True)))
    for a in [1.0,.96,.92,.88,.84]: experiments.append(('container_availability',a,dict(container_availability=a,correlated_risk=True)))
    dim_seed={'supplier_outage_days':seed,'demand_multiplier':seed+10000,'container_availability':seed+20000}
    for kind,value,kw in experiments:
        # Common random numbers within each stress dimension improve level-to-level comparability.
        m=monte_carlo_advanced(parts,suppliers,daily,policy['inventory'],n=25,seed=dim_seed[kind],days=180,
                               returnable_part_ids=retids,premium_freight_multiplier=cfg['premium_freight_multiplier'],
                               line_stop_cost_per_hour=cfg['line_stop_cost_per_hour'],**kw); k+=1
        rows.append((kind,value,m.critical_fill_rate.mean(),(m.critical_fill_rate>=.999).mean(),(m.line_stop_events>0).mean(),m.line_stop_events.mean()))
    return pd.DataFrame(rows,columns=['stress_dimension','stress_level','critical_fill_rate','prob_critical_fill_ge_999','line_stop_probability','mean_line_stop_events'])


def _ablation(policy,parts,suppliers,daily,cfg,seed=600000):
    retids=set(policy['packaging'].loc[policy['packaging'].returnable,'part_id'])
    base=dict(demand_multiplier=1.10,lead_time_multiplier=1.25,carrier_capacity_multiplier=.90,container_availability=.94,correlated_risk=True,supplier_outage_days=2)
    variants={
        'full_model':base,
        'without_supplier_correlation':{**base,'correlated_risk':False},
        'without_stochastic_lead_time':base,
        'without_returnable_constraint':{**base,'container_availability':1.0},
        'without_carrier_constraint':{**base,'carrier_capacity_multiplier':1.0},
        'without_supplier_outage':{**base,'supplier_outage_days':0},
        'without_demand_shock':{**base,'demand_multiplier':1.0},
    }
    rows=[]
    for j,(name,kw) in enumerate(variants.items()):
        sup=suppliers.copy()
        if name=='without_stochastic_lead_time': sup['lead_time_cv']=0.0
        m=monte_carlo_advanced(parts,sup,daily,policy['inventory'],n=25,seed=seed+j*200,days=180,returnable_part_ids=retids,
                               premium_freight_multiplier=cfg['premium_freight_multiplier'],line_stop_cost_per_hour=cfg['line_stop_cost_per_hour'],**kw)
        rows.append((name,m.fill_rate.mean(),m.critical_fill_rate.mean(),(m.line_stop_events>0).mean(),m.line_stop_events.mean(),m.total_disruption_cost_eur.mean()))
    return pd.DataFrame(rows,columns=['ablation','fill_rate','critical_fill_rate','line_stop_probability','mean_line_stop_events','mean_disruption_cost_eur'])


def _runtime_benchmark(parts,suppliers,packaging,compatibility,daily,vehicles,cfg):
    from .routing import supplier_flow_stats, build_milk_runs
    rows=[]
    for n in [100,300,600]:
        p=parts.iloc[:n].copy(); sids=sorted(p.supplier_id.unique()); s=suppliers[suppliers.supplier_id.isin(sids)].copy(); c=compatibility[compatibility.part_id.isin(p.part_id)].copy(); d=daily[['date']+p.part_id.tolist()].copy()
        t=time.perf_counter(); sel,freq,info=solve_packaging_frequency_milp(p,s,packaging,c,d,vehicles,cfg['holding_rate'],time_limit=30); milp_t=time.perf_counter()-t
        pack=evaluate_packaging_selection(p,packaging,d.drop(columns=['date']).sum(),sel)
        flow=supplier_flow_stats(p,d,pack,packaging,s); f=flow.merge(freq,on='supplier_id')
        t=time.perf_counter(); routes=build_milk_runs(s,f,vehicles); route_t=time.perf_counter()-t
        from .inventory import compute_inventory_policy,add_frequency_cycle_stock
        inv=compute_inventory_policy(p,s,d,cfg['holding_rate']); fp=p.set_index('part_id').supplier_id.map(freq.set_index('supplier_id').frequency_per_week); inv=add_frequency_cycle_stock(inv,fp,cfg['holding_rate'])
        t=time.perf_counter(); monte_carlo_advanced(p,s,d,inv,n=5,seed=700000+n,days=90); sim_t=time.perf_counter()-t
        rows.append((n,len(s),len(routes),milp_t,route_t,sim_t,info['mip_gap']))
    return pd.DataFrame(rows,columns=['parts','suppliers','routes','milp_runtime_s','routing_runtime_s','simulation_5rep_90d_s','mip_gap'])


def run_final(root: str|Path):
    tic=time.time(); root=Path(root); cfg=load_config(root/'configs/base.json'); raw=root/'data/raw'; proc=root/'data/processed'; out=root/'outputs'; proc.mkdir(parents=True,exist_ok=True); out.mkdir(exist_ok=True)
    print('[1/12] generate network', flush=True); ds=generate_network(cfg,raw); parts,suppliers,packaging,vehicles,daily,compatibility=[ds[k] for k in ['parts','suppliers','packaging','vehicles','daily_demand','compatibility']]
    issues=validate_data(parts,suppliers,packaging,compatibility)
    if issues: raise RuntimeError(issues)

    # Credible baselines and sequential policy.
    print('[2/12] baselines', flush=True); A=_complete_policy(baseline_a(parts,suppliers,packaging,compatibility,daily,vehicles,cfg['holding_rate']),parts,suppliers,packaging,daily,vehicles,cfg['n_receiving_docks'])
    B=_complete_policy(baseline_b(parts,suppliers,packaging,compatibility,daily,vehicles,cfg['holding_rate']),parts,suppliers,packaging,daily,vehicles,cfg['n_receiving_docks'])
    seq=_complete_policy(sequential_policy(parts,suppliers,packaging,compatibility,daily,vehicles,cfg['holding_rate']),parts,suppliers,packaging,daily,vehicles,cfg['n_receiving_docks'])

    # Nominal coordinated packaging-frequency MILP, then physical route/dock/inventory layers.
    print('[3/12] nominal MILP', flush=True); sel,milp_freq,milp_info=solve_packaging_frequency_milp(parts,suppliers,packaging,compatibility,daily,vehicles,cfg['holding_rate'],time_limit=30)
    pack=evaluate_packaging_selection(parts,packaging,daily.drop(columns=['date']).sum(),sel)
    nominal=build_policy(parts,suppliers,packaging,daily,vehicles,pack,milp_freq,cfg['holding_rate'],freq_scale=1.0,risk_freq_boost=0.0,safety_mult=1.0,critical_safety_mult=1.0,n_docks=cfg['n_receiving_docks'])
    route_issues=validate_routes(nominal['routes'],vehicles)
    if route_issues: raise RuntimeError(route_issues)

    # Scenario-based robust policy screen (training scenarios A).
    retids=set(pack.loc[pack.returnable,'part_id'])
    print('[4/12] robust screen', flush=True); screen,target,best=screen_candidates(parts,suppliers,packaging,daily,vehicles,pack,milp_freq,cfg['holding_rate'],cfg,retids,n_rep=6,seed=80000)
    target_name='Target+ robust'

    # Common out-of-sample nominal evaluation for core cost comparison.
    print('[5/12] core comparison', flush=True); compare=[]; mc_core={}
    for j,(name,pol) in enumerate([('Baseline A',A),('Baseline B',B),('Sequential',seq),('Nominal joint',nominal),(target_name,target)]):
        metrics,mc=_evaluate_policy(name,pol,parts,suppliers,packaging,daily,vehicles,cfg,seed=210000,n=60,correlated_risk=True)
        compare.append(metrics); mc_core[name]=mc
    comparison=pd.DataFrame(compare)

    # OOS scenario set B for nominal vs robust Target+.
    print('[6/12] out-of-sample', flush=True); oos_nom=_oos(nominal,parts,suppliers,packaging,daily,vehicles,cfg,seed=310000,n_each=25); oos_nom['policy']='Nominal joint'
    oos_tar=_oos(target,parts,suppliers,packaging,daily,vehicles,cfg,seed=410000,n_each=25); oos_tar['policy']=target_name
    oos=pd.concat([oos_nom,oos_tar],ignore_index=True)
    oos_summary=oos.groupby(['policy','scenario']).agg(fill_rate=('fill_rate','mean'),critical_fill_rate=('critical_fill_rate','mean'),line_stop_probability=('line_stop_events',lambda x:float((x>0).mean())),mean_line_stop_events=('line_stop_events','mean'),premium_freight_events=('premium_freight_events','mean'),p95_shortage_duration_days=('p95_shortage_duration_days','max'),mean_disruption_cost_eur=('total_disruption_cost_eur','mean')).reset_index()

    print('[7/12] stress/envelope/ablation', flush=True); stress_nom,_=_stress(nominal,parts,suppliers,packaging,daily,vehicles,cfg,seed=510000,n=30); stress_nom['policy']='Nominal joint'
    stress_tar,_=_stress(target,parts,suppliers,packaging,daily,vehicles,cfg,seed=610000,n=30); stress_tar['policy']=target_name
    stress=pd.concat([stress_nom,stress_tar],ignore_index=True)
    envelope=_resilience_envelope(target,parts,suppliers,daily,cfg)
    ablation=_ablation(target,parts,suppliers,daily,cfg)

    # Returnable closed-loop engineering.
    print('[8/12] returnables', flush=True); fleet=fleet_requirements(parts,target['packaging'],packaging,daily,suppliers,safety_pct=.10)
    states,ret_summary=simulate_returnable_loop(parts,target['packaging'],packaging,daily,suppliers,seed=20260913,days=180,safety_pct=.10)
    breakeven=returnable_break_even_by_part(parts,packaging,compatibility,target['packaging'],daily)
    rational=rationalization_curve(parts,packaging,compatibility,daily)

    # Pareto policies from robust candidate screen; cost vs transport CO2 with a transparent knee point.
    print('[9/12] pareto', flush=True); pfront=pareto_front(screen)
    if len(pfront):
        cn=(pfront.annual_cost_eur-pfront.annual_cost_eur.min())/max(pfront.annual_cost_eur.max()-pfront.annual_cost_eur.min(),1)
        en=(pfront.annual_co2e_kg-pfront.annual_co2e_kg.min())/max(pfront.annual_co2e_kg.max()-pfront.annual_co2e_kg.min(),1)
        pfront['distance_to_ideal']=np.sqrt(cn**2+en**2); pfront['knee_point']=False; pfront.loc[pfront.distance_to_ideal.idxmin(),'knee_point']=True

    print('[10/12] sensitivity', flush=True); sens,sens_prcc=sensitivity_experiment(parts,suppliers,packaging,daily,vehicles,target,cfg,set(target['packaging'].loc[target['packaging'].returnable,'part_id']),n=48)
    print('[11/12] runtime benchmark', flush=True); runtime=_runtime_benchmark(parts,suppliers,packaging,compatibility,daily,vehicles,cfg)

    # Cost component bridge against smart baseline B: accounting attribution, not causal Shapley value.
    print('[12/12] economics/output', flush=True); compB=comparison.set_index('policy').loc['Baseline B']; compT=comparison.set_index('policy').loc[target_name]
    categories=['transport_eur','packaging_material_eur','packaging_cleaning_repair_eur','reverse_logistics_eur','inventory_eur','handling_eur','damage_eur','dock_wait_eur','dock_overtime_eur','premium_freight_eur','line_stop_exposure_eur']
    bridge=pd.DataFrame({'cost_component':categories,'baseline_b_eur':[compB[c] for c in categories],'target_plus_eur':[compT[c] for c in categories]})
    bridge['saving_eur']=bridge.baseline_b_eur-bridge.target_plus_eur

    # Final economics: only incremental asset CAPEX relative to Baseline B + explicit enabling investments.
    fleetB=fleet_requirements(parts,B['packaging'],packaging,daily,suppliers,safety_pct=.10)
    incremental_container_capex=max(0.0,float(fleet.container_asset_eur.sum()-fleetB.container_asset_eur.sum()))
    enabling_capex=180000.0 # synthetic dock-slotting / tracking / implementation allowance, explicit assumption
    capex=incremental_container_capex+enabling_capex
    annual_saving=float(compB.total_landed_logistics_cost_eur-compT.total_landed_logistics_cost_eur)
    npv=probabilistic_npv(annual_saving,capex,seed=20260913,n=4096)

    # TTS/TTR proxy refreshed with target inventory coverage and supplier lead-time recovery proxy.
    pcover=target['inventory'][['part_id','mean_daily_demand','avg_inventory_units','criticality']].merge(parts[['part_id','supplier_id']],on='part_id')
    pcover['tts_days']=pcover.avg_inventory_units/np.maximum(pcover.mean_daily_demand,1e-9)
    tts=pcover.groupby('supplier_id').agg(tts_days=('tts_days','min'),critical_parts=('criticality',lambda x:int((x=='critical').sum()))).reset_index().merge(suppliers[['supplier_id','lead_time_days','risk_class','reliability_otif']],on='supplier_id')
    tts['ttr_days']=tts.lead_time_days*(1+tts.risk_class.map({'A':2.4,'B':1.5,'C':1.1}))
    tts['resilience_gap_days']=tts.ttr_days-tts.tts_days; tts['vulnerable_tts_lt_ttr']=tts.tts_days<tts.ttr_days

    # Value-of-information priority: sensitivity-backed ranking, not monetary EVPI.
    costp=sens_prcc[sens_prcc.response=='total_cost_eur'].set_index('input').prcc.abs().to_dict(); servp=sens_prcc[sens_prcc.response=='critical_fill_rate'].set_index('input').prcc.abs().to_dict()
    voi_rows=[
        ('supplier lead-time / OTIF distributions','supplier_reliability',costp.get('supplier_reliability',0)+servp.get('supplier_reliability',0),'Directly changes shortage and resilience estimates'),
        ('actual lane fill and carrier rate data','transport_cost',costp.get('transport_cost',0),'Re-estimates transport savings and consolidation value'),
        ('returnable turnaround / loss history','container_turnaround',costp.get('container_turnaround',0),'Changes operational fleet and reverse-loop economics'),
        ('actual inventory holding rate','holding_rate',costp.get('holding_rate',0),'Changes frequency vs inventory trade-off'),
        ('damage / packaging failure history','damage_probability',costp.get('damage_probability',0),'Changes packaging frontier and quality cost'),
        ('vehicle-mix / schedule variability','demand_variability',costp.get('demand_variability',0)+servp.get('demand_variability',0),'Changes service and robust-stock requirements'),
        ('dock service-time timestamps','dock_service_time',float(comparison.dock_wait_eur.max()/max(comparison.total_landed_logistics_cost_eur.mean(),1)),'Refines arrival staggering and receiving congestion'),
    ]
    voi=pd.DataFrame(voi_rows,columns=['real_data_item','linked_parameter','priority_score','decision_use']).sort_values('priority_score',ascending=False)

    # Save policies and analysis tables.
    artifacts={
        'baseline_a_routes':A['routes'],'baseline_b_routes':B['routes'],'sequential_routes':seq['routes'],'nominal_routes':nominal['routes'],'target_plus_routes':target['routes'],
        'baseline_b_packaging':B['packaging'],'nominal_packaging':nominal['packaging'],'target_plus_packaging':target['packaging'],
        'target_plus_frequency':target['frequency'],'target_plus_inventory':target['inventory'],'target_plus_dock_schedule':target['docks'],
        'robust_candidate_screen':screen,'pareto_frontier':pfront,'policy_comparison':comparison,'cost_component_bridge':bridge,
        'oos_results':oos,'oos_summary':oos_summary,'stress_suite':stress,'resilience_envelope':envelope,'ablation_study':ablation,
        'returnable_fleet_requirements':fleet,'returnable_state_history':states,'returnable_loop_summary':ret_summary,'returnable_break_even_parts':breakeven,
        'packaging_rationalization':rational,'sensitivity_samples':sens,'sensitivity_prcc':sens_prcc,'runtime_benchmark':runtime,
        'probabilistic_npv':npv,'tts_ttr':tts,'value_of_information':voi,
    }
    for name,df in artifacts.items(): df.to_csv(proc/f'{name}.csv',index=False)

    # Core final summary.
    b=float(compB.total_landed_logistics_cost_eur); nom=float(comparison.set_index('policy').loc['Nominal joint'].total_landed_logistics_cost_eur); tar=float(compT.total_landed_logistics_cost_eur)
    summary={
        'study_definition':'Research-grade synthetic automotive inbound logistics and packaging optimization study',
        'suppliers':len(suppliers),'parts':len(parts),'routes_target_plus':len(target['routes']),
        'tests_expected_minimum':40,
        'smart_baseline_b_cost_eur':b,'nominal_joint_cost_eur':nom,'robust_target_plus_cost_eur':tar,
        'robust_saving_vs_baseline_b_pct':1-tar/b,'nominal_saving_vs_baseline_b_pct':1-nom/b,
        'robustness_premium_vs_nominal_pct':tar/nom-1,
        'target_mean_cube_utilization':float(target['routes'].cube_utilization.mean()),'target_mean_weight_utilization':float(target['routes'].weight_utilization.mean()),
        'target_mean_pallet_utilization':float(target['routes'].pallet_position_utilization.mean()),
        'target_critical_fill_rate':float(compT.critical_fill_rate),'target_line_stop_probability':float(compT.line_stop_probability),
        'target_transport_co2e_kg':float(compT.transport_co2e_kg),'co2_change_vs_baseline_b_pct':float(compT.transport_co2e_kg/compB.transport_co2e_kg-1),
        'target_returnable_operational_fleet_units':int(fleet.operational_fleet.sum()),'target_returnable_theoretical_fleet_units':int(fleet.minimum_theoretical_fleet.sum()),
        'returnable_state_conservation_pass':bool(states.conserved.all()) if len(states) else True,
        'route_validation_issues':len(validate_routes(target['routes'],vehicles)),
        'dock_wait_mean_h':float(target['docks'].waiting_h.mean()),'dock_wait_p95_h':float(target['docks'].waiting_h.quantile(.95)),
        'dock_overtime_total_h_schedule':float(target['docks'].overtime_h.sum()),
        'milp_gap':milp_info['mip_gap'],'milp_nodes':milp_info['mip_node_count'],
        'chance_constraint_training_probability':float(best.chance_critical_ge_999),'training_line_stop_probability':float(best.line_stop_probability),
        'oos_target_critical_fill_rate':float(oos_tar.critical_fill_rate.mean()),'oos_nominal_critical_fill_rate':float(oos_nom.critical_fill_rate.mean()),
        'oos_target_line_stop_probability':float((oos_tar.line_stop_events>0).mean()),'oos_nominal_line_stop_probability':float((oos_nom.line_stop_events>0).mean()),
        'npv_p05_eur':float(npv.npv_eur.quantile(.05)),'npv_p50_eur':float(npv.npv_eur.quantile(.50)),'npv_p95_eur':float(npv.npv_eur.quantile(.95)),
        'npv_probability_positive':float((npv.npv_eur>0).mean()),'payback_p50_years':float(npv.payback_years.quantile(.50)),
        'incremental_capex_eur':capex,
        'main_resilience_risk_supplier':str(tts.sort_values('resilience_gap_days',ascending=False).iloc[0].supplier_id),
        'main_resilience_gap_days':float(tts.resilience_gap_days.max()),
        'vulnerable_suppliers_tts_lt_ttr':int(tts.vulnerable_tts_lt_ttr.sum()),
        'runtime_seconds':time.time()-tic,
    }
    (out/'final_summary.json').write_text(json.dumps(summary,indent=2))
    (out/'final_milp_info.json').write_text(json.dumps(milp_info,indent=2))
    return summary

if __name__=='__main__':
    import sys
    print(json.dumps(run_final(Path(sys.argv[1]) if len(sys.argv)>1 else Path.cwd()),indent=2))
