from pathlib import Path
import sys
import pandas as pd
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

@pytest.fixture(scope='session')
def root(): return ROOT

@pytest.fixture(scope='session')
def raw(root):
    d=root/'data/raw'
    return {n:pd.read_csv(d/f'{n}.csv') for n in ['suppliers','parts','packaging','vehicles','production_schedule','daily_demand','compatibility']}

@pytest.fixture(scope='session')
def proc(root):
    d=root/'data/processed'
    files={
        'packaging_choices':'target_plus_packaging',
        'frequency_policy':'target_plus_frequency',
        'inventory_policy':'target_plus_inventory',
        'routes':'target_plus_routes',
        'dock_schedule':'target_plus_docks',
        'returnable_fleet':'target_plus_returnables',
        'route_emissions':'target_plus_emissions',
        'supplier_risk':'supplier_risk',
        'baseline_packaging_choices':'baseline_a_packaging',
        'baseline_routes':'baseline_a_routes',
    }
    return {logical:pd.read_csv(d/f'{fname}.csv') for logical,fname in files.items()}
