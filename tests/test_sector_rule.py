"""Tests for the sector rule. Run from the project folder: python -m pytest tests

The layer logic is tested on a small made-up database (SQLite), not on PATSTAT. The made-up
families are chosen so that each rule decision (window, layers, exclusions, adjacent group)
changes the answer once.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
from sector_rule import SectorQueries, load_rule, rule_constants, validate_rule  # noqa: E402


# ---------------------------------------------------------------- the rule file

def test_the_rule_file_loads_and_has_the_expected_version():
    rule = load_rule()
    assert rule['version'] == 'v0.2 draft'
    assert rule['core_cpc'] == ['B62D57/032']
    assert 'humanoid' in rule['strong_kw']


def test_rule_constants_come_back_in_the_documented_order():
    rule = load_rule()
    values = rule_constants(rule)
    assert len(values) == 14
    assert values[0] == rule['core_cpc']
    assert values[10] == rule['version']
    assert values[11:13] == (2000, 2025)


def copy_of(rule):
    return yaml.safe_load(yaml.safe_dump(rule))


def test_a_cpc_code_with_blanks_is_rejected():
    rule = copy_of(load_rule())
    rule['core_cpc'] = ['B62D 57/032']
    with pytest.raises(ValueError, match='without blanks'):
        validate_rule(rule)


def test_an_upper_case_keyword_is_rejected():
    rule = copy_of(load_rule())
    rule['strong_kw'].append('Humanoid Robot')
    with pytest.raises(ValueError, match='lower case'):
        validate_rule(rule)


def test_a_keyword_that_is_both_strong_and_excluded_is_rejected():
    rule = copy_of(load_rule())
    rule['exclude_kw'].append('humanoid')
    with pytest.raises(ValueError, match='also an exclusion'):
        validate_rule(rule)


def test_an_inverted_window_is_rejected():
    rule = copy_of(load_rule())
    rule['window'] = {'year_min': 2025, 'year_max': 2000}
    with pytest.raises(ValueError, match='year_min'):
        validate_rule(rule)


# ---------------------------------------------------------------- the layers, on a made-up database

class Base(DeclarativeBase):
    pass


class Appln(Base):
    __tablename__ = 'appln'
    appln_id: Mapped[int] = mapped_column(primary_key=True)
    docdb_family_id: Mapped[int]
    ipr_type: Mapped[str]
    earliest_filing_year: Mapped[int]


class Title(Base):
    __tablename__ = 'title'
    id: Mapped[int] = mapped_column(primary_key=True)
    appln_id: Mapped[int]
    appln_title: Mapped[str]


class Abstract(Base):
    __tablename__ = 'abstract'
    id: Mapped[int] = mapped_column(primary_key=True)
    appln_id: Mapped[int]
    appln_abstract: Mapped[str]


class Cpc(Base):
    __tablename__ = 'cpc'
    id: Mapped[int] = mapped_column(primary_key=True)
    appln_id: Mapped[int]
    cpc_class_symbol: Mapped[str]


# family id: (ipr type, filing year, title, abstract, CPC codes with blanks)
FAMILIES = {
    1: ('PI', 2010, 'Humanoid walking robot', 'A humanoid robot that walks.', ['B62D 57/032']),       # layer A
    2: ('PI', 2012, 'Two-legged control', 'A biped robot with a robot hand.', ['B25J 9/16']),        # layers B, C
    3: ('PI', 2015, 'Industrial robot arm', 'A gripper with a robot hand for picking.', ['B25J 9/16']),  # layer B
    4: ('PI', 2011, 'Humanoid exoskeleton', 'A humanoid exoskeleton for walking.', ['B25J 9/0006']),  # excluded by code
    5: ('PI', 2013, 'Robot pet', 'A quadruped robot dog that uses gait control.', []),              # excluded by word
    6: ('PI', 2014, 'Six-leg machine', 'A hexapod robot.', []),                                     # adjacent group
    7: ('UM', 2016, 'Humanoid head', 'A humanoid robot head.', ['B25J 9/16']),                      # utility model
    8: ('PI', 1995, 'Old humanoid', 'A humanoid.', ['B25J 9/16']),                                  # before the window
    9: ('PI', 2016, 'Gait analysis', 'Gait analysis of animals.', []),                              # no robot code
    10: ('PI', 2017, 'Toy', 'A humanoid toy figure.', ['A63H 3/00']),                               # excluded by code
    11: ('PI', 2018, 'Robot', 'A two-legged robot that is a toy robot.', []),                       # excluded by word
}


@pytest.fixture(scope='module')
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    session = Session(engine)
    row_id = 0
    for fam, (ipr, year, title, abstract, codes) in FAMILIES.items():
        session.add(Appln(appln_id=fam, docdb_family_id=fam, ipr_type=ipr, earliest_filing_year=year))
        row_id += 1
        session.add(Title(id=row_id, appln_id=fam, appln_title=title))
        row_id += 1
        session.add(Abstract(id=row_id, appln_id=fam, appln_abstract=abstract))
        for code in codes:
            row_id += 1
            session.add(Cpc(id=row_id, appln_id=fam, cpc_class_symbol=code))
    session.commit()
    yield session
    session.close()


@pytest.fixture(scope='module')
def q(db):
    models = SimpleNamespace(APPLN=Appln, TITLE=Title, ABSTR=Abstract, CPC=Cpc)
    return SectorQueries(db, models, load_rule())


def fids(query):
    return {row[0] for row in query.all()}


def test_the_sector_is_the_union_of_the_three_layers(q):
    assert fids(q.sector_query()) == {1, 2, 3}


def test_layer_a_needs_the_core_code_and_a_strong_word(q):
    A, _, _ = q.layers()
    assert fids(A) == {1}


def test_layer_c_is_strong_words_after_exclusions(q):
    _, _, C = q.layers()
    assert fids(C) == {1, 2}


def test_exclusions_are_removed_from_the_sector(q):
    assert fids(q.excluded_families()) == {4, 5, 10, 11}
    assert not fids(q.sector_query()) & {4, 5, 10, 11}


def test_the_adjacent_group_is_legged_but_not_humanoid(q):
    assert fids(q.adjacent_families()) == {6}
    assert 6 not in fids(q.sector_query())


def test_the_window_removes_utility_models_and_old_filings(q):
    assert not fids(q.sector_query()) & {7, 8}


def test_a_gait_word_without_a_robot_code_is_not_in_the_sector(q):
    assert 9 not in fids(q.sector_query())
