# Riportmotor — rendszeraudit és fizetős QA (2026-09-30)

## Cél és állapot

Aktuális: a felhasználó engedélyezte a fizetős QA-t és utána a kiadást. A teljes motorregresszió újra 491 passed, 1 deselected (52,55 s). Három valódi gpt-5.6-luna / 4 GB kérés lefutott: szintetikus havi, kampány és havi kézi-előzmény review, összesen 64944 token. A kampány csak a kijelölt hirdetés 1250,50 HUF költését és két posztot mutatja; a havi költés 1350,50 HUF. Review után 217/200 → +17/+8,5%, szerkesztett szöveg megmaradt. A havi/kampány PDF 19/7 oldalas, nincs mért kilógás vagy üres oldal. A modell a publikált tartalom számát egyszer megjelenésnek nevezte: UI-ban javítva, `references/narrative-guide.md` jelentés tisztázva. Ez útmutató, nem szemantikai garancia. Webes kiadás következik, motor task-owned commit/push és tiszta vendor sync engedélyezve.

Aktív branch `codex/campaign-report`, HEAD `d1404b6`. A korábban elkészült kampányriport után a teljes motor + web auditja hat javításcsoportot kapott. Az új diffek helyileg teszteltek, még nincsenek commitolva/pusholva vagy élesítve. A mostani körben nincs új fizetős API-hívás. A korábbi kampány release és fizetős teszt előzményét a web handoffja rögzíti.

## Új motorváltoztatások

- `pipeline/textio.py`, új `pipeline/values.py`, Meta-parserek: UTF–16/32/Windows–1250, separator/header, lokalizált szám, ISO dátum. Hibás szám nem lehet csendben nulla; ütköző fejléc és többletcella hibát ad.
- `pipeline/detect.py`, `parsers/meta_daily.py`: fájlnévből biztos csatornajelzés felismerő/parser összhangja; azonos FB/IG napi érték ne legyen téves duplikátum. Bizonytalan csatorna továbbra is manager-jóváhagyást igényel.
- `pipeline/campaign.py`: azonos Scheduler-sor nem dupláz, eltérő poszt/snapshot adat két forrással hibát ad.
- `pipeline/images.py`, `render.py`, `campaign_render.py`: több kreatív URL, utána engedélyezett permalink fallback; robusztus Open Graph parser. Mock-fetch regresszió, nem élő CDN-garancia.
- `templates/campaign.html.j2`: PHP-hydratáláshoz posztazonosító az img-en; mobilon olvasható, oldalra görgethető Ads-tábla. Print továbbra is 1440×810.
- Új `tests/test_import_resilience.py`, bővített kampánytesztek, ISO-dátum elfogadásához igazított napi teszt.

## Webes integráció és tényleges ellenőrzés

A web worktree: `C:\Users\Mészáros Péter\.codex\worktrees\dual-repo-audit\hello report online`, branch `codex/import-easier`, HEAD `8d0de85`. A teljes térkép/javítások/QA: `docs/system-audit.md`, továbbadás: `docs/codex-handoff.md`. A motor csak `scripts/sync-upstream.ps1 -SourcePath <ez a worktree> -Force` útján került be, `upstream.json` = `d1404b6+local`.

- Friss `python -m pytest -q`: **491 passed, 1 deselected**, 79,65 másodperc; baseline 478.
- Web három PHP suite sikeres, öt JS syntax check és 20 módosított/új PHP lint sikeres.
- Helyi `tests/system_audit.py` szintetikus havi/kampány generálás, szerkesztés/újrarenderelés, kézi előzményből +17/+8,5% számolás, részleges uploadhiba, mentési versenyhelyzet és lomtár/visszaállítás sikeres. Desktop/mobile nincs pageerror vagy body-overflow.
- Havi PDF 19, kampány PDF 7 oldal; nincs üres oldal/mért kilógás, kontaktlapok és mobil screenshotok vizuálisan ellenőrizve. A szintetikus kreatív hiánya szándékos helyőrző.

## Kockázat és következő lépések

1. Külön publikálási/fizetős jóváhagyás után task-owned diff review és motor commit/push.
2. Web sync a tiszta motorcommitra; `+local` eltűnése és PHP regresszió ellenőrzése.
3. Jóváhagyott fizetős dummy OpenAI-generálás, szerkesztés, PDF; valódi kreatívok elérhetőségét külön ellenőrizni.
4. Web új verzió/commit/push/tag/release/CI, éles frissítő, utána smoke. A 4 GB-os konténer, modell, adat-integritási szabályok maradnak.

## Korlátok és külső állapot

A fő web workspace régi dirty változásait nem módosítottuk; az éles ügyféladat érintetlen. Ügyfél-export, API-kulcs, teszt-HTML/PDF és `data/` nem kerülhet Gitbe. A web audit localhost szervere 8091, offline configgal, üres API-kulccsal; QA-artifact `%TEMP%/hello-system-audit-qa-20260929`. Nincs új release/tag/telepítés.

## Folytató prompt

„Olvasd el a motor és a web `docs/codex-handoff.md` fájlját. A rendszeraudit motorváltozatai 491 teszten átmentek, a webben szinkronizált helyi copy van. Folytasd a kiadási lépésekkel kizárólag konkrét jóváhagyással. Őrizd meg az ügyféladatokat, a dirty fő workspace-et és a 4 GB-os konténert.”
