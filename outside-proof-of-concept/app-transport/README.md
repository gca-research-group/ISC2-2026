# Transport System – Simulated Service (`app-transport`)

This service simulates a transport application within a digital services integration architecture. The application enables the registration and retrieval of scheduled journeys for customers, based on transport requests issued by a secure integration process.

The main components of this service are:

- A **graphical desktop interface** developed using Tkinter (`desktop_transporte.py`);
- A **secure REST API** implemented with Flask and served via HTTPS (`API2.py`);
- A **digital certificate verification mechanism** that attests the execution environment of the integration process requesting the data (`verifyCertificate.py`).

The service utilises a local SQLite database (`transporte_app.db`) and X.509 digital certificates to ensure the authenticity of interactions.

---

## Components

- **`desktop_transporte.py`**: Graphical interface for viewing and managing transport schedules.
- **`API2.py`**: REST API with HTTPS support for receiving and recording transport requests.
- **`verifyCertificate.py`**: Script for validating X.509 certificates with custom extensions (invoked automatically by the API).
- **`transporte_app.db`**: SQLite database containing the transport-related records used by the service.
- **`keys/`**: Directory containing the cryptographic keys and digital certificates for the service.

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
sudo apt-get install python3 python3-pip python3-tk sqlite3 libsqlite3-dev openssl
```

### Python Packages

```bash
pip install flask flask-talisman cryptography
```

---

## Execution

### 1. Graphical Interface (Desktop)

```bash
python3 desktop_transporte.py
```

The interface allows users to:

- View transport records;
- Query the database for scheduled journeys.

---

### 2. REST API (HTTPS)

#### Certificate Generation:

```bash
openssl genpkey -algorithm RSA -out keys/priv.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -in keys/priv.pem -pubout -out keys/public_key.pem
openssl req -new -x509 -key keys/priv.pem -out keys/cert.pem -days 365
```

#### Launching the API:

```bash
cd api
python3 API2.py
```

> The API will be started over HTTPS on port `8080`, using the certificates located in the `../keys` directory.

During execution, the service automatically validates the certificate of the requesting integration process. The verification includes the digital signature issued by a trusted root certificate authority, as well as the analysis of X.509 extensions containing information about the operating system and hardware environment (e.g., CheriBSD on Morello Board).

---

## Directory Structure

```plaintext
app-transport/
├── api/
│   ├── API2.py                  # HTTPS Flask-based REST API
│   └── verifyCertificate.py     # Certificate verification logic (used internally by the API)
│
├── data_access/
│   └── transporte_app.db        # SQLite database storing transport records
│
├── desktop_transporte.py        # Desktop GUI application built with Tkinter
│
└── keys/
    ├── cert.pem                 # X.509 certificate for the service
    └── priv.pem                 # RSA private key
```

---

## Database Schema (`transporte_app.db`)

The relational schema used by this service comprises the following tables:

- `Agendamentos(ID, Cliente, Endereco, Telefone, Data, Status)`
- `LogAtualizacoes(ID, Mensagem)`
