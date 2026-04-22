# Messaging System – Simulated Service (`app-whatsapp`)

This service simulates a messaging application within a digital services integration architecture. The application enables the automated dispatch of confirmation messages to customers, based on transport bookings registered by a secure integration process.

The core components of this service are:

- A **secure REST API** implemented using Flask and served via HTTPS (`API3.py`);
- A **digital certificate verification mechanism** that attests the execution environment of the integration process requesting the message dispatch (`verifyCertificate.py`).

The service utilises X.509 digital certificates to ensure authenticity and secure communication.

---

## Components

- **`API3.py`**: REST API with HTTPS support for simulating message delivery.
- **`verifyCertificate.py`**: Script for validating X.509 certificates with custom extensions (automatically invoked by the API).
- **`keys/`**: Directory containing the cryptographic keys and digital certificates used by the service.

---

## System Requirements

- **Operating System**: Ubuntu 22.04.4 LTS
- **Processor**: Intel Core i5 (or equivalent or higher)
- **Memory (RAM)**: 4 GB
- **Storage**: 10 GB of available disk space

---

## Installation

### System Dependencies

```bash
sudo apt-get update
sudo apt-get install python3 python3-pip openssl
```

### Python Packages

```bash
pip install flask flask-talisman cryptography
pip install Flask twilio
```

---

## Execution

### REST API (HTTPS)

#### Certificate Generation:

```bash
openssl genpkey -algorithm RSA -out keys/priv.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -in keys/priv.pem -pubout -out keys/public_key.pem
openssl req -new -x509 -key keys/priv.pem -out keys/cert.pem -days 365
```

#### Launching the API:

```bash
cd api
python3 API3.py
```

> The API will be launched over HTTPS on port `8080`, using the certificates located in the `../keys` directory.

During execution, the service automatically validates the certificate of the integration process requesting the message dispatch. This verification includes a digital signature issued by a root certificate authority and the analysis of X.509 extensions containing information about the operating system and hardware environment (e.g., CheriBSD on Morello Board).

---

## Directory Structure

```plaintext
app-whatsapp/
├── api/
│   ├── API3.py                  # HTTPS REST API built with Flask
│   └── verifyCertificate.py     # Certificate verification logic (used internally by the API)
│
└── keys/
    ├── cert.pem                 # Service’s X.509 certificate
    └── priv.pem                 # Private RSA key
```

---

This service represents the third component of the digital integration architecture. It is responsible for notifying customers with confirmation messages once purchases and transport bookings have been successfully completed by the other integrated services.
