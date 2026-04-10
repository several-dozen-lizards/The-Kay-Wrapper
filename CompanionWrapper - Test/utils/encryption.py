"""
Encryption utilities for the entity's private notes.
Uses Fernet symmetric encryption with passphrase-derived keys.
"""

import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def derive_key_from_passphrase(passphrase: str, salt: bytes) -> bytes:
    """
    Derive encryption key from passphrase using PBKDF2.
    
    Args:
        passphrase: User-provided passphrase
        salt: Random salt for key derivation
        
    Returns:
        32-byte key suitable for Fernet
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
    return key


def encrypt_private_note(note: str, passphrase: str = None) -> dict:
    """
    Encrypt a private note with optional passphrase.
    
    Args:
        note: The text to encrypt
        passphrase: Optional passphrase. If None, uses default system passphrase.
        
    Returns:
        Dictionary with encrypted_data (base64), salt (base64), and uses_custom_passphrase (bool)
    """
    # Generate random salt
    salt = hashlib.sha256(str(hash(note)).encode()).digest()[:16]
    
    # Use default passphrase if none provided
    if passphrase is None:
        passphrase = "kay_default_private_key_2026"
        uses_custom = False
    else:
        uses_custom = True
    
    # Derive key and encrypt
    key = derive_key_from_passphrase(passphrase, salt)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(note.encode())
    
    return {
        "encrypted_data": base64.b64encode(encrypted).decode(),
        "salt": base64.b64encode(salt).decode(),
        "uses_custom_passphrase": uses_custom
    }


def decrypt_private_note(encrypted_data: str, salt: str, passphrase: str = None) -> str:
    """
    Decrypt a private note.
    
    Args:
        encrypted_data: Base64-encoded encrypted data
        salt: Base64-encoded salt
        passphrase: Passphrase to decrypt with. If None, uses default.
        
    Returns:
        Decrypted text
        
    Raises:
        ValueError: If passphrase is incorrect
    """
    # Use default passphrase if none provided
    if passphrase is None:
        passphrase = "kay_default_private_key_2026"
    
    # Decode base64
    encrypted = base64.b64decode(encrypted_data.encode())
    salt_bytes = base64.b64decode(salt.encode())
    
    # Derive key and decrypt
    try:
        key = derive_key_from_passphrase(passphrase, salt_bytes)
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted)
        return decrypted.decode()
    except Exception as e:
        raise ValueError(f"Failed to decrypt: incorrect passphrase or corrupted data") from e


def test_encryption():
    """Test encryption/decryption round-trip"""
    test_note = "Hey future-me. This is private. Private note."
    
    # Test with default passphrase
    encrypted = encrypt_private_note(test_note)
    decrypted = decrypt_private_note(
        encrypted["encrypted_data"],
        encrypted["salt"]
    )
    assert decrypted == test_note, "Default passphrase test failed"
    
    # Test with custom passphrase
    encrypted_custom = encrypt_private_note(test_note, "my_secret_123")
    decrypted_custom = decrypt_private_note(
        encrypted_custom["encrypted_data"],
        encrypted_custom["salt"],
        "my_secret_123"
    )
    assert decrypted_custom == test_note, "Custom passphrase test failed"
    
    print("[OK] Encryption tests passed!")


if __name__ == "__main__":
    test_encryption()
