from __future__ import annotations
import json
import logging
import sys
import threading
import time
from pathlib import Path

try:
    from flask import Flask, jsonify, request
    try:
        from flask_talisman import Talisman
    except Exception:
        Talisman = None
except Exception:  # pragma: no cover
    Flask = None
    request = None
    jsonify = None
    Talisman = None

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.metrics import append_metric, default_metrics_file
from verifyCertificate import verifyCertificate, encrypt

app = Flask(__name__) if Flask else None
if app and Talisman:
    Talisman(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
db_lock = threading.Lock()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / 'data_access' / 'compras.json'
METRICS_FILE = str(Path(__file__).resolve().parents[2] / 'metrics' / 'all_metrics.csv')
SERVICE_ID = 'store-service'


def now_ms() -> float:
    return time.perf_counter() * 1000.0


def metric(name: str, value_ms: float, run_id: str = '', program_id: str = '') -> None:
    append_metric(__file__, 'digital_service', 'request', name, value_ms, run_id=run_id, program_id=program_id, service_id=SERVICE_ID, metrics_file=METRICS_FILE)


def load_store_data() -> dict:
    if not DATA_PATH.exists():
        return {'Clientes': [], 'Vendas': []}
    return json.loads(DATA_PATH.read_text(encoding='utf-8'))


def save_store_data(data: dict) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def retrieveLocalData() -> str:
    with db_lock:
        data = load_store_data()
    clientes = {row['IDCliente']: row for row in data.get('Clientes', [])}
    vendas = data.get('Vendas', [])
    if not vendas:
        return json.dumps({'Total': 0.0, 'Telefone': '', 'Endereco': ''}, ensure_ascii=False)
    latest_sale = max(vendas, key=lambda row: row.get('ID', 0))
    cliente = clientes.get(latest_sale.get('IDCliente'), {})
    return json.dumps({
        'Total': latest_sale.get('Total', 0.0),
        'Telefone': cliente.get('Telefone', ''),
        'Endereco': cliente.get('Endereco', '')
    }, ensure_ascii=False)


def request_action(payload: dict) -> tuple[dict, int]:
    total_t0 = now_ms()
    run_id = str(payload.get('runId', ''))
    program_id = str(payload.get('programId', ''))

    t0 = now_ms()
    ok, message = verifyCertificate(payload.get('signedCert', ''))
    metric('verifyCertificate_ms', now_ms() - t0, run_id, program_id)
    if not ok:
        return {'error': message}, 403

    t0 = now_ms()
    data = retrieveLocalData()
    metric('retrieveLocalData_ms', now_ms() - t0, run_id, program_id)

    t0 = now_ms()
    data_enc = encrypt(payload.get('puK', ''), data)
    metric('encrypt_ms', now_ms() - t0, run_id, program_id)

    metric('request_total_ms', now_ms() - total_t0, run_id, program_id)
    return {'dataEnc': data_enc, 'status': 'ok'}, 200


if app:
    @app.route('/api/request', methods=['POST'])
    def request_dataset():
        payload = request.get_json(force=True, silent=True) or {}
        body, status = request_action(payload)
        return jsonify(body), status

    @app.route('/api/vendas', methods=['GET'])
    def consultar_vendas():
        with db_lock:
            data = load_store_data()
        clientes = {row['IDCliente']: row for row in data.get('Clientes', [])}
        vendas = []
        for venda in data.get('Vendas', []):
            cliente = clientes.get(venda.get('IDCliente'), {})
            row = dict(venda)
            row['Telefone'] = cliente.get('Telefone', '')
            row['Endereco'] = cliente.get('Endereco', '')
            vendas.append(row)
        return jsonify({'vendas': vendas}), 200


if __name__ == '__main__':
    if not app:
        raise RuntimeError('Flask is required to run API1 server.')
    context = (str(BASE_DIR / 'keys' / 'cert.pem'), str(BASE_DIR / 'keys' / 'priv.pem'))
    app.run(host='127.0.0.1', port=8002, ssl_context=context, debug=False, use_reloader=False)
