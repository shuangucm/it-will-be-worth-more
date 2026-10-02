#!/usr/bin/env python3
"""Fetch daily closes for the tracked ETFs and write docs/data/prices.json.

Run by .github/workflows/update-prices.yml. Standard library only.
"""
import csv
import datetime as dt
import io
import json
import pathlib
import sys
import urllib.request

TICKERS = ["QQQ", "VOO"]
LOOKBACK_MONTHS = 6
LONG_TERM_YEARS = 5
OUT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "data" / "prices.json"
UA = {"User-Agent": "Mozilla/5.0 (spend-vs-invest price updater)"}


def http_get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def fetch_yahoo(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=5y&interval=1d"
    result = json.loads(http_get(url))["chart"]["result"][0]
    stamps = result["timestamp"]
    quote = result["indicators"]
    # Prefer adjusted close so dividends count toward the return.
    closes = (quote.get("adjclose") or [{}])[0].get("adjclose") or quote["quote"][0]["close"]
    return [
        (dt.datetime.fromtimestamp(t, dt.timezone.utc).date(), c)
        for t, c in zip(stamps, closes)
        if c is not None
    ]


def fetch_stooq(ticker):
    text = http_get(f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d")
    rows = list(csv.DictReader(io.StringIO(text)))
    cutoff = dt.date.today() - dt.timedelta(days=366 * LONG_TERM_YEARS + 10)
    out = []
    for r in rows:
        d = dt.date.fromisoformat(r["Date"])
        if d >= cutoff:
            out.append((d, float(r["Close"])))
    return out


def fetch(ticker):
    errors = []
    for source in (fetch_yahoo, fetch_stooq):
        try:
            series = source(ticker)
            if len(series) > 250:
                return series, source.__name__.removeprefix("fetch_")
            errors.append(f"{source.__name__}: only {len(series)} rows")
        except Exception as e:  # noqa: BLE001 - try the next source
            errors.append(f"{source.__name__}: {e}")
    raise RuntimeError(f"{ticker}: all sources failed: {errors}")


def months_ago(d, months):
    y, m = divmod(d.month - 1 - months, 12)
    year, month = d.year + y, m + 1
    day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 or year % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return dt.date(year, month, day)


def close_on_or_before(series, target):
    """Last trading day on or before the target date (or the first point we have)."""
    return max((p for p in series if p[0] <= target), default=series[0])


def long_term(series, years=LONG_TERM_YEARS):
    end_date, end_close = series[-1]
    start_date, start_close = close_on_or_before(series, months_ago(end_date, 12 * years))
    span = (end_date - start_date).days / 365.25
    return {
        "long_term_start_date": start_date.isoformat(),
        "long_term_years": round(span, 2),
        "long_term_annualized_return": round((end_close / start_close) ** (1 / span) - 1, 6),
    }


def summarize(series, months=LOOKBACK_MONTHS):
    series = sorted(series)
    end_date, end_close = series[-1]
    target = months_ago(end_date, months)
    start_date, start_close = close_on_or_before(series, target)
    period_return = end_close / start_close - 1
    years = (end_date - start_date).days / 365.25
    annualized = (1 + period_return) ** (1 / years) - 1
    monthly = (1 + period_return) ** (1 / months) - 1
    return {
        "last_date": end_date.isoformat(),
        "last_close": round(end_close, 4),
        "start_date": start_date.isoformat(),
        "start_close": round(start_close, 4),
        "period_months": months,
        "period_return": round(period_return, 6),
        "avg_monthly_return": round(monthly, 6),
        "annualized_return": round(annualized, 6),
        **long_term(series),
        # Weekly closes keep the file small but are enough for a sparkline.
        "history": [
            [d.isoformat(), round(c, 2)]
            for i, (d, c) in enumerate(series)
            if d >= start_date and (i % 5 == 0 or i == len(series) - 1)
        ],
    }


def main():
    data = {"updated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "tickers": {}}
    for t in TICKERS:
        series, source = fetch(t)
        data["tickers"][t] = {"source": source, **summarize(series)}
        s = data["tickers"][t]
        print(f"{t}: {s['start_date']} {s['start_close']} -> {s['last_date']} {s['last_close']} "
              f"({s['period_return']:+.2%} / 6mo, {s['annualized_return']:+.2%} annualized; "
              f"{s['long_term_annualized_return']:+.2%}/yr over {s['long_term_years']}y) via {source}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    sys.exit(main())
