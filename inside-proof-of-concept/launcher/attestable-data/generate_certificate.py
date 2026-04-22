from __future__ import annotations
import datetime, glob, hashlib, os, platform, subprocess, sys
from pathlib import Path
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography import x509
from cryptography.x509.oid import NameOID


def _run_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception:
        return ''


def collect_attestable_data(proc_pid: str | None = None) -> dict:
    model = _run_command(['sysctl', '-n', 'hw.model']) or platform.machine()
    ncpu = _run_command(['sysctl', '-n', 'hw.ncpu']) or str(os.cpu_count() or 1)
    mem_addresses = ''
    if proc_pid:
        mem_addresses = _run_command(['procstat', '-v', str(proc_pid)])
    return {'model': model, 'ncpu': ncpu, 'memory': mem_addresses}


def generate_attestation_certificate(executable_path: str | Path, cert_dir: str | Path, proc_pid: str | None = None) -> dict:
    executable_path = Path(executable_path)
    cert_dir = Path(cert_dir)
    cert_dir.mkdir(parents=True, exist_ok=True)
    signature_base_dir = cert_dir.parent.parent / 'attestable-data' / 'signatures'
    signature_base_dir.mkdir(parents=True, exist_ok=True)

    data = collect_attestable_data(proc_pid)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    public_key = private_key.public_key()

    with executable_path.open('rb') as f:
        executable_data = f.read()
    executable_hash = hashlib.sha256(executable_data).digest()
    signature = private_key.sign(executable_hash, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, 'BR'),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, 'Rio Grande do Sul'),
        x509.NameAttribute(NameOID.LOCALITY_NAME, 'Ijui'),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'Unijui'),
        x509.NameAttribute(NameOID.COMMON_NAME, 'Integration Process Certificate'),
    ])
    cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(public_key).serial_number(
        x509.random_serial_number()).not_valid_before(datetime.datetime.now(datetime.UTC)).not_valid_after(
        datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365)
    ).add_extension(x509.SubjectAlternativeName([x509.DNSName('unijui.edu.br')]), critical=False
    ).add_extension(x509.UnrecognizedExtension(x509.ObjectIdentifier('1.2.3.4.5.6.7.8.1'), bytes(f"Model: {data['model']}", 'utf-8')), critical=False
    ).add_extension(x509.UnrecognizedExtension(x509.ObjectIdentifier('1.2.3.4.5.6.7.8.2'), bytes(f"CPUs: {data['ncpu']}", 'utf-8')), critical=False
    ).add_extension(x509.UnrecognizedExtension(x509.ObjectIdentifier('1.2.3.4.5.6.7.8.3'), bytes(f"Memory: {data['memory']}", 'utf-8')), critical=False
    ).add_extension(x509.UnrecognizedExtension(x509.ObjectIdentifier('1.2.3.4.5.6.7.8.4'), executable_hash), critical=False
    ).add_extension(x509.UnrecognizedExtension(x509.ObjectIdentifier('1.2.3.4.5.6.7.8.5'), signature), critical=False
    ).sign(private_key, hashes.SHA256(), default_backend())

    private_key_path = cert_dir / 'private_key.pem'
    public_key_path = cert_dir / 'public_key.pem'
    certificate_path = cert_dir / 'certificate.pem'
    signature_path = signature_base_dir / f'{executable_path.name}_signature.txt'

    private_key_path.write_bytes(private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.TraditionalOpenSSL, encryption_algorithm=serialization.NoEncryption()))
    public_key_path.write_bytes(public_key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo))
    certificate_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    signature_path.write_bytes(signature)

    return {
        'certificate_path': str(certificate_path),
        'public_key_path': str(public_key_path),
        'private_key_path': str(private_key_path),
        'signature_path': str(signature_path),
        'executable_hash_hex': executable_hash.hex(),
        'attestable_data': data,
    }


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: generate_certificate.py <executable_path> <cert_dir> [pid]')
        sys.exit(1)
    result = generate_attestation_certificate(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    print(result['executable_hash_hex'])
    print(result['certificate_path'])
