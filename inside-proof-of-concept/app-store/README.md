# Purchase System – Simulated Service (`app-store`)

This service simulates a purchase application within a digital services integration architecture. The application enables the registration and retrieval of data related to sales, products, customers, and vendors through the following components:

- A **graphical desktop interface** developed using Tkinter (`desktop_compras.py`);
- A **secure REST API** implemented with Flask and served over HTTPS (`API1.py`);
- A **digital certificate verification mechanism** that attests the execution environment of the integration process requesting data (`verifyCertificate.py`).

The service utilises a local SQLite database (`compras.db`) and X.509 digital certificates to ensure the authenticity of interactions.

---

## Components

- **`desktop_compras.py`**: Graphical interface for recording and querying sales.
- **`API1.py`**: REST API with HTTPS support for managing and querying transactions.
- **`verifyCertificate.py`**: Script for validating X.509 certificates with custom extensions (automatically invoked by the API).
- **`compras.db`**: SQLite database containing the relational data used in the experiment.
- **`keys/`**: Directory containing the service’s cryptographic keys and certificates.

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
python3 desktop_compras.py
```

The interface allows users to:

- Select a vendor, customer, and product;
- Input quantity and date;
- Register sales and view purchase history.

---

### 2. REST API (HTTPS)

#### Certificate Generation

```bash
openssl genpkey -algorithm RSA -out keys/priv.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -in keys/priv.pem -pubout -out keys/public_key.pem
openssl req -new -x509 -key keys/priv.pem -out keys/cert.pem -days 365
```

#### Launching the API

```bash
cd api
python3 API1.py
```

> The API will start over HTTPS on port `8080`, using the certificates located in the `../keys` directory.

During execution, the service automatically validates the certificate presented by the integration process making the request. This verification includes the digital signature issued by a trusted certification authority and the inspection of X.509 extensions containing information about the operating system and hardware environment (e.g., CheriBSD on Morello Board) from which the request originates.

---

## Directory Structure

```plaintext
app-store/
├── api/
│   ├── API1.py                  # Flask-based HTTPS REST API
│   └── verifyCertificate.py     # Certificate verification logic (invoked internally by the API)
│
├── data_access/
│   └── compras.db               # SQLite database containing relational data
│
├── desktop_compras.py           # Desktop GUI built with Tkinter
│
└── keys/
    ├── cert.pem                 # Service’s X.509 certificate
    ├── priv.pem                 # Private RSA key
    └── public_key.pem           # Public key derived from priv.pem
```

---

## Database Schema (`compras.db`)

The relational schema used by this service includes the following tables:

- `Vendedores(IDVendedor, Nome)`
- `Clientes(IDCliente, Cliente, Estado, Sexo, Status, Telefone, Endereco)`
- `Produtos(IDProduto, Produto, Preco)`
- `Vendas(ID, IDVendedor, IDCliente, Total, Data, ID_LogAtualizacoes)`
- `ItensVenda(IDItem, IDVenda, IDProduto, Quantidade, ValorUnitario, ValorTotal)`
- `LogAtualizacoes(ID, Mensagem)`

