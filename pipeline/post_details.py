"""Measured post breakdowns; missing values are never derived by subtraction."""

import hashlib
import re

from pipeline.errors import PipelineError
from pipeline.values import number

FIELDS = ('reactions', 'comments', 'saves', 'shares', 'reach')
NAMES = {'reactions': ('Reakciók', 'Kedvelések', 'Reactions', 'Likes'),
         'comments': ('Hozzászólások', 'Comments'), 'saves': ('Mentések', 'Saves'),
         'shares': ('Megosztások', 'Shares'), 'reach': ('Elérés', 'Reach')}
EMPTY = {'', '-', '–', '—', 'n/a'}


def import_details(row, label):
    def optional(aliases, integer=True):
        values = [number(value, integer=integer, label=f'{label}: {column}')
                  for column, value in row.items()
                  if column.casefold() in {alias.casefold() for alias in aliases}
                  and str(value).strip().casefold() not in EMPTY]
        if len(set(values)) > 1:
            raise PipelineError(f'{label}: eltérő értékek ugyanahhoz a bontáshoz: {aliases[0]}.')
        if any(value < 0 for value in values):
            raise PipelineError(f'{label}: {aliases[0]} nem lehet negatív.')
        return values[0] if values else None

    result = {}
    organic = {}
    for field, names in NAMES.items():
        aliases = [f'Organikus {name.lower()}' for name in names] + [f'Organic {name}' for name in names]
        value = optional(aliases)
        if value is not None:
            organic[field] = value
    if organic:
        result['organic'] = organic
    missing = [field for field, names in NAMES.items()
               if field != 'saves' and optional(names) is None]
    if missing:
        result['missing_totals'] = missing
    for field, aliases in (('followers', ('Követések', 'Új követők', 'Follows', 'New followers')),
                           ('paid_reach', ('Fizetett elérés', 'Paid reach'))):
        value = optional(aliases)
        if value is not None:
            result[field] = value
    for column in row:
        match = re.fullmatch(r'(?:Elköltött összeg|Amount spent) \(([A-Z]{3})\)', column)
        if match:
            value = optional((column,), integer=False)
            if value is not None:
                if value < 0:
                    raise PipelineError(f'{label}: a poszt költése nem lehet negatív.')
                if 'spend' in result and (result['spend'] != value or result['currency'] != match[1]):
                    raise PipelineError(f'{label}: eltérő posztköltés vagy pénznem.')
                result.update(spend=value, currency=match[1])
    return result


def card(post, manual=None, currency=None):
    """Shared Essentials/campaign view; only missing source cells are editable."""
    manual = manual or {}
    post_id = post.get('post_id') or str(post.get('key', '')).split(':', 1)[-1]
    identity = f"{post['channel']}:{post_id}"
    prefix = 'pm_' + hashlib.sha256(identity.encode()).hexdigest()[:16] + '_'
    details = post.get('details') or {}
    paid = post.get('paid') or {}
    measured = post.get('organic_measured', post.get('metrics_measured', False))

    def cell(field, value, money=False, editable=True):
        key = prefix + field.replace('.', '_')
        source = 'export' if value is not None else 'missing'
        if value is None and key in manual:
            value = number(manual[key], integer=not money, label=f'{identity}: {field}')
            if value < 0 or value > 1_000_000_000_000 or (money and abs(round(value, 2) - value) > 1e-8):
                raise PipelineError(f'{identity}: {field}: érvénytelen érték.')
            source = 'manual'
        return {'key': key, 'field': field, 'value': value, 'source': source,
                'editable': editable and source != 'export', 'money': money}

    rows = []
    if 'organic_views' in details:
        rows.append({'field': 'views', 'all': cell('all.views', post.get('views') if measured else None),
                     'organic': cell('organic.views', details['organic_views'])})
    for field in FIELDS:
        total = cell('all.' + field, post.get(field)
                     if measured and field not in details.get('missing_totals', []) else None)
        organic = cell('organic.' + field, (details.get('organic') or {}).get(field))
        if total['value'] is not None and organic['value'] is not None and organic['value'] > total['value']:
            raise PipelineError(f'{identity}: az organikus {field} nem lehet több az összesnél. Ellenőrizd a mérési időablakot.')
        rows.append({'field': field, 'all': total, 'organic': organic})
    currency = details.get('currency') or paid.get('currency') or currency
    windows = sorted(set(paid.get('windows') or []))
    return {'identity': identity, 'rows': rows,
            'followers': cell('followers', details.get('followers')),
            'paid_reach': cell('paid_reach', details.get('paid_reach', paid.get('reach'))),
            'spend': cell('spend', details.get('spend', paid.get('spend')), money=True, editable=bool(currency)),
            'currency': currency, 'paid_windows': windows if len(windows) <= 2 else [windows[0], windows[-1]],
            'more_windows': max(0, len(windows) - 2),
            'paid_scope': bool(paid) and 'paid_reach' not in details,
            'performance_source': details.get('performance_source'),
            'paid_views': details.get('paid_views')}
