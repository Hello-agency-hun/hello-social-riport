"""Standalone campaign inventory and deterministic calculation entry point."""

import argparse
import json
import sys
from pathlib import Path

from pipeline.campaign import build, discover
from pipeline.campaign_render import render_campaign
from pipeline import images
from pipeline.errors import PipelineError
from pipeline.textio import force_utf8_output


def main(argv=None):
    force_utf8_output()
    parser = argparse.ArgumentParser(prog="hello-campaign")
    parser.add_argument("directory", help="kampányprojekt mappa; input/ és campaign.yaml")
    parser.add_argument("--discover", action="store_true", help="hirdetések és posztok listája kiválasztáshoz")
    parser.add_argument("--validate", action="store_true", help="számítás és forrásellenőrzés fájlírás nélkül")
    parser.add_argument("--out", help="a kampányadat JSON célútvonala")
    parser.add_argument("--html", help="a kampány HTML-riport célútvonala")
    parser.add_argument("--variant", choices=["full", "essentials"], help="a kimenet változata")
    parser.add_argument("--offline", action="store_true", help="kreatívok letöltése nélkül")
    args = parser.parse_args(argv)
    directory = Path(args.directory)
    if not (directory / "input").is_dir():
        print("HIBA: Hiányzik az input/ mappa.", file=sys.stderr)
        return 1
    try:
        result = discover(directory) if args.discover else build(directory)
    except PipelineError as error:
        print(f"HIBA: {error}", file=sys.stderr)
        return 1
    if args.discover or args.validate:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    output = json.dumps(result, ensure_ascii=False, indent=2)
    target = Path(args.out or directory / "report_data.json")
    narrative_path = directory / "narrative.json"
    try:
        narrative = json.loads(narrative_path.read_text(encoding="utf-8")) if narrative_path.is_file() else {}
        html = render_campaign(result, narrative, cache_dir=directory / ".image-cache",
                               fetcher=(lambda url: b"") if args.offline else images.fetch,
                               variant=args.variant)
    except (PipelineError, ValueError) as error:
        print(f"HIBA: {error}", file=sys.stderr)
        return 1
    html_target = Path(args.html or directory / "Riport.html")
    target.write_text(output, encoding="utf-8")
    html_target.write_text(html, encoding="utf-8")
    print(f"→ {target}\n→ {html_target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
