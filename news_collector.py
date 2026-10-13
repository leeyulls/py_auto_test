"""
news_collector.py
분야별(사건사고, 사회, 경제, 세계, 연예, 신상품/IT) 종합 이슈 수집기
"""

import datetime
import html
import re
import feedparser
from crawler_config import NEWS_FEEDS


class NewsCollector:
    def __init__(self, history_mgr=None):
        self.history_mgr = history_mgr

    @staticmethod
    def _clean_html(text: str) -> str:
        """HTML 태그 및 특수문자 엔티티 정리"""
        if not text:
            return ""
        clean = re.sub(r"<.*?>", "", text)
        return html.unescape(clean).strip()

    def collect_all_categories(self, limit_per_feed=8) -> list:
        """모든 분야별 뉴스 기사 수집 및 중복 필터링"""
        all_articles = []
        collected_links = set()

        for category, feed_urls in NEWS_FEEDS.items():
            for url in feed_urls:
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:limit_per_feed]:
                        link = entry.get("link", "")
                        raw_title = entry.get("title", "").strip()

                        if not raw_title or link in collected_links:
                            continue

                        # 중복 여부 및 연결 이슈 판별
                        status = "신규 이슈"
                        prev_connected_title = ""
                        if self.history_mgr:
                            check_res, conn_title = self.history_mgr.check_status(raw_title, link)
                            if check_res == "duplicate":
                                continue
                            elif check_res == "follow_up":
                                status = "연결 이슈 (후속 보도)"
                                prev_connected_title = conn_title

                        # 언론사 분리 (Google News 형식 "제목 - 언론사")
                        source = ""
                        clean_title = raw_title
                        if " - " in raw_title:
                            parts = raw_title.rsplit(" - ", 1)
                            clean_title = parts[0]
                            source = parts[1]

                        # 요약 내용 추출
                        summary = self._clean_html(entry.get("summary", ""))
                        if not summary:
                            summary = clean_title

                        collected_links.add(link)
                        all_articles.append({
                            "분야": category,
                            "상태": status,
                            "기사제목": clean_title,
                            "요약내용": summary[:180] + "..." if len(summary) > 180 else summary,
                            "언론사": source,
                            "링크": link,
                            "연결된전일이슈": prev_connected_title,
                            "발행일시": entry.get("published", datetime.datetime.now().strftime("%Y-%m-%d")),
                        })
                except Exception as e:
                    print(f"[경고] {category} RSS 수집 중 오류 발생 ({url}): {e}")

        return all_articles
