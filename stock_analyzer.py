"""
stock_analyzer.py
종목별 과거/현재 주가 데이터 수집 및 기술적 지표(이동평균, RSI, 이격도) 분석 모듈
"""

import requests
from crawler_config import REQUEST_HEADERS


class StockAnalyzer:
    def __init__(self):
        self.headers = REQUEST_HEADERS

    @staticmethod
    def calculate_rsi(prices: list, period: int = 14) -> float:
        """14일 기준 RSI (상대강도지수) 계산"""
        if len(prices) < period + 1:
            return 50.0

        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 1)

    def fetch_stock_data(self, ticker: str) -> dict:
        """야후 파이낸스 차트 API로부터 6개월간 일봉 및 시세 메타데이터 수집"""
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=6mo&interval=1d"
        try:
            r = requests.get(url, headers=self.headers, timeout=8)
            if r.status_code != 200:
                return None

            data = r.json()["chart"]["result"][0]
            meta = data.get("meta", {})
            quotes = data.get("indicators", {}).get("quote", [{}])[0]
            closes = [c for c in quotes.get("close", []) if c is not None]

            if not closes:
                return None

            cur_price = meta.get("regularMarketPrice", closes[-1])
            prev_close = meta.get("chartPreviousClose", closes[-2] if len(closes) > 1 else cur_price)
            diff = cur_price - prev_close
            diff_ratio = (diff / prev_close * 100) if prev_close else 0

            # 52주 최고/최저가
            high_52w = meta.get("fiftyTwoWeekHigh", max(closes))
            low_52w = meta.get("fiftyTwoWeekLow", min(closes))

            # 이동평균선 계산
            ma20 = sum(closes[-20:]) / min(len(closes), 20) if len(closes) >= 5 else cur_price
            ma60 = sum(closes[-60:]) / min(len(closes), 60) if len(closes) >= 20 else cur_price

            # 20일선 이격도 (%)
            disparity_20 = ((cur_price - ma20) / ma20) * 100 if ma20 else 0

            # RSI 계산 (최근 14일)
            rsi = self.calculate_rsi(closes, period=14)

            # 1주일(5일) 전 대비 수익률
            price_5d_ago = closes[-5] if len(closes) >= 5 else closes[0]
            return_5d = ((cur_price - price_5d_ago) / price_5d_ago) * 100 if price_5d_ago else 0

            # 52주 내 현재가 위치 백분율 (0% ~ 100%)
            pos_52w = ((cur_price - low_52w) / (high_52w - low_52w) * 100) if high_52w > low_52w else 50.0

            is_usd = not (ticker.endswith(".KS") or ticker.endswith(".KQ"))
            currency_symbol = "$" if is_usd else "원"

            recent_high = max(closes[-20:]) if len(closes) >= 20 else max(closes)
            recent_low = min(closes[-20:]) if len(closes) >= 20 else min(closes)

            return {
                "ticker": ticker,
                "cur_price": cur_price,
                "prev_close": prev_close,
                "diff": diff,
                "diff_ratio": diff_ratio,
                "currency": currency_symbol,
                "high_52w": high_52w,
                "low_52w": low_52w,
                "recent_high": recent_high,
                "recent_low": recent_low,
                "pos_52w": round(pos_52w, 1),
                "ma20": round(ma20, 1),
                "ma60": round(ma60, 1),
                "disparity_20": round(disparity_20, 2),
                "rsi": rsi,
                "return_5d": round(return_5d, 2),
            }
        except Exception as e:
            print(f"[경고] {ticker} 주가 수집 오류: {e}")
            return None
