from datetime import date

import pytest

from pipeline.detect import identify
from pipeline.errors import PipelineError
from pipeline.parsers import zoomsphere_performance as performance
from pipeline.schema import Post


HEADER = 'postId,channel,network,postType,datePublished,message,publicUrl,thumbnail,Reach,Views,Likes,Comments,Shares,Post Saves,Followers Gained,Organic Views,Views From Ads\n'


def source(tmp_path, body):
    path = tmp_path / 'random.csv'
    path.write_text(HEADER + body, encoding='utf-8')
    return path


def test_performance_detects_by_headers_and_ignores_total(tmp_path):
    path = source(tmp_path, '10_20,Dummy,FACEBOOK,image,2026-09-01,Hello,https://facebook.com/20,https://example.com/image.jpg,100,120,0,1,2,,0,90,30\nTOTAL,,,,,,,,100,120,,,,,,,\n')
    assert identify(path).kind == 'zoomsphere_performance'
    parsed = performance.parse(path)
    assert len(parsed.payload) == 1
    post = parsed.payload[0]
    assert (post.channel, post.post_id, post.published) == ('facebook', '20', date(2026, 9, 1))
    assert post.creatives == ['https://example.com/image.jpg']
    assert post.details['followers'] == 0
    assert post.details['organic_views'] == 90
    assert post.details['paid_views'] == 30
    assert 'organic' not in post.details
    assert post.saves is None


def test_blank_metrics_stay_missing_and_explicit_zero_is_measured(tmp_path):
    path = source(tmp_path, '20,Dummy,INSTAGRAM,reel,2026-09-01,Hello,https://instagram.com/p/x,,100,120,,0,,0,0,,\n')
    post = performance.parse(path).payload[0]
    assert post.details['missing_totals'] == ['reactions', 'shares']
    assert post.comments == 0 and post.saves == 0
    assert 'organic_views' not in post.details


def test_merge_keeps_meta_totals_and_enriches_only_matching_post(tmp_path):
    path = source(tmp_path, '10_20,Dummy,FACEBOOK,image,2026-09-01,Hello,https://facebook.com/20,https://example.com/i.jpg,200,250,12,3,4,5,2,200,50\n')
    meta = Post('facebook', '20', date(2026, 9, 1), reach=100, reactions=0,
                organic_measured=True, details={'organic': {'reach': 40}})
    warnings = []
    posts = performance.enrich([meta], performance.parse(path).payload, warnings)
    assert len(posts) == 1 and posts[0].reach == 100 and posts[0].reactions == 0
    assert posts[0].details['organic']['reach'] == 40
    assert posts[0].details['followers'] == 2 and posts[0].saves == 5
    assert posts[0].creatives == ['https://example.com/i.jpg']
    assert warnings and '20' in warnings[0]


def test_repeated_snapshots_are_not_added_or_silently_chosen(tmp_path):
    path = source(tmp_path, '20,Dummy,INSTAGRAM,reel,2026-09-01,Hello,,,100,120,1,0,0,0,0,,\n')
    one = performance.parse(path).payload
    assert len(performance.enrich([], one + one, [])) == 1
    different = performance.parse(path).payload
    different[0].reach = 200
    with pytest.raises(PipelineError, match='pillanatkép'):
        performance.enrich([], one + different, [])


def test_other_clients_are_not_matched_by_caption(tmp_path):
    path = source(tmp_path, '10_21,Dummy,FACEBOOK,image,2026-09-01,Hello,,,100,120,1,0,0,0,0,,\n')
    meta = Post('facebook', '20', date(2026, 9, 1), caption='Hello', reach=300, organic_measured=True)
    posts = performance.enrich([meta], performance.parse(path).payload, [])
    assert next(p for p in posts if p.post_id == '20').details == {}


def test_non_integer_or_negative_statistics_fail_with_file_context(tmp_path):
    path = source(tmp_path, '20,Dummy,INSTAGRAM,reel,2026-09-01,Hello,,,-1,120,1,0,0,0,0,,\n')
    with pytest.raises(PipelineError, match='random.csv'):
        performance.parse(path)
