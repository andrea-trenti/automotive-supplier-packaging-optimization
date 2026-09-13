from __future__ import annotations
import json, hashlib
from pathlib import Path
import numpy as np


def load_config(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()
