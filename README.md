# Reproducing the proof-of-concept on the ARM Morello Board

This repository contains two reproducible proof-of-concept configurations of the same integration process:

- **Trusted environment (inside)**: the integration process is executed through the Launcher inside a CHERI-based compartment.
- **Conventional environment (outside)**: the integration process is executed in a conventional environment for baseline comparison.

In both cases, the orchestration workflow is initiated from **`launcher/command-line-interface.py`**. This README explains how to execute both configurations on the Morello Board and how to reproduce the statistical analysis used in the paper.

---

## Repository layout

```text
inside-proof-of-concept/
  app-store/
  app-transport/
  app-whatsapp/
  common/
  launcher/
  metrics/

outside-proof-of-concept/
  app-store/
  app-transport/
  app-whatsapp/
  common/  
  metrics/

evaluation/
  inside.csv
  outside.csv
  script.py
```

---

## What is executed in each environment

### 1. Trusted environment (`inside-proof-of-concept`)

The Launcher:
- receives the source file uploaded through the CLI,
- compiles it with `clang-morello` and the `purecap` ABI,
- creates the certificate material,
- deploys the executable,
- runs the integration process using `proccontrol -m cheric18n -s enable ...`,
- mediates `read()` and `write()` operations between the integration process and the digital services.

This configuration produces the metrics used as the **trusted environment** in the paper.

### 2. Conventional environment (`outside-proof-of-concept`)

The conventional baseline reuses the same CLI/Launcher workflow to keep the operational procedure identical, but the goal is to reproduce the **outside** measurements that serve as the baseline in the comparison. This configuration produces the metrics used as the **conventional environment** in the paper.

---

## Hardware and software requirements

### Hardware
- ARM Morello Board (Research Morello SoC r0p0)
- 4 CPU cores
- 16 GB RAM

### Operating system
- CheriBSD 24.05

### Required tools
- `python3`
- `pip`
- `clang-morello`
- `openssl`
- `proccontrol`

### Python dependencies
Install the Python packages in both environments:

```bash
pip install flask flask-talisman cryptography requests click pandas numpy scipy
```

On CheriBSD, install Python and pip if necessary:

```bash
sudo pkg64 install python39 py39-pip py39-openssl
```

---

## Part A — Trusted environment (`inside-proof-of-concept`)

### Step A1 — Start the digital services

Open three terminals.

#### Terminal 1 — Store Service
```bash
cd inside-proof-of-concept/app-store/api
python3 API1.py
```

Expected endpoint:
- `https://127.0.0.1:8000/api/request`

#### Terminal 2 — Transport Service
```bash
cd inside-proof-of-concept/app-transport/api
python3 API2.py
```

Expected endpoint:
- `https://127.0.0.1:8001/api/post`

#### Terminal 3 — Messaging Service
```bash
cd inside-proof-of-concept/app-whatsapp/api
python3 API3.py
```

Expected endpoint:
- `https://127.0.0.1:9000/api/post`

### Step A2 — Start the Launcher

Open a fourth terminal:

```bash
cd inside-proof-of-concept/launcher
python3 launcher.py
```

Expected endpoint:
- `https://127.0.0.1:5000`

### Step A3 — Start the CLI

Open a fifth terminal:

```bash
cd inside-proof-of-concept/launcher
python3 command-line-interface.py
```

The menu is interactive and offers:

```text
1. List files
2. Upload a file
3. Delete a program
4. Compile a program
5. Execute a program
6. Exit
```

### Step A4 — Upload the integration process source

Choose option `2` and provide the path to the integration process source file.

If you want to use the source already stored in the repository, use:

```text
inside-proof-of-concept/launcher/programs-data-base/sources/integration_process.c
```

The CLI sends the file to the Launcher through `/upload`.

### Step A5 — List files and note the program ID

Choose option `1`.

The CLI will print the registered program IDs. Note the ID corresponding to `integration_process.c`.

### Step A6 — Compile the integration process

Choose option `4` and enter the program ID.

This triggers:
- source retrieval,
- compilation with `clang-morello -march=morello+c64 -mabi=purecap`,
- certificate directory creation,
- executable registration.

### Step A7 — Execute the integration process

Choose option `5` and enter the same program ID.

This triggers the trusted workflow mediated by the Launcher.

### Step A8 — Repeat 30 times

Repeat option `5` until you obtain 30 complete repetitions in:

```text
inside-proof-of-concept/metrics/all_metrics.csv
```

---

## Part B — Conventional environment (`outside-proof-of-concept`)

### Step B1 — Start the digital services

Open three terminals.

#### Terminal 1 — Store Service
```bash
cd outside-proof-of-concept/app-store/api
python3 API1.py
```

Expected endpoint:
- `https://127.0.0.1:8002/api/request`

#### Terminal 2 — Transport Service
```bash
cd outside-proof-of-concept/app-transport/api
python3 API2.py
```

Expected endpoint:
- `https://127.0.0.1:8001/api/post`

#### Terminal 3 — Messaging Service
```bash
cd outside-proof-of-concept/app-whatsapp/api
python3 API3.py
```

Expected endpoint:
- `https://127.0.0.1:9000/api/post`


### Step B2 — Compile the integration process

```bash
cd inside-proof-of-concept/sources
clang-morello -o integration_process integration_process.c -lssl -lcrypto
```
### Step B3 — Execute the integration process

```bash
./integration_process
```

### Step B4 — Repeat 30 times

Repeat option `5` until you obtain 30 complete repetitions in:

```text
outside-proof-of-concept/metrics/all_metrics.csv
```

---

# Part C — Statistical analysis

The repository already contains the analysis script used to compare the two environments:

```text
evaluation/script.py
```

## Step C1 — Copy the campaign CSVs

After collecting the 30 repetitions in each environment, copy the final CSV files into `evaluation/` using the names expected by the script:

- trusted environment → `evaluation/inside.csv`
- conventional environment → `evaluation/outside.csv`

Example:

```bash
cp inside-proof-of-concept/metrics/all_metrics.csv evaluation/inside.csv
cp outside-proof-of-concept/metrics/all_metrics.csv evaluation/outside.csv
```

## Step C2 — Run the analysis script

```bash
cd evaluation
python3 script.py
```

The script generates:
- console output, and
- `analysis_results.log`

## Step C3 — What the script computes

### Cross-environment comparison
- `read_act_total_ms`
- `execute_total_ms`

For each metric, the script computes:
- mean ± standard deviation
- Shapiro–Wilk normality tests
- Mann–Whitney U test
- Holm-adjusted p-values
- Cliff’s Delta

### Robustness analysis
- IQR-based outlier removal
- recomputed means and standard deviations
- number of removed outliers in each environment

### Trusted-environment internal analysis
- selected local costs within `Read_act`
- selected measured operations associated with `Launcher.start()`

---

# Expected output files

## Trusted environment
- `inside-proof-of-concept/metrics/all_metrics.csv`

## Conventional environment
- `outside-proof-of-concept/metrics/all_metrics.csv`

## Statistical analysis
- `evaluation/analysis_results.log`

---

# Main metrics used in the paper

## Cross-environment metrics
- `read_act_total_ms`
- `execute_total_ms`

## Trusted-environment local metrics
- `lookupService_ms`
- `getCertificate_ms`
- `getProgramPublicKey_ms`
- `decrypt_ms`
- `retrieveProgram_ms`
- `compile_ms`
- `createCompartment_ms`
- `deploy_ms`
- `getIntegratedServices_ms`
- `exchangeKeys_ms`
- `generateAttestableDoc_ms`
- `generateCertificate_ms`
- `sign_ms`
- `run_ms`
- `start_total_ms`
