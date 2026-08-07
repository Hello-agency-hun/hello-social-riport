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


def render(client: dict | None, directory: str) -> str:
    client = client or {}
    has_fb = bool(client.get("fb_page_id") or client.get("fb_page_name"))
    has_ig = bool(client.get("ig_handle"))
    # Ha még nincs `client.yaml`, nem tudjuk, milyen fiókjai vannak — ilyenkor
    # mindkettőt kérjük, mert a hiányzó sor drágább, mint a fölösleges.
    if not has_fb and not has_ig:
        has_fb = has_ig = True

    lines = [
        f"Töltsd ide: {directory}/input/",
        "Ne nevezd át a fájlokat — a nevük adatot hordoz (lásd a Megtekintéseket).",
        "",
        "□ ZoomSphere → Scheduler → export a hónapra → .XLSX     (NEM pdf!)",
        "□ Meta Ads Manager → Kampányok → hónap → Exportálás → .CSV  (NEM xlsx!)",
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
