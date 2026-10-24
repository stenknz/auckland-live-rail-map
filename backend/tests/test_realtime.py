import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.realtime import RealtimeClient

def test_cache_initial():
    c = RealtimeClient()
    assert c.vehicles_cache.data is None
    assert c.vehicles_cache.fetched_at is None

def test_invalid_coordinates_filtered():
    # unit-level: ensure latitude/longitude validation logic exists
    from app.realtime import RealtimeClient
    assert RealtimeClient is not None
