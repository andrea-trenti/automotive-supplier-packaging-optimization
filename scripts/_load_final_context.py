from pathlib import Path
import sys,json,pandas as pd
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
cfg=json.load(open(ROOT/'configs/base.json')); raw=ROOT/'data/raw'; proc=ROOT/'data/processed'; out=ROOT/'outputs'
parts=pd.read_csv(raw/'parts.csv'); suppliers=pd.read_csv(raw/'suppliers.csv'); packaging=pd.read_csv(raw/'packaging.csv'); daily=pd.read_csv(raw/'daily_demand.csv'); vehicles=pd.read_csv(raw/'vehicles.csv'); compatibility=pd.read_csv(raw/'compatibility.csv')
def pol(prefix):
 d={}
 for key in ['packaging','frequency','routes','inventory','docks','returnables','emissions']:
  p=proc/f'{prefix}_{key}.csv'
  if p.exists(): d[key]=pd.read_csv(p)
 if 'packaging' in d: d['packaging']['returnable']=d['packaging'].returnable.astype(str).str.lower().eq('true')
 return d
