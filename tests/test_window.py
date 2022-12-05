import pytest
from mock import Mock

import asyncio
import time

from yarp import NoValue, Value, window, time_window

def test_window():
    v = Value(1)
    ws = Value(3)
    
    win = window(v, ws)
    
    # Should start with the current value
    assert win.value == [1]
    
    # Values should accumulate
    v.value = 2
    assert win.value == [1, 2]
    
    v.value = 3
    assert win.value == [1, 2, 3]
    
    # Should truncate to only most recent values
    v.value = 4
    assert win.value == [2, 3, 4]
    
    # Increasing the window size should be possible
    ws.value = 4
    v.value = 5
    assert win.value == [2, 3, 4, 5]
    v.value = 6
    assert win.value == [3, 4, 5, 6]
    
    # Decreasing it should be too
    ws.value = 2
    assert win.value == [5, 6]
    v.value = 7
    assert win.value == [6, 7]

class TestTimeWindow(object):
    
    @pytest.fixture
    def v(self):
        """A Value."""
        return Value(1)
    
    @pytest.fixture
    def dv(self):
        """A window delay Value."""
        return Value(0.1)
    
    @pytest.fixture
    def log(self):
        """
        A log of (time, value) pairs for all callbacks from 'win' being changed.
        """
        return []
    
    @pytest.fixture
    def sem(self):
        """
        A semaphore released whenever the 'win' value changes.
        """
        return asyncio.Semaphore(0)
    
    @pytest.fixture
    def win(self, v, dv, sem, log, event_loop):
        """
        A time_window windowing the value 'v' for 'dv' seconds. Callbacks on change
        are logged in 'log'.
        """
        win = time_window(v, dv, loop=event_loop)
        
        def on_change(value):
            log.append((time.time(), value))
            sem.release()
        win.on_value_changed(on_change)
        
        return win
    
    
    @pytest.mark.asyncio
    async def test_initial_value(self, v, dv, win, sem, log):
        start = time.time()
        
        # Should start with the current value
        assert win.value == [1]
        
        # current value should persist after delay
        await asyncio.sleep(0.15)
        assert sem.locked()
    
    @pytest.mark.asyncio
    async def test_adding_values(self, v, dv, win, sem, log):
        # Adding values should appear immediately and disappear later
        start = time.time()
        v.value = 2
        v.value = 3
        assert win.value == [1, 2, 3]
        assert len(log) == 2
        await sem.acquire()
        await sem.acquire()
        await sem.acquire()  # Expirations
        await sem.acquire()
        assert win.value == [3]
        assert len(log) == 4
        assert log[-2][0] - start >= 0.1
        assert log[-1][0] - start >= 0.1
        assert log[-2][1] == [2, 3]
        assert log[-1][1] == [3]
        
    @pytest.mark.asyncio
    async def test_adding_values_spaced(self, v, dv, win, sem, log):
        # Adding values spaced appart should disappear spaced appart
        first = time.time()
        v.value = 4
        assert win.value == [1, 4]
        assert len(log) == 1
        await asyncio.sleep(0.05)
        
        second = time.time()
        v.value = 5
        assert win.value == [1, 4, 5]
        assert len(log) == 2
        
        await sem.acquire()  # Initial settings
        await sem.acquire()
        await sem.acquire()  # Expirations
        await sem.acquire()
        
        assert win.value == [5]
        assert len(log) == 4
        assert log[-2][0] - first >= 0.1
        assert log[-1][0] - second >= 0.1
        assert log[-2][1] == [4, 5]
        assert log[-1][1] == [5]
    
    @pytest.mark.asyncio
    async def test_increase_timeout(self, v, dv, win, sem, log):
        # Insert a couple of values
        start = time.time()
        v.value = 6
        v.value = 7
        await sem.acquire()
        await sem.acquire()
        assert win.value == [1, 6, 7]
        assert len(log) == 2
        assert log[-2][1] == [1, 6]
        assert log[-1][1] == [1, 6, 7]
        
        # Increasing the timeout should keep the values for longer
        dv.value = 0.15
        await sem.acquire()
        await sem.acquire()
        assert len(log) == 4
        assert log[-2][0] - start >= 0.15
        assert log[-1][0] - start >= 0.15
        assert log[-2][1] == [6, 7]
        assert log[-1][1] == [7]
        assert win.value == [7]
    
    @pytest.mark.asyncio
    async def test_decrease_timeout(self, v, dv, win, sem, log):
        # Insert a couple more values
        start = time.time()
        v.value = 8
        v.value = 9
        await sem.acquire()
        await sem.acquire()
        assert win.value == [1, 8, 9]
        assert len(log) == 2
        assert log[-2][1] == [1, 8]
        assert log[-1][1] == [1, 8, 9]
        
        # Decreasing the timeout should make the values come out earlier
        dv.value = 0.1
        await sem.acquire()
        await sem.acquire()
        assert len(log) == 4
        assert log[-2][0] - start >= 0.1 and log[-2][0] - start < 0.15
        assert log[-1][0] - start >= 0.1 and log[-1][0] - start < 0.15
        assert log[-2][1] == [8, 9]
        assert log[-1][1] == [9]
        assert win.value == [9]
    
    @pytest.mark.asyncio
    async def test_decrease_timeout_lots(self, v, dv, win, sem, log):
        # Insert a few more values
        start = time.time()
        v.value = 10
        v.value = 11
        await sem.acquire()
        await sem.acquire()
        assert win.value == [1, 10, 11]
        assert len(log) == 2
        assert log[-2][1] == [1, 10]
        assert log[-1][1] == [1, 10, 11]
        
        await asyncio.sleep(0.05)
        assert win.value == [1, 10, 11]
        
        # Decreasing the timeout so that the previously inserted items should have
        # been expired should make them come out immediately.
        dv.value = 0.05
        assert win.value == [11]
        await sem.acquire()
        await sem.acquire()
        assert len(log) == 4
        assert log[-2][1] == [10, 11]
        assert log[-1][1] == [11]
