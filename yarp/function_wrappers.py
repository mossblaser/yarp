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

class _FnReturnValueBase(Value):
    """
    Internal use. Base class for a Value representing the return value of a function.
    """
    
    def __init__(self, fn, *args, **kwargs):
        """
        Parameters
        ----------
        fn: callable
            The function whose return value this Value represents.
        *args, **kwargs
            The arguments given to this function. These may contain
            :py:class:`Value` objects. When these values change, ``fn`` will be
            reevaluated and this :py:class:`Value` set to the new returned
            value accordingly.
            
            Inheritors should implement :py:meth:`_call_fn` which should call
            ``fn`` and set this value in whatever way is most appropraite (e.g.
            instantaneously or continuously).
        """
        super(_FnReturnValueBase, self).__init__()
        
        self._fn = fn
        
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
        """
        Return an (args, kwargs) tuple containing the current underlying values
        of the arg/kwarg :py:class:`Value` objects.
        """
        args = [a.value for a in self._args]
        kwargs = {k: a.value for k, a in self._kwargs.items()}
        
        return (args, kwargs)
    
    def _on_arg_changed(self, index, value):
        """Callback on an argument :py:class:`Value` changing."""
        args, kwargs = self._get_args_kwargs()
        args[index] = value
        
        self._call_fn(*args, **kwargs)
    
    def _on_kwarg_changed(self, key, value):
        """Callback on a keyword argument :py:class:`Value` changing."""
        args, kwargs = self._get_args_kwargs()
        kwargs[key] = value
        
        self._call_fn(*args, **kwargs)


class _PersistentFnReturnValue(_FnReturnValueBase):
    """
    Internal use. A persistent Value representing the return value of a function.
    """
    
    def __init__(self, fn, *args, **kwargs):
        super(_PersistentFnReturnValue, self).__init__(fn, *args, **kwargs)
        
        # Populate initial value
        args, kwargs = self._get_args_kwargs()
        self._value = self._fn(*args, **kwargs)
    
    def _call_fn(self, *args, **kwargs):
        self.value = self._fn(*args, **kwargs)

class _InstantaneousFnReturnValue(_FnReturnValueBase):
    """
    Internal use. A instantaneous Value representing the return value of a function.
    """
    
    def __init__(self, fn, *args, **kwargs):
        super(_InstantaneousFnReturnValue, self).__init__(fn, *args, **kwargs)
    
    def _call_fn(self, *args, **kwargs):
        self.set_instantaneous_value(self._fn(*args, **kwargs))

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
        return _PersistentFnReturnValue(f, *args, **kwargs)
    
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
        return _InstantaneousFnReturnValue(f, *args, **kwargs)
    
    return instance_maker

