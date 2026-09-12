"""LECO publishes outage notices per branch region, selected via areaId on the
same page (https://www.leco.lk/powerIntrup_e.php?areaId=N). These are the area
IDs found on the region map on that page; the branch name itself is read back
out of each response rather than hardcoded here.
"""

BASE_URL = "https://www.leco.lk/powerIntrup_e.php"
AREA_IDS = [1, 3, 5, 7, 9, 11, 13]

# The branch name each areaId's page reports itself (via parser.parse_area_html).
# Hardcoded here too so subscribers can be validated against a known branch
# list without having to scrape first. Street names are not unique across
# branches, so matching is always scoped to one branch per subscriber.
BRANCHES = ["Galle", "Kaluthara", "Kelaniya", "Kotte", "Moratuwa", "Negombo", "Nugegoda"]
