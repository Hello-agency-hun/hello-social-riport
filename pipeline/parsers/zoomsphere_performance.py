"""Optional post snapshots; publication dates are not measurement windows."""

from copy import deepcopy
from pathlib import Path

from pipeline.errors import PipelineError
from pipeline.schema import ContentItem, ParsedSource, Post
from pipeline.tabular import read_table_rows
from pipeline.values import export_day, number

REQUIRED = {'postId', 'network', 'postType', 'datePublished', 'Reach', 'Views'}
METRICS = {'reach': 'Reach', 'views': 'Views', 'reactions': 'Likes',
           'comments': 'Comments', 'shares': 'Shares', 'saves': 'Post Saves',
           'clicks': 'Clicks', 'link_clicks': 'Link Clicks'}
EXTRAS = {'followers': 'Followers Gained', 'organic_views': 'Organic Views',
          'paid_views': 'Views From Ads', 'paid_reach': 'Paid Reach'}
EMPTY = {'', '-', '–', '—', 'n/a'}


def parse(path):
    path = Path(path)
    rows = read_table_rows(path)
    if not rows or not REQUIRED.issubset(rows[0]):
        raise PipelineError(f'{path.name}: hiányos ZoomSphere Performance fejléc.')
    posts, page_ids = [], set()
    for index, row in enumerate(rows, 2):
        post_id = row['postId'].strip()
        if post_id.upper() == 'TOTAL':
            continue
        channel = row['network'].strip().casefold()
        if channel not in ('facebook', 'instagram') or not post_id:
            raise PipelineError(f'{path.name}, {index}. sor: hiányzó posztazonosító vagy nem támogatott csatorna.')
        if channel == 'facebook' and '_' in post_id:
            page_id, post_id = post_id.rsplit('_', 1)
            page_ids.add(page_id)

        def optional(column):
            raw = row.get(column, '').strip()
            return None if raw.casefold() in EMPTY else number(raw, integer=True, label=f'{path.name}, {index}. sor, {column}')

        values = {field: optional(column) for field, column in METRICS.items()}
        details = {'performance_source': path.name,
                   'missing_totals': [field for field in ('reactions', 'comments', 'shares', 'reach') if values[field] is None],
                   'missing_metrics': [field for field, value in values.items() if value is None]}
        for field, column in EXTRAS.items():
            value = optional(column)
            if value is not None:
                details[field] = value
        organic = {}
        for field, column in METRICS.items():
            value = optional('Organic ' + column)
            if value is not None and field != 'views':
                organic[field] = value
        if organic:
            details['organic'] = organic
        thumbnail = row.get('thumbnail', '').strip()
        posts.append(Post(channel, post_id, export_day(row['datePublished'], label=f'{path.name}, {index}. sor'),
                          caption=row.get('message', '').strip(), permalink=row.get('publicUrl', '').strip(),
                          post_type=row['postType'].strip().casefold(), creatives=[thumbnail] if thumbnail else [],
                          organic_measured=True, details=details,
                          **{field: value if value is not None else (None if field == 'saves' else 0) for field, value in values.items()}))
    if len(page_ids) > 1:
        raise PipelineError(f'{path.name}: több Facebook-oldal szerepel a Performance exportban.')
    return ParsedSource(kind='zoomsphere_performance', period=None,
                        client_hints={'page_id': next(iter(page_ids))} if page_ids else {}, payload=posts)


def items(posts):
    return [ContentItem(p.published, p.post_type, {p.channel: p.caption},
                        {p.channel: p.post_id}, {p.channel: p.permalink}, {p.channel: p.creatives}) for p in posts]


def enrich(content, snapshots, warnings):
    """Meta stays authoritative; conflicting Performance snapshots need a choice."""
    unique = {}
    for post in snapshots:
        key = (post.channel, post.post_id)
        if key in unique:
            left, right = deepcopy(unique[key]), deepcopy(post)
            left.details.pop('performance_source', None)
            right.details.pop('performance_source', None)
            if left != right:
                raise PipelineError(f'{post.channel}:{post.post_id}: eltérő ZoomSphere Performance pillanatkép; csak a használni kívánt exportot tartsd meg.')
        else:
            unique[key] = post
    result = deepcopy(content)
    existing = {(p.channel, p.post_id): p for p in result}
    existing_channels = {p.channel for p in result}
    for key, supplement in unique.items():
        target = existing.get(key)
        if target is None:
            # Supplementary exports must not extend a Meta channel's measured
            # cohort with a different lifetime snapshot or story population.
            if supplement.channel not in existing_channels and supplement.post_type != 'story':
                result.append(deepcopy(supplement))
            continue
        discrepancies = []
        for field in METRICS:
            value = getattr(supplement, field)
            if field in supplement.details.get('missing_metrics', []):
                continue
            missing = field in target.details.get('missing_totals', []) or (field == 'saves' and target.saves is None)
            if missing:
                setattr(target, field, value)
                target.details['missing_totals'] = [f for f in target.details.get('missing_totals', []) if f != field]
            elif getattr(target, field) != value:
                discrepancies.append(field)
        for field, value in supplement.details.items():
            if field == 'organic':
                for name, measured in value.items():
                    if name not in discrepancies:
                        target.details.setdefault('organic', {}).setdefault(name, measured)
            elif field not in ('missing_totals', 'missing_metrics'):
                if (field in ('organic_views', 'paid_views') and 'views' in discrepancies
                        or field == 'paid_reach' and 'reach' in discrepancies):
                    continue
                target.details.setdefault(field, deepcopy(value))
        for field in ('caption', 'permalink', 'post_type', 'creatives'):
            if not getattr(target, field):
                setattr(target, field, deepcopy(getattr(supplement, field)))
        if discrepancies:
            warnings.append(f'{target.channel}:{target.post_id}: eltérő Meta és ZoomSphere pillanatkép ({", ".join(discrepancies)}); a Meta forrásértékeit tartottuk meg.')
    return result
