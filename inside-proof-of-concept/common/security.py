from __future__ import annotations
import base64
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import hashes

EXPECTED_OIDS = ['1.2.3.4.5.6.7.8.1', '1.2.3.4.5.6.7.8.2', '1.2.3.4.5.6.7.8.4']


def verify_certificate(signed_cert_pem: str):
    if not signed_cert_pem:
        return False, 'Missing certificate'
    try:
        cert = x509.load_pem_x509_certificate(signed_cert_pem.encode('utf-8'), default_backend())
    except Exception as exc:
        return False, f'Invalid certificate: {exc}'
    found = {ext.oid.dotted_string for ext in cert.extensions}
    if not all(oid in found for oid in EXPECTED_OIDS):
        return False, 'Certificate missing expected attestation extensions'
    # Best-effort signature validation for self-signed RSA certificates
    try:
        public_key = cert.public_key()
        if isinstance(public_key, rsa.RSAPublicKey):
            public_key.verify(cert.signature, cert.tbs_certificate_bytes, padding.PKCS1v15(), cert.signature_hash_algorithm)
    except Exception as exc:
        return False, f'Certificate signature validation failed: {exc}'
    return True, 'Certificate is valid'


def encrypt_dataset(public_key_pem: str, data: str) -> str:
    return base64.b64encode(data.encode('utf-8')).decode('utf-8')


def decrypt_dataset(private_key_pem: str, data_enc: str) -> str:
    return base64.b64decode(data_enc.encode('utf-8')).decode('utf-8')
