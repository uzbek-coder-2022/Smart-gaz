"""Address normalization: produce a stable household_key so the same address
written differently still resolves to the same household (section 5.1 of TT)."""
from __future__ import annotations

import re
import unicodedata


_APOSTROPHES = "‘’ʻʼ`´'ʻ"
_MULTISPACE = re.compile(r"\s+")
_STREET_TYPES = [
    "kucha", "ko'cha", "ko‘cha", "koʻcha", "kocha",
    "street", "str", "st", "proezd", "tor", "mfy",
    "mikrorayon", "mkr", "massiv", "mahalla",
    "uy", "dom", "kvartira", "kv",
]


def _normalize_apostrophes(s: str) -> str:
    for a in _APOSTROPHES:
        s = s.replace(a, "'")
    return s


def normalize_address_component(s: str) -> str:
    """Lowercase, strip diacritics that shouldn't matter, fold apostrophes, collapse whitespace."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s)).strip().lower()
    s = _normalize_apostrophes(s)
    # remove punctuation except apostrophes
    s = re.sub(r"[^a-z0-9' ]+", "", s)
    # collapse apostrophes at word edges and duplicates
    s = re.sub(r"'+", "'", s)
    s = s.strip("'")
    s = _MULTISPACE.sub(" ", s).strip()
    return s


def normalize_phone(phone: str) -> str:
    """Normalize phone to +998XXXXXXXXX."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("998") and len(digits) == 12:
        return "+" + digits
    if digits.startswith("8") and len(digits) == 11 and digits[1] == "9":
        return "+998" + digits[2:]
    if digits.startswith("9989") and len(digits) == 12:
        return "+" + digits
    return "+" + digits[-12:] if len(digits) >= 9 else phone


def make_household_key(region_id: int, district_id: int, mahalla_id: int, street: str, house_number: str, apartment: str | None = None) -> str:
    parts = [str(region_id), str(district_id), str(mahalla_id)]
    parts.append(normalize_address_component(street))
    parts.append(normalize_address_component(house_number))
    if apartment:
        parts.append(normalize_address_component(apartment))
    return "|".join(parts)
