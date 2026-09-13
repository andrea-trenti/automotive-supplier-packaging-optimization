import json

def test_exactly_one_packaging_per_part(proc,raw):
    assert len(proc['packaging_choices'])==len(raw['parts'])
    assert not proc['packaging_choices'].part_id.duplicated().any()

def test_frequency_meets_physical_min(proc):
    x=proc['frequency_policy']
    assert (x.frequency_per_week + 1e-9 >= x.minimum_physical_frequency).all()

def test_summary_solver_gap(root):
    info=json.load(open(root/'outputs/final_milp_info.json'))
    assert info['mip_gap'] <= 0.002+1e-12

def test_optimized_cost_below_baseline(root):
    s=json.load(open(root/'outputs/final_summary.json'))
    assert s['robust_target_plus_cost_eur'] < s['smart_baseline_b_cost_eur']

def test_no_route_validation_issues(proc):
    assert proc['routes'].feasible.astype(str).str.lower().eq('true').all()
