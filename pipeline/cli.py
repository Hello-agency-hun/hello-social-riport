import argparse
import json
import sys
from pathlib import Path

import yaml

from pipeline.build import build, load_narrative
from pipeline.errors import FixtureAsClientError, PipelineError
from pipeline.textio import force_utf8_output


def _report_map(data: dict) -> str:
    quality = data["quality"]
    paid = data["paid"]
    content = data["content"]
    cross = data["cross"]
    channels = ", ".join(sorted(data["channels"])) or "nincs"
    unmatched = quality["unmatched_boosts"]

    return "\n".join(
        [
            f"Ügyfél:   {data['meta']['client']}",
            f"Időszak:  {data['meta']['period']}",
            "",
            f"ZoomSphere      {content['total']} tartalom — "
            + ", ".join(f"{count} {name}" for name, count in content["by_type"].items()),
            f"Posztok         {quality['posts_total']} összesen · "
            f"{quality['posts_measured']} mért organikus teljesítménnyel · "
            f"{quality['posts_with_creative']} kreatívval",
            f"Meta Ads        {paid['always_on']['campaigns']} always-on + "
            f"{paid['boosted']['campaigns']} boost, "
            f"{paid['spend']:.2f} {paid['currency']} "
            f"({quality['dropped_zero_campaign_rows']} nullás sor kiszűrve)",
            f"Napi metrikák   {channels}",
            "",
            "\n".join(
                f"Követők {name:<9} {data['audience'][name]['followers']} "
                f"({origin})"
                for name, origin in sorted(data.get("follower_origin", {}).items())
            ),
            "",
            f"Organic poszt átlagos elérése:  {cross['avg_reach_organic_post']}",
            f"Boostolt poszt átlagos elérése: {cross['avg_reach_boosted_post']}"
            f"  ({cross['reach_multiplier']}×)",
            "",
            (
                "Hiányzó források:\n"
                + "\n".join(f"  ✗ {gap}" for gap in data["missing"])
                if data["missing"]
                else "Minden várt forrás megvan."
            ),
            "",
            (
                # Ha a menedzser feltöltött képernyőképeket, azokról a hiányzó
                # számok jó eséllyel leolvashatók. Ilyenkor NE kérjük tőle
                # újra — nézzük meg. Ez az utasítás az agentnek szól.
                "📷 "
                + str(len(data["screenshots"]))
                + " képernyőkép van a mappában:\n"
                + "\n".join(f"  · {name}" for name in data["screenshots"])
                + "\n  → Olvasd ki belőlük, ami hiányzik, MIELŐTT bármit "
                "megkérdeznél a menedzsertől. Amit ezekről le lehet olvasni, "
                "azt ne kérdezd meg tőle."
                if data.get("screenshots")
                else ""
            ),
            (
                "Beszerezhető, de még nincs megadva — írd a client.yaml-be:\n"
                + "\n".join(
                    f"  → {item['label']}\n      {item['hint']}"
                    for item in data["obtainable"]
                )
                # A magyarázat egyszer szerepel, nem csatornánként: ugyanaz a
                # mondat kétszer egymás alatt zajnak látszik, nem indoklásnak.
                + f"\n\n  Miért nem tudjuk kiszámolni? {data['obtainable'][0]['why']}"
                + "\n\n  monthly_reach:\n"
                + "\n".join(
                    f"    {item['key'].split('.')[1]}: <szám>"
                    for item in data["obtainable"]
                )
                if data.get("obtainable")
                else "Minden beszerezhető adat megvan."
            ),
            "",
            (
                "⚠ kreatív nélküli poszt (helyőrző lesz a riportban — a "
                "ZoomSphere nem tud róla, tehát nem azon keresztül ment ki):\n"
                + "\n".join(f"  · {text}" for text in quality["posts_without_creative"])
                if quality.get("posts_without_creative")
                else "Minden mért poszthoz van kreatív."
            ),
            "",
            "⚠ nem illesztett boost: "
            + (f"{len(unmatched)} db — " + "; ".join(unmatched) if unmatched else "nincs"),
        ]
    )


def _refuse_the_fixture(directory: Path, allowed: bool) -> None:
    """A teszt-fixture valódi ügyféladat, és semmi nem különbözteti meg egy
    éles munkamappától: van benne `client.yaml`, teljes exportkészlet és kész
    narratíva.

    Egy agent, akit megkérnek, hogy „csinálj riportot a Larusnak júliusra”,
    rátalál, és épít belőle — ez meg is történt. A riport hibátlan lesz, csak
    épp nem arról szól, amit a menedzser feltöltött, és ez sehol nem derül ki.
    Ezért nem elég leírni, hogy ne tegye: nem szabad, hogy menjen.
    """
    if allowed:
        return
    parts = [part.lower() for part in Path(directory).resolve().parts]
    if "fixtures" in parts and "tests" in parts:
        raise FixtureAsClientError(
            f"{directory} a teszt-fixture, nem ügyfélmappa.\n"
            "Valódi ügyféladat van benne, de a tesztek kötötték le — riportot "
            "nem ebből készítünk.\n"
            "Hozz létre egy saját mappát (clients/<ugyfel>/<YYYY-MM>/input/), "
            "és oda töltsd fel az exportokat.\n"
            "(A teszteknek: --allow-fixture.)"
        )


