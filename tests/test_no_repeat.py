from mock import Mock

from yarp import NoValue, Value, no_repeat

def test_no_repeat_persistent():
    v = Value(1)
    
    # Initial value should come through
    nrv = no_repeat(v)
    assert nrv.value == 1
    
    m = Mock()
    nrv.on_value_changed(m)
    
    # Same value doesn't pass through
    v.value = 1
    assert not m.called
    
    # New values do
    v.value = 2
    assert nrv.value == 2
    m.assert_called_once_with(2)


def test_no_repeat_instantaneous():
    v = Value()
    
    nrv = no_repeat(v)
    assert nrv.value is NoValue
    
    m = Mock()
    nrv.on_value_changed(m)
    
    # New value should pass through
    v.set_instantaneous_value(1)
    m.assert_called_once_with(1)
    assert nrv.value is NoValue
    
    # Repeat should not
    m.reset_mock()
    v.set_instantaneous_value(1)
    assert not m.called
    assert nrv.value is NoValue
    
    # New value should pass through
    v.set_instantaneous_value(2)
    m.assert_called_once_with(2)
    assert nrv.value is NoValue
