from __future__ import annotations
import json, logging, os, sqlite3, threading, time, sys
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

API_DIR = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
for p in (API_DIR, ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from common.metrics import append_metric, default_metrics_file
from verifyCertificate import verifyCertificate, encrypt

app = Flask(__name__) if Flask else None
if app and Talisman:
    Talisman(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
db_lock = threading.Lock()
METRICS_FILE = os.environ.get('METRICS_FILE', str(default_metrics_file(__file__)))
DB_PATH = str(Path(__file__).resolve().parents[1] / 'data_access' / 'compras.db')


def now_ms(): return time.perf_counter() * 1000.0

def metric(name, value_ms, run_id='', program_id='', service_id='store-service'):
    append_metric(__file__, 'digital_service', 'request', name, value_ms, run_id=run_id, program_id=program_id, service_id=service_id, metrics_file=METRICS_FILE)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def retrieveLocalData():
    with db_lock:
        conn = get_db_connection(); cur = conn.cursor()
        cur.execute("SELECT V.Total, C.Telefone, C.Endereco FROM Vendas V JOIN Clientes C ON V.IDCliente = C.IDCliente ORDER BY V.ID DESC LIMIT 1")
        row = cur.fetchone(); conn.close()
    if not row:
        return json.dumps({'Total': 0.0, 'Telefone': '', 'Endereco': ''})
    return json.dumps({'Total': row['Total'], 'Telefone': row['Telefone'], 'Endereco': row['Endereco']})


def request_action(payload: dict) -> tuple[dict, int]:
    total_t0 = now_ms(); run_id = str(payload.get('runId','')); program_id = str(payload.get('programId',''))
    t0 = now_ms(); ok, message = verifyCertificate(payload.get('signedCert', '')); metric('verifyCertificate_ms', now_ms()-t0, run_id, program_id)
    if not ok: return {'error': message}, 403
    t0 = now_ms(); data = retrieveLocalData(); metric('retrieveLocalData_ms', now_ms()-t0, run_id, program_id)
    t0 = now_ms(); data_enc = encrypt(payload.get('puK', ''), data); metric('encrypt_ms', now_ms()-t0, run_id, program_id)
    metric('request_total_ms', now_ms()-total_t0, run_id, program_id)
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
            conn = get_db_connection(); cur = conn.cursor()
            cur.execute("SELECT V.ID, V.IDVendedor, V.IDCliente, V.Total, V.Data, C.Telefone, C.Endereco FROM Vendas V JOIN Clientes C ON V.IDCliente = C.IDCliente")
            vendas = [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
            conn.close()
        return jsonify({'vendas': vendas}), 200

if __name__ == '__main__':
    if not app: raise RuntimeError('Flask is required to run API1 server.')
    context = (str(Path(__file__).resolve().parents[1] / 'keys' / 'cert.pem'), str(Path(__file__).resolve().parents[1] / 'keys' / 'priv.pem'))
    app.run(host='127.0.0.1', port=8000, ssl_context=context, debug=False, use_reloader=False)
