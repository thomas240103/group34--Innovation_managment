"""Locate and validate a completed export from Thomas's Step 0."""

import json
from pathlib import Path


def load_prod_run(root, selected_folder=None, end_year=None):
    root = Path(root)
    required = ("candidates.csv", "retrieval_hits.csv", "assigned_codes.csv")

    if selected_folder is not None:
        folders = [root / Path(selected_folder).expanduser()]
    else:
        sources = [
            root / "outputs/thomas_retrieval",
            root / "results",
            root.parent / "group34-thomas-prod/outputs/thomas_retrieval",
            Path.home() / "group34-thomas-prod/outputs/thomas_retrieval",
            Path.home() / "patent_single_workflow/results",
        ]
        folders = sorted(
            (folder for parent in sources for folder in parent.glob("search_*_PROD")),
            key=lambda folder: folder.name,
            reverse=True,
        )

    for folder in folders:
        manifest = folder / "search_terms.json"
        if not manifest.is_file():
            continue
        meta = json.loads(manifest.read_text(encoding="utf-8-sig"))
        if (
            meta.get("environment") == "PROD"
            and meta.get("retrieval_complete") is True
            and meta.get("export_complete") is True
            and meta.get("cap_per_lane_period") is None
            and (end_year is None or max((end for _, end in meta["periods"]), default=0) == end_year)
            and all((folder / name).is_file() for name in required)
        ):
            return folder.resolve(), meta

    location = str(folders[0]) if selected_folder is not None else "the known TIP output folders"
    raise FileNotFoundError(
        f"No completed uncapped Step 0 PROD export found in {location}. "
        "Set PROD_FOLDER to the folder containing search_terms.json and the three CSVs."
    )
