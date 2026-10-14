"""
stock_advisor.py
주가 기술적 분석과 뉴스 모멘텀을 종합하여
'매수 추천금액' 및 '매도 추천금액'을 정밀 산출하고,
오늘/장기 매수·매도 투자 신호를 도출하는 어드바이저 모듈
"""

import datetime
import os
import pandas as pd
from stock_universe import STOCK_UNIVERSE, match_stocks_from_news
from stock_analyzer import StockAnalyzer


class StockAdvisor:
    def __init__(self, master_file_path=None, usd_krw_rate: float = 1390.0):
        self.analyzer = StockAnalyzer()
        self.usd_krw_rate = usd_krw_rate
        if master_file_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.master_file = os.path.join(base_dir, "reports", "일자별_누적_데일리_이슈_및_주식_브리핑_마스터.xlsx")
        else:
            self.master_file = master_file_path

    def get_recent_buy_picks(self, days: int = 3) -> dict:
        """최근 N일간 단기 매수로 추천되었던 종목 조회 (쿨다운 적용용)"""
        cooldown_map = {}
        if not os.path.exists(self.master_file):
            return cooldown_map

        try:
            with pd.ExcelFile(self.master_file) as reader:
                if "주식추천_누적" not in reader.sheet_names:
                    return cooldown_map
                df = pd.read_excel(reader, sheet_name="주식추천_누적")
                if df.empty or "분석일자" not in df.columns or "단기신호" not in df.columns:
                    return cooldown_map

                today = datetime.date.today()
                df["일자"] = pd.to_datetime(df["분석일자"]).dt.date
                cutoff_date = today - datetime.timedelta(days=days)

                recent_buys = df[(df["일자"] >= cutoff_date) & (df["일자"] < today) & (df["단기신호"].str.contains("오늘 단기 매수", na=False))]

                for _, row in recent_buys.iterrows():
                    ticker = str(row["티커"])
                    rec_date = row["일자"]
                    days_ago = (today - rec_date).days
                    if ticker not in cooldown_map or days_ago < cooldown_map[ticker]["days_ago"]:
                        cooldown_map[ticker] = {
                            "date": str(rec_date),
                            "days_ago": days_ago,
                            "name": str(row.get("종목명", ""))
                        }
        except Exception as e:
            print(f"[경고] 쿨다운 히스토리 조회 실패: {e}")

        return cooldown_map

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

    def analyze_universe(self, news_list: list, usd_krw_rate: float = None) -> dict:
        """관심 유니버스 전체를 대상으로 기술적 지표, 뉴스 모멘텀, 쿨다운 주기 결합 분석 및 매수가/매도가 산출"""
        if usd_krw_rate:
            self.usd_krw_rate = usd_krw_rate
        matched_news_dict = match_stocks_from_news(news_list)
        cooldown_map = self.get_recent_buy_picks(days=3)
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

            # 단기 매수 신호가 발생했더라도 최근 3일 내 추천 종목이면 쿨다운 적용
            if "오늘 단기 매수" in short_signal and ticker in cooldown_map:
                cd = cooldown_map[ticker]
                short_signal = f"⏸️ 관망/보유 (쿨다운 {cd['days_ago']}일차)"
                short_reason = f"최근 {cd['days_ago']}일 전({cd['date']}) 단기 매수 추천 이력 존재 ➔ 중복 매수 방지 쿨다운 적용(기존 포지션 분할 보유/관망 권고)"
                calc_buy_price = min(cur_p * 0.98, ma20)
                calc_sell_price = max(cur_p * 1.05, recent_high)
                calc_stop_loss = cur_p * 0.95

            # -------------------------------------------------------------
            # 2. 중장기 매매 판정 (장기 매수 vs 장기 매도)
            # -------------------------------------------------------------
            long_signal = "보유 / 중립 (HOLD)"
            long_reason = "장기 추세 유지"

            if stock["sector"] in ["반도체/IT", "반도체/AI", "방산/우주", "글로벌 AI/반도체", "자동차/모빌리티", "글로벌 AI/클라우드", "글로벌 빅테크"]:
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

            # 미국 빅테크인 경우 원화 환산 가격 병기
            krw_cur_str = f" (약 {int(cur_p * self.usd_krw_rate):,}원)" if is_usd else ""
            krw_buy_str = f" (약 {int(calc_buy_price * self.usd_krw_rate):,}원)" if is_usd else ""
            krw_sell_str = f" (약 {int(calc_sell_price * self.usd_krw_rate):,}원)" if is_usd else ""

            # 추천 리스트 집계
            if "오늘 단기 매수" in short_signal:
                today_buy_list.append({
                    "name": stock["name"],
                    "ticker": ticker,
                    "cur_price": self._format_price(cur_p, is_usd) + krw_cur_str,
                    "buy_price": str_buy_price + krw_buy_str,
                    "sell_price": str_sell_price + krw_sell_str,
                    "stop_loss": str_stop_loss,
                    "expected_yield": f"+{expected_yield:.1f}%",
                    "type": short_signal,
                    "reason": short_reason,
                })
            elif "쿨다운" in short_signal:
                pass  # 쿨다운 중인 종목은 오늘 신규 단기 매수 리스트에서 제외하여 도배 방지
            elif "매도" in short_signal or "과열" in short_signal:
                sell_warning_list.append({
                    "name": stock["name"],
                    "ticker": ticker,
                    "cur_price": self._format_price(cur_p, is_usd) + krw_cur_str,
                    "sell_price": str_sell_price + krw_sell_str,
                    "type": "단기 과열 익절",
                    "disparity": f"{disp:+.1f}%",
                    "reason": short_reason,
                })

            if "장기 적립/매수" in long_signal:
                longterm_buy_list.append({
                    "name": stock["name"],
                    "ticker": ticker,
                    "cur_price": self._format_price(cur_p, is_usd) + krw_cur_str,
                    "buy_price": str_buy_price + krw_buy_str,
                    "sell_price": str_sell_price + krw_sell_str,
                    "stop_loss": str_stop_loss,
                    "expected_yield": f"+{expected_yield:.1f}%",
                    "type": long_signal,
                    "reason": long_reason,
                })
            elif "비중 축소" in long_signal:
                sell_warning_list.append({
                    "name": stock["name"],
                    "ticker": ticker,
                    "cur_price": self._format_price(cur_p, is_usd) + krw_cur_str,
                    "sell_price": str_sell_price + krw_sell_str,
                    "type": "장기 추세 하락",
                    "disparity": f"{disp:+.1f}%",
                    "reason": long_reason,
                })

            # 뉴스 모멘텀
            news_summary = "최근 특이 뉴스 없음"
            if news_meta["matched_news"]:
                top_news = news_meta["matched_news"][0]
                news_summary = f"{top_news['title']} ({top_news['source']})"

            item_dict = {
                "종목명": stock["name"],
                "티커": ticker,
                "섹터": stock["sector"],
                "현재가": self._format_price(cur_p, is_usd) + krw_cur_str,
                "전일대비": f"{tech['diff']:+,}{tech['currency']} ({tech['diff_ratio']:+.2f}%)",
                "매수_추천금액": str_buy_price + krw_buy_str,
                "목표_매도금액": str_sell_price + krw_sell_str,
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
                "is_us": is_usd,
            }
            all_evaluations.append(item_dict)

        # 미국 빅테크 4대장 별도 선별
        us_bigtech_list = [e for e in all_evaluations if e.get("is_us")]

        return {
            "all_evaluations": all_evaluations,
            "today_buy_picks": today_buy_list,
            "longterm_buy_picks": longterm_buy_list,
            "sell_warning_picks": sell_warning_list,
            "us_bigtech_picks": us_bigtech_list,
            "cooldown_map": cooldown_map,
        }

