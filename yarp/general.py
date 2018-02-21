"""
General purpose utility functions for manipulating :py:class:`Value` values.
"""

from yarp import NoValue, Value, ensure_value

__names__ = [
    "window",
    "no_repeat",
    "filter",
]


class window(Value):
    """Produce a moving window over a :py:class:`Value`'s historical values.
    
    This function treats the Value it is passed as a persistent Value, even if
    it is instantaneous (since a window function doesn't really have any
    meaning for a instantaneous values).
    
    The ``num_values`` argument may be a (persistent) Value or a constant
    indicating the number of entries in the window. If this value later
    reduced, the contents of the window will be truncated immediately. If it is
    increaesd, any previously dropped values will not return.  ``num_values``
    is always assumed to be an integer greater than zero and never ``NoValue``.
    """
    
    def __init__(self, source_value, num_values):
        source_value = ensure_value(source_value)
        super(window, self).__init__([source_value.value])
        
        self._num_values = ensure_value(num_values)
        assert self._num_values.value >= 1
        
        source_value.on_value_changed(self._on_source_value_changed)
        self._num_values.on_value_changed(self._on_num_values_changed)
        
    
    def _on_source_value_changed(self, new_value):
        """Internal. Insert incoming Value into the window."""
        self.value = (self.value + [new_value])[-self._num_values.value:]
    
    def _on_num_values_changed(self, _instantaneous_new_num_values):
        """Internal. Handle window size changes."""
        # Truncate the window data if required
        new_num_values = self._num_values.value
        assert new_num_values >= 1
        if len(self.value) > new_num_values:
            self.value = self.value[-new_num_values:]

class no_repeat(Value):
    """
    Don't pass on change callbacks if the :py:class:`Value` hasn't changed.
    
    Works for both continuous and instantaneous :py:class:`Value`s.
    """
    
    def __init__(self, source_value):
        self._source_value = ensure_value(source_value)
        super(no_repeat, self).__init__(self._source_value.value)
        self._last_value = self.value
        
        self._source_value.on_value_changed(self._on_source_value_changed)
    
    def _on_source_value_changed(self, new_value):
        if new_value != self._last_value:
            self._last_value = new_value
            self._value = self._source_value.value
            self.set_instantaneous_value(new_value)

class filter(Value):
    """Filter change events.
    
    The filter rule should be a function which takes the new value as an
    argument and returns a boolean indicating if the value should be passed on
    or not.
    
    If the source value is persistent, the persistent value will remain
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
        """Internal. Test a value, return whether it should be retained or
        not."""
        if self._rule is NoValue:
            return value is not NoValue
        elif self._rule is None:
            return value is not NoValue and bool(value)
        else:
            return self._rule(value)
    
    def _on_source_value_changed(self, new_value):
        if self._check_value(new_value):
            self._value = self._source_value.value
            self.set_instantaneous_value(new_value)
