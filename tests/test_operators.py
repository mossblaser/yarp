from mock import Mock

from yarp import NoValue, Value, value_list, value_dict, \
    add, instantaneous_not_, str_format

def test_operator_wrapper_continous():
    # Only test addition since others are defined in exactly the same way
    a = Value(1)
    b = Value(2)
    
    a_add_b = add(a, b)
    assert a_add_b.value == 3
    
    a.value = 10
    assert a_add_b.value == 12

def test_operator_wrapper_instantaneous():
    # Only test negation since others are defined in exactly the same way
    a = Value()
    
    not_a = instantaneous_not_(a)
    assert not_a.value is NoValue
    
    m = Mock()
    not_a.on_value_changed(m)
    
    a.set_instantaneous_value(True)
    assert not_a.value is NoValue
    m.assert_called_once_with(False)
    m.reset_mock()
    
    a.set_instantaneous_value(False)
    assert not_a.value is NoValue
    m.assert_called_once_with(True)
    m.reset_mock()

def test_str_format_operator():
    # Special attention due for str_format as its an almost custom function(!)
    a = Value(0xAB)
    b = Value("hi")
    fmt = Value("{}, {}")

    stringified = str_format(fmt, a, b)
    assert stringified.value == "171, hi"
    
    a.value = 0xBC
    assert stringified.value == "188, hi"
    
    b.value = "foo"
    assert stringified.value == "188, foo"
    
    fmt.value = "0x{:04X}: {!r}"
    assert stringified.value == "0x00BC: 'foo'"

def test_native_value_operators():
    """Not exhaustive but just checks the most valuable ones."""
    a = Value(1)
    b = Value(2)
    c = value_list([a, b])
    d = value_dict({"ay": a, "be": b})
    
    a_add_b = a + b
    assert a_add_b.value == 3
    
    a.value = 0
    assert a_add_b.value == 2
    
    minus_b = -b
    assert minus_b.value == -2
    
    # Comparison
    a_lt_b = a < b
    a_eq_b = a == b
    assert a_lt_b.value
    assert not a_eq_b.value
    a.value = 2
    assert not a_lt_b.value
    assert a_eq_b.value
    
    # Non-Value things should get converted
    b_add_3 = b + 3
    assert b_add_3.value == 5
    
    four_sub_b = 4 - b
    assert four_sub_b.value == 2
    
    # Indexing
    c_0 = c[0]
    assert c_0.value == 2
    a.value = -1
    assert c_0.value == -1
    
    # Slicing
    c_backwards = c[::-1]
    assert c_backwards.value == [2, -1]
    b.value = 20
    assert c_backwards.value == [20, -1]
    a.value = -10
    assert c_backwards.value == [20, -10]
    
    # Dictionaries
    d_ay = d["ay"]
    assert d_ay.value == -10
    a.value = 10
    assert d_ay.value == 10

def test_operator_wrapper_docstring():
    assert "continous value" in Value.__add__.__doc__.lower()
    assert "continous value" in add.__doc__.lower()
    assert "instantaneous value" in instantaneous_not_.__doc__.lower()
