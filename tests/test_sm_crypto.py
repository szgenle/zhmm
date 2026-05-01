"""Tests for zhmm.data.sm_crypto — encrypt/decrypt roundtrip."""

import pytest

from zhmm.data.sm_crypto import SmCrypto


@pytest.fixture
def crypto():
    c = SmCrypto()
    c.init(open_id="test_user", pwd="StrongPassw0rd!")
    return c


class TestInitValidation:
    def test_empty_open_id_raises(self):
        c = SmCrypto()
        with pytest.raises(ValueError):
            c.init(open_id="", pwd="anything")

    def test_empty_pwd_raises(self):
        c = SmCrypto()
        with pytest.raises(ValueError):
            c.init(open_id="user", pwd="")


class TestRoundtrip:
    def test_ascii_roundtrip(self, crypto):
        plain = "hello, world!"
        encrypted = crypto.encrypt(plain)
        assert encrypted and encrypted != plain
        assert crypto.decrypt(encrypted) == plain

    def test_unicode_roundtrip(self, crypto):
        plain = "你好，世界！🌍"
        encrypted = crypto.encrypt(plain)
        assert crypto.decrypt(encrypted) == plain

    def test_long_text_roundtrip(self, crypto):
        plain = ("abc123" * 200)  # 1200 chars
        encrypted = crypto.encrypt(plain)
        assert crypto.decrypt(encrypted) == plain

    def test_empty_plaintext_rejected(self, crypto):
        with pytest.raises(ValueError):
            crypto.encrypt("")


class TestDecryptFailure:
    def test_decrypt_empty_returns_none(self, crypto):
        assert crypto.decrypt("") is None

    def test_decrypt_too_short_returns_none(self, crypto):
        assert crypto.decrypt("abcd") is None

    def test_tampered_ciphertext_returns_none(self, crypto):
        encrypted = crypto.encrypt("secret")
        # 翻转最后一位，破坏验证哈希。
        tampered = encrypted[:-1] + ("0" if encrypted[-1] != "0" else "1")
        assert crypto.decrypt(tampered) is None

    def test_wrong_password_cannot_decrypt(self):
        c1 = SmCrypto()
        c1.init(open_id="user", pwd="password-a")
        encrypted = c1.encrypt("secret message")

        c2 = SmCrypto()
        c2.init(open_id="user", pwd="password-b")
        assert c2.decrypt(encrypted) is None

    def test_wrong_open_id_cannot_decrypt(self):
        c1 = SmCrypto()
        c1.init(open_id="user-a", pwd="shared")
        encrypted = c1.encrypt("secret message")

        c2 = SmCrypto()
        c2.init(open_id="user-b", pwd="shared")
        assert c2.decrypt(encrypted) is None
