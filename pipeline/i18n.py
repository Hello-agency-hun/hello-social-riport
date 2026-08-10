"""A riport nyelve.

Minden ügyfélnek szánt szöveg itt van, egy helyen. A sablonokban nincs
szabadszöveg — `{{ t.kulcs }}` áll helyette. Ennek két oka van:

1. **Fordítható.** A nyelvet a `client.yaml` `report.language` mezője dönti el.
   Ha egy sablonban maradna magyar mondat, az angol riportba is bekerülne, és
   ez nem hibaüzenettel derülne ki, hanem az ügyfélnél.
2. **Egy helyen látszik a hangnem.** A riport szövegének következetesnek kell
   lennie; ha tíz fájlban szórva állnak a mondatok, nem az.

A narratíva NEM itt van: azt a nyelvi modell írja a `narrative.json`-be, a
riport nyelvén. Erről a `references/narrative-guide.md` szól.

Új nyelv felvételéhez a `STRINGS` alá kell egy teljes szótár — a
`test_i18n.py` ellenőrzi, hogy egyetlen kulcs se maradjon ki, mert a hiányzó
kulcs csendben a magyar szöveget hozná vissza.
"""

MONTHS = {
    "hu": [
        "január", "február", "március", "április", "május", "június",
        "július", "augusztus", "szeptember", "október", "november", "december",
    ],
    "en": [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ],
}

