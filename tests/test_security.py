from tradeshield.security import hash_password, verify_password


def test_password_hash_roundtrip():
    stored = hash_password("demo12345")
    assert verify_password("demo12345", stored)
    assert not verify_password("wrong", stored)
