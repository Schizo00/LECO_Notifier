"""LECO publishes outage notices per branch region, selected via areaId on the
same page (https://www.leco.lk/powerIntrup_e.php?areaId=N). These are the area
IDs found on the region map on that page; the branch name itself is read back
out of each response rather than hardcoded here.
"""

BASE_URL = "https://www.leco.lk/powerIntrup_e.php"
AREA_IDS = [1, 3, 5, 7, 9, 11, 13]
