"""
Temporal filters for :py:class:`Value` values.
"""

import asyncio

from yarp import NoValue, Value, ensure_value

__names__ = [
    "delay",
    "time_window",
    "rate_limit",
]

def delay(source_value, delay_seconds, loop=None):
    """
    Produce a time-delayed version of a :py:class:`Value`.
    
    Supports both instantaneous and continous :py:class:`Values`. For
    continuous :py:class:`Value`\ s, the initial value is set immediately.
    
    The ``delay_seconds`` argument may be a constant or a Value giving the
    number of seconds to delay value changes. If it is increased, previously
    delayed values will be delayed further. If it is decreased, values which
    should already have been output will be output rapidly one after another.
    
    The ``loop`` argument should be an :py:class:`asyncio.BaseEventLoop` in
    which the delays will be scheduled. If ``None``, the default loop is used.
    """
    
    source_value = ensure_value(source_value)
    delay_seconds = ensure_value(delay_seconds)
    output_value = Value(source_value.value)
    
    # An array of (insertion_time, value, instantaneous_value, handle)
    # tuples for values due to be sent.
    timers = []
    
    loop = loop or asyncio.get_event_loop()
    
    def pop_value():
        """Internal. Outputs a previously delayed value."""
        insertion_time, value, instantaneous_value, handle = timers.pop(0)
        output_value._value = value
        output_value.set_instantaneous_value(instantaneous_value)
    
    @source_value.on_value_changed
    def on_source_value_changed(instantaneous_value):
        """Internal. Schedule an incoming value to be output later."""
        insertion_time = loop.time()
        handle = loop.call_at(insertion_time + delay_seconds.value,
                              pop_value)
        timers.append((insertion_time, source_value.value, instantaneous_value, handle))
    
    @delay_seconds.on_value_changed
    def on_delay_seconds_changed(new_delay_seconds):
        """Internal. Handle the delay changing."""
        nonlocal timers
        
        now = loop.time()
        max_age = delay_seconds.value
        
        # Expire any delayed values which should have been removed by now
        while timers:
            insertion_time, value, instantaneous_value, handle = timers[0]
            age = now - insertion_time
            if age >= max_age:
                handle.cancel()
                pop_value()
            else:
                # If this timer is young enough, all others inserted after it
                # must also be young enough.
                break
        
        # Update the timeouts of the remaining timers
        def update_timer(it_v_iv_h):
            insertion_time, value, instantaneous_value, handle = it_v_iv_h
            handle.cancel()
            return (insertion_time,
                    value,
                    instantaneous_value,
                    loop.call_at(insertion_time + delay_seconds.value,
                                 pop_value))
        timers = list(map(update_timer, timers))
    
    return output_value


def time_window(source_value, duration, loop=None):
    """Produce a moving window over a :py:class:`Value`'s historical values
    within a given time period.
    
    This function treats the :py:class:`Value` it is passed as a persistent
    :py:class:`Value`, even if it is instantaneous (since a window function
    doesn't really have any meaning for an instantaneous value).
    
    The ``duration`` may be a constant or a (persistent) Value giving the
    window duration as a number of seconds. The duration should be a number of
    seconds greater than zero and never be ``NoValue``. If the value is
    reduced, previously inserted values will be expired earlier, possibly
    immediately if they should already have expired. If the value is increased,
    previously inserted values will have an increased timeout.
    
    The ``loop`` argument should be an :py:class:`asyncio.BaseEventLoop` in
    which windowing will be scheduled. If ``None``, the default loop is used.
    """
    
    source_value = ensure_value(source_value)
    output_value = Value([source_value.value])
    
    # A queue of (insertion_time, handle) pairs for calls to expire values currently
    # in the window.
    timers = []
    
    duration = ensure_value(duration)
    loop = loop or asyncio.get_event_loop()
    
    def expire_value():
        """Internal. Removes a value from the window."""
        timers.pop(0)
        output_value.value = output_value.value[1:]
    
    def schedule_value_expiration():
        """
        Internal. Drop a newly-inserted value from the window after the window
        delay occurs.
        """
        now = loop.time()
        t = now + duration.value
        timers.append((now, loop.call_at(t, expire_value)))
    
    @source_value.on_value_changed
    def on_source_value_changed(new_value):
        """Internal. Adds the new value to the window when the input changes."""
        output_value.value = output_value.value + [new_value]
        schedule_value_expiration()
    
    @duration.on_value_changed
    def on_duration_changed(_instantaneous_new_duration):
        """Internal. Handle changes in the specified window duration."""
        nonlocal timers
        # Immediately expire any values in the window older than the new
        # duration.
        now = loop.time()
        new_duration = duration.value
        while timers:
            insertion_time, handle = timers[0]
            age = now - insertion_time
            if age > new_duration:
                handle.cancel()
                expire_value()  # Side effect: removes handle from timers
            else:
                # Since the _timers array is in order, as soon as we encounter
                # a young enough timer, all others after it will be younger
                # still.
                break
        
        # Modify the timeouts of all previously inserted values
        def modify_timeout(insertion_time_and_handle):
            insertion_time, handle = insertion_time_and_handle
            handle.cancel()
            
            return (insertion_time,
                    loop.call_at(insertion_time + new_duration,
                                 expire_value))
        timers = [modify_timeout(t) for t in timers]
    
    schedule_value_expiration()
    
    return output_value

