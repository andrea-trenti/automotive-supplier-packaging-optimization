import numpy as np

def test_safety_stock_nonnegative(proc):
    assert (proc['inventory_policy'].safety_stock_units >= 0).all()

def test_rop_above_mean_lead_demand(proc):
    x=proc['inventory_policy']
    assert (x.reorder_point_units + 1e-8 >= x.mean_daily_demand*x.mean_lead_time_days).all()

def test_critical_service_ordering(proc):
    x=proc['inventory_policy']
    means=x.groupby('criticality').target_cycle_service.mean().to_dict()
    assert means['critical'] > means['high'] > means['medium'] > means['low']

def test_supplier_risk_finite(proc):
    x=proc['supplier_risk']
    assert np.isfinite(x.risk_eur).all()
    assert (x.disruption_probability_proxy.between(0,1)).all()

def test_tts_ttr_boolean(proc):
    x=proc['supplier_risk']
    assert set(x.vulnerable_tts_lt_ttr.astype(str).str.lower().unique()) <= {'true','false'}
