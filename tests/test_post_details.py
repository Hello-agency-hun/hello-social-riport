import json
from pathlib import Path

import pytest

from pipeline.parsers.meta_content import parse
from pipeline.render import render


def test_content_import_keeps_explicit_organic_and_follower_details(tmp_path):
    path = tmp_path / 'content.csv'
    path.write_text(
        'Bejegyzésazonosító,Elérés,Megtekintések,Állandó hivatkozás,Közzététel időpontja,'
        'Organikus elérés,Organikus reakciók,Organikus hozzászólások,Organikus mentések,'
        'Organikus megosztások,Követések,Fizetett elérés,Elköltött összeg (HUF),Reakciók,Hozzászólások,Megosztások,Mentések\n'
        '200,100,120,https://instagram.com/p/test,2026-07-01,40,0,2,3,4,22,80,19984,1,2,4,3\n',
        encoding='utf-8',
    )
    post = parse(path).payload[0]
    assert getattr(post, 'details', {}) == {
        'organic': {'reach': 40, 'reactions': 0, 'comments': 2, 'saves': 3, 'shares': 4},
        'followers': 22, 'paid_reach': 80, 'spend': 19984.0, 'currency': 'HUF',
    }


def test_essentials_renders_all_sample_metrics_without_inventing_organic(tmp_path):
    data = json.loads((Path(__file__).parent / 'fixtures/larus-2026-07/report_data.golden.json').read_text(encoding='utf-8'))
    data['meta']['variant'] = 'essentials'
    html = render(data, tmp_path, fetcher=lambda url: b'')
    assert 'post-metrics-table' in html
    assert 'Organikus' in html
    assert 'Követőszerzés' in html
    assert 'data-post-manual=' in html
    # Legacy total reach minus Ads reach must NOT become organic reach.
    assert 'data-post-field="organic.reach"' in html


def test_missing_details_can_be_filled_but_exported_zero_is_locked():
    from pipeline.post_details import card
    post = {'channel': 'instagram', 'post_id': '200', 'organic_measured': True,
            'reach': 100, 'reactions': 10, 'comments': 2, 'shares': 3, 'saves': 4,
            'details': {'organic': {'reactions': 0}}}
    initial = card(post, currency='HUF')
    reach = initial['rows'][-1]['organic']
    followers = initial['followers']
    out = card(post, {reach['key']: 40, followers['key']: 0}, 'HUF')
    assert out['rows'][-1]['organic']['value'] == 40
    assert out['followers']['value'] == 0
    assert out['followers']['source'] == 'manual'
    assert out['rows'][0]['organic']['editable'] is False
    assert out['rows'][0]['organic']['value'] == 0


def test_manual_organic_cannot_exceed_total():
    from pipeline.post_details import card
    from pipeline.errors import PipelineError
    post = {'channel': 'facebook', 'post_id': '200', 'organic_measured': True, 'reach': 100}
    key = card(post)['rows'][-1]['organic']['key']
    with pytest.raises(PipelineError, match='összesnél'):
        card(post, {key: 101})


def test_source_breakdown_rejects_negative_and_conflicting_aliases():
    from pipeline.post_details import import_details
    from pipeline.errors import PipelineError
    with pytest.raises(PipelineError, match='Organikus elérés'):
        import_details({'Organikus elérés': '-1'}, 'Dummy')
    with pytest.raises(PipelineError, match='eltérő'):
        import_details({'Organikus elérés': '40', 'Organic Reach': '45'}, 'Dummy')


def test_manual_spend_allows_at_most_two_decimals():
    from pipeline.post_details import card
    from pipeline.errors import PipelineError
    post = {'channel': 'facebook', 'post_id': '200'}
    key = card(post, currency='HUF')['spend']['key']
    with pytest.raises(PipelineError, match='érvénytelen'):
        card(post, {key: 1.2345}, 'HUF')
