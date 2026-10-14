"""
market_collector.py
주식, 환율 지표 및 네이버 증권 리서치 리포트 & 기업 발표/주가전망 특화 데이터 수집기
"""

import datetime
import requests
import feedparser
from crawler_config import FINANCE_FEEDS, NAVER_RESEARCH_API, REQUEST_HEADERS


class MarketCollector:
    def __init__(self, history_mgr=None):
        self.history_mgr = history_mgr

    def get_exchange_rates(self) -> list:
        """주요 국가 실시간 환율 및 전일대비 변동 수집 (야후 파이낸스 우선, 백업 er-api)"""
        results = []
        fx_symbols = [
            ("USDKRW=X", "미국 달러 (USD)", 1.0),
            ("JPYKRW=X", "일본 100엔 (JPY)", 100.0),
            ("EURKRW=X", "유로 (EUR)", 1.0),
            ("CNYKRW=X", "중국 위안 (CNY)", 1.0),
        ]
        
        # 1. 야후 파이낸스를 통한 실시간 전일대비 변동폭 산출
        for sym, name, multiplier in fx_symbols:
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d"
                r = requests.get(url, headers=REQUEST_HEADERS, timeout=6)
                if r.status_code == 200:
                    meta = r.json()["chart"]["result"][0]["meta"]
                    price = meta.get("regularMarketPrice", 0) * multiplier
                    prev = meta.get("chartPreviousClose", price) * multiplier
                    diff = price - prev
                    ratio = (diff / prev * 100) if prev else 0.0
                    sign = "+" if diff > 0 else ""
                    arrow = "▲ " if diff > 0 else ("▼ " if diff < 0 else "- ")
                    diff_str = f"{arrow}{sign}{diff:,.2f}원 ({sign}{ratio:.2f}%)"
                    results.append({
                        "통화명": name,
                        "환율(원)": f"{price:,.2f}",
                        "전일대비": diff_str,
                        "변동/기준": diff_str,
                    })
            except Exception:
                pass

        if results:
            return results

        # 2. 백업 API 폴백
        try:
            r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=8)
            if r.status_code == 200:
                rates = r.json().get("rates", {})
                krw = rates.get("KRW", 0)
                results.append({"통화명": "미국 달러 (USD)", "환율(원)": f"{krw:,.2f}", "전일대비": "기준환율", "변동/기준": "매매기준율"})
                if "JPY" in rates and rates["JPY"] > 0:
                    jpy_100 = (krw / rates["JPY"]) * 100
                    results.append({"통화명": "일본 100엔 (JPY)", "환율(원)": f"{jpy_100:,.2f}", "전일대비": "기준환율", "변동/기준": "100엔 기준"})
                if "EUR" in rates and rates["EUR"] > 0:
                    eur = krw / rates["EUR"]
                    results.append({"통화명": "유로 (EUR)", "환율(원)": f"{eur:,.2f}", "전일대비": "기준환율", "변동/기준": "매매기준율"})
                if "CNY" in rates and rates["CNY"] > 0:
                    cny = krw / rates["CNY"]
                    results.append({"통화명": "중국 위안 (CNY)", "환율(원)": f"{cny:,.2f}", "전일대비": "기준환율", "변동/기준": "매매기준율"})
        except Exception as e:
            print(f"[경고] 환율 수집 오류: {e}")
        return results

    def get_stock_indices(self) -> list:
        """코스피, 코스닥, 나스닥, S&P 500 주요 4대 지수 수집 (국내 지수는 네이버 공식 polling API 우선)"""
        results = []
        
        # 1. 국내 지수 (코스피, 코스닥) 네이버 polling API 우선 조회
        domestic_configs = [
            ("KOSPI", "코스피 (KOSPI)"),
            ("KOSDAQ", "코스닥 (KOSDAQ)")
        ]
        domestic_done = {}
        for code, name in domestic_configs:
            try:
                url = f"https://polling.finance.naver.com/api/realtime/domestic/index/{code}"
                r = requests.get(url, headers=REQUEST_HEADERS, timeout=5)
                if r.status_code == 200:
                    data = r.json().get("datas", [{}])[0]
                    price_str = data.get("closePrice", "")
                    diff_val = float(data.get("compareToPreviousClosePriceRaw", 0.0))
                    ratio_val = float(data.get("fluctuationsRatioRaw", 0.0))
                    sign = "+" if diff_val > 0 else ""
                    arrow = "▲ " if diff_val > 0 else ("▼ " if diff_val < 0 else "- ")
                    results.append({
                        "지수명": name,
                        "현재지수": price_str,
                        "전일대비": f"{arrow}{sign}{diff_val:,.2f} ({sign}{ratio_val:.2f}%)",
                    })
                    domestic_done[code] = True
            except Exception as e:
                print(f"[정보] 네이버 증시 API ({code}) 조회 실패, 야후 파이낸스로 폴백: {e}")

        # 2. 해외 지수 및 폴백 대상 야후 파이낸스 조회
        yahoo_symbols = []
        if "KOSPI" not in domestic_done:
            yahoo_symbols.append(("^KS11", "코스피 (KOSPI)"))
        if "KOSDAQ" not in domestic_done:
            yahoo_symbols.append(("^KQ11", "코스닥 (KOSDAQ)"))
        yahoo_symbols.extend([
            ("^IXIC", "나스닥 (NASDAQ)"),
            ("^GSPC", "S&P 500"),
        ])

        for sym, name in yahoo_symbols:
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
                    arrow = "▲ " if diff > 0 else ("▼ " if diff < 0 else "- ")
                    results.append({
                        "지수명": name,
                        "현재지수": f"{price:,.2f}",
                        "전일대비": f"{arrow}{sign}{diff:,.2f} ({sign}{ratio:.2f}%)",
                    })
            except Exception as e:
                print(f"[경고] {name} 지수 수집 오류: {e}")
        return results

    def get_naver_research_reports(self) -> list:
        """우선순위 3: 네이버 증권 애널리스트 기업 리서치 리포트 직접 수집"""
        reports = []
        try:
            r = requests.get(NAVER_RESEARCH_API, headers=REQUEST_HEADERS, timeout=8)
            if r.status_code == 200:
                items = r.json()
                for item in items[:10]:
                    item_name = item.get("itemName", "")
                    title = item.get("title", "").strip()
                    broker = item.get("brokerName", "증권사")
                    write_date = item.get("writeDate", "")
                    read_count = item.get("readCount", 0)
                    end_url = item.get("endUrl", "")
                    target_price = item.get("targetPrice")
                    opinion = item.get("opinion")

                    summary_parts = []
                    if opinion:
                        summary_parts.append(f"투자의견: {opinion}")
                    if target_price:
                        try:
                            summary_parts.append(f"목표주가: {int(target_price):,}원")
                        except Exception:
                            summary_parts.append(f"목표주가: {target_price}원")
                    if read_count:
                        try:
                            summary_parts.append(f"조회수: {int(read_count):,}회")
                        except Exception:
                            summary_parts.append(f"조회수: {read_count}회")
                    summary_text = " | ".join(summary_parts) if summary_parts else f"{broker} 분석 리포트"

                    reports.append({
                        "구분": "증권사 리서치",
                        "상태": "전문 리포트",
                        "관련기업/기관": item_name,
                        "기사제목": f"[{broker}] {item_name}: {title}",
                        "영향/전망": "📘 애널리스트 리포트",
                        "언론사": broker,
                        "링크": end_url or f"https://m.stock.naver.com/research/company/{item.get('researchId')}",
                        "발행시각": write_date,
                        "요약": summary_text,
                        "조회수": read_count,
                    })
        except Exception as e:
            print(f"[경고] 네이버 증권 리서치 수집 오류: {e}")
        return reports

    def get_stock_news(self, limit_per_topic=10) -> list:
        """기업 발표, 경제동향, 주가변화 예측 관련 뉴스 수집 (네이버 리서치 결합)"""
        articles = []
        collected_links = set()

        # 1. 네이버 증권 리포트 우선 탑재 (우선순위 3)
        research_reports = self.get_naver_research_reports()
        articles.extend(research_reports)
        for r in research_reports:
            collected_links.add(r["링크"])

        target_entities = [
            "삼성전자", "SK하이닉스", "LG에너지솔루션", "현대차", "기아", "카카오", "NAVER",
            "삼성바이오", "셀트리온", "한화", "포스코", "한국은행", "연준", "금감원", "IMF"
        ]

        # 2. 금융/증권 특화 검색 피드 수집
        for topic, urls in FINANCE_FEEDS.items():
            for url in urls:
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:limit_per_topic]:
                        link = entry.get("link", "")
                        title = entry.get("title", "").strip()

                        if not title or link in collected_links:
                            continue

                        status = "new"
                        if self.history_mgr:
                            check_res, prev_title = self.history_mgr.check_status(title, link)
                            if check_res == "duplicate":
                                continue
                            status = "연결 이슈(후속)" if check_res == "follow_up" else "신규"

                        source = ""
                        clean_title = title
                        if " - " in title:
                            parts = title.rsplit(" - ", 1)
                            clean_title = parts[0]
                            source = parts[1]

                        related_entity = "경제 전반"
                        for ent in target_entities:
                            if ent in clean_title:
                                related_entity = ent
                                break

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
                            "요약": clean_title,
                            "조회수": 0,
                        })
                except Exception as e:
                    print(f"[경고] {topic} 피드 수집 오류 ({url}): {e}")

        return articles
