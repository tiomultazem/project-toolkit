import base64
import hashlib
import hmac
import json
import os


PBKDF2_ROUNDS = 200_000


def stream(passphrase: str, salt: bytes, length: int) -> bytes:  # bikin byte stream dari passphrase
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, PBKDF2_ROUNDS)
    chunks = []
    total = 0
    counter = 0
    while total < length:
        counter_bytes = counter.to_bytes(8, "big")
        chunk = hmac.new(key, counter_bytes, hashlib.sha256).digest()
        chunks.append(chunk)
        total += len(chunk)
        counter += 1
    return b"".join(chunks)[:length]


def xor(data: bytes, key_stream: bytes) -> bytes:  # enkripsi/dekripsi XOR
    return bytes(item ^ key_stream[index] for index, item in enumerate(data))


def encrypt_bytes(data: bytes, passphrase: str) -> str:  # enkripsi bytes jadi payload teks
    salt = os.urandom(16)
    cipher = xor(data, stream(passphrase, salt, len(data)))
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, PBKDF2_ROUNDS)
    tag = hmac.new(key, data, hashlib.sha256).hexdigest()
    payload = {
        "v": 1,
        "salt": base64.b64encode(salt).decode(),
        "cipher": base64.b64encode(cipher).decode(),
        "tag": tag,
    }
    packed = json.dumps(payload, separators=(",", ":")).encode()
    return base64.b64encode(packed).decode()


def decrypt_bytes(payload_text: str, passphrase: str) -> bytes:  # dekripsi payload teks jadi bytes
    payload = json.loads(base64.b64decode(payload_text).decode())
    if payload.get("v") != 1:
        raise ValueError("versi payload tidak dikenal")
    salt = base64.b64decode(payload["salt"])
    cipher = base64.b64decode(payload["cipher"])
    plain = xor(cipher, stream(passphrase, salt, len(cipher)))
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, PBKDF2_ROUNDS)
    tag = hmac.new(key, plain, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(tag, payload["tag"]):
        raise ValueError("passphrase salah")
    return plain


def encrypt(source: str, passphrase: str) -> str:  # simpan source asli terenkripsi
    return encrypt_bytes(source.encode("utf-8"), passphrase)


def decrypt(payload_text: str, passphrase: str) -> str:  # buka payload terenkripsi
    return decrypt_bytes(payload_text, passphrase).decode("utf-8")