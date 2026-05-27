from cryptography.fernet import Fernet, MultiFernet, InvalidToken
from app.core.config import settings

# Build MultiFernet so key rotation works: add new key first, old key second.
# To rotate: set FERNET_KEY="new_key,old_key" and re-encrypt records in a migration job.
_keys = [Fernet(k.strip().encode()) for k in settings.FERNET_KEY.split(",")]
_fernet = MultiFernet(_keys)


def encrypt_field(plaintext: str) -> str:
    """Encrypt a PHI field. Returns URL-safe base64 ciphertext."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_field(ciphertext: str) -> str:
    """Decrypt a PHI field. Raises InvalidToken if the ciphertext was tampered."""
    return _fernet.decrypt(ciphertext.encode()).decode()
