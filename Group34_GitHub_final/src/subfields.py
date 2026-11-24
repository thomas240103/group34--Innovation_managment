"""Subfields inside the sector: what does each family protect?

- platform: the whole humanoid robot ("Humanoid robot", "Biped walking robot", "Humanoid robot with flying function");
- body: a hardware part of the robot (joint, actuator, motor, hand, leg, foot, spine, sensor, structure...);
- control: a method, an algorithm, a controller or software (gait planning, learning, navigation, dialogue...).

The idea of separating the whole robot from its parts is Thomas's (group branch thomas240103-patch-1,
src/full_classification.py), and so are the patterns that name the part of the body (TOPICS, `technology`).
His rule decides from the position of "humanoid robot" in the sentence: on our 2,907 families it left 35% of them
undecided (a part written before the robot: "humanoid robot joint speed reducer") and called "platform" many
methods ("Humanoid robot navigation method"). So the decision here reads the words of the title, in this order:
a method or control word -> control; otherwise a part of the body or of the hardware -> body; otherwise platform.

Every family of the sector already passed rule v3: the rule-v3 terms (biped, android, two-legged, human-like robot)
are written as "humanoid robot" before reading. The rules read English: the English title, or, if a family has
none, the first sentence of its English abstract. A family with neither is "unclear".
"""

import re
from unicodedata import normalize

import pandas as pd


FAMILY_ID = "docdb_family_id"

# ---------------------------------------------------------------- Thomas's patterns for the part of the body (unchanged)
TOPICS = {
    "platform": (5, r"\b(?:humanoid|android|biped(?:al)?|two[- ]legged|human[- ](?:like|shaped)|torso|whole[- ]body)\b"),
    "control_locomotion": (5, r"\b(?:gait|locomotion|stance|balance control|zero moment point|motion planning|walking control|fall control)\b"),
    "hand": (4, r"\b(?:hands?|fingers?|palm|knuckles?|phalanges|phalangeal|interphalangeal)\b"),
    "foot": (4, r"\b(?:feet|foot|ankles?|sole|heel|toe)\b"),
    "shoulder": (4, r"\b(?:shoulders?|scapul[ae]|clavicl[ae]s?)\b"),
    "arm": (4, r"\b(?:arms?|forearms?|elbows?)\b"),
    "joint": (4, r"\b(?:joints?|articulations?|actuators?|wrist|transmission)\b"),
}
TOPIC_PATTERNS = {
    key: re.compile(expression) for key, (_, expression) in TOPICS.items() if key != "platform"
}
TOPIC_PATTERNS.update({
    "leg": re.compile(r"\b(?:legs?|knees?|thighs?|shins?)\b"),
    "head_neck": re.compile(r"\b(?:heads?|necks?|face)\b"),
    "torso": re.compile(r"\b(?:torso|trunk|waist)\b"),
    "other_component": re.compile(r"\b(?:grippers?|manipulators?|end effectors?|cooling system)\b"),
})
TOPIC_PATTERNS["control_locomotion"] = re.compile(
    TOPICS["control_locomotion"][1] + r"|\b(?:fall direction|stepping|bipedal control|"
    r"posture control|humanoid (?:robot )?control)\b"
)
HTML = re.compile(r"</?[a-z][^>]*>", re.IGNORECASE)
SENTENCES = re.compile(r"(?<=[.!?])\s+")

