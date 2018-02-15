import functools
import sentinel
import asyncio

from .version import __version__

NoValue = sentinel.create("NoValue")

class Value(object):
    
    def __init__(self, initial_value = NoValue):
        self._value = initial_value
        self._on_value_changed = []
    
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, new_value):
        self._value = new_value
        self.value_changed(new_value)
    
    def value_changed(self, new_value):
        """
        Call when this value changes. Note that users should only call this for
        instantaneous values (i.e. when 'value' is not set). Setting 'value'
        automatically calls this function.
        """
        for cb in self._on_value_changed:
            cb(new_value)
    
    def on_value_changed(self, cb):
        """
        Register a callback when this function's value changes or is set.
        The callback will be called with a single argument: the new value.
        """
        self._on_value_changed.append(cb)

class ListValue(Value):
    """
    A value consisting of a list of other Values.
    """
    
    def __init__(self, list_of_values):
        self._list_of_values = list_of_values
        lst = [v.value for v in self._list_of_values]
        super(ListValue, self).__init__(lst)
        
        for i, value in enumerate(self._list_of_values):
            value.on_value_changed(functools.partial(self._element_changed, i))
    
    def _element_changed(self, index, new_value):
        self._value[index] = self._list_of_values[index].value
        
        instantaneous_value = self._value.copy()
        instantaneous_value[index] = new_value
        
        self.value_changed(instantaneous_value)

class DictValue(Value):
    """
    A value consisting of a dictionary of other Values (keys are not Values,
    however).
    """
   
    def __init__(self, dict_of_values):
        self._dict_of_values = dict_of_values
        dct = {k: v.value for k, v in self._dict_of_values.items()}
        super(DictValue, self).__init__(dct)
        
        for key, value in self._dict_of_values.items():
            value.on_value_changed(functools.partial(self._element_changed, key))
    
    def _element_changed(self, key, new_value):
        self._value[key] = self._dict_of_values[key].value
        
        instantaneous_value = self._value.copy()
        instantaneous_value[key] = new_value
        
        self.value_changed(instantaneous_value)

def ensure_value(value):
    """Ensure a variable is a Value object.
    
    * If already a Value, returns unmodified.
    * If a list or dict, applies ensure_value to all contained values and
      returns a Value with the appropriate container type. NB: Does not apply
      to tuples, sets or other standard data types.
    * If any other type, wraps the variable in a Value with the initial_value
      set to the defined value.
    """
    if isinstance(value, Value):
        return value
    elif isinstance(value, list):
        return ListValue([ensure_value(v) for v in value])
    elif isinstance(value, dict):
        return DictValue({k: ensure_value(v) for k, v in value.items()})
    else:
        return Value(value)

class FnReturnValueBase(Value):
    """
    Base class for a Value representing the output of a function.
    """
    
    def __init__(self, *args, **kwargs):
        super(FnReturnValueBase, self).__init__()
        
        # Wrap all args/kwargs in Value objects, if not already, and subscribe
        # to changes
        self._args = []
        for i, arg in enumerate(map(ensure_value, args)):
            self._args.append(arg)
            arg.on_value_changed(functools.partial(self._on_arg_changed, i))
        
        self._kwargs = {}
        for key, arg in kwargs.items():
            arg = ensure_value(arg)
            self._kwargs[key] = arg
            arg.on_value_changed(functools.partial(self._on_kwarg_changed, key))
    
    def _get_args_kwargs(self):
        args = [a.value for a in self._args]
        kwargs = {k: a.value for k, a in self._kwargs.items()}
        
        return (args, kwargs)
    
    def _on_arg_changed(self, index, value):
        args, kwargs = self._get_args_kwargs()
        args[index] = value
        
        self._call_fn(*args, **kwargs)
    
    def _on_kwarg_changed(self, key, value):
        args, kwargs = self._get_args_kwargs()
        kwargs[key] = value
        
        self._call_fn(*args, **kwargs)

class PersistentFnReturnValue(FnReturnValueBase):
    
    def __init__(self, fn, *args, **kwargs):
        super(PersistentFnReturnValue, self).__init__(*args, **kwargs)
        
        self._fn = fn
        
        # Populate initial value
        args, kwargs = self._get_args_kwargs()
        self._value = self._fn(*args, **kwargs)
    
    def _call_fn(self, *args, **kwargs):
        self.value = self._fn(*args, **kwargs)

class InstantaneousFnReturnValue(FnReturnValueBase):
    
    def __init__(self, fn, *args, **kwargs):
        super(InstantaneousFnReturnValue, self).__init__(*args, **kwargs)
        
        self._fn = fn
    
    def _call_fn(self, *args, **kwargs):
        self.value_changed(self._fn(*args, **kwargs))

def fn(f):
    @functools.wraps(f)
    def instance_maker(*args, **kwargs):
        return PersistentFnReturnValue(f, *args, **kwargs)
    
    return instance_maker

def instantaneous_fn(f):
    @functools.wraps(f)
    def instance_maker(*args, **kwargs):
        return InstantaneousFnReturnValue(f, *args, **kwargs)
    
    return instance_maker

