from pipeline import compare


def test_rejuran_style_cross_copy_disables_manual_baseline():
    channels = {
        'facebook': {'totals': {'visits': 1236, 'link_clicks': 5591,
                                'interactions': 215, 'follows': 48,
                                'views': 266205}},
        'instagram': {'totals': {'visits': 1887, 'link_clicks': 1262,
                                 'interactions': 6385, 'follows': 285,
                                 'views': 436660}},
    }
    manual = {
        'prev_facebook_visits': 1236,
        'prev_facebook_link_clicks': 5591,
        'prev_facebook_interactions': 215,
        'prev_facebook_follows': 48,
        'prev_facebook_views': 43660,
        'prev_instagram_visits': 1887,
        'prev_instagram_link_clicks': 1262,
        'prev_instagram_interactions': 6385,
        'prev_instagram_follows': 285,
        'prev_instagram_views': 266205,
    }

    resolved, warning = compare.validated_manual_baseline(manual, channels)

    assert resolved == {}
    assert warning and 'gyanús' in warning.casefold()


def test_plausible_manual_baseline_is_preserved():
    channels = {'facebook': {'totals': {'views': 1200, 'visits': 50}}}
    manual = {'prev_facebook_views': 900, 'prev_facebook_visits': 41}

    resolved, warning = compare.validated_manual_baseline(manual, channels)

    assert resolved == {'facebook': {'views': 900, 'visits': 41}}
    assert warning is None


def test_one_channel_with_unchanged_values_is_not_rejected():
    channels = {
        "facebook": {
            "totals": {"reach": 100, "views": 200, "followers": 300}
        }
    }
    manual = {
        "prev_facebook_reach": 100,
        "prev_facebook_views": 200,
        "prev_facebook_followers": 300,
    }

    resolved, warning = compare.validated_manual_baseline(manual, channels)

    assert resolved == {"facebook": {"reach": 100, "views": 200, "followers": 300}}
    assert warning is None
