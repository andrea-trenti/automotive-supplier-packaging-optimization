from __future__ import annotations
import numpy as np
import pandas as pd

def summarize_costs(pack_choices,inventory_policy,routes_emissions,returnable_fleet,mc,route_cost_per_km=1.18,weeks=50):
    transport=(routes_emissions.route_km*routes_emissions.annual_trips*route_cost_per_km).sum()
    packaging=pack_choices.annual_packaging_cost_eur.sum(); handling=pack_choices.annual_handling_cost_eur.sum(); damage=pack_choices.annual_damage_cost_eur.sum()
    inventory=inventory_policy.annual_inventory_holding_eur.sum(); reverse=0.0
    if len(returnable_fleet): reverse=returnable_fleet.required_fleet.sum()*0.25
    premium=mc.premium_freight_cost_eur.mean(); disruption=mc.line_stop_cost_eur.mean()
    total=transport+packaging+handling+damage+inventory+reverse+premium+disruption
    return {'transport_eur':transport,'packaging_eur':packaging,'inventory_eur':inventory,'handling_eur':handling,'damage_eur':damage,'reverse_logistics_eur':reverse,'premium_freight_eur':premium,'expected_disruption_eur':disruption,'total_landed_logistics_cost_eur':total,'annual_co2e_kg':routes_emissions.annual_co2e_kg.sum()}

def cvar(series,alpha=.95):
    x=np.asarray(series,float); q=np.quantile(x,alpha); tail=x[x>=q]; return float(tail.mean()) if len(tail) else float(q)
