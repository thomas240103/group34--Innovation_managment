"""Application domains of humanoid-robot patents: where would the robot work? (Step 2, Section 5.3c)

The question that matters for Electrolux is not only *what* a family protects (Step 0, Section 7.4: platform, body,
control) but *where* the robot is meant to work: in the home, in care, in factories and warehouses, in shops and public
spaces, in schools and entertainment. A family can name several domains or none (most patents describe the robot
without its use). The rule reads the English title and abstract, plus the Chinese and Japanese title words, and is
checked on a blind reading like every other rule of the project (threshold fixed before reading).
"""
from __future__ import annotations

import re
from typing import Dict, List

import pandas as pd

DOMAINS: Dict[str, List[str]] = {
    "home": [
        r"household", r"home", r"homes", r"domestic", r"house ?work", r"housekeeping", r"chores?", r"kitchen", r"cooking",
        r"cook", r"laundry", r"clothes? folding", r"fold(?:ing)? clothes", r"dish(?:es|washing)?", r"family robot",
        r"family service", r"living room", r"tidy(?:ing)?", r"home service", r"home care", r"housemaid", r"appliances?",
        "家用", "家庭", "家务", "家政", "厨房", "烹饪", "洗衣", "叠衣", "家事", "家庭用",
    ],
    "care and health": [
        r"elderly", r"aged care", r"old people", r"nursing", r"caregiv\w*", r"care ?giver", r"rehabilitat\w*",
        r"hospital", r"medical", r"patients?", r"disabled", r"accompany(?:ing)? (?:the )?elderly", r"health ?care",
        r"massage", "养老", "护理", "陪护", "康复", "医疗", "医院", "助老", "介護", "看護",
    ],
    "industry and logistics": [
        r"factory", r"factories", r"industrial", r"manufactur\w*", r"assembly line", r"production line", r"warehous\w*",
        r"logistics", r"material handling", r"carrying goods", r"sorting", r"inspection", r"power (?:grid|line|station)",
        r"substation", r"construction site", r"mining", r"nuclear", r"explosion", r"hazardous", r"welding", r"workpieces?",
        "工业", "工厂", "制造", "装配", "产线", "生产线", "仓储", "物流", "搬运", "巡检", "电力", "变电站", "工場",
    ],
    "commerce and public services": [
        r"reception", r"receptionist", r"shopping", r"retail", r"shops?", r"shopping malls?", r"restaurants?", r"hotels?",
        r"customer service", r"guid(?:e|ing) robot", r"tour guide", r"exhibition", r"security patrol", r"patrol",
        r"public places?", r"airports?", r"railway stations?", "导购", "迎宾", "接待", "导览", "讲解", "餐厅", "酒店", "银行", "巡逻", "安保",
    ],
    "education and entertainment": [
        r"educat\w*", r"teaching", r"students?", r"children", r"kids?", r"toys?", r"entertainment", r"performances?",
        r"dance", r"dancing", r"games?", r"soccer", r"football", r"competition", r"companion", r"pets?",
        "教育", "教学", "儿童", "玩具", "娱乐", "表演", "舞蹈", "足球", "比赛", "陪伴", "教育用",
    ],
}

# "home" words that describe something else in robotics ("home position" of a joint, "homing" of an axis)
HOME_FALSE = re.compile(r"\bhome (?:position|positions|posture|point|return|returning)\b|\bhoming\b|\breturn(?:ing)? home\b")


def _pattern(words: List[str]) -> re.Pattern:
    parts = []
    for w in words:
        if re.search(r"[a-z]", w):
            parts.append(r"(?<![a-z0-9])(?:" + w + r")(?![a-z0-9])")
        else:
            parts.append(re.escape(w))
    return re.compile("|".join(parts))


DOMAIN_PATTERNS = {d: _pattern(ws) for d, ws in DOMAINS.items()}


def domains_of(text: str) -> List[str]:
    """Domains named in a text (lower-cased inside); [] if none."""
    t = str(text or "").lower()
    found = []
    for d, rx in DOMAIN_PATTERNS.items():
        tt = HOME_FALSE.sub(" ", t) if d == "home" else t
        if rx.search(tt):
            found.append(d)
    return found


def family_domains(texts: pd.DataFrame, id_col: str = "docdb_family_id", text_col: str = "text") -> pd.DataFrame:
    """One row per family and domain found (families with no domain get 'unspecified'), with a weight summing to 1."""
    rows = []
    for fid, txt in zip(texts[id_col], texts[text_col]):
        ds = domains_of(txt) or ["unspecified"]
        for d in ds:
            rows.append({id_col: fid, "domain": d, "weight": 1.0 / len(ds)})
    return pd.DataFrame(rows, columns=[id_col, "domain", "weight"])
