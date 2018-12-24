.. module:: yarp

Introduction
============

This programming style will be familiar to anyone who has used a spreadsheet.
In a spreadsheet you can put values into cells. You can also put functions into
cells which compute new values based on the values in other cells. The neat
feature of spreadsheets is that if you change the value in a cell, any other
cell whose value depends on it is automatically recomputed.

Using ``yarp`` you can define :py:class:`Value`\ s, and functions acting on
those values, which are automatically reevaluated when changed. For example:

.. doctest::

    >>> from yarp import Value, fn
    
    >>> # Lets define two Values which for the moment will just be '1'
    >>> a = Value(1)
    >>> b = Value(1)
    
    >>> # Lets define a function 'add' which adds two numbers together. The
    >>> # @fn decorator automatically wraps 'add' so that it takes Value
    >>> # objects as arguments and returns a Value object. Your definition,
    >>> # however, is written just like you'd write any normal function:
    >>> # accepting and returning regular Python types in boring every-day
    >>> # ways.
    >>> @fn
    ... def add(a, b):
    ...     return a + b
    
    >>> # Calling 'add' on our 'a' and 'b' Value objects returns a new Value
    >>> # object with the result. Get the actual value using the 'value'
    >>> # property.
    >>> a_plus_b = add(a, b)
    >>> a_plus_b.value
    2
    
    >>> # Changing one of the input values will cause 'add' to automatically be
    >>> # reevaluated.
    >>> a.value = 5
    >>> a_plus_b.value
    6
    >>> b.value = 10
    >>> a_plus_b.value
    15
    
    >>> # Accessing attributes of a Value returns a Value-wrapped version of
    >>> # that attribute, e.g.
    >>> c = Value(complex(1, 2))
    >>> r = c.real
    >>> r.value
    1
    >>> i = c.imag
    >>> i.value
    2
    >>> c.value = complex(10, 100)
    >>> r.value
    10
    >>> i.value
    100
    
    >>> # You can also call (side-effect free) methods of Values to get a
    >>> # Value-wrapped version of the result which updates when the Value
    >>> # change:
    >>> c2 = c.conjugate()
    >>> c2.value
    (10-100j)
    >>> c.value = complex(123, 321)
    >>> c2.value
    (123-321j)

As well as representing continuous values which change at defined points in
time ``yarp`` can also represent values which are defined only instantaneously,
for example an ephemeral sensor reading. For example:

.. doctest::

    >>> from yarp import Value, instantaneous_fn
    
    >>> # Lets create an instantaneous value which occurs whenever a car drives
    >>> # past a speed check. At the moment of measurement, the value has the
    >>> # instantaneous value of the car's speed in MPH. For now, though, it
    >>> # has no value.
    >>> car_speed_mph = Value()
    
    >>> # We live in a civilised world so lets convert that into KM/H. This
    >>> # 'instantaneous_fn' decorator works just like the 'fn' one but returns
    >>> # instantaneous values.
    >>> @instantaneous_fn
    ... def mph_to_kph(mph):
    ...     return mph * 1.6
    
    >>> car_speed_kph = mph_to_kph(car_speed_mph)
    
    >>> # Lets setup a callback to print a car's speed whenever it is measured
    >>> def on_car_measured(speed_kph):
    ...     print("A car passed at {} KM/H".format(speed_kph))
    >>> car_speed_kph.on_value_changed(on_car_measured)
    <function ...>
    
    >>> # Now lets instantaneously set the value as if a car has just gone past
    >>> # and watch as our callback is called with the speed in KM/H
    >>> car_speed_mph.set_instantaneous_value(30)
    A car passed at 48.0 KM/H

As in these examples, the intention is that most ``yarp``-using code will be
based entirely on passing :py:class:`Value`\ s around between functions wrapped
with :py:func:`fn` and :py:func:`instantaneous_fn`.
