class PipelineError(Exception):
    """A pipeline minden saját hibájának őse."""


class UnknownSourceError(PipelineError):
    """Nem azonosítható bemeneti fájl."""


class WrongFormatError(PipelineError):
    """A fájl tartalma jó lehet, csak nem a várt formátumban van."""


class DuplicateSourceError(PipelineError):
    """Egy hónaphoz két azonos típusú forrásfájl került."""


class MissingConfigError(PipelineError):
    """Nincs `client.yaml` az ügyfél mappájában."""


class FixtureAsClientError(PipelineError):
    """Valaki a teszt-fixture-ből próbál éles riportot készíteni."""


class NoSourceError(PipelineError):
    """A hónap mappájában egyetlen felismerhető forrásfájl sincs."""


class MissingColumnError(PipelineError):
    """Kötelező oszlop hiányzik egy forrásból."""


class PeriodMismatchError(PipelineError):
    """Egy forrás időszaka nem a riportált hónapra esik."""


class ClientMismatchError(PipelineError):
    """Egy forrás más ügyfélhez tartozik."""


class ReachSummationError(PipelineError):
    """Reach-jellegű metrika összegzése tilos — nem additív."""


class ResultTypeMixError(PipelineError):
    """Eltérő eredménytípusú kampányok összeadása tilos."""


class UnmatchedBoostError(PipelineError):
    """Boostolt poszt nem illeszthető egyetlen tartalomhoz sem."""


class NarrativeError(PipelineError):
    """A narratíva szövege leírt számot tartalmaz, vagy nem létező mezőre hivatkozik."""