def rate_limit(source_value, min_interval=0.1, loop=None):
    """Prevent changes occurring above a particular rate, dropping or
    postponing changes if necessary.
    
    The ``min_interval`` argument may be a constant or a :py:class:`Value`. If
    this value is decreased, currently delayed values will be output early (or
    immediately if the value would have been output previously). If increased,
    the current delay will be increased.
    
    The ``loop`` argument should be an :py:class:`asyncio.BaseEventLoop` in
    which the delays will be scheduled. If ``None``, the default loop is used.
    """
    
    source_value = ensure_value(source_value)
    output_value = Value(source_value.value)
    
    min_interval = ensure_value(min_interval)
    loop = loop or asyncio.get_event_loop()
    
    # The last value to be received from the source
    last_value = None
    
    # Was last_value blocked from being sent due to the rate limit?
    last_value_blocked = False
    
    # The time (according to asyncio) the last blockage started. The
    # blockage will be cleared min_interval.delay seconds after this
    # time.
    last_block_start = None
    
    # The asyncio timer handle for the current blockage timer
    timer_handle = None
    
    # Is the rate limit currently being applied? (Initially yes for
    # persistant values, otherwise no)
    blocked = source_value.value is not NoValue
    
    def clear_blockage():
        """Internal. Timeout expired callback."""
        nonlocal blocked, last_value, last_value_blocked, last_block_start, timer_handle
        if last_value_blocked:
            # Pass the delayed value through
            output_value._value = source_value.value
            output_value.set_instantaneous_value(last_value)
            last_value = None
            last_value_blocked = False
            
            # Start the blockage again
            block()
        else:
            # No values queued up, just unblock
            blocked = False
            last_block_start = None
            timer_handle = None
    
    def block():
        """Setup a timer to unblock the rate_limit and output the last
        value."""
        nonlocal blocked, last_block_start, timer_handle
        blocked = True
        last_block_start = loop.time()
        timer_handle = loop.call_at(
            last_block_start + min_interval.value,
            clear_blockage)
    
    @source_value.on_value_changed
    def on_source_value_changed(new_value):
        nonlocal last_value, last_value_blocked
        if not blocked:
            # Pass the value change through
            output_value._value = source_value.value
            output_value.set_instantaneous_value(new_value)
            
            # Start a timeout
            block()
        else:
            # Keep the value back until we're unblocked
            last_value = new_value
            last_value_blocked = True
    
    @min_interval.on_value_changed
    def on_min_interval_changed(instantaneous_min_interval):
        nonlocal timer_handle
        now = loop.time()
        if not blocked:
            # No blockage in progress, nothing to do
            pass
        elif now - last_block_start >= min_interval.value:
            # New timeout has already expired, unblock immediately
            timer_handle.cancel()
            clear_blockage()
        else:
            # Reset timer for new time
            timer_handle.cancel()
            timer_handle = loop.call_at(
                last_block_start + min_interval.value,
                clear_blockage)
    
    if blocked:
        block()

    return output_value
