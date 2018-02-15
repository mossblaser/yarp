from mock import Mock

from yarp import \
    NoValue, Value, ListValue, DictValue, ensure_value, make_persistent, \
    make_instantaneous


def test_initial_value_default():
    v = Value()
    assert v.value is NoValue

def test_initial_value_specified():
    v = Value(123)
    assert v.value == 123

def test_change_callback():
    m = Mock()
    
    v = Value()
    v.on_value_changed(m)
    
    v.value = 123
    m.assert_called_once_with(123)

def test_change_callback_only():
    m = Mock()
    
    v = Value()
    v.on_value_changed(m)
    
    v.value_changed(123)
    m.assert_called_once_with(123)
    assert v.value is NoValue


def test_list_value_persistent():
    a = Value("a")
    b = Value("b")
    c = Value("c")
    
    lst = ListValue([a, b, c])
    
    # Initial value should have passed through
    assert lst.value == ["a", "b", "c"]
    
    m = Mock()
    lst.on_value_changed(m)
    
    # Changes should propagate through
    a.value = "A"
    assert lst.value == ["A", "b", "c"]
    m.assert_called_once_with(["A", "b", "c"])
    
    m.reset_mock()
    b.value = "B"
    assert lst.value == ["A", "B", "c"]
    m.assert_called_once_with(["A", "B", "c"])
    
    m.reset_mock()
    c.value = "C"
    assert lst.value == ["A", "B", "C"]
    m.assert_called_once_with(["A", "B", "C"])


def test_list_value_instantaneous():
    # A mix of instantaneous and continuous
    a = Value("a")
    b = Value()
    c = Value()
    
    lst = ListValue([a, b, c])
    
    # Initial value should have passed through
    assert lst.value == ["a", NoValue, NoValue]
    
    m = Mock()
    lst.on_value_changed(m)
    
    # Changes should propagate through
    a.value = "A"
    assert lst.value == ["A", NoValue, NoValue]
    m.assert_called_once_with(["A", NoValue, NoValue])
    
    # Instantaneous values should propagate only into the callback
    m.reset_mock()
    b.value_changed("b")
    assert lst.value == ["A", NoValue, NoValue]
    m.assert_called_once_with(["A", "b", NoValue])
    
    m.reset_mock()
    c.value_changed("c")
    assert lst.value == ["A", NoValue, NoValue]
    m.assert_called_once_with(["A", NoValue, "c"])


def test_dict_value_persistent():
    a = Value("a")
    b = Value("b")
    c = Value("c")
    
    dct = DictValue({"a": a, "b": b, "c": c})
    
    # Initial value should have passed through
    assert dct.value == {"a": "a", "b": "b", "c": "c"}
    
    m = Mock()
    dct.on_value_changed(m)
    
    # Changes should propagate through
    a.value = "A"
    assert dct.value == {"a": "A", "b": "b", "c": "c"}
    m.assert_called_once_with({"a": "A", "b": "b", "c": "c"})
    
    m.reset_mock()
    b.value = "B"
    assert dct.value == {"a": "A", "b": "B", "c": "c"}
    m.assert_called_once_with({"a": "A", "b": "B", "c": "c"})
    
    m.reset_mock()
    c.value = "C"
    assert dct.value == {"a": "A", "b": "B", "c": "C"}
    m.assert_called_once_with({"a": "A", "b": "B", "c": "C"})


def test_dict_value_instantaneous():
    # A mix of instantaneous and continuous
    a = Value("a")
    b = Value()
    c = Value()
    
    dct = DictValue({"a": a, "b": b, "c": c})
    
    # Initial value should have passed through
    assert dct.value == {"a": "a", "b": NoValue, "c": NoValue}
    
    m = Mock()
    dct.on_value_changed(m)
    
    # Changes should propagate through
    a.value = "A"
    assert dct.value == {"a": "A", "b": NoValue, "c": NoValue}
    m.assert_called_once_with({"a": "A", "b": NoValue, "c": NoValue})
    
    # Instantaneous values should propagate only into the callback
    m.reset_mock()
    b.value_changed("b")
    assert dct.value == {"a": "A", "b": NoValue, "c": NoValue}
    m.assert_called_once_with({"a": "A", "b": "b", "c": NoValue})
    
    m.reset_mock()
    c.value_changed("c")
    assert dct.value == {"a": "A", "b": NoValue, "c": NoValue}
    m.assert_called_once_with({"a": "A", "b": NoValue, "c": "c"})

def test_ensure_value_non_value():
    v = ensure_value(123)
    assert isinstance(v, Value)
    assert v.value == 123

def test_ensure_value_already_value():
    v = Value(123)
    vv = ensure_value(v)
    assert vv is v

def test_ensure_value_list():
    a = 123
    b = Value(456)
    
    v = ensure_value([a, b])
    assert isinstance(v, Value)
    assert v.value == [123, 456]
    
    b.value = 789
    assert v.value == [123, 789]

def test_ensure_value_dict():
    a = 123
    b = Value(456)
    
    v = ensure_value({"a": a, "b": b})
    assert isinstance(v, Value)
    assert v.value == {"a": 123, "b": 456}
    
    b.value = 789
    assert v.value == {"a": 123, "b": 789}

def test_ensure_value_nested():
    a = Value(123)
    b = Value(456)
    c = Value(789)
    
    v = ensure_value({"a": a, "bc": [b, c]})
    assert isinstance(v, Value)
    assert v.value == {"a": 123, "bc": [456, 789]}
    
    b.value = 654
    assert v.value == {"a": 123, "bc": [654, 789]}

def test_make_instantaneous():
    v = Value(1)
    
    iv = make_instantaneous(v)
    m = Mock()
    iv.on_value_changed(m)
    
    assert iv.value is NoValue
    
    v.value = 2
    assert iv.value is NoValue
    m.assert_called_once_with(2)

def test_make_persistent():
    v = Value()
    
    # Initially no value to be found...
    pv = make_persistent(v)
    assert pv.value is NoValue
    
    m = Mock()
    pv.on_value_changed(m)
    
    assert pv.value is NoValue
    
    v.value_changed(2)
    assert pv.value == 2
    m.assert_called_once_with(2)
