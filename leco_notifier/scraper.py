import logging

import requests

from .areas import AREA_IDS, BASE_URL

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

logger = logging.getLogger(__name__)


def fetch_area(area_id: int, timeout: int = 20) -> str:
    resp = requests.get(
        BASE_URL,
        params={"areaId": area_id},
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.text


def fetch_all_areas() -> list[tuple[int, str]]:
    pages = []
    for area_id in AREA_IDS:
        try:
            html = fetch_area(area_id)
            pages.append((area_id, html))
        except requests.RequestException as exc:
            logger.error("Failed to fetch areaId=%s: %s", area_id, exc)
    return pages
