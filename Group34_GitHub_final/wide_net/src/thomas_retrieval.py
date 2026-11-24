"""Thomas's Step 0 paginated PATSTAT query and family export."""

import json
import re


def get_code_rule(scheme, code, definitions):
    # Known definitions preserve actual official CPC descendants.
    code = re.sub(r'\s+', '', str(code)).upper()
    key = scheme + ':' + code
    if key in definitions:
        return definitions[key]
    # New /00 entries cover the whole main group. Other new codes match exactly
    # until their official descendants have been verified and added to the data.
    if code.endswith('/00'):
        return {'id': key, 'match_mode': 'main_group',
                'main_group_prefix': code.split('/')[0] + '/', 'symbols': []}
    return {'id': key, 'match_mode': 'exact', 'symbols': [code]}


def search(root, environment, settings, cap=None, patstat_edition=None):
    """Execute the existing paginated TIP search, then export one row per family."""
    ROOT = root
    RESULTS = ROOT / 'outputs' / 'thomas_retrieval'
    RESULTS.mkdir(parents=True, exist_ok=True)
    ENV, CAP = environment, cap
    PAGE_SIZE, DETAIL_BATCH = 5000, 200
    PERIODS = settings['periods']
    KEYWORDS, CPC_CODES, IPC_CODES = (settings[k] for k in ['keywords', 'cpc_codes', 'ipc_codes'])
    if not (KEYWORDS or CPC_CODES or IPC_CODES):
        raise ValueError('Choose at least one search signal.')
    if CAP is not None and CAP < 1:
        raise ValueError('The TEST cap must be positive.')
    import sqlite3
    from datetime import datetime, timezone
    from sqlalchemy import func, or_
    from epo.tipdata.patstat import PatstatClient
    from epo.tipdata.patstat.database.models import (
        TLS201_APPLN, TLS202_APPLN_TITLE, TLS203_APPLN_ABSTR,
        TLS224_APPLN_CPC, TLS209_APPLN_IPC,
    )

    assert ENV in ('TEST', 'PROD') and PAGE_SIZE > 0
    run_folder = RESULTS / (
        'search_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        + '_' + ENV
    )
    run_folder.mkdir()
    client = PatstatClient(env=ENV)
    db = client.orm()
    definitions = json.loads((ROOT / 'config' / 'thomas_code_definitions.json').read_text(encoding='utf-8'))
    cache = sqlite3.connect(run_folder / 'retrieval.sqlite')
    cache.execute('''CREATE TABLE retrieval_hits (
        appln_id INTEGER, docdb_family_id INTEGER, lane TEXT, period TEXT,
        PRIMARY KEY (appln_id, docdb_family_id, lane, period)
    )''')

    metadata = dict(
        settings, environment=ENV, periods=PERIODS, cap_per_lane_period=CAP,
        page_size=PAGE_SIZE, selection=('All matching IDs within the filters' if CAP is None else 'First matching IDs per lane and period'),
        code_scope='All PI application assignments within retrieved families',
        patstat_edition=patstat_edition or 'Not recorded: add the edition displayed in TIP',
        retrieval_complete=False, export_complete=False,
    )
    metadata_file = run_folder / 'search_terms.json'
    metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print('Saving pages in:', run_folder)

    for start, end in PERIODS:
        for lane in ['keywords', 'CPC', 'IPC']:
            query = db.query(
                TLS201_APPLN.appln_id.label('appln_id'),
                TLS201_APPLN.docdb_family_id.label('docdb_family_id'),
            )
            conditions = []
            if lane == 'keywords':
                query = query.outerjoin(
                    TLS202_APPLN_TITLE,
                    TLS201_APPLN.appln_id == TLS202_APPLN_TITLE.appln_id,
                ).outerjoin(
                    TLS203_APPLN_ABSTR,
                    TLS201_APPLN.appln_id == TLS203_APPLN_ABSTR.appln_id,
                )
                for column in [TLS202_APPLN_TITLE.appln_title, TLS203_APPLN_ABSTR.appln_abstract]:
                    text = func.replace(func.lower(func.coalesce(column, '')), '-', ' ')
                    conditions.extend(
                        text.like('%' + word.lower().strip().replace('-', ' ') + '%')
                        for word in KEYWORDS if word.strip()
                    )
            else:
                table = TLS224_APPLN_CPC if lane == 'CPC' else TLS209_APPLN_IPC
                column = table.cpc_class_symbol if lane == 'CPC' else table.ipc_class_symbol
                query = query.join(table, TLS201_APPLN.appln_id == table.appln_id)
                symbol = func.upper(func.replace(column, ' ', ''))
                for item in (CPC_CODES if lane == 'CPC' else IPC_CODES):
                    item = ''.join(str(item).upper().split())
                    if not item:
                        continue
                    if '/' not in item:
                        prefix = item if item[-1].isalpha() else item + '/'
                        conditions.append(symbol.like(prefix + '%'))
                    else:
                        rule = get_code_rule(lane, item, definitions)
                        if rule['match_mode'] == 'main_group':
                            conditions.append(symbol.like(rule['main_group_prefix'] + '%'))
                        else:
                            conditions.append(symbol.in_(rule['symbols']))
            if not conditions:
                continue
            query = query.filter(
                TLS201_APPLN.ipr_type == 'PI',
                TLS201_APPLN.docdb_family_id > 0,
                TLS201_APPLN.earliest_filing_year.between(start, end),
                or_(*conditions),
            ).distinct()

            last_id, total = 0, 0
            while CAP is None or total < CAP:
                # Keyset pagination: advance past the last application, without OFFSET.
                page_query = query.filter(TLS201_APPLN.appln_id > last_id)
                page_size = PAGE_SIZE if CAP is None else min(PAGE_SIZE, CAP - total)
                part = client.df(page_query.order_by(TLS201_APPLN.appln_id).limit(page_size))
                if part.empty:
                    break
                new_last = int(part.appln_id.max())
                assert new_last > last_id, 'Pagination did not advance.'
                cache.executemany(
                    'INSERT OR IGNORE INTO retrieval_hits VALUES (?, ?, ?, ?)',
                    [(int(r.appln_id), int(r.docdb_family_id), lane, f'{start}-{end}')
                     for r in part.itertuples(index=False)],
                )
                cache.commit()
                total += len(part)
                last_id = new_last
                print(ENV, lane, f'{start}-{end}', '| Retrieved:', total, flush=True)
            print('Finished:', lane, f'{start}-{end}', '| Rows:', total, flush=True)

    metadata['retrieval_complete'] = True
    metadata['retrieval_rows'] = cache.execute('SELECT COUNT(*) FROM retrieval_hits').fetchone()[0]
    metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    cache.close()

    import csv
    cache = sqlite3.connect(run_folder / 'retrieval.sqlite')
    metadata_file = run_folder / 'search_terms.json'
    metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
    assert metadata['retrieval_complete'], 'Retrieval must finish before exporting.'

    cache.executescript('''
        CREATE TABLE IF NOT EXISTS application_texts (
            appln_id INTEGER, docdb_family_id INTEGER, title TEXT, abstract TEXT,
            PRIMARY KEY (appln_id, docdb_family_id, title, abstract)
        );
        CREATE TABLE IF NOT EXISTS candidates (
            appln_id INTEGER, docdb_family_id INTEGER PRIMARY KEY,
            title TEXT, abstract TEXT, text_quality INTEGER
        );
        CREATE TABLE IF NOT EXISTS assigned_codes (
            docdb_family_id INTEGER, appln_id INTEGER, code TEXT, scheme TEXT,
            PRIMARY KEY (docdb_family_id, appln_id, code, scheme)
        );
    ''')
    cache.execute('''INSERT OR IGNORE INTO candidates
        SELECT MIN(appln_id), docdb_family_id, '', '', 0
        FROM retrieval_hits GROUP BY docdb_family_id''')
    cache.commit()

    # Fetch texts in small batches; keep the full application export on disk.
    cursor = cache.execute('SELECT DISTINCT appln_id FROM retrieval_hits ORDER BY appln_id')
    processed = 0
    while True:
        batch = [r[0] for r in cursor.fetchmany(DETAIL_BATCH)]
        if not batch:
            break
        query = db.query(
            TLS201_APPLN.appln_id.label('appln_id'),
            TLS201_APPLN.docdb_family_id.label('docdb_family_id'),
            TLS202_APPLN_TITLE.appln_title.label('title'),
            TLS203_APPLN_ABSTR.appln_abstract.label('abstract'),
        ).outerjoin(
            TLS202_APPLN_TITLE, TLS201_APPLN.appln_id == TLS202_APPLN_TITLE.appln_id,
        ).outerjoin(
            TLS203_APPLN_ABSTR, TLS201_APPLN.appln_id == TLS203_APPLN_ABSTR.appln_id,
        ).filter(TLS201_APPLN.appln_id.in_(batch))
        part = client.df(query).fillna('')
        records = [(int(r.appln_id), int(r.docdb_family_id), str(r.title), str(r.abstract))
                   for r in part.itertuples(index=False)]
        cache.executemany('INSERT OR IGNORE INTO application_texts VALUES (?, ?, ?, ?)', records)
        # Prefer a representative with nonempty title and abstract, then the smallest ID.
        for app, family, title, abstract in records:
            quality = int(bool(title.strip())) + int(bool(abstract.strip()))
            cache.execute('''INSERT INTO candidates VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(docdb_family_id) DO UPDATE SET
                appln_id=excluded.appln_id, title=excluded.title,
                abstract=excluded.abstract, text_quality=excluded.text_quality
                WHERE excluded.text_quality > candidates.text_quality
                   OR (excluded.text_quality = candidates.text_quality
                       AND excluded.appln_id < candidates.appln_id)''',
                (app, family, title, abstract, quality))
        cache.commit()
        processed += len(batch)
        print('Applications processed:', processed, flush=True)

    # All PI family assignments, also paginated so large families are not truncated locally.
    cursor = cache.execute('SELECT docdb_family_id FROM candidates ORDER BY docdb_family_id')
    processed = 0
    while True:
        batch = [r[0] for r in cursor.fetchmany(DETAIL_BATCH)]
        if not batch:
            break
        for scheme, table, column in [
            ('CPC', TLS224_APPLN_CPC, TLS224_APPLN_CPC.cpc_class_symbol),
            ('IPC', TLS209_APPLN_IPC, TLS209_APPLN_IPC.ipc_class_symbol),
        ]:
            query = db.query(
                TLS201_APPLN.docdb_family_id.label('docdb_family_id'),
                TLS201_APPLN.appln_id.label('appln_id'), column.label('code'),
            ).join(table, TLS201_APPLN.appln_id == table.appln_id).filter(
                TLS201_APPLN.docdb_family_id.in_(batch), TLS201_APPLN.ipr_type == 'PI',
            ).distinct()
            last_app, last_code = 0, ''
            while True:
                page_query = query.filter(or_(
                    TLS201_APPLN.appln_id > last_app,
                    (TLS201_APPLN.appln_id == last_app) & (column > last_code),
                )).order_by(TLS201_APPLN.appln_id, column).limit(PAGE_SIZE)
                part = client.df(page_query)
                if part.empty:
                    break
                next_key = (int(part.iloc[-1].appln_id), str(part.iloc[-1].code))
                assert next_key > (last_app, last_code), 'Assignment pagination did not advance.'
                cache.executemany('INSERT OR IGNORE INTO assigned_codes VALUES (?, ?, ?, ?)',
                    [(int(r.docdb_family_id), int(r.appln_id), str(r.code), scheme)
                     for r in part.itertuples(index=False)])
                cache.commit()
                last_app, last_code = next_key
        processed += len(batch)
        print('Families processed for codes:', processed, flush=True)

    def export_csv(sql, filename):
        cursor = cache.execute(sql)
        with (run_folder / filename).open('w', encoding='utf-8-sig', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([column[0] for column in cursor.description])
            writer.writerows(cursor)

    export_csv('SELECT * FROM retrieval_hits ORDER BY appln_id, lane, period', 'retrieval_hits.csv')
    export_csv('SELECT * FROM application_texts ORDER BY appln_id', 'applications.csv')
    export_csv('''SELECT appln_id, docdb_family_id, title, abstract,
        '' AS publication, '' AS claims_text, '' AS description, '' AS source_url
        FROM candidates ORDER BY docdb_family_id''', 'candidates.csv')
    export_csv('SELECT * FROM assigned_codes ORDER BY docdb_family_id, scheme, appln_id, code', 'assigned_codes.csv')
    metadata['candidate_families'] = cache.execute('SELECT COUNT(*) FROM candidates').fetchone()[0]
    metadata['representative_text'] = 'Most nonempty TA fields, then smallest retrieved application ID; no language filter'
    metadata['export_complete'] = True
    metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print('EXPORT COMPLETE | Candidate families:', metadata['candidate_families'])
    print('Saved in:', run_folder)
    cache.close()
    return run_folder
