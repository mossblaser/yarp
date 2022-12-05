import pytest
import asyncio
import time

from mock import Mock

from yarp import NoValue, Value, rate_limit

@pytest.mark.asyncio
async def test_rate_limit_persistent():
    v = Value(1)
    
    # Initial value should be passed through
    rlv = rate_limit(v, 0.1)
    assert rlv.value == 1
    
    log = []
    sem = asyncio.Semaphore(0)
    def on_change(new_value):
        log.append(new_value)
        sem.release()
    rlv.on_value_changed(on_change)
    
    # Change should not make it through yet
    v.value = 2
    assert rlv.value == 1
    assert len(log) == 0
    
    # Change should come through after a delay
    before = time.time()
    await sem.acquire()
    assert time.time() - before >= 0.1
    assert rlv.value == 2
    assert len(log) == 1
    assert log[-1] == 2
    
    # After a suitable delay, the next change should come through immediately
    await asyncio.sleep(0.15)
    v.value = 3
    assert rlv.value == 3
    assert len(log) == 2
    assert log[-1] == 3
    await sem.acquire()
    
    # A rapid succession of calls should result in only the last value
    # comming out, and then only after a delay
    v.value = 4
    v.value = 5
    v.value = 6
    assert rlv.value == 3
    assert len(log) == 2
    before = time.time()
    await sem.acquire()
    assert time.time() - before >= 0.1
    assert rlv.value == 6
    assert len(log) == 3
    assert log[-1] == 6

@pytest.mark.asyncio
async def test_rate_limit_instantaneous():
    v = Value()
    
    # No initial value to speak of
    rlv = rate_limit(v, 0.1)
    assert rlv.value is NoValue
    
    log = []
    sem = asyncio.Semaphore(0)
    def on_change(new_value):
        log.append(new_value)
        sem.release()
    rlv.on_value_changed(on_change)
    
    # First change should make it through immediately
    v.set_instantaneous_value(1)
    assert rlv.value is NoValue
    assert len(log) == 1
    assert log[-1] == 1
    await sem.acquire()
    
    # Another change made immediately after should be delayed
    v.set_instantaneous_value(2)
    assert rlv.value is NoValue
    assert len(log) == 1
    
    # Change should come through after a delay
    before = time.time()
    await sem.acquire()
    assert time.time() - before >= 0.1
    assert rlv.value is NoValue
    assert len(log) == 2
    assert log[-1] == 2
    
    # After a suitable delay, the next change should come through immediately
    await asyncio.sleep(0.15)
    v.set_instantaneous_value(3)
    assert rlv.value is NoValue
    assert len(log) == 3
    assert log[-1] == 3
    await sem.acquire()
    
    # A rapid succession of calls should result in only the last value
    # comming out, and then only after a delay
    v.set_instantaneous_value(4)
    v.set_instantaneous_value(5)
    v.set_instantaneous_value(6)
    assert rlv.value is NoValue
    assert len(log) == 3
    before = time.time()
    await sem.acquire()
    assert time.time() - before >= 0.1
    assert rlv.value is NoValue
    assert len(log) == 4
    assert log[-1] == 6

@pytest.mark.asyncio
async def test_rate_limit_min_interval_change():
    v = Value(123)
    mi = Value(0.1)
    
    start = time.time()
    rlv = rate_limit(v, mi)
    
    log = []
    sem = asyncio.Semaphore(0)
    def on_change(new_value):
        log.append(new_value)
        sem.release()
    rlv.on_value_changed(on_change)
    
    # The initial value will have blocked changes for 0.1 seconds, increase
    # this to 0.15 seconds and ensure it takes place
    v.value = 321
    mi.value = 0.15
    assert rlv.value == 123
    await sem.acquire()
    assert time.time() - start >= 0.15
    assert rlv.value == 321
    assert len(log) == 1
    assert log[-1] == 321
    
    # Should be able to shorten the blocking period, too
    start = time.time()
    v.value = 1234
    mi.value = 0.1
    assert rlv.value == 321
    await sem.acquire()
    assert 0.1 <= time.time() - start < 0.125
    assert rlv.value == 1234
    assert len(log) == 2
    assert log[-1] == 1234
    
    # Also, should be able to shorten the blocking period to shorter than has
    # already ellapsed and the value should emmerge immediately
    v.value = 4321
    assert rlv.value == 1234
    await asyncio.sleep(0.05)
    assert rlv.value == 1234
    mi.value = 0.025
    assert rlv.value == 4321
    assert len(log) == 3
    assert log[-1] == 4321
    await sem.acquire()
    
    # If we ensure blocking is not occurring, changing the time shouldn't cause
    # problems
    await asyncio.sleep(0.05)
    mi.value = 0.1
    v.value = 12345
    assert rlv.value == 12345
    await sem.acquire()
    v.value = 54321
    start = time.time()
    assert rlv.value == 12345
    await sem.acquire()
    assert rlv.value == 54321
    assert time.time() - start >= 0.1
