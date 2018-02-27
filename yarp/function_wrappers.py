"""
Wrappers for making reactive Python functions which accept and produce
:py:class:`Value` objects.
"""

import functools

from yarp import NoValue, Value, ensure_value

__names__ = [
    "fn",
    "instantaneous_fn",
]

def _function_call_on_argument_value_change(call_immediately, callback,
                                            *value_args, **value_kwargs):
    """
    Internal use. Call a regular Python function whenever a :py:class:`Value`
    in the arguments change.
    
    Parameters
    ----------
    call_immediately: bool
        If True, calls 'callback' immediately with the current value of the
        argument :py:class:`Values`.
    callback: callable
        Call this function with value-substituted arguments whenever an
        argument value changes.
    *value_args, **value_kwargs
        The arguments given to this function. These may contain
        :py:class:`Value` objects. When these values change, ``callback`` will
        be called with the latest underlying values from the arguments.
    """
    args = []
    kwargs = {}
    
    def get_args_kwargs():
        """
        Return an (args, kwargs) tuple containing the current underlying values
        of the arg/kwarg :py:class:`Value` objects.
        """
        a = [a.value for a in args]
        k = {k: a.value for k, a in kwargs.items()}
        
        return (a, k)
    
    def on_arg_changed(index, value):
        """Callback on an argument :py:class:`Value` changing."""
        args, kwargs = get_args_kwargs()
        args[index] = value
        
        callback(*args, **kwargs)
    
    def on_kwarg_changed(key, value):
        """Callback on a keyword argument :py:class:`Value` changing."""
        args, kwargs = get_args_kwargs()
        kwargs[key] = value
        
        callback(*args, **kwargs)
    
    # Wrap all args/kwargs in Value objects, if not already, and subscribe
    # to changes
    for i, arg in enumerate(map(ensure_value, value_args)):
        args.append(arg)
        arg.on_value_changed(functools.partial(on_arg_changed, i))
    
    for key, arg in value_kwargs.items():
        arg = ensure_value(arg)
        kwargs[key] = arg
        arg.on_value_changed(functools.partial(on_kwarg_changed, key))
    
    if call_immediately:
        a, k = get_args_kwargs()
        callback(*a, **k)
    


def fn(f):
    """
    Decorator. Wraps a function so that it may be called with :py:class:`Value`
    objects and itself return a persistent :py:class:`Value`.
    
    Say a function is defined and wrapped with :py:func:`fn` like so::
    
        >>> @yarp.fn
        ... def add(a, b):
        ...     return a + b
    
    The function can now be called with :py:class:`Value` objects like so::
    
        >>> a = yarp.Value(1)
        >>> b = yarp.Value(2)
        >>> c = add(a, b)
    
    The returned value will itself be a :py:class:`Value` object which will be
    updated whenever any of the arguments change.
    
        >>> c.value
        3
    
    The wrapped function doesn't need to know anything about
    :py:class:`Value` objects: the wrapper unpacks the :py:class:`Value`\ s of
    each argument before passing it on and automatically wrapps the return
    value in a :py:class:`Value`. (Non-:py:class:`Value` arguments passed to
    the function are automatically passed through without modification).
    
    The wrapped function is called once immediately when it is called and then
    again is required when its arguments change. The output :py:class:`Value`
    will be persistent.
    
    See also: :py:func:`instantaneous_fn`.
    """
    @functools.wraps(f)
    def instance_maker(*args, **kwargs):
        output_value = Value()
        first_call = True
        def callback(*args, **kwargs):
            nonlocal first_call
            if first_call:
                first_call = False
                output_value._value = f(*args, **kwargs)
            else:
                output_value.value = f(*args, **kwargs)
        
        _function_call_on_argument_value_change(
            True, callback, *args, **kwargs)
        return output_value
    
    return instance_maker

def instantaneous_fn(f):
    """
    Decorator. Like :py:func:`fn` but the function output will be wrapped as an
    instantaneous :py:class:`Value`.
    
    The only other difference is that the function will not be called
    immediately and instead will only be called later when its inputs change.
    """
    @functools.wraps(f)
    def instance_maker(*args, **kwargs):
        output_value = Value()
        def callback(*args, **kwargs):
            output_value.set_instantaneous_value(f(*args, **kwargs))
        
        _function_call_on_argument_value_change(
            False, callback, *args, **kwargs)
        return output_value
    
    return instance_maker
