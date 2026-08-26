#!/usr/bin/env python3
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TZ = timezone(timedelta(hours=8))


def load_json(name, default):
    p = ROOT / name
    if not p.exists():
        return default
    with p.open('r', encoding='utf-8') as f:
        return json.load(f)


def save_json(name, data):
    p = ROOT / name
    with p.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def num(v):
    try:
        x = float(v)
        return x if x == x else None
    except Exception:
        return None


def valuation_state(stock):
    price = num(stock.get('price'))
    values = [num(v) for v in stock.get('values', [])]
    values = sorted(v for v in values if v is not None)
    if price is None or len(values) < 5:
        return None
    if price <= values[0]:
        return '特價'
    if price <= values[1]:
        return '便宜價'
    if len(values) >= 6:
        if price <= values[2]:
            return '合理價(下緣)'
        if price <= values[3]:
            return '合理價(上緣)'
        if price <= values[4]:
            return '昂貴價'
        return '瘋狂價'
    if price <= values[3]:
        return '合理價'
    return '昂貴價'


def push_line(token, target, text):
    body = json.dumps({
        'to': target,
        'messages': [{'type': 'text', 'text': text}],
    }, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        'https://api.line.me/v2/bot/message/push',
        data=body,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status < 200 or resp.status >= 300:
            raise RuntimeError(f'LINE push failed: HTTP {resp.status}')


def message(stock, state, updated, dashboard_url):
    code = stock.get('code', '')
    name = stock.get('name', '')
    price = num(stock.get('price'))
    pe = num(stock.get('pe'))
    base_pe = num(stock.get('basePE'))
    emoji = '🟩' if state == '便宜價' else '💚'
    lines = [
        f'{emoji} 估值到價提醒',
        f'{name} {code}',
        f'目前股價：{price:,.2f} 元' if price is not None else '目前股價：—',
        f'估值狀態：{state}',
        f'即時本益比：{pe:.2f} 倍' if pe is not None else '即時本益比：—',
        f'60日基準 PE：{base_pe:.2f} 倍' if base_pe is not None else '60日基準 PE：—',
        f'資料更新：{updated or "—"}',
        '提醒用途：估值條件通知，非買賣指示。',
    ]
    if dashboard_url:
        lines.append(dashboard_url)
    return '\n'.join(lines)


def main():
    db = load_json('stocks.json', {})
    config = load_json('line_alert_config.json', {})
    state_doc = load_json('line_alert_state.json', {'updated': None, 'stocks': {}})
    stocks = db.get('stocks', {})
    watchlist = [str(x).strip() for x in config.get('watchlist', []) if str(x).strip()]
    alert_states = set(config.get('alertStates', ['便宜價', '特價']))
    dashboard_url = config.get('dashboardUrl', '')
    token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '').strip()
    target = os.environ.get('LINE_TARGET_ID', '').strip()
    can_send = bool(token and target and config.get('enabled', True))
    now = datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')
    previous = state_doc.setdefault('stocks', {})
    changed = False
    sent = 0

    print(f'watchlist={watchlist}')
    print(f'LINE configured={can_send}')

    for code in watchlist:
        stock = stocks.get(code)
        if not stock:
            print(f'{code}: missing from stocks.json')
            continue
        current = valuation_state(stock)
        old = previous.get(code, {}).get('state')
        print(f'{code} {stock.get("name", "")}: {old} -> {current}')
        if current is None:
            continue

        entering_alert = current in alert_states and old != current
        # Moving from 特價 to 便宜價 is not treated as a fresh bargain entry.
        if old == '特價' and current == '便宜價':
            entering_alert = False

        if entering_alert:
            if not can_send:
                print(f'{code}: alert condition met but LINE secrets are not configured; state is NOT advanced.')
                continue
            text = message(stock, current, db.get('updated'), dashboard_url)
            push_line(token, target, text)
            sent += 1
            previous[code] = {'state': current, 'notifiedAt': now}
            changed = True
            print(f'{code}: LINE sent')
        else:
            old_doc = previous.get(code, {})
            if old_doc.get('state') != current:
                previous[code] = {**old_doc, 'state': current, 'observedAt': now}
                changed = True

    if changed:
        state_doc['updated'] = now
        save_json('line_alert_state.json', state_doc)
    print(f'sent={sent}, state_changed={changed}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
