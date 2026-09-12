import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s*([AP]M)", re.IGNORECASE)
SECTION_RE = re.compile(r"(next|current|previous)\s+month", re.IGNORECASE)
TRAILING_ROADS_RE = re.compile(r"\s*and by roads\.?\s*$", re.IGNORECASE)


@dataclass
class Outage:
    area_id: int
    branch: Optional[str]
    section: Optional[str]
    source: str
    town: str
    date_from_raw: str
    date_to_raw: str
    date_from: Optional[datetime]
    date_to: Optional[datetime]
    streets: list = field(default_factory=list)
    streets_raw: str = ""
    id: str = ""

    def __post_init__(self):
        if not self.id:
            key = "|".join(
                [
                    str(self.area_id),
                    self.source,
                    self.town,
                    self.date_from_raw,
                    self.date_to_raw,
                    self.streets_raw,
                ]
            )
            self.id = hashlib.sha1(key.encode("utf-8")).hexdigest()


def _parse_leco_date(raw: str) -> Optional[datetime]:
    m = DATE_RE.search(raw)
    if not m:
        return None
    ymd, hm, ampm = m.groups()
    year, month, day = (int(x) for x in ymd.split("-"))
    hour, minute = (int(x) for x in hm.split(":"))
    ampm = ampm.upper()
    if ampm == "PM" and hour != 12:
        hour += 12
    if ampm == "AM" and hour == 12:
        hour = 0
    return datetime(year, month, day, hour, minute)


def _clean_street_list(text: str) -> list:
    text = TRAILING_ROADS_RE.sub("", text)
    return [s.strip() for s in text.split(",") if s.strip()]


def parse_area_html(area_id: int, html: str) -> list:
    # lxml's HTML parser auto-closes unclosed <p> tags per the HTML spec,
    # which LECO's markup relies on to delimit town/date/street paragraphs.
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.table")
    if table is None:
        return []

    outages = []
    branch = None
    section = None

    for tr in table.find_all("tr"):
        tds = tr.find_all("td", recursive=False)

        if len(tds) == 1:
            header_text = tds[0].get_text(" ", strip=True)
            section_match = SECTION_RE.search(header_text)
            if section_match:
                word = section_match.group(1).lower()
                section = f"{word.capitalize()} Month"
            elif header_text:
                branch = header_text
            continue

        if len(tds) != 2:
            continue

        source_label = tds[0].get_text(" ", strip=True).upper()
        if source_label not in ("LECO", "CEB"):
            continue

        cell = tds[1]
        current_town = None
        current_date_from_raw = None
        current_date_to_raw = None

        for p in cell.find_all("p", recursive=False):
            text = p.get_text(" ", strip=True)
            if not text:
                continue
            if "consumers are advised" in text.lower():
                continue  # CEB boilerplate intro paragraph

            bolds = p.find_all("b")
            italics = p.find_all("i")
            is_town_header = (
                len(bolds) == 1 and len(italics) == 0 and text == bolds[0].get_text(" ", strip=True)
            )
            if is_town_header:
                current_town = text
                current_date_from_raw = None
                current_date_to_raw = None
                continue

            if len(italics) >= 2 and re.search(r"\bto\b", text, re.IGNORECASE):
                current_date_from_raw = italics[0].get_text(" ", strip=True)
                current_date_to_raw = italics[1].get_text(" ", strip=True)
                continue

            if "no scheduled interruptions" in text.lower():
                continue

            if not current_town or not current_date_from_raw or not current_date_to_raw:
                continue

            outages.append(
                Outage(
                    area_id=area_id,
                    branch=branch,
                    section=section,
                    source=source_label,
                    town=current_town,
                    date_from_raw=current_date_from_raw,
                    date_to_raw=current_date_to_raw,
                    date_from=_parse_leco_date(current_date_from_raw),
                    date_to=_parse_leco_date(current_date_to_raw),
                    streets=_clean_street_list(text),
                    streets_raw=text,
                )
            )

    return outages


def parse_all_areas(pages) -> list:
    outages = []
    for area_id, html in pages:
        outages.extend(parse_area_html(area_id, html))
    return outages
