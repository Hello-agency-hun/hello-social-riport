"""Gépi azonosítók emberi megnevezése.

A pipeline végig a Meta saját kulcsait használja (`actions:omni_landing_page_view`,
`link_clicks`), mert azok stabilak és visszavezethetők a forrásra. A riportot
viszont az ügyfél olvassa — oda ezek nem kerülhetnek ki nyersen.

Ismeretlen kulcsnál a nyers érték marad. Így ha a Meta új eredménytípust vezet
be, az látható lesz a riportban — csak csúnyán —, nem pedig eltűnik.
"""

PAGE_FIELDS = {
    "visits": "Felkeresések",
    "follows": "Új követők",
    "interactions": "Interakciók",
    "link_clicks": "Hivatkozáskattintások",
    "views": "Megtekintések",
}

RESULT_TYPES = {
    "reach": "Elérés",
    "actions:omni_landing_page_view": "Érkezésioldal-megtekintés",
    "profile_visit_view": "Profil-felkeresés",
    "actions:post_engagement": "Poszt-interakció",
    "actions:link_click": "Hivatkozáskattintás",
    "actions:click_to_call_native_call_placed": "Telefonhívás",
}

CHANNELS = {
    "facebook": "Facebook",
    "instagram": "Instagram",
}

POST_TYPES = {
    "image": "kép",
    "story": "story",
    "reel": "reel",
}


def page_field(key: str) -> str:
    return PAGE_FIELDS.get(key, key)


def result_type(key: str) -> str:
    return RESULT_TYPES.get(key, key)


def channel(key: str) -> str:
    return CHANNELS.get(key, key)


def post_type(key: str) -> str:
    return POST_TYPES.get(key, key)


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
