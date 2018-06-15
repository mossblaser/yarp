"""
File-backed Yarp Values.
"""

import asyncio
import pickle
import traceback

from yarp import NoValue, Value

__names__ = [
    "file_backed_value",
]

def file_backed_value(filename, initial_value=NoValue):
    """
    A persistent, file-backed value.
    
    Upon creation, the value will be loaded from the specified filename.
    Whenever the value is changed it will be rewritten to disk. Changes made to
    the file while your program is running will be ignored.
    
    If the file does not exist, it will be created and the value set to
    the value given by `initial_value`.
    
    The value must be pickleable.
    """
    try:
        with open(filename, "rb") as f:
            source_value = Value(pickle.load(f))
    except FileNotFoundError:
        # If the file doesn't exist, use the initial value
        source_value = Value(initial_value)
    except Exception:
        # If there's a pickling error or similar, show the error but continue
        # with the provided initial value.
        traceback.print_exc()
        source_value = Value(initial_value)
    
    # Store changes to disk
    @source_value.on_value_changed
    def on_value_changed(new_value):
        with open(filename, "wb") as f:
            pickle.dump(new_value, f)
    
    # Immediately trigger a store (incase the file did not exist yet)
    on_value_changed(source_value.value)
    
    return source_value
