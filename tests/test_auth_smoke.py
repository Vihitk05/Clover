from api.security import create_access_token, decode_token, hash_password, verify_password


def test_password_hash_roundtrip():
    raw = "super-secret-password"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True


def test_access_token_roundtrip():
    token = create_access_token(subject="user-123", extra={"email": "user@example.com"})
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
