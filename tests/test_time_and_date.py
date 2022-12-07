import pytest

import asyncio

from yarp import Value, now

import _datetime


class TestNow(object):
    
    @pytest.fixture
    def interval(self):
        """Interval duration, seconds."""
        return Value(0.1)
    
    @pytest.fixture
    def log(self):
        """An array of (time, value) tuples for each callback from 'now'."""
        return []
    
    @pytest.fixture
    def sem(self):
        """A semaphore released whenever the callback is called."""
        return asyncio.Semaphore(0)
    
    @pytest.fixture
    def t(self, interval, log, sem, event_loop):
        """'Now' value."""
        t = now(interval, loop=event_loop)
        
        @t.on_value_changed
        def on_change(value):
            log.append((event_loop.time(), value))
            sem.release()
        
        return t
    
    @pytest.mark.asyncio
    async def test_initial_value(self, t):
        # Initial value should be current time (or near enough...)
        assert abs((t.value - _datetime.datetime.now()).total_seconds()) < 0.05
    
    @pytest.mark.asyncio
    async def test_regular_interval(self, t, sem, log):
        await sem.acquire()
        await sem.acquire()
        await sem.acquire()
        assert len(log) == 3
        
        cb_deltas = [b - a for (a, _), (b, _) in zip(log, log[1:])]
        t_deltas = [(b - a).total_seconds() for (_, a), (_, b) in zip(log, log[1:])]
        
        assert all(0.05 < d < 0.15 for d in cb_deltas)
        assert all(0.05 < t < 0.15 for t in t_deltas)
    
    @pytest.mark.asyncio
    async def test_change_interval(self, t, interval, sem, log):
        await sem.acquire()
        await sem.acquire()
        assert len(log) == 2
        
        await asyncio.sleep(0.05)
        interval.value = 0.2
        
        await sem.acquire()
        await sem.acquire()
        assert len(log) == 4
        
        cb_deltas = [b - a for (a, _), (b, _) in zip(log, log[1:])]
        t_deltas = [(b - a).total_seconds() for (_, a), (_, b) in zip(log, log[1:])]
        
        assert 0.05 < cb_deltas[0] < 0.15
        assert 0.05 < t_deltas[0] < 0.15
        
        # Delay should be from setting 'interval' onward
        assert 0.22 < cb_deltas[1] < 0.28
        assert 0.22 < t_deltas[1] < 0.28
        
        # Subsequent delays should be longer
        assert 0.15 < cb_deltas[2] < 0.25
        assert 0.15 < t_deltas[2] < 0.25
