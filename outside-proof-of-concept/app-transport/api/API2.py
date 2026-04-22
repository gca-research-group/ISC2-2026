from __future__ import annotations
import json
import sys
import threading
import time
from pathlib import Path

try:
    from flask import Flask, jsonify, request
except Exception:
    Flask = None
    request = None
    jsonify = None

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.metrics import append_metric
from verifyCertificate import verifyCertificate, decrypt

app = Flask(__name__) if Flask else None

db_lock = threading.Lock()
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / 'data_access' / 'transporte_app.json'
METRICS_FILE = str(Path(__file__).resolve().parents[2] / 'metrics' / 'all_metrics.csv')
SERVICE_ID = 'transport-service'


def now_ms():
    return time.perf_counter() * 1000.0


def append_local_metric(name, value_ms, run_id='', program_id=''):
    append_metric(__file__, 'digital_service', 'post', name, value_ms, run_id=run_id, program_id=program_id, service_id=SERVICE_ID, metrics_file=METRICS_FILE)


def load_transport_data() -> dict:
    if not DATA_PATH.exists():
        return {'Viagens': [], 'LogAtualizacoes': []}
    return json.loads(DATA_PATH.read_text(encoding='utf-8'))


def save_transport_data(data: dict) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _next_id(rows: list[dict]) -> int:
    return max((int(r.get('id', 0)) for r in rows), default=0) + 1


def storeLocalData(data):
    parsed = json.loads(data)
    with db_lock:
        db = load_transport_data()
        viagens = db.setdefault('Viagens', [])
        viagem = {
            'id': _next_id(viagens),
            'id_motorista': parsed.get('id_motorista', 1),
            'id_veiculo': parsed.get('id_veiculo', 2),
            'id_passageiro': parsed.get('id_passageiro', 3),
            'data_hora_inicio': parsed.get('data_hora_inicio'),
            'data_hora_fim': parsed.get('data_hora_fim'),
            'local_origem': parsed.get('local_origem'),
            'local_destino': parsed.get('local_destino'),
            'valor': parsed.get('valor'),
            'telefone_cliente': parsed.get('telefone_cliente')
        }
        viagens.append(viagem)
        logs = db.setdefault('LogAtualizacoes', [])
        logs.append({'ID': len(logs) + 1, 'Mensagem': 'Nova viagem cadastrada', 'DataHora': time.strftime('%Y-%m-%d %H:%M:%S')})
        save_transport_data(db)


def post_action(payload):
    total_t0 = now_ms()
    run_id = str(payload.get('runId', ''))
    program_id = str(payload.get('programId', ''))

    t0 = now_ms()
    ok, msg = verifyCertificate(payload.get('signedCert', ''))
    append_local_metric('verifyCertificate_ms', now_ms() - t0, run_id, program_id)
    if not ok:
        return {'error': msg}, 403

    t0 = now_ms()
    data = decrypt('', payload.get('dataEnc', ''))
    append_local_metric('decrypt_ms', now_ms() - t0, run_id, program_id)

    t0 = now_ms()
    storeLocalData(data)
    append_local_metric('storeLocalData_ms', now_ms() - t0, run_id, program_id)

    append_local_metric('post_total_ms', now_ms() - total_t0, run_id, program_id)
    return {'status': 'ok'}, 200


if app:
    @app.route('/api/post', methods=['POST'])
    def post():
        payload = request.get_json(force=True)
        body, status = post_action(payload)
        return jsonify(body), status

    @app.route('/api/viagens', methods=['GET'])
    def listar_viagens():
        with db_lock:
            db = load_transport_data()
        return jsonify({'viagens': db.get('Viagens', [])}), 200


if __name__ == '__main__':
    if not app:
        raise RuntimeError('Flask is required to run API2 server.')
    app.run(host='127.0.0.1', port=8001, ssl_context=(str(BASE_DIR / 'keys' / 'cert.pem'), str(BASE_DIR / 'keys' / 'priv.pem')), debug=False, use_reloader=False)
