"""Subfields (src/subfields.py): platform, body or control, read from the English title. Titles of the kind found
in the sector (Step 0, Section 7.4, run of 23 November), no PATSTAT data."""
import pandas as pd
import pytest

from subfields import as_humanoid, subfield_of, subfields


@pytest.mark.parametrize("title, expected, kind", [
    # the whole robot
    ("Humanoid robot", "platform", "platform"),
    ("Humanoid robot with flying function", "platform", "platform"),
    ("Biped walking robot", "platform", "platform"),                       # a rule-v3 term, read as "humanoid robot"
    ("Two-legged walking-type human-shaped robot", "platform", "platform"),
    ("Wheel leg type humanoid robot with internal oil flowing", "platform", "platform"),   # a form of robot, not a leg
    ("Humanoid robot for classroom light environment detection", "platform", "platform"),
    # a part of the body or of the hardware, wherever it stands in the title
    ("Waterproof and dustproof humanoid robot actuator", "body", "joint"),
    ("High-precision zero-backlash humanoid robot joint speed reducer", "body", "joint"),
    ("Self-supporting spine of a humanoid robot", "body", "other_part"),
    ("Dexterous hand and humanoid robot", "body", "hand"),
    ("Humanoid robot leg structure based on planetary roller screw", "body", "leg"),
    ("Human-like biped robot foot structure", "body", "foot"),
    # a method, an algorithm, a controller or software
    ("Humanoid robot navigation method", "control", "navigation_planning"),
    ("Humanoid robot reinforcement learning training method, device and storage medium", "control", "learning"),
    ("Gait planning method for biped humanoid robot walking on slope", "control", "locomotion"),
    ("Humanoid robot-oriented dialogue arrangement method and related equipment", "control", "interaction"),
    ("Design method for visual sensing system of humanoid robot", "control", "perception"),
    ("Embedded motion controller of humanoid robot", "control", "other_control"),
])
def test_titles(title, expected, kind):
    sub, k, source = subfield_of(title, "")
    assert (sub, k, source) == (expected, kind, "title")


def test_a_method_on_a_part_is_control():
    "Control words come first: a method that acts on a part is a control family."
    assert subfield_of("Method of tracking control for foot force of biped robot", "")[0] == "control"


def test_no_english_title_uses_the_first_sentence_of_the_abstract():
    sub, kind, source = subfield_of("人形机器人", "The invention discloses a waist joint of a humanoid robot. It has a motor.")
    assert (sub, kind, source) == ("body", "torso", "abstract")      # the first part named: waist


def test_no_english_text_is_unclear():
    assert subfield_of("人形机器人", "")[0] == "unclear"
    assert subfield_of("", "")[0] == "unclear"


def test_v3_terms_become_humanoid_robot():
    assert as_humanoid("A BIPED walking robot") == "a humanoid robot"
    assert as_humanoid("Human-like robot arm") == "humanoid robot arm"
    assert as_humanoid("Quadruped robot") == "quadruped robot"          # not a rule-v3 term: unchanged


def test_table_one_row_per_family():
    texts = pd.DataFrame({"docdb_family_id": [1, 2, 3, 4],
                          "title_en": ["Humanoid robot", "Waist joint of humanoid robot", "Humanoid robot gait control method", None],
                          "abstract_en": ["", "", "", None]})
    out = subfields(texts)
    assert out["docdb_family_id"].tolist() == [1, 2, 3, 4]
    assert out["subfield"].tolist() == ["platform", "body", "control", "unclear"]
    with pytest.raises(ValueError):
        subfields(pd.concat([texts, texts]))