# ---------------------------------------------------------------- our patterns
# The English terms of rule v3 (config/sector_rule_v3.yaml, Step 0 cell TERM_ROBOT), with at most one word before
# "robot", written as "humanoid robot": inside the sector they all mean a humanoid robot.
V3_TERM = re.compile(
    r"(?<![a-z0-9])(?:biped|bipedal|android|anthropomorphic|human-like|humanlike|human like|"
    r"human-shaped|human shaped|human-type|human type|human-form|two-legged|two legged)"
    r"\s+(?:[a-z0-9-]+\s+)?robots?(?![a-z0-9])"
)
# Forms of the robot that contain a body word but name the whole robot ("wheel-legged humanoid robot")
ROBOT_FORM = re.compile(r"\bwheel[- ]?(?:leg|legs|legged|foot)(?:[- ]type| type)?\b|\blegged\b")
CONTROL = re.compile(
    r"\b(?:methods?|algorithms?|programs?|software|storage media|storage medium|computer|"
    r"learning|training|planning|recognition|navigation|simulation|estimation|calibration|optimi[sz]ation|"
    r"dialogue|conversation|controllers?|control (?:systems?|modules?|units?|circuits?|devices?|apparatus|boards?))\b"
)
BODY = re.compile(
    r"\b(?:joints?|actuators?|reducers?|motors?|gears?|gearboxes?|transmissions?|clutch\w*|bearings?|springs?|"
    r"tendons?|cables?|hands?|fingers?|palms?|thumbs?|grippers?|arms?|forearms?|elbows?|wrists?|shoulders?|"
    r"legs?|knees?|thighs?|shins?|calf|calves|feet|foot|ankles?|soles?|toes?|heels?|hips?|waist|pelvis|spine|"
    r"vertebra\w*|ribs?|thoracic|chest|torso|trunk|heads?|necks?|faces?|facial|eyes?|eyeballs?|mouth|lips?|ears?|"
    r"skin|shells?|housings?|covers?|frames?|skeletons?|structures?|mechanisms?|assembl\w+|modules?|parts?|"
    r"components?|sensors?|batter\w+|circuits?|driv\w+ (?:devices?|mechanisms?|units?|systems?)|power supply)\b"
)
# What a control family is about (for Step 2); the first match wins
CONTROL_KIND = [
    ("learning", re.compile(r"\b(?:learning|neural|reinforcement|training|imitation|large model|language model)\b")),
    ("locomotion", re.compile(r"\b(?:gait|walk\w*|balance|zmp|zero moment point|fall\w*|locomotion|stance|jump\w*|"
                              r"run(?:ning)?|kick\w*|step\w*|stairs?)\b")),
    ("perception", re.compile(r"\b(?:vision|visual|image|camera|recognition|sensing|perception|detection|tactile|"
                              r"localization|mapping|slam)\b")),
    ("interaction", re.compile(r"\b(?:dialogue|conversation|speech|voice|emotion\w*|interaction|expression|"
                               r"language|teleoperat\w*|remote)\b")),
    ("navigation_planning", re.compile(r"\b(?:navigation|path|trajectory|planning|obstacle\w*)\b")),
]
LATIN = re.compile(r"[a-z]")


# ---------------------------------------------------------------- functions
def clean(text):
    text = HTML.sub(" ", normalize("NFKC", text)).translate(str.maketrans("‐‑–—", "----"))
    return " ".join(text.lower().split())


def technology(text):
    found = [(match.start(), name) for name, pattern in TOPIC_PATTERNS.items() if (match := pattern.search(text))]
    return min(found)[1] if found else ""


def as_humanoid(text):
    """Lower case, cleaned as Thomas does, with every rule-v3 term written as "humanoid robot"."""
    return V3_TERM.sub("humanoid robot", clean(text or ""))


def control_kind(text):
    return next((name for name, pattern in CONTROL_KIND if pattern.search(text)), "other_control")


def subfield_of(title_en, abstract_en):
    """Subfield of one family of the sector: (subfield, kind, source).

    subfield: "platform", "body", "control" or "unclear" (no English text).
    kind: for body, the part (Thomas's topics: hand, leg, foot, joint...; "other_part" if none);
          for control, what it controls (learning, locomotion, perception, interaction, navigation_planning, other_control).
    source: "title" or "abstract" (the first sentence of the abstract, only when there is no English title)."""
    title = as_humanoid(title_en)
    source = "title"
    if not LATIN.search(title):              # a title with no English words (a Chinese title, for example)
        title = SENTENCES.split(as_humanoid(abstract_en)[:600], maxsplit=1)[0]
        source = "abstract"
    if not LATIN.search(title):
        return "unclear", "", "no_english_title_or_abstract"
    text = ROBOT_FORM.sub(" ", title)
    if CONTROL.search(text):
        return "control", control_kind(text), source
    if BODY.search(text):
        return "body", technology(text) or "other_part", source
    return "platform", "platform", source


def subfields(texts):
    """Subfield of every family. texts: one row per family, columns docdb_family_id, title_en, abstract_en
    (empty string when PATSTAT has no English text). Returns docdb_family_id, subfield, technology, reason
    (technology = the kind of part or of control; reason = the text read: title or abstract)."""
    if not texts[FAMILY_ID].is_unique:
        raise ValueError("texts must have one row per family")
    rows = [subfield_of(t, a) for t, a in zip(texts["title_en"].fillna(""), texts["abstract_en"].fillna(""))]
    out = pd.DataFrame(rows, columns=["subfield", "technology", "reason"], index=texts.index)
    return pd.concat([texts[[FAMILY_ID]], out], axis=1).reset_index(drop=True)
