from __future__ import annotations
import pandas as pd

def route_emissions(routes:pd.DataFrame,vehicles:pd.DataFrame,weeks=50)->pd.DataFrame:
    v=vehicles.set_index('vehicle_id')
    out=routes.copy()
    # Activity-based t-km using actual loaded mass; conservative factor already embeds average empty running/load factor when default GLEC factor is used.
    out['annual_trips']=out.frequency_per_week*weeks
    out['tonne_km_per_trip']=(out.load_weight_kg/1000)*out.route_km
    out['wtw_gco2e_tkm']=out.vehicle_id.map(v.glec_wtw_gco2e_tkm)
    out['annual_co2e_kg']=out.tonne_km_per_trip*out.wtw_gco2e_tkm*out.annual_trips/1000
    return out
