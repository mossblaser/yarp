import pytest
import asyncio
import time

from mock import Mock

from yarp import NoValue, Value, delay

class TestDelayPersistent(object):
    
    @pytest.fixture
    def v(self):
        """Value, pre-delay."""
        return Value(123)
    
    @pytest.fixture
    def dt(self):
        """Delay duration, seconds."""
        return Value(0.1)
    
    @pytest.fixture
    def log(self):
        """An array of (time, value) tuples for each callback from 'delay'."""
        return []
    
    @pytest.fixture
    def sem(self, event_loop):
        """A semaphore released whenever the callback is called."""
        return asyncio.Semaphore(0, loop=event_loop)
    
    @pytest.fixture
    def dv(self, v, dt, log, sem, event_loop):
        """Delayed value"""
        dv = delay(v, dt, loop=event_loop)
        
        def on_change(value):
            log.append((event_loop.time(), value))
            sem.release()
        dv.on_value_changed(on_change)
        
        return dv
    
    @pytest.mark.asyncio
    async def test_initial_value(self, dv):
        # Initial value should pass through immediately
        assert dv.value == 123
    
    @pytest.mark.asyncio
    async def test_single_change(self, v, dv, sem, log, event_loop):
        # Trigger a change for later...
        before = event_loop.time()
        v.value = 321
        assert dv.value == 123
        assert len(log) == 0
        await sem.acquire()
        assert len(log) == 1
        assert log[-1][0] - before >= 0.1
        assert log[-1][1] == 321
        assert dv.value == 321
    
    @pytest.mark.asyncio
    async def test_rapid_changes(self, v, dv, sem, log, event_loop):
        # Trigger a sequence of rapid changes
        before = event_loop.time()
        v.value = 1234
        v.value = 12345
        v.value = 123456
        assert dv.value == 123
        assert len(log) == 0
        await sem.acquire()
        await sem.acquire()
        await sem.acquire()
        assert len(log) == 3
        assert log[-3][0] - before >= 0.1
        assert log[-2][0] - before >= 0.1
        assert log[-1][0] - before >= 0.1
        assert log[-3][1] == 1234
        assert log[-2][1] == 12345
        assert log[-1][1] == 123456
        assert dv.value == 123456
    
    @pytest.mark.asyncio
    async def test_delay_increase(self, v, dv, dt, sem, log, event_loop):
        before = event_loop.time()
        v.value = 321
        
        # Changing the delay after a value change has occurred should push that
        # change further into the past, but only relative to its original start
        # time
        await asyncio.sleep(0.05, loop=event_loop)
        dt.value = 0.2
        
        await sem.acquire()
        assert len(log) == 1
        assert log[-1][0] - before >= 0.2
        assert dv.value == 321
    
    @pytest.mark.asyncio
    async def test_delay_decrease(self, v, dv, dt, sem, log, event_loop):
        before = event_loop.time()
        v.value = 321
        
        # Changing the delay after a value change has occurred should push that
        # delay closer
        await asyncio.sleep(0.025, loop=event_loop)
        dt.value = 0.05
        
        await sem.acquire()
        assert len(log) == 1
        assert 0.05 <= log[-1][0] - before < 0.10
        assert dv.value == 321
    
    @pytest.mark.asyncio
    async def test_delay_decrease_lots(self, v, dv, dt, sem, log, event_loop):
        before = event_loop.time()
        v.value = 321
        
        # Changing the delay such that a still-delayed value should have been
        # output already should cause that value to be output immediately
        await asyncio.sleep(0.05, loop=event_loop)
        dt.value = 0.01
        
        assert len(log) == 1
        assert log[-1][0] - before >= 0.05
        assert log[-1][1] == 321
        assert dv.value == 321

class TestDelayInstantaneous(object):

    @pytest.mark.asyncio
    async def test_instantaneous(self, event_loop):
        value = Value()
        
        delayed_value = delay(value, 0.1, loop=event_loop)
        assert delayed_value.value is NoValue
        
        # Monitor changes
        evt = asyncio.Event(loop=event_loop)
        m = Mock(side_effect=lambda *_: evt.set())
        delayed_value.on_value_changed(m)
        
        # Trigger a change for later...
        before = time.time()
        value.set_instantaneous_value(123)
        assert delayed_value.value is NoValue
        assert not m.mock_calls
        await evt.wait()
        assert time.time() - before >= 0.1
        m.assert_called_once_with(123)
        assert delayed_value.value is NoValue
    
