


def test_enforce_standard():
    """Test sample strings that don't follow the standard"""

    from lib import signature

    assert signature.enforce_standard("1,2,3|4,5,6|7,8,9") == True
    assert signature.enforce_standard("1,2,3|4,5,6|7,8,9|10") == True
    assert signature.enforce_standard("1|2|3,4|5|6") == True

    assert signature.enforce_standard("1,2,3|4,5,6|7,8,9|") == False
    assert signature.enforce_standard("|1,2,3|4,5,6|7,8,9") == False

    assert signature.enforce_standard("1,2,3|4,5,6|7,8,9|10,") == False
    assert signature.enforce_standard(",1,2,3|4,5,6|7,8,9|10") == False

    assert signature.enforce_standard("1,2,ab|4,5,6|7,8,9|10,11") == False
    assert signature.enforce_standard("1,2,3.5|4,5,6|7,8,9|10,11") == False
    assert signature.enforce_standard("1,,2,3|4,5,6|7,8,9|10,11") == False