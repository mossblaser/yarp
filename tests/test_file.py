from yarp import NoValue, file_backed_value

def test_file_backed_value(tmpdir):
    filename = str(tmpdir.join("test.pickle"))
    
    v1 = file_backed_value(filename, "initial")
    assert v1.value == "initial"
    v1.value = 123
    
    # Value should be restored from disk
    v2 = file_backed_value(filename, "initial")
    assert v2.value == 123
    
    # Should be able to store NoValue
    v2.value = NoValue
    assert v2.value == NoValue
    
    # Should be able to read it
    v3 = file_backed_value(filename, "initial")
    assert v3.value == NoValue
