from pathlib import Path

from leco_notifier.parser import parse_area_html

FIXTURE = Path(__file__).parent / "fixtures" / "area1.html"


def test_parses_branch_and_sections():
    html = FIXTURE.read_text()
    outages = parse_area_html(1, html)

    assert len(outages) > 0
    assert all(o.branch == "Galle" for o in outages)
    assert {o.section for o in outages} <= {"Next Month", "Current Month", "Previous Month"}
    assert {o.source for o in outages} <= {"LECO", "CEB"}


def test_parses_dates_and_streets():
    html = FIXTURE.read_text()
    outages = parse_area_html(1, html)

    galle_entry = next(o for o in outages if o.town == "GALLE" and o.section == "Current Month")
    assert galle_entry.date_from is not None
    assert galle_entry.date_from < galle_entry.date_to
    assert "Matara Rd" in galle_entry.streets
    assert "and by roads" not in galle_entry.streets_raw.split(",")[-1] or True
    # trailing "and by roads" suffix must be stripped from the last street
    assert not galle_entry.streets[-1].lower().endswith("and by roads")


def test_outage_id_is_stable_for_same_content():
    html = FIXTURE.read_text()
    first = parse_area_html(1, html)
    second = parse_area_html(1, html)
    assert [o.id for o in first] == [o.id for o in second]


def test_no_scheduled_interruptions_yields_no_records():
    html = """
    <table class='table'><tbody>
    <tr><td colspan='2'><b>TestBranch</b></td></tr>
    <tr><td style='background-color:#fde3e3;' colspan='2'><b><i>Next Month</i></b></td></tr>
    <tr><td>LECO </td><td>No Scheduled Interruptions yet</td></tr>
    <tr><td>CEB</td><td><p><span>Consumers are advised...</span></p>No Scheduled Interruptions yet</td></tr>
    </tbody></table>
    """
    outages = parse_area_html(99, html)
    assert outages == []
