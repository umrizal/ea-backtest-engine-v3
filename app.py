from __future__ import annotations

import tempfile
import importlib
from pathlib import Path

# Load Flask dynamically so environments without Flask type stubs do not flag
# this module's import during static analysis.
_flask = importlib.import_module("flask")
Flask = _flask.Flask
jsonify = _flask.jsonify
request = _flask.request
send_from_directory = _flask.send_from_directory
from parser import EAParser
from backtest.data_feed import CSVDataFeed
from backtest.engine import BacktestConfig, BacktestEngine

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
app = Flask(__name__, static_folder=str(FRONTEND), static_url_path="")


def _jsonable(obj):
    from dataclasses import asdict, is_dataclass
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


@app.get("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "engine": "EA Backtest Engine V3"})


@app.post("/api/parse-ea")
def parse_ea():
    payload = request.get_json(silent=True) or {}
    source = payload.get("source", "")
    if not source.strip():
        return jsonify({"error": "source is required"}), 400
    ir = EAParser().parse(source)
    return jsonify(_jsonable(ir))


@app.post("/api/run-backtest")
def run_backtest():
    if "data" not in request.files:
        return jsonify({"error": "CSV file field 'data' is required"}), 400
    uploaded = request.files["data"]
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        uploaded.save(tmp.name)
        path = Path(tmp.name)
    try:
        symbol = request.form.get("symbol", "XAUUSD")
        initial_balance = float(request.form.get("initial_balance", 10000))
        point = float(request.form.get("point", 0.01))
        spread = float(request.form.get("spread", 0))
        slippage = float(request.form.get("slippage", 0))
        execution_mode = request.form.get("execution_mode", "heuristic")
        cfg = BacktestConfig(
            symbol=symbol,
            initial_balance=initial_balance,
            point=point,
            execution_mode=execution_mode,
            default_spread_points=spread,
            slippage_points=slippage,
        )
        result = BacktestEngine(cfg).run(CSVDataFeed(path, symbol=symbol, point=point).bars())
        return jsonify(_jsonable(result))
    finally:
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
