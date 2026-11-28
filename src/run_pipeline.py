"""Run the pipeline notebooks in order, top to bottom, on TIP (kick-off layout: src/01_extract.py ... 06_quadrant.py).

Each numbered script in src/ calls `run(step)`; `python src/run_pipeline.py` runs every step. The notebooks are
executed in place with nbconvert, so their outputs are saved in the notebook (aggregated tables and figures only:
never commit a notebook that displays raw PATSTAT titles or abstracts to a public remote).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEPS = {
    "01_extract": ["step0_sector_definition.ipynb"],                       # Step 0: sector, validation, tables
    "02_describe": ["step1_volume_growth.ipynb"],                          # Step 1: volume, technologies, geography
    "03_landscape": ["step2_concentration_subfields.ipynb",                # Step 2: concentration, entrants, subfields, PEST
                     "t2_20_epab_humanoid.ipynb", "t2_21_text_humanoid.ipynb"],
    "04_present_score": ["step3_present_score.ipynb"],                     # Step 3 (and Section 11: the common set of firms)
    "05_future_score": ["step4_future_score.ipynb"],                       # Step 4 (and the data of the quadrant)
    # "06_quadrant": Step 5, to be written (reads outputs/step4/magic_quadrant_data.csv)
}


def run(step: str, timeout: int = 6 * 3600) -> None:
    for nb in STEPS[step]:
        path = ROOT / nb
        print(f"[{step}] running {nb} ...", flush=True)
        subprocess.run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace",
                        f"--ExecutePreprocessor.timeout={timeout}", str(path)], check=True, cwd=ROOT)


if __name__ == "__main__":
    for s in (sys.argv[1:] or list(STEPS)):
        run(s)
