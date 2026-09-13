import numpy as np
from aspilo.validation import validate_data,validate_routes

def test_data_quality(raw):
    assert validate_data(raw['parts'],raw['suppliers'],raw['packaging'],raw['compatibility']) == []

def test_every_part_has_packaging(raw):
    assert set(raw['parts'].part_id) <= set(raw['compatibility'].part_id)

def test_route_weight_and_cube(proc,raw):
    assert validate_routes(proc['routes'],raw['vehicles']) == []

def test_utilization_bounded(proc):
    assert (proc['routes'].weight_utilization <= 1+1e-9).all()
    assert (proc['routes'].cube_utilization <= 1+1e-9).all()
    assert (proc['routes'][['weight_utilization','cube_utilization']] >= 0).all().all()

def test_packaging_geometry_limits(proc):
    p=proc['packaging_choices']
    assert (p.units_per_container >= 1).all()
    assert (p.cube_utilization <= 1+1e-9).all()
    assert (p.gross_weight_kg > 0).all()

def test_returnable_fleet_positive(proc):
    r=proc['returnable_fleet']
    assert (r.required_fleet > 0).all()
    assert (r.container_asset_eur > 0).all()

def test_emissions_nonnegative(proc):
    assert (proc['route_emissions'].annual_co2e_kg >= 0).all()

def test_dock_wait_nonnegative(proc):
    assert (proc['dock_schedule'].waiting_h >= 0).all()
    assert (proc['dock_schedule'].scheduled_end_h >= proc['dock_schedule'].scheduled_start_h).all()
