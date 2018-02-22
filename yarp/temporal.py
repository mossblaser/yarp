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

class delay(Value):
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
    
    def __init__(self, source_value, delay_seconds, loop=None):
        self._source_value = ensure_value(source_value)
        self._delay_seconds = ensure_value(delay_seconds)
        super(delay, self).__init__(self._source_value.value)
        
        # An array of (insertion_time, value, instantaneous_value, handle)
        # tuples for values due to be sent.
        self._timers = []
        
        self._loop = loop or asyncio.get_event_loop()
        
        self._source_value.on_value_changed(self._on_source_value_changed)
        self._delay_seconds.on_value_changed(self._on_delay_seconds_changed)
    
    def _pop_value(self):
        """Internal. Outputs a previously delayed value."""
        insertion_time, value, instantaneous_value, handle = self._timers.pop(0)
        self._value = value
        self.set_instantaneous_value(instantaneous_value)
    
    def _on_source_value_changed(self, instantaneous_value):
        """Internal. Schedule an incoming value to be output later."""
        insertion_time = self._loop.time()
        value = self._source_value.value
        handle = self._loop.call_at(insertion_time + self._delay_seconds.value,
                                    self._pop_value)
        self._timers.append((insertion_time, value, instantaneous_value, handle))
    
    def _on_delay_seconds_changed(self, new_delay_seconds):
        """Internal. Handle the delay changing."""
        now = self._loop.time()
        max_age = self._delay_seconds.value
        
        # Expire any delayed values which should have been removed by now
        while self._timers:
            insertion_time, value, instantaneous_value, handle = self._timers[0]
            age = now - insertion_time
            if age >= max_age:
                handle.cancel()
                self._pop_value()
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
                    self._loop.call_at(insertion_time + self._delay_seconds.value,
                                       self._pop_value))
        self._timers = list(map(update_timer, self._timers))


class time_window(Value):
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
    
    def __init__(self, source_value, duration, loop=None):
        source_value = ensure_value(source_value)
        super(time_window, self).__init__([source_value.value])
        
        # A queue of (insertion_time, handle) pairs for calls to expire values currently
        # in the window.
        self._timers = []
        
        self._duration = ensure_value(duration)
        self._loop = loop or asyncio.get_event_loop()
        
        source_value.on_value_changed(self._on_source_value_changed)
        self._duration.on_value_changed(self._on_duration_changed)
        
        self._schedule_value_expiration()
    
    def _schedule_value_expiration(self):
        """
        Internal. Drop a newly-inserted value from the window after the window
        delay occurs.
        """
        now = self._loop.time()
        t = now + self._duration.value
        self._timers.append((now, self._loop.call_at(t, self._expire_value)))
    
    def _expire_value(self):
        """Internal. Removes a value from the window."""
        self._timers.pop(0)
        self.value = self.value[1:]
    
    def _on_source_value_changed(self, new_value):
        """Internal. Adds the new value to the window when the input changes."""
        self.value = self.value + [new_value]
        self._schedule_value_expiration()
    
    def _on_duration_changed(self, _instantaneous_new_duration):
        """Internal. Handle changes in the specified window duration."""
        # Immediately expire any values in the window older than the new
        # duration.
        now = self._loop.time()
        new_duration = self._duration.value
        while self._timers:
            insertion_time, handle = self._timers[0]
            age = now - insertion_time
            if age > new_duration:
                handle.cancel()
                self._expire_value()  # Side effect: removes handle from self._timers
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
                    self._loop.call_at(insertion_time + new_duration,
                                       self._expire_value))
        self._timers = [modify_timeout(t) for t in self._timers]

class rate_limit(Value):
    """Prevent changes occurring above a particular rate, dropping or
    postponing changes if necessary.
    
    The ``min_interval`` argument may be a constant or a :py:class:`Value`. If
    this value is decreased, currently delayed values will be output early (or
    immediately if the value would have been output previously). If increased,
    the current delay will be increased.
    
    The ``loop`` argument should be an :py:class:`asyncio.BaseEventLoop` in
    which the delays will be scheduled. If ``None``, the default loop is used.
    """
    
    def __init__(self, source_value, min_interval=0.1, loop=None):
        self._source_value = ensure_value(source_value)
        super(rate_limit, self).__init__(self._source_value.value)
        
        self._min_interval = ensure_value(min_interval)
        self._loop = loop or asyncio.get_event_loop()
        
        # The last value to be received from the source
        self._last_value = None
        
        # Was self._last_value blocked from being sent due to the rate limit?
        self._last_value_blocked = False
        
        # The time (according to asyncio) the last blockage started. The
        # blockage will be cleared self._min_interval.delay seconds after this
        # time.
        self._last_block_start = None
        
        # The asyncio timer handle for the current blockage timer
        self._timer_handle = None
        
        self._source_value.on_value_changed(self._on_source_value_changed)
        self._min_interval.on_value_changed(self._on_min_interval_changed)
        
        # Is the rate limit currently being applied? (Initially yes for
        # persistant values, otherwise no)
        self._blocked = self._source_value.value is not NoValue
        if self._blocked:
            self._block()
    
    def _on_source_value_changed(self, new_value):
        if not self._blocked:
            # Pass the value change through
            self._value = self._source_value.value
            self.set_instantaneous_value(new_value)
            
            # Start a timeout
            self._block()
        else:
            # Keep the value back until we're unblocked
            self._last_value = new_value
            self._last_value_blocked = True
    
    def _clear_blockage(self):
        """Internal. Timeout expired callback."""
        if self._last_value_blocked:
            # Pass the delayed value through
            self._value = self._source_value.value
            self.set_instantaneous_value(self._last_value)
            self._last_value = None
            self._last_value_blocked = False
            
            # Start the blockage again
            self._block()
        else:
            # No values queued up, just unblock
            self._blocked = False
            self._last_block_start = None
            self._timer_handle = None
    
    def _block(self):
        """Setup a timer to unblock the rate_limit and output the last
        value."""
        self._blocked = True
        self._last_block_start = self._loop.time()
        self._timer_handle = self._loop.call_at(
            self._last_block_start + self._min_interval.value,
            self._clear_blockage)
    
    def _on_min_interval_changed(self, instantaneous_min_interval):
        now = self._loop.time()
        if not self._blocked:
            # No blockage in progress, nothing to do
            pass
        elif now - self._last_block_start >= self._min_interval.value:
            # New timeout has already expired, unblock immediately
            self._timer_handle.cancel()
            self._clear_blockage()
        else:
            # Reset timer for new time
            self._timer_handle.cancel()
            self._timer_handle = self._loop.call_at(
                self._last_block_start + self._min_interval.value,
                self._clear_blockage)