STRINGS = {
    "hu": {
        # gombok, felület
        "save_to_folder": "Mentés a mappába",
        "save": "Mentés",
        "download_pdf": "Letöltés PDF-ként",
        "comment": "megjegyzés",
        "comment_done": "megjegyzés ✓",
        "saved_tell_claude": "Mentve ✓ — szólj Claude-nak",
        "save_failed": "Nem sikerült — használd a Mentés gombot",
        "comment_prompt": "Megjegyzés ehhez az oldalhoz:",
        "save_picker": "A hónap mappájába, a report_data.json mellé",
        "manual_mark": "kézi adat",
        # címlap
        "cover_eyebrow": "Social media riport",
        "measured_period": "Mért időszak",
        "month_not_closed": "a hónap még nem zárult le",
        "data_until_here": "az adatok eddig a napig tartanak",
        # a hónap számokban
        "overview": "Áttekintés",
        "month_in_numbers": "A hónap számokban",
        "content_published": "kiküldött tartalom",
        "post_reach_total": "poszt-elérés összesen",
        "ad_spend": "hirdetési költés",
        "boosted_vs_organic": "boostolt / organikus elérés",
        "post_reach_note": "A poszt-elérés a hónap posztjainak elérés-összege. "
        "Nem azonos a havi egyedi eléréssel: aki több posztot is látott, itt "
        "többször szerepel.",
        # tartalom
        "what_we_did": "Mit csináltunk",
        "month_content": "A hónap tartalma",
        "stories_by_channel": "Story-k csatornánként:",
        # trendek
        "daily_trend": "Napi alakulás",
        # összehasonlítás
        "change_vs_previous": "Változás az előző hónaphoz",
        "previous_month": "előző hónap",
        "change_of": "változása",
        "in_month": "a hónapban",
        "previous_month_slot": "előző hónap",
        "previous_month_hint": "A múlt havi riportból; vagy másold be a "
        "previous.json-t. Mínusz és százalék is beírható.",
        # csatorna
        "month_performance": "A hónap teljesítménye",
        "highlighted_content": "kiemelt tartalmak",
        "best_performing_posts": "A legjobban teljesítő posztok",
        "biggest_reach_posts": "A legnagyobb elérésű posztok",
        "boosted_posts_of_month": "A hónap támogatott posztjai",
        "resonance": "Rezonancia",
        "among_boosted": "a támogatottak közt",
        "among_organic": "az organikusok közt",
        "no_stable_baseline": "nincs stabil alap",
        "engagement_rate": "Interakciós arány",
        "reach": "Elérés",
        "of_which_paid": "ebből fizetett",
        "paid_reach": "fizetett elérés",
        "spend": "költés",
        "reactions": "Reakció",
        "performance_vs_typical": "Teljesítmény a szokásoshoz képest",
        # módszertan
        "methodology": "Módszertan",
        "methodology_title": "Mi alapján válogattuk ki ezeket a posztokat?",
        "methodology_lead": "Nem elérés szerint — az ugyanis nem a tartalomról szól.",
        "methodology_1_title": "Az elérést a költés dönti el",
        "methodology_1_body": "Amelyik posztra több hirdetési pénz megy, ahhoz "
        "több néző jut el. Ha elérés szerint rangsorolnánk, a lista azt mutatná "
        "meg, mire költöttünk a legtöbbet — nem azt, mi működött.",
        "methodology_2_title": "Ezért azt nézzük, ki reagált",
        "methodology_2_body": "a posztot látó nézők közül hányan reagáltak rá. "
        "A hozzászólás és a megosztás nagyobb súllyal számít, mint egy reakció "
        "— egy lájk egy koppintás, egy megosztás a saját név.",
        "methodology_3_title": "Hasonlót a hasonlóhoz",
        "methodology_3_body": "A hirdetés hidegebb közönséghez is eljut, ami "
        "természetes módon kevesebbet reagál. Ezért a támogatott posztokat a "
        "támogatottakhoz, az organikusakat az organikusakhoz mérjük — a kártyán "
        "ott is áll, melyikről van szó.",
        "methodology_close": "tehát azt jelenti: kétszer annyian reagáltak, mint "
        "egy szokásos posztnál — a saját mezőnyén belül. Mindkét mezőnyből kerül "
        "poszt a listára, hogy a kép ne dőljön el egyik irányba sem.",
        "twofold": "kétszeres",
        "ranking_note": "Azok közül, akik látták, hányan reagáltak — a csatorna "
        "havi mediánjához mérve. Így a hirdetési költés nem torzítja a sorrendet.",
        # fizetett
        "paid_advertising": "Fizetett hirdetés",
        "campaigns_by_result": "Kampányok eredménytípus szerint",
        "result_type": "Eredménytípus",
        "campaign": "Kampány",
        "result": "Eredmény",
        "earlier_posts_note_1": "Ebből",
        "earlier_posts_note_2": "hirdetés korábbi hónapban megjelent bejegyzést "
        "támogatott",
        "earlier_posts_note_3": "A költésük ebben a hónapban merült fel, ezért a "
        "fenti összegben szerepel.",
        "result_types_note": "Az eredménytípusok külön sorokban szerepelnek, mert "
        "mást mérnek — összegük nem értelmezhető.",
        # boost értéke
        "organic_and_paid": "Organikus és fizetett",
        "what_boost_is_worth": "Mennyit ér a boost",
        "avg_organic_reach": "organikus poszt átlagos elérése",
        "avg_boosted_reach": "boostolt poszt átlagos elérése",
        "boosted_posts": "boostolt poszt",
        "with_spend": "költséggel a havi poszt-elérés",
        "share_of": "-át adta.",
        "reach_split_label": "A poszt-elérés megoszlása",
        "boosted_posts_label": "Boostolt posztok",
        "organic_posts_label": "Organikus posztok",
        # narratíva-oldalak
        "executive_summary": "Vezetői összefoglaló",
        "month_in_brief": "A hónap röviden",
        "key_finding": "A hónap kulcsmegállapítása",
        "assessment": "Értékelés",
        "what_worked_title": "Mi működött, min javítsunk",
        "what_worked": "Mi működött",
        "what_to_improve": "Min javítsunk",
        "next_steps": "Következő lépések",
        "next_month": "Mit csinálunk a jövő hónapban",
        # fókusz
        "summary": "Összefoglaló",
        "month_focus": "A hónap fókusza",
        "post_reach": "poszt-elérés",
        "boost_multiplier": "a boost szorzója",
        "follower": "követő",
        "monthly_reach": "havi elérés",
        "times_the_audience": "× a követőtábor",
        "footer_note": "— naptári hónap, elsejétől a hónap utolsó napjáig. Az "
        "adatok forrása a Meta Business Suite és a ZoomSphere hivatalos exportja.",
        "generated_on": "Készült:",
        # zárás
        "lets_talk": "Beszéljünk arról, mi jön ezután.",
        "thanks": "Köszönjük a kíváncsiságot! Maradt még kérdés? Keress minket "
        "nyugodtan!",
        # diagram-feliratok
        "no_data": "nincs adat",
        "peak": "csúcs",
        "total": "összesen",
    },
    "en": {
        "save_to_folder": "Save to folder",
        "save": "Save",
        "download_pdf": "Download as PDF",
        "comment": "comment",
        "comment_done": "comment ✓",
        "saved_tell_claude": "Saved ✓ — let Claude know",
        "save_failed": "Couldn't save — use the Save button",
        "comment_prompt": "Comment on this page:",
        "save_picker": "Into the month folder, next to report_data.json",
        "manual_mark": "entered manually",
        "cover_eyebrow": "Social media report",
        "measured_period": "Period measured",
        "month_not_closed": "the month is not over yet",
        "data_until_here": "the data runs to this date",
        "overview": "Overview",
        "month_in_numbers": "The month in numbers",
        "content_published": "pieces published",
        "post_reach_total": "total post reach",
        "ad_spend": "ad spend",
        "boosted_vs_organic": "boosted / organic reach",
        "post_reach_note": "Total post reach is the sum of this month's posts' "
        "reach. It is not the same as monthly unique reach: someone who saw "
        "several posts is counted here more than once.",
        "what_we_did": "What we did",
        "month_content": "This month's content",
        "stories_by_channel": "Stories by channel:",
        "daily_trend": "Day by day",
        "change_vs_previous": "Change from last month",
        "previous_month": "last month",
        "change_of": "change",
        "in_month": "this month",
        "previous_month_slot": "last month",
        "previous_month_hint": "From last month's report, or drop in "
        "previous.json. Minus signs and percentages are accepted.",
        "month_performance": "This month's performance",
        "highlighted_content": "highlights",
        "best_performing_posts": "Best performing posts",
        "biggest_reach_posts": "Posts with the largest reach",
        "boosted_posts_of_month": "Boosted posts this month",
        "resonance": "Resonance",
        "among_boosted": "among boosted",
        "among_organic": "among organic",
        "no_stable_baseline": "no stable baseline",
        "engagement_rate": "Engagement rate",
        "reach": "Reach",
        "of_which_paid": "of which paid",
        "paid_reach": "paid reach",
        "spend": "spend",
        "reactions": "Reactions",
        "performance_vs_typical": "Performance against the usual",
        "methodology": "Methodology",
        "methodology_title": "How did we pick these posts?",
        "methodology_lead": "Not by reach — reach isn't about the content.",
        "methodology_1_title": "Reach is decided by spend",
        "methodology_1_body": "The more ad money a post gets, the more viewers "
        "it reaches. Ranking by reach would show what we spent the most on — "
        "not what worked.",
        "methodology_2_title": "So we look at who responded",
        "methodology_2_body": "how many of the people who saw the post "
        "responded to it. A comment and a share count for more than a reaction "
        "— a like is one tap, a share puts someone's own name behind it.",
        "methodology_3_title": "Like against like",
        "methodology_3_body": "Advertising also reaches a colder audience, "
        "which naturally responds less. So we measure boosted posts against "
        "boosted ones and organic against organic — each card says which.",
        "methodology_close": "therefore means twice as many people responded as "
        "on a typical post — within its own field. Both fields are represented "
        "in the list, so the picture doesn't tip either way.",
        "twofold": "Twofold",
        "ranking_note": "Of the people who saw it, how many responded — measured "
        "against the channel's monthly median. This keeps ad spend from "
        "distorting the order.",
        "paid_advertising": "Paid advertising",
        "campaigns_by_result": "Campaigns by result type",
        "result_type": "Result type",
        "campaign": "Campaigns",
        "result": "Results",
        "earlier_posts_note_1": "Of these,",
        "earlier_posts_note_2": "ads supported posts published in an earlier "
        "month",
        "earlier_posts_note_3": "The spend fell in this month, so it is included "
        "in the total above.",
        "result_types_note": "Result types are listed separately because they "
        "measure different things — their sum is meaningless.",
        "organic_and_paid": "Organic and paid",
        "what_boost_is_worth": "What boosting is worth",
        "avg_organic_reach": "average reach of an organic post",
        "avg_boosted_reach": "average reach of a boosted post",
        "boosted_posts": "boosted posts",
        "with_spend": "in spend accounted for",
        "share_of": "of this month's post reach.",
        "reach_split_label": "How post reach breaks down",
        "boosted_posts_label": "Boosted posts",
        "organic_posts_label": "Organic posts",
        "executive_summary": "Executive summary",
        "month_in_brief": "The month in brief",
        "key_finding": "Key finding of the month",
        "assessment": "Assessment",
        "what_worked_title": "What worked, what to improve",
        "what_worked": "What worked",
        "what_to_improve": "What to improve",
        "next_steps": "Next steps",
        "next_month": "What we'll do next month",
        "summary": "Summary",
        "month_focus": "The month in focus",
        "post_reach": "post reach",
        "boost_multiplier": "the boost multiplier",
        "follower": "followers",
        "monthly_reach": "monthly reach",
        "times_the_audience": "× the follower base",
        "footer_note": "— a calendar month, from the first to the last day. The "
        "data comes from the official Meta Business Suite and ZoomSphere exports.",
        "generated_on": "Generated:",
        "lets_talk": "Let's talk about what comes next.",
        "thanks": "Thank you for your interest! Any questions left? Do get in "
        "touch.",
        "no_data": "no data",
        "peak": "peak",
        "total": "total",
    },
}

