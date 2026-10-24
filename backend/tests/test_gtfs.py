import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.gtfs import GtfsData


def test_load_gtfs():
    g = GtfsData()
    g.load()
    assert g.loaded is True
    assert g.error is None
    assert len(g.routes) == 4
    assert len(g.stops) > 0
    assert len(g.shapes) > 0
    assert len(g.trips) > 0


def test_rail_route_ids():
    g = GtfsData()
    g.load()
    assert "E-W-201" in g.rail_route_ids
    assert "S-C-201" in g.rail_route_ids


def test_stop_name():
    g = GtfsData()
    g.load()
    name = g.stop_name(g.stops[0]["stop_id"])
    assert name is not None


def test_active_services():
    g = GtfsData()
    g.load()
    # any date in GTFS calendar range should yield some services or empty but no crash
    sv = g.active_service_ids("20261025")
    assert isinstance(sv, set)
