"""The humanoid sector rule (Step 0), written as database queries.

The rule itself lives in config/sector_rule.yaml. Step 0, Tutorial 2 notebook 20 and
notebook 21 all load it from here, so a change to the rule is made once.

Every query returns family IDs (column 'fid'). Filtering and counting stay in the database,
so no family IDs travel to Python unless a notebook asks for them.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml
from sqlalchemy import func, or_

CONFIG_PATH = Path(__file__).resolve().parent.parent / 'config' / 'sector_rule.yaml'

REQUIRED_KEYS = ['version', 'window', 'ipr_type', 'core_cpc', 'robot_cpc', 'exclude_cpc', 'prosthesis_cpc',
                 'exclude_prostheses', 'truth_cpc', 'strong_kw', 'medium_kw', 'adjacent_kw', 'exclude_kw',
                 'segment_cpc', 'comparison_segments']
CPC_KEYS = ['core_cpc', 'robot_cpc', 'exclude_cpc', 'prosthesis_cpc', 'truth_cpc']
KEYWORD_KEYS = ['strong_kw', 'medium_kw', 'adjacent_kw', 'exclude_kw']
CPC_PATTERN = re.compile(r'^[A-Z]\d{2}[A-Z][0-9/]*$')      # e.g. B25J, B62D57/032, A61F2/58


def load_rule(path=CONFIG_PATH):
    """Read the rule from the YAML file and check it. Raises ValueError with every problem found."""
    with open(path, encoding='utf-8') as f:
        rule = yaml.safe_load(f)
    return validate_rule(rule)


def validate_rule(rule):
    problems = [f'missing key: {k}' for k in REQUIRED_KEYS if k not in rule]
    if problems:
        raise ValueError('\n'.join(problems))
    if rule['window']['year_min'] > rule['window']['year_max']:
        problems.append('window: year_min is after year_max')
    for key in CPC_KEYS:
        for code in rule[key]:
            if not CPC_PATTERN.match(str(code)):
                problems.append(f'{key}: "{code}" is not a CPC code without blanks')
    for key in KEYWORD_KEYS:
        terms = rule[key]
        if len(set(terms)) != len(terms):
            problems.append(f'{key}: a term is listed twice')
        for term in terms:
            if not term.strip() or term != term.lower():
                problems.append(f'{key}: "{term}" must be lower case and not empty')
    shared = set(rule['strong_kw']) & set(rule['exclude_kw'])
    if shared:
        problems.append(f'a strong keyword is also an exclusion: {sorted(shared)}')
    if not isinstance(rule['exclude_prostheses'], bool):
        problems.append('exclude_prostheses must be true or false')
    if problems:
        raise ValueError('\n'.join(problems))
    return rule


def rule_constants(rule):
    """The rule as the flat values the notebooks use, in this fixed order:
    core_cpc, robot_cpc, exclude_cpc, prosthesis_cpc, exclude_prostheses, strong_kw, medium_kw,
    adjacent_kw, exclude_kw, truth_cpc, version, year_min, year_max, ipr_type."""
    w = rule['window']
    return (rule['core_cpc'], rule['robot_cpc'], rule['exclude_cpc'], rule['prosthesis_cpc'],
            rule['exclude_prostheses'], rule['strong_kw'], rule['medium_kw'], rule['adjacent_kw'],
            rule['exclude_kw'], rule['truth_cpc'], rule['version'], w['year_min'], w['year_max'],
            rule['ipr_type'])


class SectorQueries:
    """The humanoid sector as queries.

    db     : a SQLAlchemy session on PATSTAT (patstat.orm() on TIP, or a test database)
    models : any object with the PATSTAT tables as attributes:
             APPLN (TLS201_APPLN), TITLE (TLS202_APPLN_TITLE), ABSTR (TLS203_APPLN_ABSTR),
             CPC (TLS224_APPLN_CPC)
    rule   : the dictionary returned by load_rule()
    """

    def __init__(self, db, models, rule):
        self.db = db
        self.rule = rule
        self.APPLN = models.APPLN
        self.TITLE = models.TITLE
        self.ABSTR = models.ABSTR
        self.CPC = models.CPC

    def window_filters(self):
        w = self.rule['window']
        return (self.APPLN.ipr_type == self.rule['ipr_type'],
                self.APPLN.earliest_filing_year.between(w['year_min'], w['year_max']))

    def cpc_families(self, prefixes):
        """Families with a CPC code that starts with one of the prefixes (blanks ignored)."""
        symbol = func.replace(self.CPC.cpc_class_symbol, ' ', '')
        cond = or_(*(symbol.like(p + '%') for p in prefixes))
        return (self.db.query(self.APPLN.docdb_family_id.label('fid'))
                .join(self.CPC, self.APPLN.appln_id == self.CPC.appln_id)
                .filter(cond, *self.window_filters())
                .distinct())

    def keyword_families(self, terms):
        """Families with one of the terms in the title or the abstract (case-insensitive)."""
        title = func.lower(self.TITLE.appln_title)
        abstract = func.lower(self.ABSTR.appln_abstract)
        cond = or_(*(col.like('%' + t.lower() + '%') for t in terms for col in (title, abstract)))
        return (self.db.query(self.APPLN.docdb_family_id.label('fid'))
                .outerjoin(self.TITLE, self.APPLN.appln_id == self.TITLE.appln_id)
                .outerjoin(self.ABSTR, self.APPLN.appln_id == self.ABSTR.appln_id)
                .filter(cond, *self.window_filters())
                .distinct())

    def excluded_families(self):
        r = self.rule
        q = self.cpc_families(r['exclude_cpc']).union(self.keyword_families(r['exclude_kw']))
        if r['exclude_prostheses']:
            q = q.union(self.cpc_families(r['prosthesis_cpc']))
        return q

    def adjacent_families(self):
        """Legged but not humanoid: a multi-legged word and no strong word in the same family."""
        return self.keyword_families(self.rule['adjacent_kw']).except_(
            self.keyword_families(self.rule['strong_kw']))

    def layers(self):
        """Layer A: core code and a strong word. Layer B: robot code and a medium word.
        Layer C: a strong word. Exclusions and the adjacent group are removed from every layer.
        Layer A is a subset of layer C (both need a strong word): it adds no family to the sector,
        it marks the most certain ones. Taking the core code alone is an open Step 0 decision."""
        r = self.rule
        excl = self.excluded_families().union(self.adjacent_families())
        A = self.cpc_families(r['core_cpc']).intersect(self.keyword_families(r['strong_kw'])).except_(excl)
        B = self.cpc_families(r['robot_cpc']).intersect(self.keyword_families(r['medium_kw'])).except_(excl)
        C = self.keyword_families(r['strong_kw']).except_(excl)
        return A, B, C

    def sector_query(self):
        A, B, C = self.layers()
        return A.union(B).union(C)

    def sector_subquery(self):
        """The sector as a subquery with one column, fid, to join other queries to."""
        sub = self.sector_query().subquery()
        return self.db.query(list(sub.c)[0].label('fid')).subquery()

    def scope(self, q, sector):
        """Keep only the families of the sector. The join runs in the database."""
        return q.join(sector, self.APPLN.docdb_family_id == sector.c.fid)

    def family_years(self, restrict=None):
        """One row per family: fid, and year = earliest priority year among its applications in the window."""
        q = (self.db.query(self.APPLN.docdb_family_id.label('fid'),
                           func.min(self.APPLN.earliest_filing_year).label('year'))
             .filter(*self.window_filters()))
        if restrict is not None:
            q = q.join(restrict, self.APPLN.docdb_family_id == restrict.c.fid)
        return q.group_by(self.APPLN.docdb_family_id).subquery()
