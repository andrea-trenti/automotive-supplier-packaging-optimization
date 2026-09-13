from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.stats import norm

CRIT_SERVICE={'critical':0.999,'high':0.995,'medium':0.985,'low':0.97}

def compute_inventory_policy(parts:pd.DataFrame,suppliers:pd.DataFrame,daily_demand:pd.DataFrame,holding_rate:float)->pd.DataFrame:
    sm=suppliers.set_index('supplier_id')
    demand=daily_demand.drop(columns=['date'])
    rows=[]
    for _,p in parts.iterrows():
        s=sm.loc[p.supplier_id]
        x=demand[p.part_id].to_numpy(float)
        mu=float(np.mean(x)); sd=float(np.std(x,ddof=1))
        L=float(s.lead_time_days); sdL=float(s.lead_time_days*s.lead_time_cv)
        sigma_lt=np.sqrt(max(0,L*sd**2 + (mu**2)*(sdL**2)))
        service=CRIT_SERVICE[p.criticality]; z=float(norm.ppf(service))
        ss=z*sigma_lt; rop=mu*L+ss
        rows.append((p.part_id,mu,sd,L,sdL,service,z,ss,rop))
    out=pd.DataFrame(rows,columns=['part_id','mean_daily_demand','sd_daily_demand','mean_lead_time_days','sd_lead_time_days','target_cycle_service','z','safety_stock_units','reorder_point_units'])
    out=out.merge(parts[['part_id','unit_value_eur','criticality']],on='part_id')
    out['annual_safety_stock_holding_eur']=out.safety_stock_units*out.unit_value_eur*holding_rate
    return out


def add_frequency_cycle_stock(policy:pd.DataFrame, frequency_per_week:pd.Series, holding_rate:float)->pd.DataFrame:
    out=policy.copy(); f=out.part_id.map(frequency_per_week).fillna(5).clip(lower=.5)
    interval=5.0/f
    out['delivery_interval_days']=interval
    out['cycle_stock_units']=0.5*out.mean_daily_demand*interval
    out['pipeline_inventory_units']=out.mean_daily_demand*out.mean_lead_time_days
    out['avg_inventory_units']=out.safety_stock_units+out.cycle_stock_units+out.pipeline_inventory_units
    out['annual_inventory_holding_eur']=out.avg_inventory_units*out.unit_value_eur*holding_rate
    return out
