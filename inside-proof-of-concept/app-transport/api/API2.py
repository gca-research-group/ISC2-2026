from __future__ import annotations
import json, logging, os, sqlite3, threading, time, sys
from pathlib import Path
try:
    from flask import Flask, jsonify, request
except Exception:
    Flask = None; request = None; jsonify = None
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from common.metrics import append_metric, default_metrics_file
from verifyCertificate import verifyCertificate, decrypt

app = Flask(__name__) if Flask else None
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
db_lock = threading.Lock()
METRICS_FILE = os.environ.get('METRICS_FILE', str(default_metrics_file(__file__)))
DB_PATH = str(Path(__file__).resolve().parents[1] / 'data_access' / 'transporte_app.db')

def now_ms(): return time.perf_counter()*1000.0

def metric(name, value_ms, run_id='', program_id='', service_id='transport-service'):
    append_metric(__file__, 'digital_service', 'post', name, value_ms, run_id=run_id, program_id=program_id, service_id=service_id, metrics_file=METRICS_FILE)

def get_db_connection(): return sqlite3.connect(DB_PATH)

def storeLocalData(data: dict):
    with db_lock:
        conn = get_db_connection(); c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS Viagens (id INTEGER PRIMARY KEY AUTOINCREMENT, id_motorista INTEGER NOT NULL, id_veiculo INTEGER NOT NULL, id_passageiro INTEGER, data_hora_inicio TEXT NOT NULL, data_hora_fim TEXT, local_origem TEXT NOT NULL, local_destino TEXT NOT NULL, valor REAL NOT NULL, telefone_cliente TEXT)")
        c.execute("INSERT INTO Viagens (id_motorista, id_veiculo, id_passageiro, data_hora_inicio, local_origem, local_destino, valor, telefone_cliente) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
            data.get('id_motorista', 1), data.get('id_veiculo', 1), data.get('id_passageiro', 1), data.get('data_hora_inicio', '2026-01-01 00:00'), data.get('local_origem'), data.get('local_destino'), data.get('valor', 0.0), data.get('telefone_cliente')))
        conn.commit(); conn.close()

def post_action(payload: dict) -> tuple[dict,int]:
    total_t0=now_ms(); run_id=str(payload.get('runId','')); program_id=str(payload.get('programId',''))
    t0=now_ms(); ok,message=verifyCertificate(payload.get('signedCert','')); metric('verifyCertificate_ms', now_ms()-t0, run_id, program_id)
    if not ok: return {'error': message}, 403
    t0=now_ms(); data_json=decrypt('', payload.get('dataEnc','')); metric('decrypt_ms', now_ms()-t0, run_id, program_id)
    data=json.loads(data_json)
    t0=now_ms(); storeLocalData(data); metric('storeLocalData_ms', now_ms()-t0, run_id, program_id)
    metric('post_total_ms', now_ms()-total_t0, run_id, program_id)
    return {'status':'ok'}, 200

if app:
    @app.route('/api/post', methods=['POST'])
    def post_dataset():
        payload=request.get_json(force=True, silent=True) or {}
        body,status=post_action(payload)
        return jsonify(body), status

    @app.route('/api/viagens', methods=['GET'])
    def listar_viagens():
        conn=get_db_connection(); c=conn.cursor(); c.execute("SELECT id, local_origem, local_destino, telefone_cliente, valor FROM Viagens")
        rows=c.fetchall(); conn.close()
        return jsonify([{'id':r[0],'local_origem':r[1],'local_destino':r[2],'telefone_cliente':r[3],'valor':r[4]} for r in rows]), 200

if __name__ == '__main__':
    if not app: raise RuntimeError('Flask is required to run API2 server.')
    context = (str(Path(__file__).resolve().parents[1] / 'keys' / 'cert.pem'), str(Path(__file__).resolve().parents[1] / 'keys' / 'priv.pem'))
    app.run(host='127.0.0.1', port=8001, ssl_context=context, debug=False, use_reloader=False)
