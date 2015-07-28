import myprofiler
import pytest

def test_SummingCollector():
    collector = myprofiler.SummingCollector()

    assert collector.summary() == []

    collector.append("foo")
    collector.append("bar")
    collector.append("foo")

    assert collector.summary() == [("foo", 2), ("bar", 1)]

    collector.turn()

def test_CappedCollector():
    collector = myprofiler.CappedCollector(3)

    assert collector.summary() == []

    collector.append("foo")
    collector.append("bar")
    collector.turn()
    collector.append("foo")
    collector.turn()

    assert collector.summary() == [("foo", 2), ("bar", 1)]

    collector.turn()

    assert collector.summary() == [("foo", 1)]

    collector.turn()

    assert collector.summary() == []

class DummyProcesslist(object):
    querylist = [
            ["foo"] * 3,
            ["bar"] * 2,
            ["baz"],
            ]

    def __init__(self):
        self.iter = iter(self.querylist)

    def __call__(self, con):
        return next(self.iter)


def test_profile(monkeypatch):
    monkeypatch.setattr(myprofiler, 'processlist', DummyProcesslist())

    summaries = []
    def show_summary(collector, num_summary):
        summaries.append(collector.summary())
    monkeypatch.setattr(myprofiler, 'show_summary', show_summary)

    try:
        myprofiler.profile(None, 1, 0, 0, None)
    except StopIteration:
        pass

    assert len(summaries) == 3
    assert summaries[0] == [('foo', 3)]
    assert summaries[1] == [('foo', 3), ('bar', 2)]
    assert summaries[2] == [('foo', 3), ('bar', 2), ('baz', 1)]

def test_profile_capped(monkeypatch):
    monkeypatch.setattr(myprofiler, 'processlist', DummyProcesslist())

    summaries = []
    def show_summary(collector, num_summary):
        summaries.append(collector.summary())
    monkeypatch.setattr(myprofiler, 'show_summary', show_summary)

    try:
        myprofiler.profile(None, 1, 2, 0, None)
    except StopIteration:
        pass

    assert len(summaries) == 3
    assert summaries[0] == [('foo', 3)]
    assert summaries[1] == [('foo', 3), ('bar', 2)]
    assert summaries[2] == [('bar', 2), ('baz', 1)]

def test_normalize():
    normalize = myprofiler.normalize_query
    assert normalize("IN ('a', 'b', 'c')") == "IN (S, S, S)"
    assert normalize("IN ('a', 'b', 'c', 'd', 'e')") == "IN (...S)"
    assert normalize("IN (1, 2, 3)") == "IN (N, N, N)"
    assert normalize("IN (1, 2, 3, 4, 5)") == "IN (...N)"
