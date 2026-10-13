"""
stock_advisor.py
주가 기술적 분석과 뉴스 모멘텀을 종합하여
'오늘 사면 좋을 주식', '장기적으로 사면 좋을 주식', '팔면 좋을 주식' 추천 신호를 도출하는 어드바이저 모듈
"""

from stock_universe import STOCK_UNIVERSE, match_stocks_from_news
from stock_analyzer import StockAnalyzer


class StockAdvisor:
    def __init__(self):
        self.analyzer = StockAnalyzer()

    def analyze_universe(self, news_list: list) -> dict:
        """관심 유니버스 전체를 대상으로 기술적 지표와 뉴스 모멘텀 결합 분석"""
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

            # -------------------------------------------------------------
            # 1. 단기 매매 판정 (오늘의 매수 vs 매도)
            # -------------------------------------------------------------
            rsi = tech["rsi"]
            disp = tech["disparity_20"]
            ret5 = tech["return_5d"]

            short_signal = "관망 (HOLD)"
            short_reason = "중립 구간 유지 중"

            # 단기 매수 조건
            if (rsi <= 38 or disp <= -5.0) and sentiment >= 0:
                short_signal = "🟢 오늘 단기 매수 (저점 반등)"
                short_reason = f"RSI {rsi}로 단기 과매도 구간 진입, 기술적 기술 반등 노림"
                today_buy_list.append({"name": stock["name"], "ticker": ticker, "reason": short_reason, "price": f"{tech['cur_price']:,}{tech['currency']}"})
            elif (disp >= -2.0 and disp <= 3.0) and sentiment >= 1:
                short_signal = "🟢 오늘 단기 매수 (뉴스 모멘텀)"
                short_reason = "20일선 안착 중 호재성 뉴스 모멘텀 발생"
                today_buy_list.append({"name": stock["name"], "ticker": ticker, "reason": short_reason, "price": f"{tech['cur_price']:,}{tech['currency']}"})
            # 단기 매도/익절 조건
            elif rsi >= 70 or disp >= 7.0:
                short_signal = "🔴 오늘 단기 매도 (과열 차익실현)"
                short_reason = f"RSI {rsi}, 20일선 이격도 {disp:+.1f}%로 단기 과열권, 분할 차익 실현 권고"
                sell_warning_list.append({"name": stock["name"], "ticker": ticker, "type": "단기 과열 매도", "reason": short_reason})
            elif sentiment <= -1 and ret5 <= -4.0:
                short_signal = "🔴 단기 비중 축소 (악재 주의)"
                short_reason = "악재 보도 및 5일 연속 약세로 단기 추가 하락 위험"
                sell_warning_list.append({"name": stock["name"], "ticker": ticker, "type": "단기 리스크 관리", "reason": short_reason})

            # -------------------------------------------------------------
            # 2. 중장기 매매 판정 (장기 매수 vs 장기 매도)
            # -------------------------------------------------------------
            pos_52w = tech["pos_52w"]
            ma20 = tech["ma20"]
            ma60 = tech["ma60"]
            cur_p = tech["cur_price"]

            long_signal = "보유 / 중립 (HOLD)"
            long_reason = "장기 추세 유지"

            # 장기 매수 조건
            if stock["sector"] in ["반도체/AI", "방산/우주", "글로벌 AI/반도체", "자동차/모빌리티"]:
                if 25.0 <= pos_52w <= 75.0 and cur_p >= ma60 * 0.95:
                    long_signal = "⭐ 장기 적립/매수 (유망 섹터)"
                    long_reason = f"주도 산업(성장성 높음) + 52주 고점 대비 건전한 눌림목({pos_52w}% 위치), 장기 분할 매수 적기"
                    longterm_buy_list.append({"name": stock["name"], "ticker": ticker, "reason": long_reason, "price": f"{tech['cur_price']:,}{tech['currency']}"})
            # 장기 매도 조건
            if cur_p < ma60 * 0.90 and sentiment <= 0 and pos_52w < 20.0:
                long_signal = "⚠️ 장기 비중 축소 / 손절 검토"
                long_reason = "60일선 하향 이탈 및 52주 신저가 부근, 중장기 추세 하향 전환 우려"
                sell_warning_list.append({"name": stock["name"], "ticker": ticker, "type": "장기 추세 하락", "reason": long_reason})

            # 뉴스 모멘텀 텍스트
            news_summary = "최근 특이 뉴스 없음"
            if news_meta["matched_news"]:
                top_news = news_meta["matched_news"][0]
                news_summary = f"{top_news['title']} ({top_news['source']})"

            all_evaluations.append({
                "종목명": stock["name"],
                "티커": ticker,
                "섹터": stock["sector"],
                "현재가": f"{tech['cur_price']:,}{tech['currency']}",
                "전일대비": f"{tech['diff']:+,}{tech['currency']} ({tech['diff_ratio']:+.2f}%)",
                "RSI(14)": tech["rsi"],
                "20일선이격도": f"{tech['disparity_20']:+.1f}%",
                "52주위치": f"{tech['pos_52w']}%",
                "단기신호": short_signal,
                "단기근거": short_reason,
                "장기신호": long_signal,
                "장기근거": long_reason,
                "관련뉴스수": news_count,
                "핵심뉴스": news_summary
            })

        return {
            "all_evaluations": all_evaluations,
            "today_buy_picks": today_buy_list,
            "longterm_buy_picks": longterm_buy_list,
            "sell_warning_picks": sell_warning_list
        }
