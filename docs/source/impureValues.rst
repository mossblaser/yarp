.. module:: yarp

Creating impure Values
======================

In general, ``yarp`` :py:class:`Value`\ s are intended to be passed between
simple, pure_ functions wrapped by the :py:func:`fn` decorator. Specifically,
these functions don't hold any state and the resulting :py:class:`Value`\ s
change when-and-only-when any input :py:class:`Value` changes. This type of
function is very easy to write and reason about with ``yarp`` but is
fundamentally constrained. For example, it is not possible to implement
:py:func:`delay` using such a function since input :py;class:`Value` changes do
not immediately result in the :py:class:`Value` changing. Simillarly, the
:py:func:`no_repeat` function also cannot be replicated since it doesn't always
change its output :py:class:`Value` when its input changes.

.. _pure: https://en.wikipedia.org/wiki/Pure_function

To get around this limitation it is necessary to manipulate :py:class:`Value`\
s 'by hand'. Lets begin by seeing how :py:func:`no_repeat` is implemented.

The following pseudo code implementation goes the 'obvious' implementation for
a no-repeat value:

.. code-block:: text

    on source value changed:
        if source value != last source value:
            output value = source value
        last source value = source value

The actual Python implementation looks like:

.. doctest::
    :hide:

    >>> from yarp import NoValue, Value

.. doctest::

    >>> def no_repeat(source_value):
    ...     last_value = source_value.value
    ...
    ...     # Initially take on the source value
    ...     output_value = Value(last_value)
    ...     
    ...     @source_value.on_value_changed
    ...     def on_source_value_changed(new_value):
    ...         nonlocal last_value
    ...         if new_value != last_value:
    ...             last_value = new_value
    ...             # Copy to output whether continuous or instantaneous
    ...             output_value._value = source_value.value
    ...             output_value.set_instantaneous_value(new_value)
    ...     
    ...     return output_value

In this example we create function (or rather, a closure) called
``on_source_value_changed`` and set it as the callback for the source
:py:class:`Value` using :py:meth:`Value.on_value_changed`.

.. note::
    
    This example uses the Python `decorator syntax
    <https://www.python.org/dev/peps/pep-0318/>`_ making the code read a little
    more naturally, as in the pseudo-code version.

The ``last_value`` variable is accessed from the enclosing scope is used to
keep track of the last value received from the source. The `nonlocal
<https://docs.python.org/3/reference/simple_stmts.html#nonlocal>`_ keyword is
used to gain access to it from our callback.

The last detail is the way the output :py:class:`Value` is updated. If
``source_value`` is a continuous function we could update the output using
either:

.. code-block:: python

    output_value.value = new_value

Or:

.. code-block:: python

    output_value.value = source_value.value

However, if ``source_value`` is an instantaneous value, we'd need to do use
:py:meth:`Value.set_instantaneous_value`:

.. code-block:: python

    output_value.set_instantaneous_value(new_value)

Since we'd like to make our output :py:class:`Value` mimic the input regardless
of whether it is continuous or instantaneous, instead we use the following
two-step process:

.. code-block:: python

    output_value._value = source_value.value
    output_value.set_instantaneous_value(new_value)

By setting ``_value`` we change :py:attr:`Value.value` without triggering any
callbacks registered with :py:meth:`Value.on_value_changed`. We set this to the
continuous value of the source (which is :py:data`NoValue` if the source is
instantaneous). By calling :py:meth:`Value.set_instantaneous_value` with the
just-received value from the source we cause the callback to occur in the
output :py:class:`Value`.

You can try it out, first lets try a continuous value:

.. doctest::

    >>> # Create a value to de-repeat
    >>> v = Value(123)
    >>> nrv = no_repeat(v)
    >>> nrv.on_value_changed(print)
    <built-in function print>
    
    >>> # Repeated values should not pass through
    >>> v.value = 321
    321
    >>> v.value = 321
    >>> v.value = 321
    >>> v.value = 123
    123

Next lets try an instantaneous value:

.. doctest::

    >>> # Create another instantaneous value to de-repeat
    >>> iv = Value()
    >>> nriv = no_repeat(iv)
    >>> nriv.on_value_changed(print)
    <built-in function print>
    
    >>> nriv.value is NoValue
    True
    
    >>> iv.set_instantaneous_value(123)
    123
    >>> nriv.value is NoValue
    True
    
    >>> iv.set_instantaneous_value(123)
    >>> nriv.value is NoValue
    True
    
    >>> iv.set_instantaneous_value(321)
    321
    >>> nriv.value is NoValue
    True
