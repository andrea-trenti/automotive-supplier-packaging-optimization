from pathlib import Path
from src.aspilo.final_pipeline import run_final
import json
if __name__=='__main__':
    print(json.dumps(run_final(Path(__file__).resolve().parent),indent=2))
