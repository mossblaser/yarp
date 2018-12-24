import asyncio

from yarp import NoValue, Value, ensure_value

import datetime as _datetime


__names__ = [
    "now",
]


def now(interval=1.0, tz=None, loop=None):
    """
    Returns a continuous :py:class:`Value` containing a
    :py:class:`datetime.datetime` object holding the current time, refreshed
    every ``interval`` seconds.
    
    The ``interval`` argument may be a constant or a :py:class:`Value` giving
    the number of seconds to wait between updates. If the Value changes, the
    time until the next update will be reset starting from that moment in time.
    
    The ``tz`` argument is passed on to :py:func:`datetime.datetime.now`. This
    must be a constant.
    
    The ``loop`` argument should be an :py:class:`asyncio.BaseEventLoop` in
    which the delays will be scheduled. If ``None``, the default loop is used.
    """
    loop = loop or asyncio.get_event_loop()
    interval = ensure_value(interval)
    
    v = Value()
    timer_handle = None
    next_update_time = loop.time()
    
    def update_time():
        nonlocal next_update_time, timer_handle
        
        v.value = _datetime.datetime.now(tz)
        next_update_time += interval.value
        timer_handle = loop.call_at(next_update_time, update_time)
    update_time()
    
    @interval.on_value_changed
    def on_interval_changed(new_interval):
        nonlocal next_update_time, timer_handle
        
        if timer_handle is not None:
            timer_handle.cancel()
        next_update_time = loop.time() + interval.value
        timer_handle = loop.call_at(next_update_time, update_time)
    
    return v
