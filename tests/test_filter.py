import pytest

from mock import Mock

from yarp import NoValue, Value, filter

@pytest.mark.parametrize("rule,pass_values,block_values", [
    (NoValue, [0, 123, True, False, None], [NoValue]),
    (None, [123, True], [NoValue, False, None, 0]),
    (lambda x: x != 123, [0, True, False, None, NoValue], [123]),
    
])
def test_check_value(rule, pass_values, block_values):
    # Test the internal rule-checking implementation
    v = Value(123)
    fv = filter(v, rule)
    
    for value in pass_values:
        assert fv._check_value(value) is True
    for value in block_values:
        assert fv._check_value(value) is False


def test_check_initial_value():
    # Initial value should also be filtered
    rule = lambda x: x == 123
    
    v = Value(123)
    fl = filter(v, rule)
    assert fl.value == 123
    
    v = Value(321)
    fl = filter(v, rule)
    assert fl.value is NoValue


def test_change_persistent():
    rule = lambda x: x < 10
    
    m = Mock()
    v = Value(1)
    fl = filter(v, rule)
    fl.on_value_changed(m)
    assert fl.value == 1
    
    v.value = 2
    assert fl.value == 2
    m.assert_called_once_with(2)
    
    # Above ten, shouldn't get through
    v.value = 100
    assert fl.value == 2
    m.assert_called_once_with(2)

def test_change_persistent_initial_value_filtered():
    rule = lambda x: x < 10
    
    v = Value(123)
    fl = filter(v, rule)
    
    # Initial value should be rejected by the filter and thus not passed
    # through
    assert fl.value is NoValue


def test_change_instantaneous():
    rule = lambda x: x < 10
    
    m = Mock()
    v = Value()
    fl = filter(v, rule)
    fl.on_value_changed(m)
    assert fl.value is NoValue
    
    v.set_instantaneous_value(2)
    assert fl.value is NoValue
    m.assert_called_once_with(2)
    
    # Above ten, shouldn't get through
    v.set_instantaneous_value(100)
    assert fl.value is NoValue
    m.assert_called_once_with(2)

