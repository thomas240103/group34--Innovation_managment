"""Harmonisation of applicant names (Step 0, Section 7.2), copied from step0_sector_definition.ipynb.

tests/test_notebook_in_sync.py checks that this file and the notebook cell define the same functions and lists.
"""
import re
import unicodedata
from math import comb

import pandas as pd
from cleanco import basename

# Legal forms and company words that do not identify the organisation (dictionary of the prof's method A, extended
# with the forms of the countries of our sector: China, Japan, Korea, Taiwan).
LEGAL_FORMS = {
    "INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LIMITED", "LLC", "LP", "PLC",
    "GMBH", "AG", "KG", "MBH", "SE", "SA", "SAS", "SPA", "SRL", "BV", "NV", "AB", "AS", "ASA", "OY", "OYJ",
    "KK", "KABUSHIKI", "KAISHA", "LTDA", "PTY", "THE", "AKTIENGESELLSCHAFT", "GESELLSCHAFT",
    "SARL", "SNC", "GIE", "EV", "UG", "COOP", "HOLDING", "HOLDINGS", "GROUP",
}


def clean_with_dictionary(name):
    "Prof's method A: upper-case, letters and digits only, legal-form words dropped at the start and at the end."
    words = re.sub(r"[^A-Z0-9 ]", " ", str(name).upper()).split()
    while words and words[-1] in LEGAL_FORMS:
        words.pop()
    while words and words[0] in LEGAL_FORMS:
        words.pop(0)
    return " ".join(words)


def normalise(name):
    "applicant_norm: cleanco first (abbreviations with dots, e.g. S.p.A.), then method A; non-Latin names kept as they are."
    s = unicodedata.normalize("NFKC", str(name)).strip()    # full-width letters (Ｓ) become plain letters (S)
    key = clean_with_dictionary(basename(s)) if s else ""
    return key if key else s.upper()


def pairs_inside(group_sizes):
    return sum(comb(int(n), 2) for n in group_sizes)


def precision_recall_f1(gold_groups, predicted_groups):
    "Pairwise precision, recall and F1 (the prof's function)."
    df = pd.DataFrame({"gold": list(gold_groups), "pred": list(predicted_groups)})
    tp = pairs_inside(df.groupby(["gold", "pred"]).size())
    tp_fp = pairs_inside(df.groupby("pred").size())
    tp_fn = pairs_inside(df.groupby("gold").size())
    precision = tp / tp_fp if tp_fp else 1.0
    recall = tp / tp_fn
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"groups found": df["pred"].nunique(), "precision": precision, "recall": recall, "F1": f1}


# ---------------------------------------------------------------- brand key (main version) and coarse key
# Chinese names start with the city or province ("SHENZHEN UBTECH ROBOTICS"): the place is skipped.
PLACES = {
    "BEIJING", "SHANGHAI", "SHENZHEN", "GUANGZHOU", "HANGZHOU", "TIANJIN", "CHONGQING", "NANJING", "SUZHOU", "WUHAN",
    "CHENGDU", "XIAN", "XI", "AN", "HEFEI", "JINAN", "QINGDAO", "DALIAN", "SHENYANG", "HARBIN", "CHANGSHA", "CHANGZHOU",
    "NINGBO", "XIAMEN", "FUZHOU", "ZHENGZHOU", "KUNMING", "NANCHANG", "TAIYUAN", "SHIJIAZHUANG", "WUXI", "DONGGUAN",
    "FOSHAN", "ZHUHAI", "WENZHOU", "JIAXING", "SHAOXING", "YANGZHOU", "XUZHOU", "NANTONG", "CHANGCHUN", "LANZHOU",
    "GUIYANG", "NANNING", "HAIKOU", "URUMQI", "HOHHOT", "YINCHUAN", "XINING", "LHASA", "TANGSHAN", "BAODING", "LUOYANG",
    "ZHEJIANG", "JIANGSU", "GUANGDONG", "SHANDONG", "HUBEI", "HUNAN", "HENAN", "HEBEI", "SICHUAN", "FUJIAN", "ANHUI",
    "JIANGXI", "SHAANXI", "SHANXI", "LIAONING", "JILIN", "HEILONGJIANG", "YUNNAN", "GUIZHOU", "GUANGXI", "HAINAN",
    "GANSU", "QINGHAI", "NINGXIA", "XINJIANG", "TIBET", "INNER", "MONGOLIA",
    "CHINA", "CHINESE", "JAPAN", "KOREA", "KOREAN", "TAIWAN", "HONG", "KONG", "SEOUL", "TOKYO", "OSAKA",
}
# A name whose distinctive word is generic needs one more word ("GENERAL ELECTRIC" is not "GENERAL MOTORS").
GENERIC = {
    "GENERAL", "INTERNATIONAL", "NATIONAL", "UNITED", "AMERICAN", "ADVANCED", "NEW", "FIRST", "GLOBAL", "SMART",
    "INTELLIGENT", "INTELLIGENCE", "ROBOT", "ROBOTS", "ROBOTIC", "ROBOTICS", "TECHNOLOGY", "TECHNOLOGIES", "TECH",
    "ELECTRIC", "ELECTRONIC", "ELECTRONICS", "INDUSTRIAL", "INDUSTRIES", "INDUSTRY", "SCIENCE", "SCIENCES", "DIGITAL",
    "AUTOMATION", "MACHINE", "MACHINERY", "POWER", "ENERGY", "MEDICAL", "DATA", "SYSTEMS", "SYSTEM", "STATE", "ROYAL",
    "INSTITUTE", "UNIVERSITY", "ACADEMY", "CENTRE", "CENTER", "RESEARCH", "LAB", "LABORATORY", "NORTH", "SOUTH",
    "EAST", "WEST", "NORTHWESTERN", "SOUTHEAST", "SOUTHWEST", "NORTHEAST", "NORTHEASTERN", "CENTRAL", "EUROPEAN",
    "DEUTSCHE", "ITALIANA", "FRANCAISE", "NIPPON", "INTERNATIONALE", "GENERALE", "NOUVELLE", "INDUSTRIE", "FOURIER",   # checked by hand: SHANGHAI FOURIER INTELLIGENT and FOURIER POWER (BEIJING) are two companies
}
# Universities, institutes, labs, hospitals keep their whole name (otherwise all "INSTITUTE ..." would merge).
INSTITUTION_WORDS = re.compile(r"\b(UNIV\w*|INST\w*|ACADEM\w*|COLLEGE|SCHOOL|HOSPITAL|LAB\w*|CENT(?:ER|RE)|"
                                  r"FRAUNHOFER|CNRS|CNR|CSIC|RIKEN|AIST|KIST|ETRI|KAIST|"
                                  r"DAXUE|XUEYUAN|YANJIUYUAN|YANJIUSUO)\b")      # university, college, institute in pinyin
