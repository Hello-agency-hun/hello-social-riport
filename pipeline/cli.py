import argparse
import json
import sys
from pathlib import Path

from pipeline.build import build
from pipeline.errors import PipelineError
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
            f"Organic poszt átlagos elérése:  {cross['avg_reach_organic_post']}",
            f"Boostolt poszt átlagos elérése: {cross['avg_reach_boosted_post']}"
            f"  ({cross['reach_multiplier']}×)",
            "",
            "⚠ nem illesztett boost: "
            + (f"{len(unmatched)} db — " + "; ".join(unmatched) if unmatched else "nincs"),
        ]
    )


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
    args = parser.parse_args(argv)

    try:
        data = build(Path(args.directory), period=args.period)
    except PipelineError as error:
        print(f"HIBA: {error}", file=sys.stderr)
        return 1

    print(_report_map(data))

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
            ),
            encoding="utf-8",
        )
        print(f"→ {html_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
