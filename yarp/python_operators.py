"""
Implementations of native Python operations on :py:class:`Value` objects.
"""

from functools import wraps

from yarp.function_wrappers import Value, fn, instantaneous_fn

import operator

# Functions from the operator module to wrap.
wrapped_operator_functions = [
    # Comparison
    "lt",
    "le",
    "eq",
    "ne",
    "ge",
    "gt",
    # Logical operators
    "not_",
    "truth",
    "is_",
    "is_not",
    # Mathematical/bitwise
    "abs",
    "add",
    "and_",
    "floordiv",
    "index",
    "inv",
    "invert",
    "lshift",
    "mod",
    "mul",
    "matmul",
    "neg",
    "or_",
    "pos",
    "pow",
    "rshift",
    "sub",
    "truediv",
    "xor",
    "concat",
    "contains",
    "countOf",
    "getitem",
    "indexOf",
    "length_hint",
]

# Array of (name, function, native name, e.g. operator.add) tuples.
wrapped_functions = [
    ("bool", bool, "bool"),
    ("min", min, "min"),
    ("max", max, "max"),
    ("sum", sum, "sum"),
    ("map", map, "map"),
    ("sorted", sorted, "sorted"),
    ("str", str, "str"),
    ("repr", repr, "repr"),
    ("str_format",
        lambda a, *args, **kwargs: a.format(*args, **kwargs),
        "str.format(...)"),
    ("oct", oct, "oct"),
    ("hex", hex, "hex"),
    ("zip", zip, "zip"),
] + [
    (name, getattr(operator, name), "operator.{}".format(name))
    for name in wrapped_operator_functions
]

for function_name, function, full_name in wrapped_functions:
    continous = fn(function)
    continous.__doc__ = \
        "Version of {} which returns a continous Values\n{}".format(
            full_name, continous.__doc__
        )
    
    instantaneous = instantaneous_fn(function)
    instantaneous.__doc__ = \
        "Version of {} which returns an instantaneous Values\n{}".format(
            full_name, instantaneous.__doc__
        )
    
    # Add operators to namespace
    globals()[function_name] = continous
    globals()["instantaneous_" + function_name] = instantaneous

def swap_args(f):
    """
    Return a version of 'f' which takes two arguments in the opposite order.
    """
    @wraps(f)
    def wrapper(*args):
        return f(*reversed(args))
    return wrapper

value_operators = [
    # Arithmatic
    ("__add__", operator.add, "a + b"),
    ("__sub__", operator.sub, "a - b"),
    ("__mul__", operator.mul, "a * b"),
    ("__matmul__", operator.matmul, "a @ b"),
    ("__truediv__", operator.truediv, "a / b"),
    ("__floordiv__", operator.floordiv, "a // b"),
    ("__mod__", operator.floordiv, "a % b"),
    ("__divmod__", lambda a, b: divmod(a, b), "divmod(a, b)"),
    ("__pow__", operator.pow, "a ** b"),
    ("__lshift__", operator.lshift, "a << b"),
    ("__rshift__", operator.rshift, "a >> b"),
    ("__and__", operator.and_, "a & b"),
    ("__xor__", operator.xor, "a ^ b"),
    ("__or__", operator.or_, "a | b"),
    # Reversed-Arithmatic
    ("__radd__", swap_args(operator.add), "b + a"),
    ("__rsub__", swap_args(operator.sub), "b - a"),
    ("__rmul__", swap_args(operator.mul), "b * a"),
    ("__rmatmul__", swap_args(operator.matmul), "b @ a"),
    ("__rtruediv__", swap_args(operator.truediv), "b / a"),
    ("__rfloordiv__", swap_args(operator.floordiv), "b // a"),
    ("__rmod__", swap_args(operator.floordiv), "b % a"),
    ("__rdivmod__", lambda b, a: divmod(a, b), "divmod(b, a)"),
    ("__rpow__", swap_args(operator.pow), "b ** a"),
    ("__rlshift__", swap_args(operator.lshift), "b << a"),
    ("__rrshift__", swap_args(operator.rshift), "b >> a"),
    ("__rand__", swap_args(operator.and_), "b & a"),
    ("__rxor__", swap_args(operator.xor), "b ^ a"),
    ("__ror__", swap_args(operator.or_), "b | a"),
    # Unary operators
    ("__neg__", operator.neg, "-a"),
    ("__pos__", operator.pos, "+a"),
    ("__abs__", operator.abs, "abs(a)"),
    ("__invert__", operator.invert, "~a"),
    # Comparisons
    ("__lt__", operator.lt, "a < b"),
    ("__le__", operator.le, "a <= b"),
    ("__eq__", operator.eq, "a == b"),
    ("__ne__", operator.ne, "a != b"),
    ("__ge__", operator.ge, "a >= b"),
    ("__gt__", operator.gt, "a > b"),
    # Container acceessors
    ("__getitem__", operator.getitem, "a[key]"),
    # Type conversions
    ("__complex__", complex, "complex(a)"),
    ("__int__", int, "int(a)"),
    ("__float__", float, "float(a)"),
    ("__round__", round, "round(a)"),
]
for function_name, native_function, doc in value_operators:
    continous = fn(native_function)
    continous.__doc__ = "{} (returning a continous Value)".format(doc)
    
    # Add to Value class as operator implementations
    setattr(Value, function_name, continous)

__names__ = (
    [name for name, _, _ in wrapped_functions] +
    ["instantaneous_" + name for name, _, _ in wrapped_functions]
)