DEFAULT = "hu"

# Amit a böngészőben futó JavaScript használ. Csak ez a nyolc kulcs kerül a
# lapra: az egész szótár beinjektálása fölösleges szöveget vinne a riportba, és
# egy „nincs narratíva" ellenőrzés is elbukna rajta, mert a narratíva-oldalak
# feliratai ott lennének a forrásban akkor is, ha az oldalak nincsenek.
UI_KEYS = (
    "save",
    "save_to_folder",
    "saved_tell_claude",
    "save_failed",
    "save_picker",
    "comment",
    "comment_done",
    "comment_prompt",
)


def ui(language: str | None) -> dict:
    table = strings(language)
    return {key: table[key] for key in UI_KEYS}


class Strings(dict):
    """Szótár, ami hiányzó kulcsnál MEGÁLL, nem csendben üreset ad.

    Egy elgépelt kulcs a sablonban üres helyet hagyna a riportban, és ez csak
    az ügyfélnél derülne ki.
    """

    def __getattr__(self, key: str) -> str:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"nincs ilyen riportszöveg: {key!r}") from None


def strings(language: str | None) -> Strings:
    return Strings(STRINGS.get(language or DEFAULT, STRINGS[DEFAULT]))


def months(language: str | None) -> list[str]:
    return MONTHS.get(language or DEFAULT, MONTHS[DEFAULT])