# Words that open many European firm names without identifying them ("SOCIETE L'OREAL", "COMPAGNIE IBM").
LEADING_WORDS = {"SOCIETE", "SOCIETA", "SOCIEDAD", "COMPAGNIE", "COMPANIA", "COMPANHIA", "ETABLISSEMENTS", "ETS",
                 "FABBRICA", "FIRMA", "DITE", "SOC", "CIE", "STE", "ANONIMA", "ANONYME", "DE", "DES", "DU", "DI", "DELLA"}

# Explicit aliases: the same company under different names (renamed, or a Latin and a pinyin name).
# Only certain cases; probable ones are noted in Step 2 and NOT merged. Parent and subsidiary with different
# names stay apart (Boston Dynamics is not Google nor Hyundai): the applicant is the owner named on the patent.
ALIASES = {
    "YOUBIXUAN": "UBTECH",          # Youbixuan is the Chinese name of UBTECH Robotics
    "YUSHU": "UNITREE",             # Hangzhou Yushu Technology trades as Unitree (founded as Hangzhou Unitree Technology)
    "ALDEBARAN": "SOFTBANK",        # Aldebaran (Paris) was SoftBank Robotics Europe from 2016 to 2022: the same company
    "FOURIER INTELLIGENCE": "FOURIER INTELLIGENT",   # Fourier Intelligence is the English name of Shanghai Fourier Intelligent
}


def distinctive_words(norm):
    "The words of a firm name without the opening place names and opening legal words; initials joined."
    merged = []
    for w in str(norm).split():                       # F I L A -> FILA
        if len(w) == 1 and merged and merged[-1][1]:
            merged[-1] = (merged[-1][0] + w, True)
        else:
            merged.append((w, len(w) == 1))
    words = [w for w, _ in merged]
    while len(words) > 1 and (words[0] in PLACES or words[0] in LEADING_WORDS):
        words.pop(0)
    return words


def brand_key(norm, is_individual=False):
    """The brand of an organisation: the key that groups its spellings and its subsidiaries by name.
    Individuals and institutions keep their whole normalised name; for firms, the first word that is not a place,
    plus the next one if it is generic."""
    norm = str(norm)
    if is_individual or INSTITUTION_WORDS.search(norm):
        return norm
    words = distinctive_words(norm)
    if not words:
        return norm
    if len(words[0]) == 1 and len(words) > 1:          # "L OREAL" -> "LOREAL"
        return words[0] + words[1]
    return " ".join(words[:2]) if words[0] in GENERIC else words[0]


def applicant_key(norm, is_individual=False):
    "applicant (main version, C): the brand key, then the explicit aliases."
    key = brand_key(norm, is_individual)
    return ALIASES.get(key, key)


def coarse_key(norm, is_individual=False):
    "applicant_auto (D): for firms, the first distinctive word even when it is generic (merges too much on purpose)."
    norm = str(norm)
    if is_individual or INSTITUTION_WORDS.search(norm):
        return norm
    words = distinctive_words(norm)
    if not words:
        return norm
    key = "".join(words[:2]) if len(words[0]) == 1 and len(words) > 1 else words[0]
    return ALIASES.get(key, key)
