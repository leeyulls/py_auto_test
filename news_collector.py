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

    COMMON_STOPWORDS = {
        "속보", "단독", "종합", "포토", "영상", "오늘", "내일", "결국", "최근", "올해", "지난해",
        "이유", "이후", "왜", "논란", "충격", "발표", "주장", "전망", "시장", "정부", "국내",
        "기업", "글로벌", "대표", "개최", "특강", "사진", "게시판", "행사", "인사", "부고", "동정",
        "관련", "대해", "통해", "위해", "이번", "다시", "주요", "진행", "예정"
    }

    @staticmethod
    def _clean_html(text: str) -> str:
        """HTML 태그 및 특수문자 엔티티 정리"""
        if not text:
            return ""
        clean = re.sub(r"<.*?>", "", text)
        return html.unescape(clean).strip()

    @classmethod
    def _extract_keywords(cls, title: str) -> list:
        """기사 제목에서 핵심 2음절 이상 명사/키워드 추출"""
        t = re.sub(r"\[.*?\]|\(.*?\)|<.*?>", " ", title)
        t = re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", t)
        words = [w for w in t.split() if len(w) >= 2 and w not in cls.COMMON_STOPWORDS]
        return words

    @classmethod
    def _extract_distinct_entities(cls, title: str) -> list:
        """기사 제목에서 인물명(3음절), 특정 기업/핵심 고유명사 엔티티 추출"""
        clean = re.sub(r"\[.*?\]|\(.*?\)|<.*?>|['\"“”‘’]", " ", title)
        tokens = [w for w in re.split(r"[\s,·…]+", clean) if len(w) >= 2 and w not in cls.COMMON_STOPWORDS]
        entities = []
        for tok in tokens:
            # 3글자 한국인 인명 패턴 (예: 김지용, 이재명, 윤석열, 한동훈, 최태원, 정의선 등)
            if re.fullmatch(r"[가-힣]{3}", tok) and tok not in ["대통령", "국정원", "검찰청", "금리인", "반도체", "현대차", "위원장", "총괄장", "사무관"]:
                entities.append(tok)
            # 4글자 이상의 명확한 고유명사 (예: 포스코홀딩스, 오픈AI 등)
            elif len(tok) >= 4:
                entities.append(tok)
        return list(set(entities))

    EXCLUDE_TITLE_TERMS = {
        "운세", "띠별", "별자리", "로또", "복권", "부고", "인사", "동정", "TV편성", "편성표",
        "날씨", "미세먼지", "포토뉴스", "화보", "출국", "입국", "카드뉴스", "한컷"
    }

    TRUNCATED_ENDINGS = {"다음", "보", "있", "했", "됐", "될", "할", "등", "및", "관", "위", "알", "못", "않", "이", "그"}

    @classmethod
    def _clean_informative_summary(cls, raw_summary: str, title: str) -> str:
        """기사 요약에서 언론사/기자/특수문자 및 '...' 말줄임표 잡음을 완벽히 제거하고 완결된 2~3개 완성 문장 생성"""
        clean_title = re.sub(r"\[.*?\]|\(.*?\)|<.*?>", "", title).strip()
        clean_title = re.sub(r"['\"“”‘’]", "", clean_title)

        if not raw_summary:
            return f"{clean_title} 소식이 전해진 가운데, 관련 당사자들의 공식 입장과 향후 대응 방향 및 일정에 대한 심층 보도가 이어지고 있습니다."

        # 1. Google News RSS의 <ol><li> 클러스터 기사 목록 구조 정밀 파싱
        if "<li" in raw_summary or "<ol" in raw_summary or "<font" in raw_summary:
            items = []
            li_matches = re.findall(r'<li[^>]*>(.*?)</li>', raw_summary, re.DOTALL)
            if not li_matches:
                li_matches = [raw_summary]

            for block in li_matches:
                a_match = re.search(r'<a[^>]*>(.*?)</a>', block, re.DOTALL)
                font_match = re.search(r'<font[^>]*>(.*?)</font>', block, re.DOTALL)
                if a_match:
                    h_text = cls._clean_html(a_match.group(1)).strip()
                    m_text = cls._clean_html(font_match.group(1)).strip() if font_match else ""
                    h_text = re.sub(r"\[.*?\]|\(.*?\)", "", h_text).strip()
                    h_text = re.sub(r"\s*-\s*(카드/한컷|멀티미디어|카드뉴스|포토뉴스).*$", "", h_text).strip()
                    h_text = re.sub(r"\.{2,}|…+", "", h_text).strip()
                    if len(h_text) >= 15 and not any(ex in h_text for ex in cls.EXCLUDE_TITLE_TERMS):
                        items.append((h_text, m_text))

            if items:
                first_h, first_m = items[0]
                if not first_h.endswith(('.', '!', '?')):
                    first_h += '.'

                if len(items) > 1:
                    second_h, second_m = items[1]
                    if not second_h.endswith(('.', '!', '?')):
                        second_h += '.'
                    if not cls._is_similar_headline(first_h, second_h, threshold=0.5) and not cls._is_similar_headline(clean_title, second_h, threshold=0.5):
                        return f"{first_h} 아울러 {second_h}"
                if not cls._is_similar_headline(clean_title, first_h, threshold=0.6):
                    return f"{clean_title} 관련 보도입니다. {first_h}"
                return first_h

        # 2. 일반 텍스트 요약문(연합뉴스, 매일경제 등) 정제
        text = cls._clean_html(raw_summary)
        text = re.sub(r"^[▲■◆●▶\s=]+", "", text)
        text = re.sub(r"^.*?=\s*", "", text)
        text = re.sub(r"\[.*?\]|\(.*?\)", " ", text)
        text = re.sub(r"^[가-힣a-zA-Z\s]+기자\s*=\s*", "", text)
        text = re.sub(r"[가-힣a-zA-Z\s]+기자\s*", "", text)
        text = re.sub(r"\b(서울|세종|부산|뉴욕|워싱턴|도쿄|베이징)=뉴스[1원]|뉴시스|연합뉴스|이데일리|머니투데이|헤럴드경제|한국경제|매일경제|조선일보|중앙일보|동아일보\b", "", text)
        text = re.sub(r"무단전재.*", "", text)
        text = re.sub(r"\s*-\s*(카드/한컷|멀티미디어|카드뉴스|포토뉴스).*$", "", text)
        text = re.sub(r"\.{2,}|…+", "", text)
        text = re.sub(r"\s+", " ", text).strip()

        # 문장 분리 및 말줄임/불완전 끝단 정제
        raw_sentences = re.split(r'(?<=[.!?다함음])\s+', text)
        good_sentences = []
        for s in raw_sentences:
            s_clean = s.strip()
            if len(s_clean) >= 20 and not any(junk in s_clean for junk in ["기자", "포토", "무단", "저작권", "사진="]):
                words = s_clean.split()
                if words:
                    last_w = re.sub(r"[.!?]+$", "", words[-1])
                    if last_w in cls.TRUNCATED_ENDINGS or len(last_w) == 1:
                        words = words[:-1]
                        s_clean = " ".join(words)
                if s_clean and not s_clean.endswith(('.', '!', '?')):
                    s_clean += '.'
                if len(s_clean) >= 20:
                    good_sentences.append(s_clean)

        if good_sentences:
            combined = " ".join(good_sentences[:4])
            if len(combined) >= 30:
                return combined

        if len(text) >= 35:
            cleaned_text = re.sub(r'[\s.,·…]+$', '', text)
            if not cleaned_text.endswith(('.', '!', '?')):
                cleaned_text += '.'
            return cleaned_text

        return f"{clean_title} 소식이 전해진 가운데, 관련 당사자들의 공식 입장과 향후 대응 방향 및 일정에 대한 심층 보도가 이어지고 있습니다."

    @classmethod
    def _is_similar_headline(cls, title1: str, title2: str, threshold: float = 0.4) -> bool:
        """두 기사 제목 간의 키워드 및 고유명사(엔티티) 공유 여부 판별"""
        if not title1 or not title2:
            return False

        # 1. 특정 인명/핵심 엔티티(예: 김지용)가 둘 다 포함되어 있으면 동일 이슈로 판정
        ent1 = set(cls._extract_distinct_entities(title1))
        ent2 = set(cls._extract_distinct_entities(title2))
        if ent1 and ent2 and ent1.intersection(ent2):
            return True

        # 2. 키워드 자카드 유사도 검사
        clean1 = re.sub(r"\[.*?\]|\(.*?\)|<.*?>|['\"“”‘’]", " ", title1)
        clean2 = re.sub(r"\[.*?\]|\(.*?\)|<.*?>|['\"“”‘’]", " ", title2)

        words1 = set([w for w in clean1.split() if len(w) >= 2 and w not in cls.COMMON_STOPWORDS])
        words2 = set([w for w in clean2.split() if len(w) >= 2 and w not in cls.COMMON_STOPWORDS])

        if not words1 or not words2:
            return False

        intersection = words1.intersection(words2)
        union = words1.union(words2)
        similarity = len(intersection) / len(union)

        # 2개 이상 중요 단어가 겹치거나 자카드 유사도 충족 시 중복
        if len(intersection) >= 2 or similarity >= threshold:
            return True
        return False

    def collect_all_categories(self, limit_per_feed=20, top_n_per_category=15) -> dict:
        """
        7대 분야별 뉴스 수집 (Global Entity Cap 및 뉴스 임팩트 스코어링 적용)
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

                        if any(term in raw_title for term in self.EXCLUDE_TITLE_TERMS):
                            continue

                        source = "주요언론"
                        clean_title = raw_title
                        if " - " in raw_title:
                            parts = raw_title.rsplit(" - ", 1)
                            clean_title = parts[0].strip()
                            source = parts[1].strip()

                        summary = self._clean_informative_summary(entry.get("summary", ""), clean_title)

                        collected_links.add(link)
                        raw_articles.append({
                            "분야": category,
                            "기사제목": clean_title,
                            "요약내용": summary,
                            "언론사": source,
                            "링크": link,
                            "발행일시": entry.get("published", datetime.datetime.now().strftime("%Y-%m-%d")),
                            "keywords": self._extract_keywords(clean_title),
                            "entities": self._extract_distinct_entities(clean_title),
                            "feed_rank": rank_idx,
                        })
                except Exception as e:
                    print(f"[경고] {category} RSS 수집 중 오류 ({url}): {e}")

        # 키워드별 언론사 보도량 집계 (클러스터링)
        keyword_media_map = collections.defaultdict(set)
        for art in raw_articles:
            for kw in art["keywords"]:
                keyword_media_map[kw].add(art["언론사"])

        # 뉴스 임팩트 스코어링 (Impact Scoring Model)
        major_media = {"한국경제", "매일경제", "연합뉴스", "조선일보", "중앙일보", "동아일보", "KBS", "SBS", "MBC", "YTN", "JTBC", "서울경제"}
        hard_news_terms = {"금리", "관세", "환율", "수출", "물가", "실적", "영업이익", "M&A", "인수", "공급계약", "수주", "제재", "법안", "정책", "규제", "긴급"}
        gossip_terms = {"포토", "인터뷰", "결혼", "이혼", "열애", "부고", "인사", "동정", "화보", "출국", "입국", "패션"}

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

            # 임팩트 스코어 계산
            score = max_media_count * 10
            if any(term in art["기사제목"] for term in hard_news_terms):
                score += 30
            if any(media in art["언론사"] for media in major_media):
                score += 15
            if any(term in art["기사제목"] for term in gossip_terms):
                score -= 40
            art["impact_score"] = score

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

        # 분야별 정렬 (임팩트 스코어 ➔ 언론사 집중도 ➔ 피드 순위)
        categorized_articles = collections.defaultdict(list)
        for art in filtered_articles:
            categorized_articles[art["분야"]].append(art)

        # 분야별 상위 N건 리스트 추출 (Global Entity Cap & 유사도 중복 전면 제거)
        category_top_picks = {}
        all_picked_titles = []
        global_entity_counts = collections.defaultdict(int)

        for cat, items in categorized_articles.items():
            items.sort(key=lambda x: (x["impact_score"], x["media_count"], -x["feed_rank"]), reverse=True)
            unique_items = []
            for item in items:
                t = item["기사제목"]
                ents = item.get("entities", [])

                # 1) Global Entity Cap: 특정 인물/엔티티가 전체 브리핑에서 이미 노출된 경우 배제 (최대 1건)
                if any(global_entity_counts[e] >= 1 for e in ents):
                    continue

                # 2) 현재 분야 내 이미 선별된 기사와 유사도 검사
                if any(self._is_similar_headline(t, picked["기사제목"]) for picked in unique_items):
                    continue

                # 3) 타 분야에 이미 메인으로 선정된 기사와 중복 여부 검사
                if any(self._is_similar_headline(t, prev_t) for prev_t in all_picked_titles):
                    continue

                unique_items.append(item)
                all_picked_titles.append(t)
                for e in ents:
                    global_entity_counts[e] += 1

                if len(unique_items) >= top_n_per_category:
                    break

            # 최소 3건 확보 보장 폴백 (엄격한 엔티티 캡 등으로 누락 방지)
            if len(unique_items) < 3 and items:
                for item in items:
                    if item not in unique_items:
                        unique_items.append(item)
                        if len(unique_items) >= 3:
                            break

            category_top_picks[cat] = unique_items

        all_sorted = sorted(filtered_articles, key=lambda x: (x["impact_score"], x["media_count"]), reverse=True)
        mega_issue = all_sorted[0] if (all_sorted and all_sorted[0]["media_count"] >= 3) else None

        return {
            "all_articles": filtered_articles,
            "category_top_picks": category_top_picks,
            "mega_issue": mega_issue,
        }
