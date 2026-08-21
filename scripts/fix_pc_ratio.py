import json, math, os, re
from datetime import datetime
import requests

ROOT = os.path.dirname(os.path.dirname(__file__))
MARKET = os.path.join(ROOT, 'market.json')
HISTORY = os.path.join(ROOT, 'market_history.json')
URL = 'https://openapi.taifex.com.tw/v1/PutCallRatio'


def num(v):
    try:
        if v is None:
            return None
        s = str(v).replace(',', '').replace('%', '').strip()
        if not s or s in ('--', '-', 'null', 'None'):
            return None
        x = float(s)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def norm(k):
    return re.sub(r'[\s_/%()（）-]+', '', str(k)).lower()


def row_date(row):
    preferred, other = [], []
    for k, v in row.items():
        (preferred if ('date' in norm(k) or '日期' in str(k)) else other).append(v)
    for v in preferred + other:
        digits = ''.join(ch for ch in str(v) if ch.isdigit())
        if len(digits) >= 8:
            d = digits[:8]
            if d.startswith('20'):
                try:
                    return datetime.strptime(d, '%Y%m%d').date().isoformat()
                except Exception:
                    pass
    return None


def pick(row, predicates):
    for k, v in row.items():
        nk = norm(k)
        if any(p(nk, str(k)) for p in predicates):
            x = num(v)
            if x is not None:
                return x
    return None


def direct_ratios(row):
    trade = pick(row, [
        lambda k, raw: ('putcall' in k and ('volume' in k or '成交' in raw) and 'ratio' in k),
        lambda k, raw: ('買賣權成交量比率' in raw or '賣買權成交量比率' in raw),
    ])
    oi = pick(row, [
        lambda k, raw: ('putcall' in k and ('oi' in k or 'openinterest' in k or '未平倉' in raw) and 'ratio' in k),
        lambda k, raw: ('買賣權未平倉量比率' in raw or '賣買權未平倉量比率' in raw),
    ])
    return trade, oi


def calculated_ratios(row):
    put_vol = pick(row, [
        lambda k, raw: ('putvolume' in k and 'ratio' not in k),
        lambda k, raw: ('賣權成交量' in raw and '比率' not in raw),
    ])
    call_vol = pick(row, [
        lambda k, raw: ('callvolume' in k and 'ratio' not in k),
        lambda k, raw: ('買權成交量' in raw and '比率' not in raw),
    ])
    put_oi = pick(row, [
        lambda k, raw: (('putopeninterest' in k or 'putoi' in k) and 'ratio' not in k),
        lambda k, raw: ('賣權未平倉量' in raw and '比率' not in raw),
    ])
    call_oi = pick(row, [
        lambda k, raw: (('callopeninterest' in k or 'calloi' in k) and 'ratio' not in k),
        lambda k, raw: ('買權未平倉量' in raw and '比率' not in raw),
    ])
    trade = (put_vol / call_vol) if put_vol is not None and call_vol not in (None, 0) else None
    oi = (put_oi / call_oi) if put_oi is not None and call_oi not in (None, 0) else None
    return trade, oi


def decimal_ratio(v):
    if v is None:
        return None
    return v / 100.0 if v > 10 else v


def main():
    with open(MARKET, 'r', encoding='utf-8') as f:
        market = json.load(f)
    target = market.get('date')

    r = requests.get(URL, timeout=30, headers={'User-Agent': 'Mozilla/5.0 TaiwanStockDashboard/2.2'})
    r.raise_for_status()
    data = r.json()
    rows = data if isinstance(data, list) else data.get('data', []) if isinstance(data, dict) else []
    if not rows:
        raise RuntimeError('TAIFEX PutCallRatio returned no rows')

    exact = [row for row in rows if row_date(row) == target]
    if not exact:
        available = [(row_date(row), row) for row in rows if row_date(row)]
        raise RuntimeError(f'No exact TAIFEX P/C row for {target}; latest={max((d for d,_ in available), default="unknown")}')

    row = exact[0]
    trade, oi = direct_ratios(row)
    trade = decimal_ratio(trade)
    oi = decimal_ratio(oi)

    c_trade, c_oi = calculated_ratios(row)
    if trade is None:
        trade = c_trade
    if oi is None:
        oi = c_oi

    if trade is None or oi is None:
        print('TAIFEX row keys:', list(row.keys()))
        raise RuntimeError(f'Could not parse P/C ratios for {target}: trade={trade}, oi={oi}')

    market['pc'] = {'trade': round(trade, 4), 'oi': round(oi, 4), 'date': target}
    market.setdefault('sources', {})['taifexPC'] = True
    with open(MARKET, 'w', encoding='utf-8') as f:
        json.dump(market, f, ensure_ascii=False, indent=2)

    try:
        with open(HISTORY, 'r', encoding='utf-8') as f:
            hist = json.load(f)
        rows_h = hist if isinstance(hist, list) else hist.get('days', []) if isinstance(hist, dict) else []
        for h in rows_h:
            if h.get('date') == target:
                h['pc'] = market['pc']
                break
        with open(HISTORY, 'w', encoding='utf-8') as f:
            json.dump(hist, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print('history update skipped:', e)

    print(f'P/C updated for {target}: trade={trade:.4f}, oi={oi:.4f}')


if __name__ == '__main__':
    main()
