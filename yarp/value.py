"""
The fundamental :py:class:`Value` type for yarp, along with relatively
generic low-level utilities for creating and manipulating them.
"""


import functools
import sentinel

__names__ = [
    "NoValue",
    "Value",
    "ListValue",
    "TupleValue",
    "DictValue",
    "ensure_value",
    "make_instantaneous",
    "make_persistent",
]


"""
A special value indicating that a ``yarp`` value has not been assigned a value.
"""
NoValue = sentinel.create("NoValue")

class Value(object):
    """
    A continuous or instantaneous value which can be read and set.
    
    This base class defines the fundamental type in ``yarp``: the 'value'.
    """
    
    def __init__(self, initial_value = NoValue):
        self._value = initial_value
        self._on_value_changed = []
    
    @property
    def value(self):
        """
        A property holding the current continuous value held by this object. If
        not yet set, or if this object represents only instantaneous values,
        this will be ``NoValue``.
        """
        return self._value
    
    @value.setter
    def value(self, new_value):
        """
        Sets the (continuous) contents of this value (raising the
        on_value_changed callback afterwards).
        
        To set the instantaneous value, see :py:meth:`set_instantaneous_value`.
        
        To change the value without raising a callback, set the
        :py:attr:`_value` attribute directly. This may be useful if you wish to
        make this Value mimic another by, in a callback function, setting
        :py:attr:`_value` in this Value directly from the other Value's
        :py:attr:`value` and calling :py:meth:`set_instantaneous_value` with
        the passed variable explicitly. You must always be sure to call
        :py:meth:`set_instantaneous_value` after changing :py:attr:`_value`.
        """
        self._value = new_value
        self.set_instantaneous_value(new_value)
    
    def set_instantaneous_value(self, new_value):
        """
        Set the instantaneous value of this Value, calling the on_value_changed
        callbacks with the passed value but not storing it in the
        :py:attr:`value` property (which will remain unchanged).
        """
        for cb in self._on_value_changed:
            cb(new_value)
    
    def on_value_changed(self, cb):
        """
        Registers ``callback`` as a callback function to be called when this
        value changes.
        
        The callback function will be called with a single argument: the value
        now held by this object. If the value is continuous, the value given as
        the argument will match the :py:attr:`ValueBase.value` property.
        Otherwise, if this value is instantaneous, the value will not be
        reflected in the :py:attr:`ValueBase.value` property.
        
        .. note::
        
            There is no way to remove callbacks. For the moment this is an
            intentional restriction: if this causes you difficulties this is a
            good sign what you're doing is 'serious' enough that ``yarp`` is
            not for you.
        """
        self._on_value_changed.append(cb)

class ListValue(Value):
    """
    A :py:class:`Value` consisting of a fixed list of other :py:class:`Values
    <Value>`.
    """
    
    def __init__(self, list_of_values):
        """
        Params
        ------
        list_of_values: [:py:class:`Value`, ...]
            A fixed list of :py:class:`Value`s. The :py:attr:`value` of this
            object will be an array of the underlying values. Callbacks will be
            raised whenever a value in the list changes.
            
            It is not possible to modify the list or set the contained values
            directly from this object.
            
            For instantaneous list members, the instantaneous value will be
            present in the version of this list passed to registered callbacks
            but otherwise not retained. (Typically the instantaneous values
            will be represented by :py:class:`NoValue` in :py:attr:`value` or
            in callbacks resulting from other :py:class:`Value`s changing.
        """
        self._list_of_values = list_of_values
        lst = [v.value for v in self._list_of_values]
        super(ListValue, self).__init__(lst)
        
        for i, value in enumerate(self._list_of_values):
            value.on_value_changed(functools.partial(self._element_changed, i))
    
    def _element_changed(self, index, new_value):
        self._value[index] = self._list_of_values[index].value
        
        # Substitute in the instantaneous value of the changed element
        instantaneous_value = self._value.copy()
        instantaneous_value[index] = new_value
        
        self.set_instantaneous_value(instantaneous_value)

