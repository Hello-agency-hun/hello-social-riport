from dataclasses import dataclass, field
from datetime import date


@dataclass
class Campaign:
    """Egy Meta Ads kampánysor."""

    name: str
    spend: float = 0.0
    currency: str = "EUR"
    reach: int = 0
    impressions: int = 0
    frequency: float = 0.0
    link_clicks: int = 0
    results: int = 0
    result_type: str = ""
    cost_per_result: float = 0.0
    status: str = ""
    channel: str | None = None
    is_boost: bool = False


@dataclass
class ContentItem:
    """Egy ZoomSphere sor — amit kiküldtünk."""

    published: date
    post_type: str
    captions: dict[str, str] = field(default_factory=dict)
    post_ids: dict[str, str] = field(default_factory=dict)
    permalinks: dict[str, str] = field(default_factory=dict)
    creatives: dict[str, list[str]] = field(default_factory=dict)

    def caption(self, channel: str) -> str:
        return self.captions.get(channel, "")


@dataclass
class Post:
    """A join eredménye: tartalom + organic teljesítmény + fizetett háttér."""

    channel: str
    post_id: str
    published: date
    caption: str = ""
    permalink: str = ""
    post_type: str = ""
    creatives: list[str] = field(default_factory=list)
    reach: int = 0
    views: int = 0
    reactions: int = 0
    comments: int = 0
    shares: int = 0
    clicks: int = 0
    link_clicks: int = 0
    paid: Campaign | None = None

    @property
    def is_boosted(self) -> bool:
        return self.paid is not None


@dataclass
class DailySeries:
    channel: str
    field: str
    metric: str
    points: list[tuple[date, int]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(value for _, value in self.points)


@dataclass
class ParsedSource:
    """Amit minden parser visszaad — így a build egységesen kezelheti őket."""

    kind: str
    period: tuple[date, date] | None = None
    client_hints: dict[str, str] = field(default_factory=dict)
    payload: object = None
