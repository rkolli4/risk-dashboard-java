from __future__ import annotations

import json
import math
import os
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import yfinance as yf

ROOT = Path(__file__).resolve().parents[2]
PORT = int(os.environ.get("PRISM_PORT", "8080"))

DEFAULT_POSITION = {
    "symbol": "RELIANCE.NS",
    "lot_size": 1,
    "quantity": 10,
    "buy_price": 0.0,
    "collateral": 250000.0,
}

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PRISM Live Risk</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@600;700;800&display=swap');
:root{--ink:#102a2c;--muted:#667574;--paper:#f5f1e8;--lime:#d9f26b;--coral:#ed7659;--line:#c9c5b9;--white:#fffdf8}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:Arial,sans-serif}body:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.16;background-image:linear-gradient(var(--line) 1px,transparent 1px),linear-gradient(90deg,var(--line) 1px,transparent 1px);background-size:44px 44px}.shell{position:relative;max-width:1180px;margin:auto;padding:36px 24px 64px}.top{display:flex;justify-content:space-between;align-items:end;border-bottom:2px solid var(--ink);padding-bottom:22px}.mark{font:700 12px 'DM Mono',monospace;letter-spacing:2px}.top h1{font:800 clamp(42px,8vw,86px)/.87 Syne,sans-serif;letter-spacing:-2px;margin:12px 0 0}.live{font:500 12px 'DM Mono',monospace;display:flex;gap:8px;align-items:center}.dot{width:9px;height:9px;border-radius:50%;background:var(--coral);box-shadow:0 0 0 5px #ed765933}.layout{display:grid;grid-template-columns:330px 1fr;gap:48px;margin-top:42px}.panel{background:var(--white);border:1px solid var(--line);padding:24px;box-shadow:8px 8px 0 var(--ink)}.panel h2{font:700 19px Syne,sans-serif;margin:0 0 24px}.field{margin:0 0 18px}.field label{display:block;font:500 11px 'DM Mono',monospace;text-transform:uppercase;color:var(--muted);margin-bottom:7px}.field input{width:100%;border:0;border-bottom:2px solid var(--ink);background:transparent;padding:9px 0;font:500 17px 'DM Mono',monospace;color:var(--ink);outline:none}.field input:focus{border-color:var(--coral)}.row{display:grid;grid-template-columns:1fr 1fr;gap:16px}.button{width:100%;border:2px solid var(--ink);background:var(--lime);color:var(--ink);font:700 13px 'DM Mono',monospace;padding:14px;cursor:pointer;margin-top:4px}.button:hover{transform:translate(-2px,-2px);box-shadow:4px 4px 0 var(--ink)}.hint{color:var(--muted);font-size:12px;line-height:1.5;margin:18px 0 0}.hero{display:grid;grid-template-columns:1fr 1fr;gap:16px}.quote,.risk{padding:28px;background:var(--ink);color:var(--white);min-height:206px}.quote small,.risk small{font:500 11px 'DM Mono',monospace;color:#a9bdb7;text-transform:uppercase}.quote h2{font:700 56px Syne,sans-serif;margin:24px 0 4px;letter-spacing:-2px}.quote p{font:500 13px 'DM Mono',monospace;margin:0;color:#a9bdb7}.risk{background:var(--coral);color:var(--ink)}.risk small{color:#69382f}.risk h2{font:800 42px Syne,sans-serif;margin:22px 0 10px}.risk p{font-size:14px;line-height:1.45;margin:0;max-width:290px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:16px}.metric{border-top:4px solid var(--ink);padding-top:14px}.metric label{display:block;color:var(--muted);font:500 11px 'DM Mono',monospace;text-transform:uppercase}.metric strong{display:block;font:700 24px Syne,sans-serif;margin-top:9px;overflow-wrap:anywhere}.meter{margin-top:35px;border-top:1px solid var(--line);padding-top:20px}.meter-head{display:flex;justify-content:space-between;font:500 12px 'DM Mono',monospace}.track{height:17px;background:#d8d5cb;margin-top:10px;position:relative}.fill{height:100%;width:0;background:var(--lime);transition:width .5s,background .5s}.foot{font:500 11px 'DM Mono',monospace;color:var(--muted);margin-top:28px}@media(max-width:800px){.layout{grid-template-columns:1fr;gap:30px}.hero{grid-template-columns:1fr}.metrics{grid-template-columns:1fr 1fr}.top{display:block}.live{margin-top:18px}}
</style></head><body><main class="shell"><header class="top"><div><div class="mark">PRISM / LIVE RISK DESK</div><h1>Know your<br>downside.</h1></div><div class="live"><i class="dot"></i><span id="connection">CONNECTING / 1 SEC FEED</span></div></header>
<section class="layout"><aside class="panel"><h2>Position setup</h2><form id="position-form"><div class="field"><label for="symbol">Share / Yahoo symbol</label><input id="symbol" value="RELIANCE.NS" required></div><div class="row"><div class="field"><label for="lot">Lot size</label><input id="lot" type="number" min="1" value="1" required></div><div class="field"><label for="quantity">Lots held</label><input id="quantity" type="number" min="1" value="10" required></div></div><div class="field"><label for="buy">Average buy price (optional)</label><input id="buy" type="number" min="0" step="0.01" value="0"></div><div class="field"><label for="collateral">Collateral available</label><input id="collateral" type="number" min="0" step="1000" value="250000" required></div><button class="button" type="submit">UPDATE POSITION ↗</button></form><p class="hint">Use Yahoo symbols such as <b>RELIANCE.NS</b>, <b>INFY.NS</b>, <b>AAPL</b>, or <b>TSLA</b>. Quotes refresh every second while this page is open.</p></aside>
<div><div class="hero"><article class="quote"><small id="symbol-label">RELIANCE.NS / LIVE QUOTE</small><h2 id="price">--</h2><p id="change">Waiting for market data</p></article><article class="risk"><small>COLLATERAL CHECK</small><h2 id="state">LOADING</h2><p id="message">Fetching quote and calculating your margin.</p></article></div><div class="metrics"><div class="metric"><label>Position value</label><strong id="value">--</strong></div><div class="metric"><label>SPAN-style margin</label><strong id="margin">--</strong></div><div class="metric"><label>Est. worst loss</label><strong id="loss">--</strong></div><div class="metric"><label>Headroom</label><strong id="headroom">--</strong></div></div><div class="meter"><div class="meter-head"><span>COLLATERAL UTILIZATION</span><span id="utilization">--</span></div><div class="track"><div class="fill" id="fill"></div></div></div><div class="foot" id="updated">No snapshot yet</div></div></section></main>
<script>
const $=id=>document.getElementById(id);let timer;
function money(v){return v==null?'--':new Intl.NumberFormat('en-IN',{maximumFractionDigits:2}).format(v)}
function payload(){return {symbol:$('symbol').value.trim().toUpperCase(),lot_size:Number($('lot').value),quantity:Number($('quantity').value),buy_price:Number($('buy').value),collateral:Number($('collateral').value)}}
async function refresh(){try{const r=await fetch('/api/state',{cache:'no-store'});const d=await r.json();$('connection').textContent=d.market_open?'LIVE / 1 SEC FEED':'CLOSED / LAST AVAILABLE QUOTE';$('symbol-label').textContent=d.symbol+' / LIVE QUOTE';$('price').textContent=money(d.price);$('change').textContent=(d.change_percent>=0?'▲ ':'▼ ')+Number(d.change_percent||0).toFixed(2)+'% today';$('state').textContent=d.state;$('message').textContent=d.message;$('value').textContent=money(d.position_value);$('margin').textContent=money(d.span_margin);$('loss').textContent=money(d.worst_loss);$('headroom').textContent=money(d.headroom);$('utilization').textContent=(d.utilization*100).toFixed(1)+'%';$('fill').style.width=Math.min(100,d.utilization*100)+'%';$('fill').style.background=d.utilization>1?'var(--coral)':'var(--lime)';$('updated').textContent='Updated '+new Date(d.updated_at).toLocaleTimeString()+' · volatility '+(d.volatility*100).toFixed(1)+'%';}catch(e){$('connection').textContent='RECONNECTING';}}
$('position-form').addEventListener('submit',async e=>{e.preventDefault();await fetch('/api/position',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload())});refresh()});refresh();timer=setInterval(refresh,1000);
</script></body></html>"""

class RiskState:
    def __init__(self) -> None:
        self.position = DEFAULT_POSITION.copy()
        self.quote: dict = {"price": None, "change_percent": 0.0, "volatility": 0.25, "updated_at": None, "market_open": False}
        self.lock = threading.Lock()
        self.ticker: yf.Ticker | None = None
        self.ticker_symbol = ""

    def update_quote(self) -> None:
        with self.lock:
            symbol = self.position["symbol"]
        try:
            if self.ticker is None or self.ticker_symbol != symbol:
                self.ticker, self.ticker_symbol = yf.Ticker(symbol), symbol
            history = self.ticker.history(period="5d", interval="1m", auto_adjust=False, raise_errors=False)
            if history.empty:
                raise RuntimeError("Yahoo returned no candles")
            close = history["Close"].dropna()
            price = float(close.iloc[-1])
            returns = close.pct_change().dropna()
            volatility = max(0.05, min(1.5, float(returns.std() * math.sqrt(252 * 390)) if len(returns) > 10 else 0.25))
            previous = float(close.iloc[-2]) if len(close) > 1 else price
            with self.lock:
                self.quote = {"price": price, "change_percent": (price / previous - 1) * 100 if previous else 0, "volatility": volatility, "updated_at": time.time(), "market_open": True}
        except Exception as exc:
            with self.lock:
                self.quote["error"] = str(exc)
                self.quote["updated_at"] = time.time()

    def state(self) -> dict:
        with self.lock:
            position, quote = self.position.copy(), self.quote.copy()
        price = quote.get("price") or position.get("buy_price") or 0.0
        units = position["lot_size"] * position["quantity"]
        position_value = price * units
        buy_price = position.get("buy_price") or price
        volatility = quote.get("volatility", 0.25)
        scenarios = [buy_price * (1 - volatility * shock) for shock in (0.5, 1.0, 1.5, 2.0)]
        worst_loss = max(0.0, (buy_price - min(scenarios)) * units)
        span_margin = worst_loss + position_value * 0.02
        collateral = position["collateral"]
        utilization = span_margin / collateral if collateral > 0 else 1.0
        if collateral <= 0 or span_margin > collateral:
            state, message = "BREACH", "Estimated loss and SPAN-style margin exceed your collateral."
        elif utilization >= 0.8:
            state, message = "CAUTION", "Collateral is getting tight under the current volatility scan."
        else:
            state, message = "COVERED", "Collateral covers the current SPAN-style risk estimate."
        return {**quote, **position, "position_value": position_value, "worst_loss": worst_loss, "span_margin": span_margin, "headroom": collateral - span_margin, "utilization": utilization, "state": state, "message": message, "updated_at": quote.get("updated_at") or time.time()}

state = RiskState()

def worker() -> None:
    while True:
        state.update_quote()
        time.sleep(1)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def send(self, code: int, content_type: str, body: str) -> None:
        raw = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/state":
            self.send(HTTPStatus.OK, "application/json; charset=utf-8", json.dumps(state.state()))
        elif path == "/":
            self.send(HTTPStatus.OK, "text/html; charset=utf-8", HTML)
        else:
            self.send(HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8", "Not found")

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/position":
            self.send(HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8", "Not found")
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            position = {"symbol": str(body["symbol"]).strip().upper(), "lot_size": max(1, int(body["lot_size"])), "quantity": max(1, int(body["quantity"])), "buy_price": max(0.0, float(body.get("buy_price", 0))), "collateral": max(0.0, float(body["collateral"]))}
            with state.lock:
                if position["symbol"] != state.position["symbol"]:
                    state.ticker = None
                state.position = position
            self.send(HTTPStatus.OK, "application/json; charset=utf-8", json.dumps({"ok": True}))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.send(HTTPStatus.BAD_REQUEST, "application/json; charset=utf-8", json.dumps({"error": str(exc)}))

if __name__ == "__main__":
    threading.Thread(target=worker, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"PRISM live dashboard running at http://localhost:{PORT}")
    server.serve_forever()
