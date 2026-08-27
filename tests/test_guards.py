from datetime import date

import pytest

from pipeline.errors import (
    ClientMismatchError,
    PeriodMismatchError,
    ReachSummationError,
    ResultTypeMixError,
)
from pipeline.guards import (
    check_client,
    check_period,
    sum_additive,
    sum_results,
)
from pipeline.schema import Campaign


def test_reach_may_not_be_summed():
    with pytest.raises(ReachSummationError):
        sum_additive([100, 200], field="reach")


def test_additive_fields_are_summed():
    assert sum_additive([100, 200], field="link_clicks") == 300


def test_results_of_the_same_type_are_summed():
    campaigns = [
        Campaign(name="a", results=10, result_type="actions:link_click"),
        Campaign(name="b", results=5, result_type="actions:link_click"),
    ]
    assert sum_results(campaigns) == 15


def test_results_of_mixed_types_raise():
    campaigns = [
        Campaign(name="a", results=10, result_type="reach"),
        Campaign(name="b", results=5, result_type="actions:link_click"),
    ]
    with pytest.raises(ResultTypeMixError):
        sum_results(campaigns)


def test_period_inside_the_target_month_passes():
    check_period("zoomsphere", (date(2026, 7, 1), date(2026, 7, 29)), "2026-07")


def test_period_outside_the_target_month_raises():
    with pytest.raises(PeriodMismatchError, match="zoomsphere"):
        check_period("zoomsphere", (date(2026, 6, 1), date(2026, 6, 30)), "2026-07")


def test_matching_client_passes():
    check_client(
        {"page_id": "100064824963030", "page_name": "Larus Étterem"},
        {"fb_page_id": "100064824963030", "fb_page_name": "Larus Étterem"},
    )


def test_alternate_meta_page_id_passes_when_page_name_matches():
    check_client(
        {
            "page_id": "100064789718198",
            "page_name": "Mammut Bevásárló- és Szórakoztató Központ",
        },
        {
            "fb_page_id": "218802662004",
            "fb_page_name": "mammut.bevasarlo.es.szorakoztato.kozpont",
        },
    )


def test_display_name_and_page_slug_are_the_same_client():
    check_client(
        {"page_name": "Mammut Bevásárló- és Szórakoztató Központ"},
        {"fb_page_name": "mammut.bevasarlo.es.szorakoztato.kozpont"},
    )


def test_foreign_page_name_raises_without_page_id():
    with pytest.raises(ClientMismatchError, match="page_name"):
        check_client(
            {"page_name": "Másik Bevásárlóközpont"},
            {"fb_page_name": "mammut.bevasarlo.es.szorakoztato.kozpont"},
        )


def test_foreign_page_id_raises():
    with pytest.raises(ClientMismatchError, match="page_id"):
        check_client(
            {"page_id": "999", "page_name": "Mammut"},
            {"fb_page_id": "100064824963030", "fb_page_name": "Larus Étterem"},
        )


def test_foreign_page_id_raises_without_page_name():
    with pytest.raises(ClientMismatchError, match="page_id"):
        check_client(
            {"page_id": "999"},
            {"fb_page_id": "100064824963030", "fb_page_name": "Larus Étterem"},
        )
