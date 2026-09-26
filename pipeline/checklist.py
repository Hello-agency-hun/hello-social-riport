"""A letöltendő fájlok listája — kipipálható, nem próza.

A Mammut-próba legdrágább hibája nem kódhiba volt, hanem a kérés pontatlansága.
A menedzser négy bekezdésnyi prózát kapott arról, honnan mit töltsön le, és
ebből **öt kör** oda-vissza lett: a Tartalom exportok kimaradtak, a ZoomSphere
PDF-ként jött, az Ads XLSX-ként, a havi elérés és a követőszám külön körben,
és jött két olyan fájl, amire nincs is szükség.

A menedzser nem olvas el négy bekezdést, mielőtt letölt. **Kipipál.** A próza
akkor jó, amikor egy dolog hiányzik; a munka elején viszont tizenhat dolog van,
és kettő olyan, amiről nem is sejti, hogy létezik — a havi elérés csempéje
csatornánként más néven fut.

A lista a `client.yaml`-ből szűkül: akinek nincs Instagram-fiókja, ne kapjon
Instagram-sorokat.
"""

FIVE_TILES = "Felkeresések · Hivatkozáskattintások · Interakciók · Követők · Megtekintések"


def _campaign(client: dict, directory: str, exact_range: str, has_fb: bool, has_ig: bool) -> str:
    """A kampányriport listája. Más a kérdés, más a letöltés: a Meta Ads
    export a lényeg, a kampány teljes idejére — a többi kiegészítés."""
    lines = [
        f"Kampányriport — töltsd ide: {directory}/input/",
        "Ne nevezd át a fájlokat — a nevük adatot hordoz.",
        "",
        f"Időszak: a kampány teljes ideje ({exact_range}).",
        "",
        "□ Meta Ads Manager → Kampányok → időszak: a kampány teljes ideje → Exportálás → .CSV  (NEM xlsx!)",
        "  Heti görbéhez: előtte Bontás → Idő → Hét. Az idővonalhoz adj hozzá egy „Kezdés” oszlopot.",
        "  Minden kampányt exportálhatsz — a riport a client.yaml `campaign.match` mintája szerint válogat.",
        "□ Ads Manager → jelöld ki a riport kampányait → az összesítő sor „Elérés” értéke",
        "  → client.yaml: campaign.reach   (több kampány elérése nem adható össze)",
        "",
        "Kiegészítés — ha megvan, a riport többet mond:",
    ]
    if has_fb:
        lines.append("□ Business Suite → Eredmények → Facebook fül, öt csempe")
    if has_ig:
        lines.append("□ Business Suite → Eredmények → Instagram fül, öt csempe")
    lines += [
        "  A kampány idejére ÉS az előtte lévő, ugyanolyan hosszú időszakra együtt:",
        "  ebből látszik, mozdult-e az oldal a kampány alatt.",
    ]
    if has_fb:
        lines.append("□ Business Suite → Tartalom → FACEBOOK → .csv   (a hirdetett posztokhoz)")
    if has_ig:
        lines.append("□ Business Suite → Tartalom → INSTAGRAM → .csv")
    lines += [
        "□ ZoomSphere → Scheduler → export a kampány idejére → .XLSX   (a kreatívokhoz)",
        "",
        "A client.yaml-be:",
        "  report:",
        "    variant: campaign",
        "  campaign:",
        '    title: "<a kampány neve a címlapon>"',
        '    match: ["<a kampánynevekben közös szórészlet>"]',
        '    goal: "<a kampány célja egy mondatban — opcionális>"',
        '    post_match: ["<#hashtag vagy kulcsszó a kapcsolódó posztokhoz — opcionális>"]',
    ]
    return "\n".join(lines)


def render(
    client: dict | None,
    directory: str,
    measurement_start: str | None = None,
    measurement_end: str | None = None,
    variant: str | None = None,
) -> str:
    client = client or {}
    has_fb = bool(client.get("fb_page_id") or client.get("fb_page_name"))
    has_ig = bool(client.get("ig_handle"))
    # Ha még nincs `client.yaml`, nem tudjuk, milyen fiókjai vannak — ilyenkor
    # mindkettőt kérjük, mert a hiányzó sor drágább, mint a fölösleges.
    if not has_fb and not has_ig:
        has_fb = has_ig = True

    exact_range = (
        f"{measurement_start} – {measurement_end}"
        if measurement_start and measurement_end
        else "a kiválasztott pontos mérési időszak"
    )
    if variant == "campaign":
        return _campaign(
            client,
            directory,
            exact_range if measurement_start and measurement_end
            else "a kampány első és utolsó napja",
            has_fb,
            has_ig,
        )

    lines = [
        f"Töltsd ide: {directory}/input/",
        "Ne nevezd át a fájlokat — a nevük adatot hordoz (lásd a Megtekintéseket).",
        "",
        f"Mérési időszak: {exact_range} (a 25–24-es pénzügyi ciklus teljes értékű hónap).",
        "Minden napi, Tartalom- és Scheduler-exportnál pontosan ezt az időszakot állítsd be.",
        "",
        "□ ZoomSphere → Scheduler → export erre az időszakra → .XLSX     (NEM pdf!)",
        "□ Meta Ads Manager → Kampányok → ugyanerre az időszakra → Exportálás → .CSV  (NEM xlsx!)",
        "  Ha az Ads-export tágabb időszakot fed, a teljes összeg bekerül, de tájékoztató jelölést kap.",
        "  A Jelentés kezdete/vége a lekérési ablak; nem a kampány kezdete/vége.",
    ]

    if has_fb:
        lines.append("□ Business Suite → Tartalom → FACEBOOK → .csv")
    if has_ig:
        lines.append(
            "□ Business Suite → Tartalom → INSTAGRAM → .csv"
            "     ← a leggyakrabban ez marad ki"
        )

    lines.append("")
    if has_fb:
        lines += ["□ Business Suite → Eredmények → Facebook fül, öt csempe:",
                  f"     {FIVE_TILES}"]
    if has_ig:
        lines += ["□ Business Suite → Eredmények → Instagram fül, ugyanaz az öt:",
                  f"     {FIVE_TILES}"]

    lines.append("")
    lines.append("Képernyőkép (ezekről olvasom le a havi elérést — nem CSV-ből):")
    if has_fb:
        lines.append('□ Facebook → "Nézők" csempe      (a Facebookon ez az elérés neve)')
    if has_ig:
        lines.append('□ Instagram → "Elérés" csempe')

    lines.append("")
    lines.append("Követőszám (a Business Suite → Közönség pontos, az oldal fejléce kerekít):")
    if has_fb:
        lines.append("□ Facebook követőszám")
    if has_ig:
        lines.append("□ Instagram követőszám")

    lines += [
        "",
        "□ Előző havi report_data.json → previous.json     (ha volt előző hónap)",
        "",
        "NEM kell, és hibát okoz:",
        '  · napi "Nézők" / "Elérés" CSV — a napi elérés nem összegezhető',
        "  · a ZoomSphere PDF-változata — nincs benne poszt-azonosító és kép-URL",
        "",
        "Ha valamit rossz formátumban töltöttél le, akkor is tedd be — megmondom,"
        " mit lehet vele kezdeni.",
    ]
    return "\n".join(lines)
