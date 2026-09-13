from __future__ import annotations
import numpy as np
import pandas as pd

def supplier_risk(parts,suppliers,daily_demand):
    annual=daily_demand.drop(columns=['date']).sum()
    p=parts[['part_id','supplier_id','unit_value_eur','criticality']].copy(); p['annual_units']=p.part_id.map(annual)
    crit={'critical':4,'high':3,'medium':2,'low':1}; p['crit_score']=p.criticality.map(crit)
    agg=p.groupby('supplier_id').agg(parts=('part_id','count'),criticality_exposure=('crit_score','sum'),annual_spend_proxy=('annual_units',lambda x:0)).reset_index()
    spend=(p.annual_units*p.unit_value_eur).groupby(p.supplier_id).sum(); agg['annual_spend_proxy']=agg.supplier_id.map(spend)
    out=agg.merge(suppliers[['supplier_id','reliability_otif','lead_time_days','risk_class']],on='supplier_id')
    out['disruption_probability_proxy']=(1-out.reliability_otif).clip(.002,.25)
    out['exposure_eur']=out.annual_spend_proxy*(1+0.15*out.criticality_exposure/out.parts)
    out['risk_eur']=out.disruption_probability_proxy*out.exposure_eur
    out['tts_days_proxy']=2.0+5.0*out.reliability_otif
    out['ttr_days_proxy']=out.lead_time_days*(1+out.risk_class.map({'A':2.4,'B':1.5,'C':1.1}))
    out['vulnerable_tts_lt_ttr']=out.tts_days_proxy<out.ttr_days_proxy
    return out
