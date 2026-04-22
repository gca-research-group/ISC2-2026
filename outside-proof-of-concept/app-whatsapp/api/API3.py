from __future__ import annotations
import logging
import sys
import time
from pathlib import Path

try:
    from flask import Flask, request, jsonify
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
logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parents[1]
LOG_FILE = BASE_DIR / 'messages.log'
METRICS_FILE = str(Path(__file__).resolve().parents[2] / 'metrics' / 'all_metrics.csv')
SERVICE_ID = 'messaging-service'


def now_ms():
    return time.perf_counter() * 1000.0


def append_local_metric(name, value_ms, run_id='', program_id=''):
    append_metric(__file__, 'digital_service', 'post', name, value_ms, run_id=run_id, program_id=program_id, service_id=SERVICE_ID, metrics_file=METRICS_FILE)


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
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(data + "\n")
    append_local_metric('storeMessage_ms', now_ms() - t0, run_id, program_id)

    append_local_metric('post_total_ms', now_ms() - total_t0, run_id, program_id)
    return {'status': 'ok'}, 200


if app:
    @app.route('/api/post', methods=['POST'])
    def post():
        payload = request.get_json(force=True)
        body, status = post_action(payload)
        return jsonify(body), status


if __name__ == '__main__':
    if not app:
        raise RuntimeError('Flask is required to run API3 server.')
    app.run(host='127.0.0.1', port=9000, ssl_context=(str(BASE_DIR / 'keys' / 'cert.pem'), str(BASE_DIR / 'keys' / 'priv.pem')), debug=False, use_reloader=False)
