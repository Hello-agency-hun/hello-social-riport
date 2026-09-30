"""Export values with explicit errors instead of silently fabricated zeroes."""

from datetime import datetime
from decimal import Decimal, InvalidOperation
import re

from pipeline.errors import PipelineError


def number(value, *, integer=False, label="szám"):
    text = str(value or "").strip()
    if text in ("", "—", "–", "-", "N/A"):
        return 0 if integer else 0.0
    text = re.sub(r"[\s\u00a0\u202f]", "", text)
    if "," in text and "." in text:
        decimal = "," if text.rfind(",") > text.rfind(".") else "."
        group = "." if decimal == "," else ","
        text = text.replace(group, "").replace(decimal, ".")
    elif integer and re.fullmatch(r"[+-]?\d{1,3}(?:[.,]\d{3})+", text):
        text = text.replace(",", "").replace(".", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        result = Decimal(text)
        if not result.is_finite() or (integer and (result < 0 or result != result.to_integral_value())):
            raise InvalidOperation
    except InvalidOperation as error:
        raise PipelineError(f"{label}: nem értelmezhető {'egész ' if integer else ''}szám — {value!r}.") from error
    return int(result) if integer else float(result)


def export_day(value, *, label="dátum"):
    text = str(value or "").strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for pattern in ("%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y", "%Y.%m.%d", "%Y.%m.%d."):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            pass
    raise PipelineError(f"{label}: nem értelmezhető dátum — {value!r}.")
