"""src/ and config/ must say what the notebooks say: a change made in one place only makes these tests fail."""
import ast
import json
import re
from pathlib import Path

import pytest

from sector_rule import load_rule, part_phrase_pattern, term_robot_pattern

ROOT = Path(__file__).resolve().parents[1]


def code_of(notebook):
    path = ROOT / notebook
    if not path.exists():
        pytest.skip(f"{notebook} not found")
    cells = json.load(open(path, encoding="utf-8"))["cells"]
    return "\n".join("".join(c["source"]) for c in cells if c["cell_type"] == "code")


def definitions(source):
    "Every top-level function of a piece of code, as a normalised syntax tree."
    clean = "\n".join(l for l in source.split("\n") if not l.lstrip().startswith(("%", "!")))
    tree = ast.parse(clean)
    return {n.name: ast.dump(n) for n in tree.body if isinstance(n, ast.FunctionDef)}


def assigned_value(source, name):
    "The literal value assigned to a name in the notebook (the last assignment)."
    value = None
    clean = "\n".join(l for l in source.split("\n") if not l.lstrip().startswith(("%", "!")))
    for node in ast.walk(ast.parse(clean)):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            try:
                value = ast.literal_eval(node.value)
            except ValueError:
                pass
    return value


@pytest.mark.parametrize("module, notebook", [("names.py", "step0_sector_definition.ipynb"),
                                              ("measures.py", "step2_concentration_subfields.ipynb")])
def test_functions_identical(module, notebook):
    ours = definitions((ROOT / "src" / module).read_text(encoding="utf-8"))
    theirs = definitions(code_of(notebook))
    if module == "measures.py":                       # wilson lives in Step 0
        theirs.update({k: v for k, v in definitions(code_of("step0_sector_definition.ipynb")).items() if k == "wilson"})
    for name, tree in ours.items():
        assert name in theirs, f"{name} is in src/{module} but not in {notebook}"
        assert tree == theirs[name], f"{name} differs between src/{module} and the notebook"


def test_rule_lists_identical():
    src, rule = code_of("step0_sector_definition.ipynb"), load_rule()
    assert assigned_value(src, "STRONG_TERMS") == rule["block_A"]["strong_terms"]
    assert assigned_value(src, "WEAK_TERMS") == rule["block_A"]["weak_terms"]
    assert assigned_value(src, "ROBOT_WORDS") == rule["block_A"]["robot_words"]
    assert assigned_value(src, "ROBOT_CONTEXT_CPC") == tuple(rule["block_A"]["robot_context_codes"])
    assert assigned_value(src, "EXO_CODES") == tuple(rule["exclusions"]["exo_codes"])
    for name in ("EXO_TERMS", "DUMMY_TERMS", "VIRTUAL_TERMS", "TOY_TERMS"):
        assert assigned_value(src, name) == rule["exclusions"][name.lower()]
    assert assigned_value(src, "PART_WORDS") == rule["version_2"]["part_words"]
    assert assigned_value(src, "PART_MODIFIERS") == rule["version_2"]["part_modifiers"]


def test_patterns_identical():
    "The regular expressions of versions 2 and 3, rebuilt from the YAML, are the notebook's ones."
    src, rule = code_of("step0_sector_definition.ipynb"), load_rule()
    ns = {"re": re, "PART_WORDS": rule["version_2"]["part_words"], "PART_MODIFIERS": rule["version_2"]["part_modifiers"]}
    for name in ("TERM_ROBOT", "PART_PHRASE"):
        m = re.search(rf"^{name} = re\.compile\(.*?\)\)?\n(?=\S|\n)", src, flags=re.M | re.S)
        assert m, f"{name} not found in the notebook"
        exec(m.group(0), ns)
    assert ns["TERM_ROBOT"].pattern == term_robot_pattern(rule).pattern
    assert ns["PART_PHRASE"].pattern == part_phrase_pattern(rule).pattern
