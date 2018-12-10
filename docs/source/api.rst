.. module:: yarp

``yarp`` API
============

Value type
----------

At the core of the ``yarp`` API is the :py:class:`Value` type. This type is
defined below.

.. autodata:: NoValue

.. autoclass:: Value

Aggregate Values
----------------

The ``yarp`` API provides a limited set of convenience functions which which
turn certain native Python data structures into :py:class:`Value`\ s which
update whenever the underlying :py:class:`Value`\ s do.

.. autofunction:: value_list

.. autofunction:: value_tuple

.. autofunction:: value_dict

Value casting
-------------

The following low-level funcitons are provided for creating and casting
:py:class:`Value` objects.

.. autofunction:: ensure_value

.. autofunction:: make_instantaneous

.. autofunction:: make_persistent

Value Operators
---------------

The :py:class:`Value` class also supports many (but not all) of the native
Python operations, producing corresponding (continuous) :py:class:`Value`
objects as results. These operations support the mixing of :py:class:`Value`
objects and other suitable Python objects. The following operators are
supported:

* Arithmetic
    * ``a + b``
    * ``a - b``
    * ``a * b``
    * ``a @ b``
    * ``a / b``
    * ``a // b``
    * ``a % b``
    * ``divmod(a, b)``
    * ``a ** b``
* Bit-wise
    * ``a << b``
    * ``a >> b``
    * ``a & b``
    * ``a | b``
    * ``a ^ b``
* Unary
    * ``-a``
    * ``+a``
    * ``abs(a)``
    * ``~a``
* Comparison
    * ``a < b``
    * ``a <= b``
    * ``a == b``
    * ``a != b``
    * ``a >= b``
    * ``a > b``
* Container operators
    * ``a[key]``
* Numerical conversions
    * ``complex(a)``
    * ``int(a)``
    * ``float(a)``
    * ``round(a)``

Unfortunately this list *doesn't* include boolean operators (i.e.  ``not``,
``and``, ``or`` and ``bool``). This is due to a limitation of the Python data
model which means that ``bool`` may only return an actual boolean value, not
some other type of object. As a workaround you can substitute:

* ``bool(a)`` for ``a == True`` (works in most cases)
* ``a and b`` for ``a & b`` (works for boolean values but produces numbers)
* ``a or b`` for ``a | b`` (works for boolean values but produces numbers)

For a similar reasons, the ``len`` and ``in`` operators are also not supported.

This list also doesn't include mutating operators, for example ``a[key] = b``.
This is because the Python objects within a :py:class:`Value` are treated as
being immutable.

Finally, to reiterate, the result of these operators will always be continuous
:py:class:`Values`. For instantaneous versions of these operators, see the
Python builtins section below.

Python builtins
---------------

The ``yarp`` API provides :py:class:`Value`-compatible versions of a number of
Python builtins and functions from the standard library:

* Builtins
    * ``bool(a)``
    * ``any(a)``
    * ``all(a)``
    * ``min(a)``
    * ``max(a)``
    * ``sum(a)``
    * ``map(a)``
    * ``sorted(a)``
    * ``str(a)``
    * ``repr(a)``
    * ``str_format(a, ...)`` (equivalent to ``a.format(...)``)
    * ``oct(a)``
    * ``hex(a)``
    * ``zip(a)``
    * ``len(a)``
* Most non-mutating, non-underscore prefixed functions from the
  :py:mod:`operator` module.

These wrappers produce continuous :py:class:`Value`\ s. Corresponding
versions prefixed with ``instantaneous_`` are provided which produce
instantaneous :py:class:`Value`\ s.

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

.. autofunction:: replace_novalue

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

File-backed Values
------------------

The following function can be used to make *very* persistent
:py:class:`Value`\ s

.. autofunction:: file_backed_value
