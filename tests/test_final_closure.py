from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest

from aspilo.returnables_dynamic import fleet_requirements, simulate_returnable_loop
from aspilo.advanced_economics import probabilistic_npv

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / 'data' / 'processed'
OUT = ROOT / 'outputs'


def read(name):
    return pd.read_csv(PROC / f'{name}.csv')


def test_final_cost_reconciliation_all_policies():
    x = read('policy_comparison')
    components = [
        'transport_eur','packaging_material_eur','packaging_cleaning_repair_eur',
        'reverse_logistics_eur','inventory_eur','handling_eur','damage_eur',
        'dock_wait_eur','dock_overtime_eur','premium_freight_eur','line_stop_exposure_eur'
    ]
    reconstructed = x[components].sum(axis=1)
    assert np.allclose(reconstructed, x.total_landed_logistics_cost_eur, rtol=0, atol=0.02)


def test_bridge_reconciles_target_plus_saving():
    bridge = read('cost_component_bridge')
    comp = read('policy_comparison').set_index('policy')
    expected = comp.loc['Baseline B','total_landed_logistics_cost_eur'] - comp.loc['Target+ robust','total_landed_logistics_cost_eur']
    assert bridge.saving_eur.sum() == pytest.approx(expected, abs=0.05)


def test_defensible_saving_is_single_digit_not_legacy_40pct():
    comp = read('policy_comparison').set_index('policy')
    b = comp.loc['Baseline B','total_landed_logistics_cost_eur']
    t = comp.loc['Target+ robust','total_landed_logistics_cost_eur']
    saving = 1 - t/b
    assert 0.09 < saving < 0.10
    assert saving < 0.20


def test_robustness_premium_is_small_positive():
    comp = read('policy_comparison').set_index('policy')
    nominal = comp.loc['Nominal joint','total_landed_logistics_cost_eur']
    target = comp.loc['Target+ robust','total_landed_logistics_cost_eur']
    premium = target/nominal - 1
    assert 0 < premium < 0.01


def test_target_routes_obey_payload_cube_and_pallet_capacity():
    routes = read('target_plus_routes')
    veh = pd.read_csv(ROOT/'data/raw/vehicles.csv').set_index('vehicle_id')
    assert (routes.load_weight_kg <= routes.vehicle_id.map(veh.max_payload_kg) + 1e-8).all()
    assert (routes.load_cube_m3 <= routes.vehicle_id.map(veh.usable_cube_m3) + 1e-8).all()
    assert (routes.pallet_positions_used <= routes.vehicle_id.map(veh.pallet_positions) + 1e-8).all()


def test_target_route_time_is_physically_nonnegative_and_feasible():
    routes = read('target_plus_routes')
    assert (routes.route_duration_h > 0).all()
    assert routes.feasible.astype(str).str.lower().eq('true').all()


def test_transport_emissions_unit_formula_reconciles():
    e = read('target_plus_emissions')
    expected = e.tonne_km_per_trip * e.wtw_gco2e_tkm * e.annual_trips / 1000.0
    assert np.allclose(expected, e.annual_co2e_kg, rtol=1e-12, atol=1e-9)


def test_tonne_km_uses_kg_to_tonnes_conversion():
    e = read('target_plus_emissions')
    expected = (e.load_weight_kg / 1000.0) * e.route_km
    assert np.allclose(expected, e.tonne_km_per_trip, rtol=1e-12, atol=1e-9)


def test_co2_claim_is_baseline_specific():
    comp = read('policy_comparison').set_index('policy')
    target = comp.loc['Target+ robust','transport_co2e_kg']
    assert target < comp.loc['Baseline B','transport_co2e_kg']
    assert target > comp.loc['Baseline A','transport_co2e_kg']


def test_returnable_state_conservation_every_day():
    # GitHub distribution intentionally omits the multi-megabyte state-history artifact.
    # Recreate a deterministic 30-day audit in memory so the public package remains
    # lightweight while independently testing the closed-loop conservation invariant.
    parts = pd.read_csv(ROOT/'data/raw/parts.csv')
    suppliers = pd.read_csv(ROOT/'data/raw/suppliers.csv')
    packaging = pd.read_csv(ROOT/'data/raw/packaging.csv')
    daily = pd.read_csv(ROOT/'data/raw/daily_demand.csv')
    choices = read('target_plus_packaging')
    choices['returnable'] = choices.returnable.astype(str).str.lower().eq('true')
    states, _ = simulate_returnable_loop(
        parts, choices, packaging, daily, suppliers, seed=20260913, days=30, safety_pct=.10
    )
    assert not states.empty
    assert states.conserved.astype(str).str.lower().eq('true').all()
    base = states.groupby('part_id').apply(
        lambda g: int(g.iloc[0].live_fleet + g.iloc[0].lost), include_groups=False
    )
    reconstructed = states.live_fleet + states.lost
    expected = states.part_id.map(base)
    assert (reconstructed.to_numpy() == expected.to_numpy()).all()


