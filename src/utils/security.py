import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def get_cipher():
    password = os.getenv("MASTER_KEY", "default-unsafe-key-change-this").encode()
    salt = b'fixed-salt-for-demo' # In prod, use a unique salt per user/install
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return Fernet(key)

def encrypt_data(data: str) -> str:
    f = get_cipher()
    return f.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    f = get_cipher()
    return f.decrypt(encrypted_data.encode()).decode()
