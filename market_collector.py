"""
market_collector.py
주식, 환율 지표 및 기업 발표/주가전망 특화 데이터 수집기
"""

import datetime
import re
import requests
import feedparser
from crawler_config import FINANCE_FEEDS, REQUEST_HEADERS


class MarketCollector:
    def __init__(self, history_mgr=None):
        self.history_mgr = history_mgr

    def get_exchange_rates(self) -> list:
        """주요 국가 실시간 환율 수집"""
        results = []
        try:
            r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=8)
            if r.status_code == 200:
                rates = r.json().get("rates", {})
                krw = rates.get("KRW", 0)
                results.append({"통화명": "미국 달러 (USD)", "환율(원)": f"{krw:,.2f}", "변동/기준": "매매기준율"})
                if "JPY" in rates and rates["JPY"] > 0:
                    jpy_100 = (krw / rates["JPY"]) * 100
                    results.append({"통화명": "일본 100엔 (JPY)", "환율(원)": f"{jpy_100:,.2f}", "변동/기준": "100엔 기준"})
                if "EUR" in rates and rates["EUR"] > 0:
                    eur = krw / rates["EUR"]
                    results.append({"통화명": "유로 (EUR)", "환율(원)": f"{eur:,.2f}", "변동/기준": "매매기준율"})
                if "CNY" in rates and rates["CNY"] > 0:
                    cny = krw / rates["CNY"]
                    results.append({"통화명": "중국 위안 (CNY)", "환율(원)": f"{cny:,.2f}", "변동/기준": "매매기준율"})
        except Exception as e:
            print(f"[경고] 환율 수집 오류: {e}")
        return results

    def get_stock_indices(self) -> list:
        """코스피, 코스닥 지수 수집"""
        results = []
        symbols = [("^KS11", "코스피 (KOSPI)"), ("^KQ11", "코스닥 (KOSDAQ)")]
        for sym, name in symbols:
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d"
                r = requests.get(url, headers=REQUEST_HEADERS, timeout=8)
                if r.status_code == 200:
                    meta = r.json()["chart"]["result"][0]["meta"]
                    price = meta.get("regularMarketPrice", 0)
                    prev = meta.get("chartPreviousClose", price)
                    diff = price - prev
                    ratio = (diff / prev * 100) if prev else 0
                    sign = "+" if diff > 0 else ""
                    results.append({
                        "지수명": name,
                        "현재지수": f"{price:,.2f}",
                        "전일대비": f"{sign}{diff:,.2f} ({sign}{ratio:.2f}%)",
                    })
            except Exception as e:
                print(f"[경고] {name} 지수 수집 오류: {e}")
        return results

    def get_stock_news(self, limit_per_topic=10) -> list:
        """기업 발표, 경제동향, 주가변화 예측 관련 뉴스 수집"""
        articles = []
        collected_links = set()

        # 주요 대기업 및 기관 키워드 패턴
        target_entities = [
            "삼성전자", "SK하이닉스", "LG에너지솔루션", "현대차", "기아", "카카오", "네이버",
            "삼성바이오", "셀트리온", "한화", "포스코", "한국은행", "연준", "금감원", "IMF"
        ]

        for topic, urls in FINANCE_FEEDS.items():
            for url in urls:
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:limit_per_topic]:
                        link = entry.get("link", "")
                        title = entry.get("title", "").strip()

                        if not title or link in collected_links:
                            continue

                        # 중복 및 연결 이슈 필터링
                        status = "new"
                        if self.history_mgr:
                            check_res, prev_title = self.history_mgr.check_status(title, link)
                            if check_res == "duplicate":
                                continue
                            status = "연결 이슈(후속)" if check_res == "follow_up" else "신규"

                        # 제목에서 언론사 분리 (Google News 포맷: "제목 - 언론사")
                        source = ""
                        clean_title = title
                        if " - " in title:
                            parts = title.rsplit(" - ", 1)
                            clean_title = parts[0]
                            source = parts[1]

                        # 관련 기업/기관 탐지
                        related_entity = "경제 전반"
                        for ent in target_entities:
                            if ent in clean_title:
                                related_entity = ent
                                break

                        # 주가 및 시장 영향 키워드 분석
                        impact = "시장 동향 관망"
                        if any(w in clean_title for w in ["상승", "급등", "호조", "최고", "목표가 상향", "매수"]):
                            impact = "🟢 긍정적 / 상승 전망"
                        elif any(w in clean_title for w in ["하락", "급락", "부진", "우려", "사이드카", "목표가 하향", "매도"]):
                            impact = "🔴 부정적 / 변동성 주의"
                        elif any(w in clean_title for w in ["공개", "발표", "출시", "도입", "협약", "인수"]):
                            impact = "🔵 신규 발표 / 모멘텀 형성"

                        collected_links.add(link)
                        articles.append({
                            "구분": topic,
                            "상태": status,
                            "관련기업/기관": related_entity,
                            "기사제목": clean_title,
                            "영향/전망": impact,
                            "언론사": source,
                            "링크": link,
                            "발행시각": entry.get("published", datetime.datetime.now().strftime("%Y-%m-%d")),
                        })
                except Exception as e:
                    print(f"[경고] {topic} 피드 수집 오류 ({url}): {e}")

        return articles
