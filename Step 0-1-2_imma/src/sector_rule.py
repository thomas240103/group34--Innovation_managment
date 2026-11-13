"""The sector rule of Step 0, version 3, as plain functions.

The rule is read from config/sector_rule_v3.yaml. step0_sector_definition.ipynb applies the same rule cell by cell
(Sections 5.9, 5.13, 5.16 and 5.19); tests/test_notebook_in_sync.py checks that the lists and patterns are the same.

Input: one row per DOCDB family with
    docdb_family_id, title_text, abstract_text  (all titles / abstracts of the family, joined and lower-cased),
    ipr_types                                   (the IPR types of its applications joined with '|', e.g. 'PI|UM'),
and one row per family and classification code (CPC or IPC, no spaces, e.g. 'B62D57/032').
In the notebook the rule runs on the families of the wide net (Section 5.6), which holds every family that can pass it.
"""
from pathlib import Path
import re

import numpy as np
import pandas as pd
import yaml

CONFIG = Path(__file__).resolve().parents[1] / "config" / "sector_rule_v3.yaml"


def load_rule(path=CONFIG):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def term_pattern(terms, whole_word=False):
    """One regular expression for a list of terms.

    Latin-script terms must start a word: 'biped' finds 'bipedal' but 'hip' does not find 'ship'.
    With whole_word=True they must also end a word ('hip' does not find 'hipped').
    Chinese, Japanese and Korean terms are matched as they are (no spaces between words).
    """
    parts = []
    for term in terms:
        t = re.escape(term.lower())
        if re.search(r"[a-z]", term.lower()):
            parts.append(r"(?<![a-z0-9])" + t + (r"(?![a-z0-9])" if whole_word else ""))
        else:
            parts.append(t)
    return re.compile("|".join(parts))


def term_robot_pattern(rule):
    """Version 3: a humanoid term directly followed by 'robot(s)', with at most one word in between,
    or a Chinese, Japanese or Korean compound that already contains 'robot'."""
    v3 = rule["version_3"]
    return re.compile(
        r"(?<![a-z0-9])(?:" + "|".join(v3["term_robot_terms"]) + r")"
        r"\s+(?:[a-z0-9-]+\s+)?robots?(?![a-z0-9])"
        r"|" + "|".join(v3["term_robot_compounds"]))


def part_phrase_pattern(rule):
    """Version 2: 'humanoid' used only as the adjective of a body part (humanoid wrist, anthropomorphic hand)."""
    v2 = rule["version_2"]
    return re.compile(
        r"(?<![a-z0-9])(?:" + "|".join(v2["part_adjectives"]) + r")\s+"
        r"(?:(?:" + "|".join(map(re.escape, v2["part_modifiers"])) + r")\s+)*"
        r"(?:" + "|".join(v2["part_words"]) + r")(?![a-z0-9])"
        r"|" + "|".join(v2["part_compounds"]))


def classify(families, codes, rule=None):
    """Flags of the rule for every family, and the final column in_sector_v3.

    Returns a DataFrame with one row per family of `families`, in the same order."""
    rule = rule or load_rule()
    a, ex, v2 = rule["block_A"], rule["exclusions"], rule["version_2"]
    weak = a["weak_terms"]
    core = [t for t in a["strong_terms"] if t not in weak]
    title = families["title_text"].fillna("").str.lower()
    abstract = families["abstract_text"].fillna("").str.lower()
    ids = families["docdb_family_id"]

    def any_code(prefixes):
        found = set(codes.loc[codes["code"].str.startswith(tuple(prefixes)), "docdb_family_id"])
        return ids.isin(found).to_numpy()

    def has(text, terms, whole_word=False):
        return text.str.contains(term_pattern(terms, whole_word)).to_numpy()

    f = pd.DataFrame({"docdb_family_id": ids.to_numpy()})
    f["robot_code"] = any_code(a["robot_context_codes"])
    f["robot_word"] = has(title, a["robot_words"]) | has(abstract, a["robot_words"])
    f["core_title"] = has(title, core)
    f["weak_title"] = has(title, weak)
    f["block_A"] = (f["core_title"] & (f["robot_code"] | f["robot_word"])) | (f["weak_title"] & f["robot_code"])

    # Exclusions. Code B25J9/0006 ("exoskeletons, i.e. resembling a human figure") also tags humanoids, so the
    # code with an exoskeleton word in the abstract excludes a family only if its title does not name a humanoid.
    exo = has(title, ex["exo_terms"]) | (any_code(ex["exo_codes"]) & has(abstract, ex["exo_terms"]) & ~f["core_title"])
    dummy = has(title, ex["dummy_terms"], whole_word=True)
    virtual = has(title, ex["virtual_terms"]) & ~has(title, a["robot_words"])
    toy = has(title, ex["toy_terms"], whole_word=True)
    f["excluded"] = np.select([exo, dummy, virtual, toy],
                              ["exoskeleton/prosthesis", "mannequin/dummy", "virtual", "toy (broad only)"], default="")
    f["is_pi"] = families["ipr_types"].fillna("").str.contains("|".join(rule["window"]["ipr_types_sector"])).to_numpy()
    f["block_A_final"] = f["is_pi"] & (f["excluded"] == "") & f["block_A"]

    # Version 2 exclusions and version 3 requirement.
    part = part_phrase_pattern(rule)
    core_re = term_pattern(core)
    f["part_only"] = [bool(part.search(t)) and not core_re.search(part.sub(" ", t)) for t in title]
    f["other_sense"] = title.str.contains(re.compile(r"(?<![a-z0-9])" + v2["other_sense"])).to_numpy()
    f["term_robot_title"] = title.str.contains(term_robot_pattern(rule)).to_numpy()
    f["in_sector_v3"] = f["block_A_final"] & f["term_robot_title"] & ~f["part_only"] & ~f["other_sense"]
    return f
