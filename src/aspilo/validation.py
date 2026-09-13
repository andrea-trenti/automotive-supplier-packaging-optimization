from __future__ import annotations
import pandas as pd

def validate_data(parts,suppliers,packaging,compatibility):
    issues=[]
    if parts.part_id.duplicated().any(): issues.append('duplicate part_id')
    if suppliers.supplier_id.duplicated().any(): issues.append('duplicate supplier_id')
    if (parts.unit_weight_kg<=0).any(): issues.append('nonpositive part weight')
    if (parts.unit_volume_m3<=0).any(): issues.append('nonpositive part volume')
    if (packaging.internal_volume_m3<=0).any(): issues.append('nonpositive packaging volume')
    missing=set(parts.supplier_id)-set(suppliers.supplier_id)
    if missing: issues.append(f'missing suppliers: {len(missing)}')
    feasible=set(compatibility.part_id); no_pack=set(parts.part_id)-feasible
    if no_pack: issues.append(f'parts without feasible packaging: {len(no_pack)}')
    return issues

def validate_routes(routes,vehicles):
    vm=vehicles.set_index('vehicle_id'); issues=[]
    for _,r in routes.iterrows():
        v=vm.loc[r.vehicle_id]
        if r.load_weight_kg>v.max_payload_kg+1e-9: issues.append(f'{r.route_id}: payload overload')
        if r.load_cube_m3>v.usable_cube_m3+1e-9: issues.append(f'{r.route_id}: cube overload')
        if 'pallet_positions_used' in routes.columns and r.pallet_positions_used>v.pallet_positions+1e-9: issues.append(f'{r.route_id}: pallet-position overload')
        if r.route_duration_h>11.5+1e-9: issues.append(f'{r.route_id}: route duration')
    return issues
