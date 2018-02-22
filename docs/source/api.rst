.. module:: yarp

``yarp`` API
============

Value type
----------

At the core of the ``yarp`` API is the :py:class:`Value` type. This type is
defined below.

.. autodata:: NoValue

.. autoclass:: Value

Aggregate Value types
---------------------

The ``yarp`` API provides a limited set of convenience wrappers around
:py:class:`Value` which turn certain native Python data structures into
:py:class:`Value`\ s which update whenever the underlying :py:class:`Value`\ s
do.

.. autoclass:: ListValue

.. autoclass:: TupleValue

.. autoclass:: DictValue

Value casting
-------------

The following low-level funcitons are provided for creating and casting
:py:class:`Value` objects.

.. autofunction:: ensure_value

.. autofunction:: make_instantaneous

.. autofunction:: make_persistent


Function wrappers
-----------------

The primary mode of interaction with ``yarp`` :py:class:`Value`\ s is intended
to be via simple Python functions wrapped with :py:func:`fn` or
:py:func:`instantaneous_fn`. These wrappers are defined below.

.. autofunction:: fn

.. autofunction:: instantaneous_fn

General Value manipulation
--------------------------

The following utility functions are defined which accept and return
:py:class:`Value`\ s.

.. autofunction:: window

.. autofunction:: no_repeat

.. autofunction:: filter

Temporal Value manipulation
---------------------------

The following utility functions are defined which accept and return
:py:class:`Value`\ s but may delay or filter changes. These all use
:py:mod:`asyncio` internally and require that a
:py:class:`asyncio.BaseEventLoop` be running.

.. autofunction:: delay

.. autofunction:: time_window

.. autofunction:: rate_limit