class TupleValue(Value):
    """
    A :py:class:`Value` consisting of a tuple of other :py:class:`Values
    <Value>`.
    """
    
    def __init__(self, list_of_values):
        """
        Params
        ------
        tuple_of_values: (:py:class:`Value`, ...)
            A fixed tuple of :py:class:`Value`s. The :py:attr:`value` of this
            object will be a tuple of the underlying values. Callbacks will be
            raised whenever a value in the tuple changes.
            
            It is not possible to modify the tuple or set the contained values
            directly from this object.
            
            For instantaneous tuple members, the instantaneous value will be
            present in the version of this tuple passed to registered callbacks
            but otherwise not retained. (Typically the instantaneous values
            will be represented by :py:class:`NoValue` in :py:attr:`value` or
            in callbacks resulting from other :py:class:`Value`s changing.
        """
        self._tuple_of_values = list_of_values
        tup = tuple(v.value for v in self._tuple_of_values)
        super(TupleValue, self).__init__(tup)
        
        for i, value in enumerate(self._tuple_of_values):
            value.on_value_changed(functools.partial(self._element_changed, i))
    
    def _element_changed(self, index, new_value):
        self._value = tuple(v.value for v in self._tuple_of_values)
        
        # Substitute in the instantaneous value of the changed element
        instantaneous_value = tuple(
            v.value if i != index else new_value
            for i, v in enumerate(self._tuple_of_values)
        )
        
        self.set_instantaneous_value(instantaneous_value)

class DictValue(Value):
    """
    A :py:class:`Value` consisting of a dictionary where the values (but not
    keys) are  :py:class:`Values <Value>`.
    """
   
    def __init__(self, dict_of_values):
        """
        Params
        ------
        dict_of_values: {key: :py:class:`Value`, ...}
            A fixed dictionary of :py:class:`Value`s. The :py:attr:`value` of this
            object will be a dictionary of the underlying values. Callbacks will be
            raised whenever a value in the dictionary changes.
            
            It is not possible to modify the set of keys in the dictionary nor
            directly change the values of its elements from this object.
            
            For instantaneous dictionary members, the instantaneous value will
            be present in the version of this dict passed to registered
            callbacks but otherwise not retained. (Typically the instantaneous
            values will be represented by :py:class:`NoValue` in
            :py:attr:`value` or in callbacks resulting from other
            :py:class:`Value`s changing.
        """
        self._dict_of_values = dict_of_values
        dct = {k: v.value for k, v in self._dict_of_values.items()}
        super(DictValue, self).__init__(dct)
        
        for key, value in self._dict_of_values.items():
            value.on_value_changed(functools.partial(self._element_changed, key))
    
    def _element_changed(self, key, new_value):
        self._value[key] = self._dict_of_values[key].value
        
        instantaneous_value = self._value.copy()
        instantaneous_value[key] = new_value
        
        self.set_instantaneous_value(instantaneous_value)

def ensure_value(value):
    """Ensure a variable is a :py:class:`Value` object, wrapping it accordingly
    if not.
    
    * If already a :py:class:`Value`, returns unmodified.
    * If a list, tuple or dict, applies :py:func:`ensure_value` to all contained values and
      returns a :py:class:`ListValue`, :py:class:`TupleValue` or
      :py:class:`DictValue` respectively.
    * If any other type, wraps the variable in a continous :py:class:`Value`
      with the initial value set to the defined value.
    """
    if isinstance(value, Value):
        return value
    elif isinstance(value, list):
        return ListValue([ensure_value(v) for v in value])
    elif isinstance(value, tuple):
        return TupleValue(tuple(ensure_value(v) for v in value))
    elif isinstance(value, dict):
        return DictValue({k: ensure_value(v) for k, v in value.items()})
    else:
        return Value(value)

class make_instantaneous(Value):
    """
    Make a persistent :py:class`Value` into an instantaneous one which 'fires'
    whenever the persistant value is changed.
    """
    
    def __init__(self, source_value):
        super(make_instantaneous, self).__init__()
        ensure_value(source_value).on_value_changed(self.set_instantaneous_value)

class make_persistent(Value):
    """
    Make an instantaneous :py:class:`Value` into a persistant one, keeping the old value
    between changes. Initially sets the :py:class:`Value` to ``initial_value``.
    """
    
    def __init__(self, source_value, initial_value=NoValue):
        source_value = ensure_value(source_value)
        super(make_persistent, self).__init__(initial_value)
        source_value.on_value_changed(self._on_source_value_changed)
    
    def _on_source_value_changed(self, new_value):
        self.value = new_value