def test_returnable_fleet_totals_and_allowance():
    f = read('returnable_fleet_requirements')
    assert int(f.minimum_theoretical_fleet.sum()) == 129888
    assert int(f.operational_fleet.sum()) == 150272
    assert (f.operational_fleet >= f.minimum_theoretical_fleet).all()


def test_returnable_loop_lost_containers_nonnegative_and_bounded():
    s = read('returnable_loop_summary')
    assert (s.containers_lost >= 0).all()
    assert (s.container_shortage_rate.between(0,1)).all()


def test_training_chance_service_requirement_is_met():
    c = json.load(open(OUT/'robust_selected_candidate.json'))
    assert c['chance_critical_ge_999'] >= 0.95
    assert c['critical_fill_rate'] >= 0.999


def test_oos_target_improves_tail_risk_over_nominal():
    o = read('oos_results')
    n = o[o.policy.eq('Nominal joint')]
    t = o[o.policy.eq('Target+ robust')]
    assert t.critical_fill_rate.mean() > n.critical_fill_rate.mean()
    assert (t.line_stop_events > 0).mean() < (n.line_stop_events > 0).mean()


def test_oos_scenario_sets_match_between_policies():
    s = read('oos_summary')
    n = set(s.loc[s.policy.eq('Nominal joint'),'scenario'])
    t = set(s.loc[s.policy.eq('Target+ robust'),'scenario'])
    assert n == t
    assert {'nominal','correlated','demand10','carrier','container','combined'} <= n


def test_combined_stress_remains_a_visible_failure_region():
    s = read('stress_suite').set_index(['policy','scenario'])
    n = s.loc[('Nominal joint','combined_shock')]
    t = s.loc[('Target+ robust','combined_shock')]
    assert t.critical_fill_rate > n.critical_fill_rate
    assert t.critical_fill_rate < 0.999
    assert t.line_stop_probability == pytest.approx(1.0)


def test_financial_monte_carlo_size_and_interpretation_inputs():
    # The public GitHub package omits the raw 4,096-row draw table; recreate it from
    # the frozen policy economics so the exact sample size and interpretation remain testable.
    parts = pd.read_csv(ROOT/'data/raw/parts.csv')
    suppliers = pd.read_csv(ROOT/'data/raw/suppliers.csv')
    packaging = pd.read_csv(ROOT/'data/raw/packaging.csv')
    daily = pd.read_csv(ROOT/'data/raw/daily_demand.csv')
    target = read('target_plus_packaging')
    base_b = read('baseline_b_packaging')
    for df in (target, base_b):
        df['returnable'] = df.returnable.astype(str).str.lower().eq('true')
    target_fleet = fleet_requirements(parts,target,packaging,daily,suppliers,safety_pct=.10)
    base_fleet = fleet_requirements(parts,base_b,packaging,daily,suppliers,safety_pct=.10)
    capex = max(0.0, float(target_fleet.container_asset_eur.sum()-base_fleet.container_asset_eur.sum())) + 180000.0
    comp = read('policy_comparison').set_index('policy')
    annual_saving = float(
        comp.loc['Baseline B','total_landed_logistics_cost_eur']
        - comp.loc['Target+ robust','total_landed_logistics_cost_eur']
    )
    n = probabilistic_npv(annual_saving, capex, seed=20260913, n=4096)
    assert len(n) == 4096
    assert n.npv_eur.quantile(.05) > 0
    assert (n.npv_eur > 0).mean() == pytest.approx(1.0)
    assert n.payback_years.quantile(.50) > 0


def test_tts_ttr_vulnerability_count():
    x = read('tts_ttr')
    flag = x.vulnerable_tts_lt_ttr.astype(str).str.lower().eq('true')
    assert int(flag.sum()) == 28
    assert x.resilience_gap_days.max() > 5.0
