import pandas as pd
from aspilo.simulation import simulate

def test_mc_fill_rate_bounds(root):
    x=pd.read_csv(root/'data/processed/oos_results.csv')
    assert x.fill_rate.between(0,1).all()
    assert x.critical_fill_rate.between(0,1).all()

def test_mc_costs_nonnegative(root):
    x=pd.read_csv(root/'data/processed/stress_suite.csv')
    cols=['annual_cost_eur','mean_line_stop_events','premium_freight_events_mean','p95_shortage_duration_days']
    assert (x[cols] >= 0).all().all()

def test_stress_scenarios_present(root):
    x=pd.read_csv(root/'data/processed/stress_suite.csv')
    x=x[x.policy.eq('Target+ robust')]
    required={'nominal','fuel_plus_50pct','demand_plus_20pct','critical_supplier_disruption','container_shortage','carrier_capacity_shortage','combined_shock'}
    assert required <= set(x.scenario)

def test_demand_stress_reduces_service(root):
    x=pd.read_csv(root/'data/processed/stress_suite.csv')
    x=x[x.policy.eq('Target+ robust')].set_index('scenario')
    assert x.loc['demand_plus_20pct','critical_fill_rate'] < x.loc['nominal','critical_fill_rate']

def test_combined_stress_reduces_service(root):
    x=pd.read_csv(root/'data/processed/stress_suite.csv')
    x=x[x.policy.eq('Target+ robust')].set_index('scenario')
    assert x.loc['combined_shock','critical_fill_rate'] < x.loc['nominal','critical_fill_rate']
    assert x.loc['combined_shock','line_stop_probability'] == 1.0

def test_reproducibility(raw,proc):
    kwargs=dict(parts=raw['parts'],suppliers=raw['suppliers'],daily_demand=raw['daily_demand'],inventory_policy=proc['inventory_policy'],seed=991,days=40)
    a=simulate(**kwargs); b=simulate(**kwargs)
    assert a==b
