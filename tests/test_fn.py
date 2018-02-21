from mock import Mock

from yarp import NoValue, Value, fn, instantaneous_fn

def test_no_args():
    @fn
    def example():
        return 123
    
    # Function call should return a Value with the function called just the
    # once. Since it takes no arguments, it won't ever be called again.
    result = example()
    assert result.value == 123


def test_positional_args():
    m = Mock()
    
    @fn
    def example(a, b):
        return a - b
    
    a_value = Value(10)
    b_value = Value(5)
    
    # Initial value should pass through
    result = example(a_value, b_value)
    result.on_value_changed(m)
    assert result.value == 5
    
    # Changes should propagate, callbacks should fire
    m.reset_mock()
    a_value.value = 20
    m.assert_called_once_with(15)
    assert result.value == 15
    
    m.reset_mock()
    b_value.value = -5
    m.assert_called_once_with(25)
    assert result.value == 25


def test_positional_kwargs():
    m = Mock()
    
    @fn
    def example(a, b):
        return a - b
    
    a_value = Value(10)
    b_value = Value(5)
    
    # Initial value should pass through
    result = example(a=a_value, b=b_value)
    result.on_value_changed(m)
    assert result.value == 5
    
    # Changes should propagate, callbacks should fire
    m.reset_mock()
    a_value.value = 20
    m.assert_called_once_with(15)
    assert result.value == 15
    
    m.reset_mock()
    b_value.value = -5
    m.assert_called_once_with(25)
    assert result.value == 25


def test_inst_positional_args():
    m = Mock()
    
    @instantaneous_fn
    def example(*args, **kwargs):
        return (args, kwargs)
    
    a_value = Value()
    b_value = Value()
    
    # No value should be assigned
    result = example(a_value, b_value)
    result.on_value_changed(m)
    assert result.value is NoValue
    
    # Changes should propagate, callbacks should fire but no value should be
    # stored
    m.reset_mock()
    a_value.set_instantaneous_value(123)
    m.assert_called_once_with(((123, NoValue), {}))
    assert result.value is NoValue
    
    m.reset_mock()
    b_value.set_instantaneous_value(123)
    m.assert_called_once_with(((NoValue, 123), {}))
    assert result.value is NoValue


def test_inst_positional_kwargs():
    m = Mock()
    
    @instantaneous_fn
    def example(*args, **kwargs):
        return (args, kwargs)
    
    a_value = Value()
    b_value = Value()
    
    # No value should be assigned
    result = example(a=a_value, b=b_value)
    result.on_value_changed(m)
    assert result.value is NoValue
    
    # Changes should propagate, callbacks should fire but no value should be
    # stored
    m.reset_mock()
    a_value.set_instantaneous_value(123)
    m.assert_called_once_with(((), {"a": 123, "b": NoValue}))
    assert result.value is NoValue
    
    m.reset_mock()
    b_value.set_instantaneous_value(123)
    m.assert_called_once_with(((), {"a": NoValue, "b": 123}))
    assert result.value is NoValue
