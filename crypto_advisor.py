"""
crypto_advisor.py
비트코인(BTC), 이더리움(ETH), 솔라나(SOL) 3대 가상자산 전용 시세 수집,
뉴스/전망 모멘텀 분석, 매수 추천금액 및 목표 매도금액 산출 모듈 (업비트 API 연동)
"""

import datetime
import requests
import feedparser

UPBIT_TICKER_API = "https://api.upbit.com/v1/ticker"
UPBIT_CANDLES_API = "https://api.upbit.com/v1/candles/days"
CRYPTO_NEWS_RSS = "https://news.google.com/rss/search?q=%EB%B9%84%ED%8A%B8%EC%BD%94%EC%9D%B8+OR+%EC%9D%B4%EB%8D%94%EB%A6%AC%EC%9B%80+OR+%EC%86%94%EB%9D%BC%EB%82%98+%EC%A0%84%EB%A7%9D&hl=ko&gl=KR&ceid=KR:ko"

COIN_TARGETS = [
    {"market": "KRW-BTC", "symbol": "BTC", "name": "비트코인", "icon": "🟠"},
    {"market": "KRW-ETH", "symbol": "ETH", "name": "이더리움", "icon": "🔷"},
    {"market": "KRW-SOL", "symbol": "SOL", "name": "솔라나", "icon": "🟣"},
]


class CryptoAdvisor:
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    @staticmethod
    def calculate_rsi(prices: list, period: int = 14) -> float:
        """14일 기준 RSI 계산"""
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

    @staticmethod
    def _format_krw(price: float) -> str:
        """원화 호가 단위 포맷팅"""
        if price >= 10000000:  # 천만 원 이상 (비트코인)
            rounded = round(price / 1000) * 1000
        elif price >= 1000000:  # 백만 원 이상 (이더리움)
            rounded = round(price / 500) * 500
        elif price >= 100000:  # 십만 원 이상 (솔라나)
            rounded = round(price / 100) * 100
        else:
            rounded = round(price / 10) * 10
        return f"{int(rounded):,}원"

    def get_crypto_news(self, limit=5) -> list:
        """비트코인, 이더리움, 솔라나 관련 최신 뉴스 및 전망 수집"""
        news_items = []
        try:
            feed = feedparser.parse(CRYPTO_NEWS_RSS)
            for entry in feed.entries[:limit]:
                title = entry.get("title", "").strip()
                source = "코인뉴스"
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = parts[0].strip()
                    source = parts[1].strip()

                news_items.append({
                    "title": title,
                    "link": entry.get("link", ""),
                    "source": source,
                    "date": entry.get("published", "")
                })
        except Exception as e:
            print(f"[경고] 코인 뉴스 수집 오류: {e}")
        return news_items

    def analyze_coins(self) -> dict:
        """업비트 실시간 시세 및 캔들 분석을 통한 매수/매도 추천금액 산출"""
        coin_results = []
        markets_param = ",".join(c["market"] for c in COIN_TARGETS)

        # 1. 실시간 시세 조회
        ticker_map = {}
        try:
            r = requests.get(f"{UPBIT_TICKER_API}?markets={markets_param}", headers=self.headers, timeout=6)
            if r.status_code == 200:
                for item in r.json():
                    ticker_map[item["market"]] = item
        except Exception as e:
            print(f"[경고] 업비트 실시간 시세 조회 오류: {e}")

        # 2. 코인 뉴스 수집
        crypto_news = self.get_crypto_news(limit=6)

        # 3. 코인별 일봉 캔들 조회 및 추천가 산출
        for target in COIN_TARGETS:
            market = target["market"]
            symbol = target["symbol"]
            name = target["name"]
            icon = target["icon"]

            ticker_data = ticker_map.get(market)
            if not ticker_data:
                continue

            cur_p = ticker_data["trade_price"]
            change_rate = ticker_data["signed_change_rate"] * 100
            high_24h = ticker_data["high_price"]
            low_24h = ticker_data["low_price"]
            acc_volume_24h = ticker_data["acc_trade_price_24h"]

            # 30일 일봉 캔들 조회
            closes = []
            try:
                c_url = f"{UPBIT_CANDLES_API}?market={market}&count=30"
                c_res = requests.get(c_url, headers=self.headers, timeout=6)
                if c_res.status_code == 200:
                    candles = c_res.json()
                    closes = [c["trade_price"] for c in reversed(candles)]
            except Exception as e:
                print(f"[경고] {name} 캔들 조회 오류: {e}")

            # 기술적 지표 계산
            ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else cur_p
            disparity_20 = ((cur_p - ma20) / ma20) * 100 if ma20 else 0.0
            rsi = self.calculate_rsi(closes, period=14) if closes else 50.0

            # -------------------------------------------------------------
            # 매수/매도 추천 신호 및 추천 호가 계산
            # -------------------------------------------------------------
            signal = "관망 / 분할 적립 (HOLD)"
            outlook = "중립 횡보 추세"

            if rsi <= 38 or disparity_20 <= -4.0:
                signal = "🟢 단기 매수 유망 (과매도 반등)"
                outlook = f"RSI {rsi}로 단기 과매도 구간 진입, 기술적 반등 기대"
                calc_buy_price = cur_p * 0.992
                calc_sell_price = max(cur_p * 1.06, ma20 * 0.99)
                calc_stop_loss = cur_p * 0.965
            elif rsi >= 70 or disparity_20 >= 6.5:
                signal = "🔴 단기 매도 / 분할 익절 (과열 주의)"
                outlook = f"RSI {rsi}, 20일선 이격도 {disparity_20:+.1f}%로 단기 과열권, 분할 차익실현 권고"
                calc_buy_price = ma20 * 0.99  # 20일선까지 조정 시 매수
                calc_sell_price = cur_p * 1.01  # 현재가 부근 익절
                calc_stop_loss = cur_p * 0.97
            elif disparity_20 >= -1.5 and disparity_20 <= 2.5:
                signal = "⭐ 지지선 안착 매수 (눌림목)"
                outlook = "20일 이동평균선 지지선 안착, 상승 추세 지속 전망"
                calc_buy_price = cur_p * 0.995
                calc_sell_price = cur_p * 1.08
                calc_stop_loss = ma20 * 0.97
            else:
                calc_buy_price = min(cur_p * 0.985, ma20)
                calc_sell_price = max(cur_p * 1.06, ma20 * 1.05)
                calc_stop_loss = cur_p * 0.95

            expected_yield = ((calc_sell_price - calc_buy_price) / calc_buy_price * 100) if calc_buy_price else 0.0

            coin_results.append({
                "symbol": symbol,
                "name": name,
                "icon": icon,
                "cur_price": self._format_krw(cur_p),
                "change_rate": f"{change_rate:+.2f}%",
                "high_24h": self._format_krw(high_24h),
                "low_24h": self._format_krw(low_24h),
                "buy_price": self._format_krw(calc_buy_price),
                "sell_price": self._format_krw(calc_sell_price),
                "stop_loss": self._format_krw(calc_stop_loss),
                "expected_yield": f"+{expected_yield:.1f}%",
                "signal": signal,
                "outlook": outlook,
                "rsi": rsi,
                "disparity_20": f"{disparity_20:+.1f}%",
                "volume_24h_krw": f"{int(acc_volume_24h / 100000000):,}억원",
            })

        return {
            "coins": coin_results,
            "crypto_news": crypto_news,
        }
