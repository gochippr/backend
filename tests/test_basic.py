# tests/test_basic.py
def test_basic_math():
    """Basic test to ensure pytest is working."""
    assert 1 + 1 == 2

def test_string_operations():
    """Test basic string operations."""
    text = "hello"
    assert text.upper() == "HELLO"
    assert len(text) == 5