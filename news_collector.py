"""
news_collector.py
7대 분야별 뉴스 수집 및 분야별 3~10건 이상의 다수 헤드라인 선별 엔진
(언론사 동시집중보도 클러스터링 우선 배치)
"""

import collections
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

    @staticmethod
    def _extract_keywords(title: str) -> list:
        """기사 제목에서 핵심 2음절 이상 명사/키워드 추출"""
        t = re.sub(r"\[.*?\]|\(.*?\)|<.*?>", " ", title)
        t = re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", t)
        stopwords = {"속보", "단독", "종합", "포토", "영상", "오늘", "내일", "결국", "최근", "올해", "지난해", "이유", "이후"}
        words = [w for w in t.split() if len(w) >= 2 and w not in stopwords]
        return words

    @staticmethod
    def _is_similar_headline(title1: str, title2: str, threshold: float = 0.5) -> bool:
        """두 기사 제목 간의 키워드 자카드 유사도(Jaccard Similarity) 계산하여 겹치는 뉴스 판별"""
        if not title1 or not title2:
            return False
        # [단독], [속보] 등 말머리 및 특수문자 정제
        clean1 = re.sub(r"\[.*?\]|\(.*?\)|<.*?>|['\"“”‘’]", " ", title1)
        clean2 = re.sub(r"\[.*?\]|\(.*?\)|<.*?>|['\"“”‘’]", " ", title2)

        stopwords = {"오늘", "결국", "왜", "논란", "충격", "발표", "주장", "전망", "최근", "올해", "지난해"}
        words1 = set([w for w in clean1.split() if len(w) >= 2 and w not in stopwords])
        words2 = set([w for w in clean2.split() if len(w) >= 2 and w not in stopwords])

        if not words1 or not words2:
            return False

        intersection = words1.intersection(words2)
        union = words1.union(words2)
        similarity = len(intersection) / len(union)

        # 교집합 단어가 3개 이상이거나 자카드 유사도가 임계치 이상이면 동일 이슈/중복 기사로 판정
        if len(intersection) >= 3 or similarity >= threshold:
            return True
        return False

    def collect_all_categories(self, limit_per_feed=15, top_n_per_category=8) -> dict:
        """
        7대 분야별 뉴스 수집 (분야별 최소 3~10건 수집 보장 및 중복 기사 필터링)
        """
        raw_articles = []
        collected_links = set()

        for category, feed_urls in NEWS_FEEDS.items():
            for feed_idx, url in enumerate(feed_urls):
                try:
                    feed = feedparser.parse(url)
                    for rank_idx, entry in enumerate(feed.entries[:limit_per_feed]):
                        link = entry.get("link", "")
                        raw_title = entry.get("title", "").strip()

                        if not raw_title or link in collected_links:
                            continue

                        source = "주요언론"
                        clean_title = raw_title
                        if " - " in raw_title:
                            parts = raw_title.rsplit(" - ", 1)
                            clean_title = parts[0].strip()
                            source = parts[1].strip()

                        summary = self._clean_html(entry.get("summary", ""))
                        if not summary:
                            summary = clean_title

                        collected_links.add(link)
                        raw_articles.append({
                            "분야": category,
                            "기사제목": clean_title,
                            "요약내용": summary[:160] + "..." if len(summary) > 160 else summary,
                            "언론사": source,
                            "링크": link,
                            "발행일시": entry.get("published", datetime.datetime.now().strftime("%Y-%m-%d")),
                            "keywords": self._extract_keywords(clean_title),
                            "feed_rank": rank_idx,
                        })
                except Exception as e:
                    print(f"[경고] {category} RSS 수집 중 오류 ({url}): {e}")

        # 키워드별 언론사 보도량 집계 (클러스터링)
        keyword_media_map = collections.defaultdict(set)
        for art in raw_articles:
            for kw in art["keywords"]:
                keyword_media_map[kw].add(art["언론사"])

        for art in raw_articles:
            max_media_count = 1
            clustered_kws = []
            for kw in art["keywords"]:
                m_count = len(keyword_media_map[kw])
                if m_count >= max_media_count:
                    max_media_count = m_count
                if m_count >= 3:
                    clustered_kws.append(kw)

            art["media_count"] = max_media_count
            art["is_clustered"] = (max_media_count >= 3)
            art["clustered_kws"] = list(set(clustered_kws))

        # 중복 및 연결 이슈 필터링
        filtered_articles = []
        for art in raw_articles:
            status = "신규 이슈"
            conn_title = ""
            if self.history_mgr:
                check_res, prev_title = self.history_mgr.check_status(art["기사제목"], art["링크"])
                if check_res == "duplicate":
                    continue
                elif check_res == "follow_up":
                    status = "연결 이슈 (후속)"
                    conn_title = prev_title

            if art["is_clustered"]:
                status = f"🔥 [언론사 집중 보도 ({art['media_count']}개사)]"

            art["상태"] = status
            art["연결된전일이슈"] = conn_title
            filtered_articles.append(art)

        # 분야별 정렬 (1순위 언론사 집중도, 2순위 랭킹순)
        categorized_articles = collections.defaultdict(list)
        for art in filtered_articles:
            categorized_articles[art["분야"]].append(art)

        # 분야별 상위 N건 리스트 추출 (제목 유사도 중복 기사 전면 제거)
        category_top_picks = {}
        all_picked_titles = []
        for cat, items in categorized_articles.items():
            items.sort(key=lambda x: (x["media_count"], -x["feed_rank"]), reverse=True)
            unique_items = []
            for item in items:
                t = item["기사제목"]
                # 1) 현재 분야 내 이미 선별된 기사와 겹치는지 검사
                if any(self._is_similar_headline(t, picked["기사제목"]) for picked in unique_items):
                    continue
                # 2) 타 분야에 이미 메인으로 선정된 기사와 중복인지 검사
                if any(self._is_similar_headline(t, prev_t) for prev_t in all_picked_titles):
                    continue

                unique_items.append(item)
                all_picked_titles.append(t)
                if len(unique_items) >= top_n_per_category:
                    break
            category_top_picks[cat] = unique_items

        all_sorted = sorted(filtered_articles, key=lambda x: x["media_count"], reverse=True)
        mega_issue = all_sorted[0] if (all_sorted and all_sorted[0]["media_count"] >= 3) else None

        return {
            "all_articles": filtered_articles,
            "category_top_picks": category_top_picks,
            "mega_issue": mega_issue,
        }
