"""Applicant names: the brand key on cases met in our sector (Step 0, Section 7.2)."""
import pandas as pd

from names import applicant_key, coarse_key, normalise, precision_recall_f1


def key(name):
    return applicant_key(normalise(name))


def test_spellings_of_one_firm_merge():
    assert key("UBTECH ROBOTICS CORP LTD") == key("Shenzhen UBTECH Robotics Co., Ltd.") == "UBTECH"


def test_aliases():
    assert key("SHENZHEN YOUBIXUAN TECHNOLOGY CO LTD") == "UBTECH"
    assert key("HANGZHOU YUSHU TECHNOLOGY CO LTD") == "UNITREE"
    assert key("ALDEBARAN ROBOTICS") == key("SOFTBANK ROBOTICS CORP") == "SOFTBANK"


def test_full_width_letters():
    assert normalise("ＳＯＦＴＢＡＮＫ") == normalise("SOFTBANK")


def test_institutions_keep_their_name():
    assert key("HARBIN INSTITUTE OF TECHNOLOGY") != key("BEIJING INSTITUTE OF TECHNOLOGY")


def test_generic_first_word_takes_two_words():
    assert key("FOURIER POWER (BEIJING) CO LTD") != key("SHANGHAI FOURIER INTELLIGENT CO LTD")


def test_coarse_key_merges_more():
    assert coarse_key(normalise("GENERAL ELECTRIC CO")) == coarse_key(normalise("GENERAL MOTORS CORP"))


def test_pairwise_scores():
    gold = ["a", "a", "b", "b"]
    assert precision_recall_f1(gold, [1, 1, 2, 2])["F1"] == 1.0
    assert precision_recall_f1(gold, [1, 1, 1, 1])["precision"] == 2 / 6
