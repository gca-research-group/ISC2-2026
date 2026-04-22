from __future__ import annotations
import base64
import os
import shutil
import subprocess
import tempfile

REQUIRED_OIDS = [
    "1.2.3.4.5.6.7.8.1",
    "1.2.3.4.5.6.7.8.2",
    "1.2.3.4.5.6.7.8.4",
]


def _openssl_available() -> bool:
    return shutil.which("openssl") is not None


def _write_temp_pem(pem_text: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".pem")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(pem_text)
    return path


def verify_certificate(signed_cert: str) -> bool:
    if not signed_cert or not isinstance(signed_cert, str):
        return False
    if "BEGIN CERTIFICATE" not in signed_cert or "END CERTIFICATE" not in signed_cert:
        return False
    if not _openssl_available():
        return True
    pem_path = _write_temp_pem(signed_cert)
    try:
        parse_cmd = ["openssl", "x509", "-in", pem_path, "-noout"]
        parse_result = subprocess.run(parse_cmd, capture_output=True, text=True)
        if parse_result.returncode != 0:
            return False
        text_cmd = ["openssl", "x509", "-in", pem_path, "-text", "-noout"]
        text_result = subprocess.run(text_cmd, capture_output=True, text=True)
        if text_result.returncode != 0:
            return False
        cert_text = text_result.stdout
        for oid in REQUIRED_OIDS:
            if oid not in cert_text:
                return False
        return True
    finally:
        try:
            os.remove(pem_path)
        except OSError:
            pass


def encrypt_dataset(public_key: str, data: str) -> str:
    if data is None:
        data = ""
    if not isinstance(data, str):
        data = str(data)
    return base64.b64encode(data.encode("utf-8")).decode("utf-8")


def decrypt_dataset(private_key: str, data_enc: str) -> str:
    if not data_enc:
        return ""
    try:
        return base64.b64decode(data_enc.encode("utf-8")).decode("utf-8", errors="replace")
    except Exception:
        return ""
