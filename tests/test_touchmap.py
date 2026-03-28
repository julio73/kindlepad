"""Tests for TouchMap and TouchZone."""

from server.touchmap import TouchMap, TouchZone


class TestResolveHit:
    def test_resolve_hit(self):
        """A point inside a zone should resolve to that zone."""
        tm = TouchMap()
        zone = TouchZone(x=10, y=10, width=100, height=100, action="toggle")
        tm.add(zone)

        result = tm.resolve(50, 50)
        assert result is zone

    def test_resolve_hit_params(self):
        """Resolved zone should carry its params."""
        tm = TouchMap()
        zone = TouchZone(x=0, y=0, width=200, height=200, action="set_on", params={"id": "abc"})
        tm.add(zone)

        result = tm.resolve(100, 100)
        assert result is not None
        assert result.params == {"id": "abc"}


class TestResolveMiss:
    def test_resolve_miss(self):
        """A point outside all zones returns None."""
        tm = TouchMap()
        zone = TouchZone(x=10, y=10, width=100, height=100, action="toggle")
        tm.add(zone)

        assert tm.resolve(500, 500) is None

    def test_resolve_miss_empty(self):
        """Empty TouchMap always returns None."""
        tm = TouchMap()
        assert tm.resolve(0, 0) is None


class TestResolveOverlap:
    def test_resolve_overlap(self):
        """Two overlapping zones — the last one added wins."""
        tm = TouchMap()
        zone_a = TouchZone(x=0, y=0, width=200, height=200, action="first")
        zone_b = TouchZone(x=50, y=50, width=200, height=200, action="second")
        tm.add(zone_a)
        tm.add(zone_b)

        # Point (100, 100) is inside both zones
        result = tm.resolve(100, 100)
        assert result is zone_b
        assert result.action == "second"


class TestResolveEdge:
    def test_resolve_edge_top_left(self):
        """Point exactly on the top-left corner boundary is inside."""
        tm = TouchMap()
        zone = TouchZone(x=10, y=10, width=100, height=100, action="edge")
        tm.add(zone)

        assert tm.resolve(10, 10) is zone

    def test_resolve_edge_bottom_right(self):
        """Point exactly on the bottom-right corner boundary is inside."""
        tm = TouchMap()
        zone = TouchZone(x=10, y=10, width=100, height=100, action="edge")
        tm.add(zone)

        assert tm.resolve(110, 110) is zone