class delay(Value):
    """
    Produce a time-delayed version of a value.
    
    The delay_seconds argument may also be a Value. If it is increased,
    previously delayed values will be delayed further. If it is decreased,
    values which should already have been output will be output rapidly one
    after another.
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
        insertion_time, value, instantaneous_value, handle = self._timers.pop(0)
        self._value = value
        self.value_changed(instantaneous_value)
    
    def _on_source_value_changed(self, instantaneous_value):
        insertion_time = self._loop.time()
        value = self._source_value.value
        handle = self._loop.call_at(insertion_time + self._delay_seconds.value,
                                    self._pop_value)
        self._timers.append((insertion_time, value, instantaneous_value, handle))
    
    def _on_delay_seconds_changed(self, new_delay_seconds):
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

class window(Value):
    """Produce a moving window over a Value's historical values.
    
    This function treats the Value it is passed as a persistent Value, even if
    it is instantaneous (since a window function doesn't really have any
    meaning for an instantaneous value).
    
    The num_values argument may be a (persistent) Value. If this value is
    reduced, the contents of the window will be truncated immediately. If it is
    increaesd, any previously dropped values will not return.
    
    num_values is always assumed to be an integer greater than zero and never
    NoValue.
    """
    
    def __init__(self, source_value, num_values):
        source_value = ensure_value(source_value)
        super(window, self).__init__([source_value.value])
        
        self._num_values = ensure_value(num_values)
        assert self._num_values.value >= 1
        
        source_value.on_value_changed(self._on_source_value_changed)
        self._num_values.on_value_changed(self._on_num_values_changed)
        
    
    def _on_source_value_changed(self, new_value):
        self.value = (self.value + [new_value])[-self._num_values.value:]
    
    def _on_num_values_changed(self, _instantaneous_new_num_values):
        # Truncate the window data if required
        new_num_values = self._num_values.value
        assert new_num_values >= 1
        if len(self.value) > new_num_values:
            self.value = self.value[-new_num_values:]

class time_window(Value):
    """Produce a moving window over a Value's historical values within a given
    time duration.
    
    This function treats the Value it is passed as a persistent Value, even if
    it is instantaneous (since a window function doesn't really have any
    meaning for an instantaneous value).
    
    The duration may also be a (persistent) Value. The duration should be a
    number of seconds greater than zero and never be NoValue. If the value is
    reduced, previously inserted values will be expired earlier, possibly
    immediately if they should already have expired. If the value is increased,
    previously inserted values will have an increased timeout.
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
        now = self._loop.time()
        t = now + self._duration.value
        self._timers.append((now, self._loop.call_at(t, self._expire_value)))
    
    def _expire_value(self):
        self._timers.pop(0)
        self.value = self.value[1:]
    
    def _on_source_value_changed(self, new_value):
        self.value = self.value + [new_value]
        self._schedule_value_expiration()
    
    def _on_duration_changed(self, _instantaneous_new_duration):
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

class make_instantaneous(Value):
    """
    Make a persistent Value into an instantaneous one which 'fires' whenever
    the persistant value is set.
    """
    
    def __init__(self, source_value):
        super(make_instantaneous, self).__init__()
        ensure_value(source_value).on_value_changed(self.value_changed)

class make_persistent(Value):
    """
    Make an instantaneous Value into a persistant one, keeping the value
    between changes.
    """
    
    def __init__(self, source_value):
        source_value = ensure_value(source_value)
        super(make_persistent, self).__init__(source_value.value)
        source_value.on_value_changed(self._on_source_value_changed)
    
    def _on_source_value_changed(self, new_value):
        self.value = new_value

class no_repeat(Value):
    """Don't pass on changes if no value change has occurred."""
    
    def __init__(self, source_value):
        self._source_value = ensure_value(source_value)
        super(no_repeat, self).__init__(self._source_value.value)
        self._last_value = self.value
        
        self._source_value.on_value_changed(self._on_source_value_changed)
    
    def _on_source_value_changed(self, new_value):
        if new_value != self._last_value:
            self._last_value = new_value
            self._value = self._source_value.value
            self.value_changed(new_value)

class rate_limit(Value):
    """Prevent changes occurring above a particular rate, dropping or
    postponing changes if the rate grows too high.
    
    The min_interval argument may be a Value. If this value is decreased,
    currently delayed values will be output early (or immediately if the value
    would have been output previously). If increased, the current delay will be
    increased.
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
            self.value_changed(new_value)
            
            # Start a timeout
            self._block()
        else:
            # Keep the value back until we're unblocked
            self._last_value = new_value
            self._last_value_blocked = True
    
    def _clear_blockage(self):
        if self._last_value_blocked:
            # Pass the delayed value through
            self._value = self._source_value.value
            self.value_changed(self._last_value)
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

class filter(Value):
    """Filter change events.
    
    The filter rule should be a function which takes the new value as an
    argument and returns a boolean indicating if the value should be passed on
    or not. If the source value is persistent, the persistent value will remain
    unchanged when a value change is not passed on.
    
    If the filter rule is ``None``, non-truthy values and ``NoValue`` will be
    filtered out. If the filter rule is ``NoValue`` (the default) only
    ``NoValue`` will be filtered out.
    """
    
    def __init__(self, source_value, rule=NoValue):
        self._source_value = ensure_value(source_value)
        self._rule = rule
        super(filter, self).__init__(
            self._source_value.value
            if (self._source_value.value is not NoValue and
                self._check_value(self._source_value.value))
            else NoValue)
        
        self._source_value.on_value_changed(self._on_source_value_changed)
    
    def _check_value(self, value):
        if self._rule is NoValue:
            return value is not NoValue
        elif self._rule is None:
            return value is not NoValue and bool(value)
        else:
            return self._rule(value)
    
    def _on_source_value_changed(self, new_value):
        if self._check_value(new_value):
            self._value = self._source_value.value
            self.value_changed(new_value)
