"""The v3 rule on made-up families: each case is one decision of Step 0, Sections 5.9-5.19."""
import pandas as pd
import pytest

from sector_rule import classify, load_rule

CASES = [
    # (title, abstract, codes, ipr_types, in sector?)
    ("Humanoid robot with a waist joint", "", ["B25J9/00"], "PI", True),
    ("Biped walking robot and its control method", "", ["B62D57/032"], "PI", True),         # one word between term and robot
    ("Bipedal robot", "", [], "PI", True),                                                    # 'robot' in the title is enough
    ("人形机器人的手臂结构", "", ["B25J17/00"], "PI", True),                                  # Chinese compound
    ("Humanoid robot", "", ["B25J9/00"], "UM", False),                                        # utility model: not a patent of invention
    ("Robot arm", "a joint for a humanoid robot", ["B25J9/00"], "PI", False),                  # humanoid only in the abstract
    ("Humanoid dexterous hand", "", ["B25J15/00"], "PI", False),                               # term does not name the robot
    ("Humanoid robot dexterous hand with tendons", "", ["B25J15/00"], "PI", False),           # a hand for a humanoid robot: removed by
                                                                                              # version 2 ("robot" is a part modifier, 5.16)
    ("Humanoid wrist", "", ["B25J17/02"], "PI", False),                                        # body part only
    ("Humanoid intelligent control method for a robot", "", ["G05B13/00"], "PI", False),      # control theory
    ("Exoskeleton humanoid robot", "", ["B25J9/0006"], "PI", False),                          # exoskeleton word in the title
    ("Humanoid robot toy", "", ["A63H11/00"], "PI", False),                                    # toy
    ("Crash test dummy with humanoid robot neck", "", [], "PI", False),                       # dummy
    ("Two-legged robot", "", [], "PI", False),                                                 # weak term needs a robotics code
    ("Two-legged robot", "", ["B62D57/032"], "PI", True),
    ("Quadruped robot", "", ["B62D57/032"], "PI", False),                                     # no humanoid term
]


@pytest.fixture(scope="module")
def result():
    fam = pd.DataFrame({"docdb_family_id": range(len(CASES)),
                        "title_text": [c[0].lower() for c in CASES],
                        "abstract_text": [c[1].lower() for c in CASES],
                        "ipr_types": [c[3] for c in CASES]})
    codes = pd.DataFrame([(i, code) for i, c in enumerate(CASES) for code in c[2]], columns=["docdb_family_id", "code"])
    return classify(fam, codes, load_rule())


@pytest.mark.parametrize("i", range(len(CASES)))
def test_case(result, i):
    assert bool(result.loc[i, "in_sector_v3"]) == CASES[i][4], CASES[i][0]


def test_one_row_per_family(result):
    assert len(result) == len(CASES) and result["docdb_family_id"].is_unique
