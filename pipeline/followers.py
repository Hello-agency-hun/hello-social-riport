"""Követőszám: honnan tudjuk, és mikor kell újra megkérdezni.

A Meta nem exportálja. Az első hónapban a menedzser leolvassa a profilról —
fél perc. Utána viszont **nem kell újra**: a múlt havi állomány plusz a havi
új követés kiadja a mostanit.

De csak akkor, ha a két hónap tényleg egymás után jön. Ha kimarad kettő, a
lánc elszakad: a júliusi riportból a szeptemberi állomány nem jön ki, mert a
közte eltelt idő gyarapodását senki nem mérte. Ilyenkor újra kérdezünk.
Kitalálni nem lehet, és nem is próbáljuk.

Ugyanígy szakad a lánc ott, ahol nincs napi követés-csempe (az Instagramnál
jellemzően nincs): állomány + semmi = nem tudjuk, mennyi lett.
"""

from datetime import date

from pipeline.bootstrap import FOLLOWER_HINT
from pipeline.errors import MissingConfigError


def previous_period(period: str) -> str:
    """A közvetlenül megelőző hónap. Csak ebből lehet továbbszámolni."""
    year, month = (int(part) for part in period.split("-"))
    return f"{year - 1}-12" if month == 1 else f"{year}-{month - 1:02d}"


def wanted_channels(client: dict) -> list[str]:
    names = []
    if client.get("fb_page_id") or client.get("fb_page_name"):
        names.append("facebook")
    if client.get("ig_handle"):
        names.append("instagram")
    return names


def resolve(
    config: dict,
    channels: dict,
    previous: dict | None,
    period: str,
    measurement_start: str | None = None,
):
    """(követőszámok, honnan) — vagy hiba, ha valamelyik tényleg hiányzik.

    A `honnan` a menedzsernek szól: a továbbszámolt értéket látnia kell, hogy
    ránézésre kiszúrja, ha elcsúszott.
    """
    client = config.get("client") or {}
    given = config.get("followers") or {}

    chained = _chainable(previous, period, measurement_start)

    resolved: dict[str, int] = {}
    origin: dict[str, str] = {}
    gaps: list[str] = []

    for name in wanted_channels(client):
        if isinstance(given.get(name), int):
            resolved[name] = given[name]
            origin[name] = "client.yaml"
            continue

        carried = _carry_forward(chained, channels, name)
        if carried is None:
            gaps.append(name)
            continue

        resolved[name], gained = carried
        origin[name] = (
            f"az előző hónap állományából továbbszámolva (+{gained} új követés)"
        )

    if gaps:
        raise MissingConfigError(_help(gaps, previous, period, measurement_start))
    return resolved, origin


def _chainable(
    previous: dict | None, period: str, measurement_start: str | None = None
) -> dict | None:
    """Az előző havi riportadat — de csak ha tényleg az előző hónapé."""
    if not previous:
        return None
    meta = previous.get("meta") or {}
    previous_end = meta.get("measurement_end")
    if measurement_start and previous_end:
        try:
            if (date.fromisoformat(measurement_start) - date.fromisoformat(previous_end)).days != 1:
                return None
        except ValueError:
            return None
    elif meta.get("period") != previous_period(period):
        return None
    return previous.get("audience") or {}


def _carry_forward(chained, channels: dict, name: str):
    if not chained:
        return None
    before = (chained.get(name) or {}).get("followers")
    gained = ((channels.get(name) or {}).get("totals") or {}).get("follows")
    if not isinstance(before, int) or not isinstance(gained, int):
        return None
    return before + gained, gained


def _help(
    gaps: list[str],
    previous: dict | None,
    period: str,
    measurement_start: str | None = None,
) -> str:
    lines = "\n".join(f"  {name}: <{FOLLOWER_HINT[name]}>" for name in gaps)

    if previous is None:
        why = "Ez az első hónap ennél az ügyfélnél, tehát nincs miből továbbszámolni."
    elif _chainable(previous, period, measurement_start) is None:
        before = previous.get("meta") or {}
        got = before.get("measurement_end") or before.get("period", "ismeretlen")
        expected = previous_period(period)
        why = (
            f"A previous.json zárása ({got}) nem a közvetlenül megelőzőé. "
            f"A naptári címke alapján a(z) {expected} riport kellene. "
            "A köztes idő gyarapodását senki nem "
            "mérte, tehát nem lehet továbbszámolni."
        )
    else:
        why = (
            "Az előző hónap állománya megvan, de ezen a csatornán nincs napi "
            "követés-adat, amivel tovább lehetne vinni."
        )

    return (
        f"hiányzik a követőszám ({', '.join(gaps)}).\n{why}\n"
        "Olvasd le a profilról, és írd a client.yaml-be:\n\nfollowers:\n" + lines
    )
