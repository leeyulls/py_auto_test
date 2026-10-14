"""
disclosure_collector.py
금융감독원 전자공시(DART / KIND 상장공시시스템) '특수 공시' 실시간 연동 수집기
- 대주주/임원 장내매수 (책임경영 및 저평가 신호)
- 자사주 취득/소각 (주주환원 및 주가 부양 신호)
- 대규모 단일판매·공급계약 체결 (실적 퀀텀점프 호재)
- 무상증자 및 주식배당 (유통주식수 확대 및 친주주 정책)
"""

import datetime
import html
import re
import feedparser
from urllib.parse import quote


class DisclosureCollector:
    def __init__(self, history_mgr=None):
        self.history_mgr = history_mgr
        self.feeds = [
            "https://news.google.com/rss/search?q=" + quote("공시 (장내매수 OR 자사주 OR 무상증자 OR 단일판매 OR 공급계약)") + "&hl=ko&gl=KR&ceid=KR:ko",
            "https://news.google.com/rss/search?q=" + quote('"금융감독원" OR "전자공시" (장내매수 OR "자사주 소각" OR 공급계약 OR 무상증자)') + "&hl=ko&gl=KR&ceid=KR:ko",
        ]

    @staticmethod
    def _clean_text(raw_html: str) -> str:
        """HTML 태그 및 특수문자 정제"""
        if not raw_html:
            return ""
        text = re.sub(r"<[^>]+>", " ", raw_html)
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    def classify_disclosure(self, title: str, summary: str) -> dict:
        """공시 제목 및 내용을 분석하여 4대 특수 공시 유형 및 투자 시사점 도출"""
        combined = f"{title} {summary}"

        # 1. 자사주 취득 / 소각
        if any(w in combined for w in ["자사주 소각", "자기주식 소각"]):
            return {
                "category": "💎 자사주 소각 (주주환원 극대화)",
                "impact": "발행주식 총수 감소로 주당순이익(EPS) 및 주주가치 대폭 상승",
                "badge": "자사주 소각",
                "action_badge": "💎 중장기 비중확대",
                "strategy": "주식수가 영구 소멸되는 가장 강력한 호재입니다. 단기 차익 매물 소화 후 전고점 돌파 시 중장기 비중 확대 전략이 유리합니다.",
                "score": 95,
            }
        elif any(w in combined for w in ["자사주 취득", "자기주식 취득", "자사주 매입", "자기주식 매수"]):
            return {
                "category": "💎 자사주 취득 (주가 부양)",
                "impact": "기업 자금 투입으로 유통 물량 흡수 및 강력한 주가 바닥 지지 신호",
                "badge": "자사주 취득",
                "action_badge": "🟢 눌림목 분할매수",
                "strategy": "공시 직후 당일 장초반 갭상승 추격매수는 피하고, 3~6개월간 회사의 실제 매수 창구 유입을 확인하며 20일 이동평균선 지지 시 분할 매수로 접근하십시오.",
                "score": 90,
            }

        # 2. 대주주 / 임원 장내매수
        elif any(w in combined for w in ["장내매수", "장내 매수", "지분 취득", "최대주주 매수", "대표이사 매수"]):
            return {
                "category": "🏛️ 대주주/임원 장내매수 (책임경영)",
                "impact": "내부 사정을 가장 잘 아는 경영진의 직접 매수로 기업가치 저평가 방증",
                "badge": "내부자 매수",
                "action_badge": "🛡️ 바닥 지지선 매수",
                "strategy": "경영진 매수 단가는 강력한 심리적 '바닥 지지선' 역할을 합니다. 주가가 해당 매수가 부근까지 밀릴 때 안전마진을 확보한 분할 매수 타점으로 활용하십시오.",
                "score": 88,
            }

        # 3. 대규모 수주 / 공급계약
        elif any(w in combined for w in ["공급계약", "단일판매", "수주", "계약체결"]):
            return {
                "category": "📈 대규모 단일판매·공급계약",
                "impact": "매출액 직결 확정 계약으로 향후 분기 실적 퀀텀점프 기대",
                "badge": "대규모 수주",
                "action_badge": "⚡ 급등 시 단기익절 / 조정 시 재진입",
                "strategy": "계약 총액이 최근 매출액의 10% 이상인지 확인하십시오. 공시 당일 5~10% 이상 급등 시 1차 단기 익절하고, 이후 잔여 수주잔고와 실적 반영 분기를 체크하며 눌림목 재진입을 권고합니다.",
                "score": 85,
            }

        # 4. 무상증자 / 주식배당
        elif any(w in combined for w in ["무상증자", "신주배정", "주식배당"]):
            return {
                "category": "🎁 무상증자 / 주식배당",
                "impact": "주주 보상 정책 및 유통 주식 활성화로 시장 유동성 증대",
                "badge": "무상증자",
                "action_badge": "🎯 권리락 전 분할매도",
                "strategy": "권리락 발생일까지는 단기 변동성 확대를 활용한 트레이딩이 유효하나, 권리락 이후 신주 상장일 전후 물량 출회 리스크가 있으므로 권리락 전 분할 매도로 수익을 확정하는 것이 안전합니다.",
                "score": 82,
            }

        return None

    def collect_special_disclosures(self, limit: int = 10) -> list:
        """4대 특수 공시 데이터 수집 및 정제"""
        collected = []
        seen_titles = set()

        for feed_url in self.feeds:
            try:
                parsed = feedparser.parse(feed_url)
                for entry in parsed.entries:
                    raw_title = self._clean_text(entry.get("title", ""))
                    raw_summary = self._clean_text(entry.get("summary", ""))
                    link = entry.get("link", "")
                    pub_date = entry.get("published", "")

                    if " - " in raw_title:
                        parts = raw_title.rsplit(" - ", 1)
                        clean_title = parts[0].strip()
                        source = parts[1].strip()
                    else:
                        clean_title = raw_title
                        source = "공시통보"

                    # 제목 중복 제거
                    simp_key = re.sub(r"[\s\W_]+", "", clean_title)[:25]
                    if simp_key in seen_titles:
                        continue
                    seen_titles.add(simp_key)

                    # 특수 공시 판정
                    cls_info = self.classify_disclosure(clean_title, raw_summary)
                    if not cls_info:
                        continue

                    # 종목명 추정 (예: [공시 Pick] 스틱인베스트먼트, 41억원... -> 스틱인베스트먼트)
                    match_corp = re.search(r"([가-힣A-Za-z0-9]+)\s*,\s*\d+", clean_title)
                    if not match_corp:
                        match_corp = re.search(r"\[[^\]]+\]\s*([가-힣A-Za-z0-9]+)", clean_title)
                    corp_name = match_corp.group(1) if match_corp else ""

                    collected.append({
                        "공시구분": cls_info["category"],
                        "공시배지": cls_info["badge"],
                        "액션배지": cls_info.get("action_badge", ""),
                        "관련기업": corp_name,
                        "공시제목": clean_title,
                        "영향전망": cls_info["impact"],
                        "투자전략": cls_info.get("strategy", ""),
                        "언론사": source,
                        "링크": link,
                        "공시일시": pub_date,
                        "score": cls_info["score"],
                    })

                    if len(collected) >= limit * 2:
                        break
            except Exception as e:
                print(f"[경고] 특수 공시 피드 수집 오류 ({feed_url}): {e}")

        # 중요도 높은 순 정렬 후 상위 limit건 반환
        collected.sort(key=lambda x: x["score"], reverse=True)
        return collected[:limit]
