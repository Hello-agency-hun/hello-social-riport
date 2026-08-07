"""Gépi azonosítók emberi megnevezése.

A pipeline végig a Meta saját kulcsait használja (`actions:omni_landing_page_view`,
`link_clicks`), mert azok stabilak és visszavezethetők a forrásra. A riportot
viszont az ügyfél olvassa — oda ezek nem kerülhetnek ki nyersen.

Ismeretlen kulcsnál a nyers érték marad. Így ha a Meta új eredménytípust vezet
be, az látható lesz a riportban — csak csúnyán —, nem pedig eltűnik.
"""

PAGE_FIELDS = {
    "hu": {
        "visits": "Felkeresések",
        "follows": "Új követők",
        "interactions": "Interakciók",
        "link_clicks": "Hivatkozáskattintások",
        "views": "Megtekintések",
    },
    "en": {
        "visits": "Profile visits",
        "follows": "New followers",
        "interactions": "Interactions",
        "link_clicks": "Link clicks",
        "views": "Views",
    },
}

RESULT_TYPES = {
    "hu": {
        "reach": "Elérés",
        "actions:omni_landing_page_view": "Érkezésioldal-megtekintés",
        "profile_visit_view": "Profil-felkeresés",
        "actions:post_engagement": "Poszt-interakció",
        "actions:link_click": "Hivatkozáskattintás",
        "actions:click_to_call_native_call_placed": "Telefonhívás",
    },
    "en": {
        "reach": "Reach",
        "actions:omni_landing_page_view": "Landing page view",
        "profile_visit_view": "Profile visit",
        "actions:post_engagement": "Post engagement",
        "actions:link_click": "Link click",
        "actions:click_to_call_native_call_placed": "Phone call",
    },
}

CHANNELS = {
    "facebook": "Facebook",
    "instagram": "Instagram",
}

POST_TYPES = {
    "hu": {"image": "kép", "story": "story", "reel": "reel", "video": "videó"},
    "en": {"image": "image", "story": "story", "reel": "reel", "video": "video"},
}


def _lookup(table: dict, key: str, language: str) -> str:
    """Ismeretlen kulcsnál a nyers érték marad — így ha a Meta új
    eredménytípust vezet be, az látható lesz a riportban, csak csúnyán, nem
    pedig eltűnik."""
    return table.get(language, table["hu"]).get(key, key)


def page_field(key: str, language: str = "hu") -> str:
    return _lookup(PAGE_FIELDS, key, language)


def result_type(key: str, language: str = "hu") -> str:
    return _lookup(RESULT_TYPES, key, language)


def channel(key: str) -> str:
    return CHANNELS.get(key, key)


def post_type(key: str, language: str = "hu") -> str:
    return _lookup(POST_TYPES, key, language)


def shorten(text: str, limit: int) -> str:
    """Rövidítés **szóhatáron**, nem a szó közepén.

    A poszt-szövegeket karakterszámra vágva olyan feliratok születtek, mint
    „Ahogy szereti" vagy „lehet panas" — az ügyfélnek szánt dokumentumban ez
    hanyagságnak látszik.

    Ha a legközelebbi szóhatár túl korán jönne (a limit alatt jóval), inkább a
    kemény vágás marad — egyetlen hosszú szó ne tüntesse el az egész feliratot.
    """
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text

    cut = text[:limit].rstrip()
    space = cut.rfind(" ")
    if space > limit * 0.5:
        cut = cut[:space]
    return cut.rstrip(" ,.;:!?-–—") + "…"