def _also_worth_knowing(directory: Path, period: str) -> None:
    """A megállás után: mi az, ami úgyis hiányozni fog?

    A build az első hibánál megáll — muszáj, mert a többi számítás arra épül.
    A menedzser viszont emiatt körönként egy hibát lát: kijavít egyet,
    újrafuttat, kap egy másikat. A PETI-próbán ez négy kör volt az első
    sikeres futásig.

    A hiányzó `client.yaml`-mezők ettől függetlenül megállapíthatók, mert csak
    a konfigurációtól függenek. Ezeket tehát előre megmondjuk, hogy egy körben
    lehessen mindent pótolni. Ha ez maga is hibára fut, csendben elhallgat: a
    segítség sosem takarhatja el az eredeti hibát.
    """
    from pipeline import bootstrap, followers, manual

    try:
        path = Path(directory) / "client.yaml"
        if not path.exists():
            return
        config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        client = config.get("client") or {}
        gaps = []

        given_followers = config.get("followers") or {}
        given_reach = config.get("monthly_reach") or {}
        for name in followers.wanted_channels(client):
            if not isinstance(given_followers.get(name), int):
                gaps.append(f"followers.{name} — {bootstrap.FOLLOWER_HINT[name]}")
            if not isinstance(given_reach.get(name), int):
                hint = manual.OBTAINABLE["monthly_reach"]["hint"].get(name, "")
                gaps.append(f"monthly_reach.{name} — {hint}")

        if gaps:
            print(
                "\nEz úgyis hiányozni fog — érdemes most pótolni, "
                "hogy ne kelljen még egy kört futni:",
                file=sys.stderr,
            )
            for index, gap in enumerate(gaps, 1):
                print(f"  {index}. {gap}", file=sys.stderr)
    except Exception:
        # A segítség sosem takarhatja el az eredeti hibát.
        return


def main(argv: list[str] | None = None) -> int:
    force_utf8_output()
    parser = argparse.ArgumentParser(prog="hello-report")
    parser.add_argument(
        "directory", help="ügyfél-hónap mappa, pl. clients/larus/2026-07"
    )
    parser.add_argument("--period", required=True, help="YYYY-MM")
    parser.add_argument("--validate", action="store_true", help="csak ellenőrzés")
    parser.add_argument("--out", default=None, help="report_data.json útvonala")
    parser.add_argument("--html", default=None, help="Riport.html útvonala")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="ne töltsön le képet — a kreatívok helyén helyőrző jelenik meg",
    )
    parser.add_argument(
        "--apply-review",
        action="store_true",
        help="a review.json szövegjavításait beírja a narrative.json-be",
    )
    parser.add_argument(
        "--allow-fixture",
        action="store_true",
        help="a teszt-fixture-ből is engedjen építeni — csak a teszteknek",
    )
    args = parser.parse_args(argv)

    try:
        _refuse_the_fixture(Path(args.directory), args.allow_fixture)
        data = build(Path(args.directory), period=args.period)
    except PipelineError as error:
        print(f"HIBA: {error}", file=sys.stderr)
        _also_worth_knowing(Path(args.directory), args.period)
        return 1

    print(_report_map(data))

    if args.apply_review:
        from pipeline import review as review_module

        directory = Path(args.directory)
        stored = review_module.load_review(directory)
        current = load_narrative(directory)

        if stored["edits"] and current:
            applied = review_module.applied_edits(current, stored["edits"])
            updated = review_module.apply_edits(current, stored["edits"])
            (directory / "narrative.json").write_text(
                json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"{len(applied)} szövegjavítás alkalmazva.")
            # Amit nem tudtunk hova tenni, azt megnevezzük — a néma elnyelés
            # rosszabb, mint a hiba.
            for path in stored["edits"]:
                if path not in applied:
                    print(f"  ⚠ nem alkalmazható javítás: {path!r} — nincs ilyen blokk")

        for comment in stored["comments"]:
            print(f"  megjegyzés — {comment['page']}. oldal: {comment['text']}")

    if not args.validate:
        target = Path(args.out or Path(args.directory) / "report_data.json")
        target.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n→ {target}")

        from pipeline import images
        from pipeline.render import render

        html_path = Path(args.html or Path(args.directory) / "Riport.html")
        fetcher = (lambda url: b"") if args.offline else images.fetch
        html_path.write_text(
            render(
                data,
                cache_dir=Path(args.directory) / ".image-cache",
                fetcher=fetcher,
                manual=data.get("manual"),
                narrative=load_narrative(Path(args.directory)),
            ),
            encoding="utf-8",
        )
        print(f"→ {html_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
