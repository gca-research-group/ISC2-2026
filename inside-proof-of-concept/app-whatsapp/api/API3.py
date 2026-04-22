from __future__ import annotations
import json, os, time, sys
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
METRICS_FILE = os.environ.get('METRICS_FILE', str(default_metrics_file(__file__)))
MESSAGES_FILE = str(Path(__file__).resolve().parents[1] / 'data_access' / 'messages.log')

def now_ms(): return time.perf_counter()*1000.0

def metric(name, value_ms, run_id='', program_id='', service_id='messaging-service'):
    append_metric(__file__, 'digital_service', 'post', name, value_ms, run_id=run_id, program_id=program_id, service_id=service_id, metrics_file=METRICS_FILE)

def storeLocalData(data: dict):
    os.makedirs(os.path.dirname(MESSAGES_FILE), exist_ok=True)
    with open(MESSAGES_FILE, 'a', encoding='utf-8') as f: f.write(json.dumps(data)+'\n')

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

if __name__ == '__main__':
    if not app: raise RuntimeError('Flask is required to run API3 server.')
    context = (str(Path(__file__).resolve().parents[1] / 'keys' / 'cert.pem'), str(Path(__file__).resolve().parents[1] / 'keys' / 'priv.pem'))
    app.run(host='127.0.0.1', port=9000, ssl_context=context, debug=False, use_reloader=False)
