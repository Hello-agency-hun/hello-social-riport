import unicodedata
from datetime import date
from typing import Iterable

from pipeline.errors import (
    ClientMismatchError,
    PeriodMismatchError,
    ReachSummationError,
    ResultTypeMixError,
)
from pipeline.schema import Campaign

NON_ADDITIVE = {"reach", "frequency", "followers_total"}


def sum_additive(values: Iterable[float], field: str) -> float:
    """Összegzés csak additív metrikákra.

    A reach egyedi emberek száma: napi vagy poszt-szintű értékek összege nem
    havi reach, mert ugyanazt az embert többször számolná. Nincs olyan
    részadatunk, amiből a helyes érték kiszámítható lenne — az kézi bevitel.
    """
    if field in NON_ADDITIVE:
        raise ReachSummationError(
            f"{field!r} nem additív metrika — összegzése hibás értéket adna. "
            "A havi értéket kézi bevitelből kell venni (page_metrics.yaml)."
        )
    return sum(values)


def sum_results(campaigns: list[Campaign]) -> int:
    """Az `Eredmények` oszlop csak azonos `Eredmény jelzése` mellett összegezhető."""
    types = {c.result_type for c in campaigns if c.result_type}
    if len(types) > 1:
        raise ResultTypeMixError(
            "eltérő eredménytípusok nem adhatók össze: " + ", ".join(sorted(types))
        )
    return sum(c.results for c in campaigns)


def check_period(kind: str, period: tuple[date, date] | None, target: str) -> None:
    """`target` formátuma `YYYY-MM`."""
    if period is None:
        return
    year, month = (int(part) for part in target.split("-"))
    for boundary in period:
        if (boundary.year, boundary.month) != (year, month):
            raise PeriodMismatchError(
                f"{kind}: a forrás időszaka {period[0]}–{period[1]}, "
                f"a riportált hónap {target}. Valószínűleg rossz fájl került a mappába."
            )


def _identity_key(value: str) -> str:
    """Az oldal megjelenített neve és URL-slugja ugyanazt az ügyfelet jelentheti."""
    folded = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in folded if character.isascii() and character.isalnum())


def check_client(hints: dict[str, str], config: dict[str, str]) -> None:
    found_name = hints.get("page_name")
    expected_name = config.get("fb_page_name")
    names_match = bool(
        found_name
        and expected_name
        and _identity_key(found_name) == _identity_key(expected_name)
    )
    pairs = [("page_id", "fb_page_id"), ("page_name", "fb_page_name")]
    for hint_key, config_key in pairs:
        found, expected = hints.get(hint_key), config.get(config_key)
        if not found or not expected or found == expected:
            continue
        if names_match:
            continue
        if found != expected:
            raise ClientMismatchError(
                f"{hint_key}: a forrásban {found!r}, a client.yaml-ben {expected!r}. "
                "Más ügyfél adata került a mappába."
            )
