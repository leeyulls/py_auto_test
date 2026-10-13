"""
stock_advisor.py
주가 기술적 분석과 뉴스 모멘텀을 종합하여
'매수 추천금액' 및 '매도 추천금액'을 정밀 산출하고,
오늘/장기 매수·매도 투자 신호를 도출하는 어드바이저 모듈
"""

from stock_universe import STOCK_UNIVERSE, match_stocks_from_news
from stock_analyzer import StockAnalyzer


class StockAdvisor:
    def __init__(self):
        self.analyzer = StockAnalyzer()

    @staticmethod
    def _format_price(price: float, is_usd: bool) -> str:
        """통화별 호가 단위 정밀 포맷팅"""
        if is_usd:
            return f"${price:,.2f}"
        # 국내 주식 호가 단위 반올림 (10만원 이상 500원 단위, 1만원 이상 100원 단위, 미만 10원 단위)
        if price >= 100000:
            rounded = round(price / 500) * 500
        elif price >= 10000:
            rounded = round(price / 100) * 100
        elif price >= 1000:
            rounded = round(price / 10) * 10
        else:
            rounded = round(price)
        return f"{int(rounded):,}원"

    def analyze_universe(self, news_list: list) -> dict:
        """관심 유니버스 전체를 대상으로 기술적 지표와 뉴스 모멘텀 결합 분석 및 매수가/매도가 산출"""
        matched_news_dict = match_stocks_from_news(news_list)
        all_evaluations = []

        today_buy_list = []
        longterm_buy_list = []
        sell_warning_list = []

        for stock in STOCK_UNIVERSE:
            ticker = stock["ticker"]
            tech = self.analyzer.fetch_stock_data(ticker)
            if not tech:
                continue

            news_meta = matched_news_dict.get(ticker, {
                "sentiment_score": 0,
                "news_count": 0,
                "matched_news": []
            })
            sentiment = news_meta["sentiment_score"]
            news_count = news_meta["news_count"]

            cur_p = tech["cur_price"]
            is_usd = tech["currency"] == "$"
            rsi = tech["rsi"]
            disp = tech["disparity_20"]
            ret5 = tech["return_5d"]
            ma20 = tech["ma20"]
            ma60 = tech["ma60"]
            pos_52w = tech["pos_52w"]
            recent_high = tech["recent_high"]
            recent_low = tech["recent_low"]

            # -------------------------------------------------------------
            # 1. 단기 매매 판정 (오늘의 매수 vs 매도)
            # -------------------------------------------------------------
            short_signal = "관망 (HOLD)"
            short_reason = "중립 구간 유지 중"

            # 매수가 & 매도가 초기화
            calc_buy_price = cur_p
            calc_sell_price = cur_p * 1.05
            calc_stop_loss = cur_p * 0.96

            # 단기 매수 조건
            if (rsi <= 38 or disp <= -5.0) and sentiment >= 0:
                short_signal = "🟢 오늘 단기 매수 (저점 반등)"
                short_reason = f"RSI {rsi}로 단기 과매도 구간 진입, 기술적 반등 노림"
                # 매수 추천가: 현재가 ~ -1.5% 분할 매수선
                calc_buy_price = cur_p * 0.99
                # 목표 매도가: 20일선 복귀 또는 +6~8% 목표
                calc_sell_price = max(cur_p * 1.06, ma20 * 0.98)
                calc_stop_loss = cur_p * 0.965
            elif (disp >= -2.0 and disp <= 3.0) and sentiment >= 1:
                short_signal = "🟢 오늘 단기 매수 (뉴스 모멘텀)"
                short_reason = "20일선 안착 중 호재성 뉴스 모멘텀 발생"
                calc_buy_price = cur_p
                calc_sell_price = cur_p * 1.07
                calc_stop_loss = cur_p * 0.96
            # 단기 매도/익절 조건
            elif rsi >= 70 or disp >= 7.0:
                short_signal = "🔴 오늘 단기 매도 (과열 차익실현)"
                short_reason = f"RSI {rsi}, 20일선 이격도 {disp:+.1f}%로 단기 과열권, 분할 차익 실현 권고"
                calc_buy_price = ma20  # 매수 보류, 20일선까지 조정 시 매수
                calc_sell_price = cur_p  # 즉시 분할 매도
                calc_stop_loss = cur_p * 0.98
            elif sentiment <= -1 and ret5 <= -4.0:
                short_signal = "🔴 단기 비중 축소 (악재 주의)"
                short_reason = "악재 보도 및 5일 연속 약세로 단기 추가 하락 위험"
                calc_buy_price = recent_low * 0.95
                calc_sell_price = cur_p * 0.99
                calc_stop_loss = cur_p * 0.97
            else:
                # 관망 중립 상태
                calc_buy_price = min(cur_p * 0.98, ma20)
                calc_sell_price = max(cur_p * 1.05, recent_high)
                calc_stop_loss = cur_p * 0.95

            # -------------------------------------------------------------
            # 2. 중장기 매매 판정 (장기 매수 vs 장기 매도)
            # -------------------------------------------------------------
            long_signal = "보유 / 중립 (HOLD)"
            long_reason = "장기 추세 유지"

            if stock["sector"] in ["반도체/IT", "반도체/AI", "방산/우주", "글로벌 AI/반도체", "자동차/모빌리티"]:
                if 25.0 <= pos_52w <= 75.0 and cur_p >= ma60 * 0.95:
                    long_signal = "⭐ 장기 적립/매수 (유망 섹터)"
                    long_reason = f"성장 주도 산업 + 52주 고점 대비 건전한 눌림목({pos_52w}%), 장기 분할 매수 적기"
                    # 장기 투자 매수/매도가 조정
                    calc_buy_price = cur_p * 0.985
                    calc_sell_price = max(cur_p * 1.15, tech["high_52w"] * 0.95)
                    calc_stop_loss = ma60 * 0.94

            if cur_p < ma60 * 0.90 and sentiment <= 0 and pos_52w < 20.0:
                long_signal = "⚠️ 장기 비중 축소 / 손절 검토"
                long_reason = "60일선 하향 이탈 및 52주 신저가 부근, 중장기 추세 하향 전환 우려"

            # 금액 문자열 포맷팅
            str_buy_price = self._format_price(calc_buy_price, is_usd)
            str_sell_price = self._format_price(calc_sell_price, is_usd)
            str_stop_loss = self._format_price(calc_stop_loss, is_usd)
            expected_yield = ((calc_sell_price - calc_buy_price) / calc_buy_price * 100) if calc_buy_price else 0.0

            # 추천 리스트 집계
            if "매수" in short_signal:
                today_buy_list.append({
                    "name": stock["name"],
                    "ticker": ticker,
                    "cur_price": self._format_price(cur_p, is_usd),
                    "buy_price": str_buy_price,
                    "sell_price": str_sell_price,
                    "expected_yield": f"+{expected_yield:.1f}%",
                    "reason": short_reason,
                })
            elif "매도" in short_signal or "과열" in short_signal:
                sell_warning_list.append({
                    "name": stock["name"],
                    "ticker": ticker,
                    "cur_price": self._format_price(cur_p, is_usd),
                    "sell_price": str_sell_price,
                    "type": "단기 과열 익절",
                    "reason": short_reason,
                })

            if "장기 적립/매수" in long_signal:
                longterm_buy_list.append({
                    "name": stock["name"],
                    "ticker": ticker,
                    "cur_price": self._format_price(cur_p, is_usd),
                    "buy_price": str_buy_price,
                    "sell_price": str_sell_price,
                    "expected_yield": f"+{expected_yield:.1f}%",
                    "reason": long_reason,
                })
            elif "비중 축소" in long_signal:
                sell_warning_list.append({
                    "name": stock["name"],
                    "ticker": ticker,
                    "cur_price": self._format_price(cur_p, is_usd),
                    "sell_price": str_sell_price,
                    "type": "장기 추세 하락",
                    "reason": long_reason,
                })

            # 뉴스 모멘텀
            news_summary = "최근 특이 뉴스 없음"
            if news_meta["matched_news"]:
                top_news = news_meta["matched_news"][0]
                news_summary = f"{top_news['title']} ({top_news['source']})"

            all_evaluations.append({
                "종목명": stock["name"],
                "티커": ticker,
                "섹터": stock["sector"],
                "현재가": self._format_price(cur_p, is_usd),
                "전일대비": f"{tech['diff']:+,}{tech['currency']} ({tech['diff_ratio']:+.2f}%)",
                "매수_추천금액": str_buy_price,
                "목표_매도금액": str_sell_price,
                "손절_기준가": str_stop_loss,
                "기대_수익률": f"{expected_yield:+.1f}%",
                "단기신호": short_signal,
                "단기근거": short_reason,
                "장기신호": long_signal,
                "장기근거": long_reason,
                "RSI(14)": tech["rsi"],
                "20일선이격도": f"{tech['disparity_20']:+.1f}%",
                "52주위치": f"{tech['pos_52w']}%",
                "핵심뉴스": news_summary,
            })

        return {
            "all_evaluations": all_evaluations,
            "today_buy_picks": today_buy_list,
            "longterm_buy_picks": longterm_buy_list,
            "sell_warning_picks": sell_warning_list,
        }
