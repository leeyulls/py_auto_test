"""
story_dive_engine.py
유튜브 슈카월드 스타일의 '투 트랙(Two-Track) 딥다이브 스토리텔링 엔진'
1) 🌐 [경제·사회 딥다이브] "아! 이래서 그런 거였어" (역사, 지정학, 제도, 숨은 배경)
2) 🔥 [유행·트렌드·신상품] "요즘 왜 이게 유행할까?" (SNS 화제, 품절 대란, 발단, 소비 심리)
"""

import datetime
import html
import re
import feedparser
from urllib.parse import quote


class StoryDiveEngine:
    def __init__(self, history_mgr=None):
        self.history_mgr = history_mgr
        self.trend_feed_url = (
            "https://news.google.com/rss/search?q="
            + quote("품절대란 OR 오픈런 OR \"유행 열풍\" OR \"신상품 화제\" OR \"소비 트렌드\" OR 팝업스토어")
            + "&hl=ko&gl=KR&ceid=KR:ko"
        )

    @staticmethod
    def _clean_text(raw_html: str) -> str:
        """HTML 태그 및 특수문자 정제"""
        if not raw_html:
            return ""
        text = re.sub(r"<[^>]+>", " ", raw_html)
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    def fetch_trend_candidates(self) -> list:
        """트렌드/유행/신상품 특화 뉴스 후보 수집"""
        candidates = []
        try:
            parsed = feedparser.parse(self.trend_feed_url)
            for entry in parsed.entries[:15]:
                raw_title = self._clean_text(entry.get("title", ""))
                summary = self._clean_text(entry.get("summary", ""))
                link = entry.get("link", "")
                source = "트렌드인사이트"
                if " - " in raw_title:
                    parts = raw_title.rsplit(" - ", 1)
                    clean_title = parts[0].strip()
                    source = parts[1].strip()
                else:
                    clean_title = raw_title

                candidates.append({
                    "title": clean_title,
                    "summary": summary,
                    "link": link,
                    "source": source,
                    "category": "트렌드/유행"
                })
        except Exception as e:
            print(f"[경고] 트렌드 후보 수집 오류: {e}")
        return candidates

    def search_deep_context(self, keyword: str) -> list:
        """키워드에 대한 과거 배경, 비하인드, 타임라인 심층 기사 추가 크롤링"""
        results = []
        if not keyword:
            return results
        query = quote(f'"{keyword}" (배경 OR 이유 OR 시초 OR 언제부터 OR 비하인드 OR 원인 OR 역사)')
        search_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            parsed = feedparser.parse(search_url)
            for entry in parsed.entries[:5]:
                title = self._clean_text(entry.get("title", ""))
                summary = self._clean_text(entry.get("summary", ""))
                link = entry.get("link", "")
                source = "심층취재"
                if " - " in title:
                    title, source = title.rsplit(" - ", 1)
                results.append({
                    "title": title.strip(),
                    "summary": summary.strip(),
                    "link": link,
                    "source": source.strip()
                })
        except Exception as e:
            print(f"[경고] 심층 콘텍스트 검색 오류 ({keyword}): {e}")
        return results

    def extract_core_entity(self, title: str) -> str:
        """기사 제목에서 핵심 키워드/주제명 추출"""
        # 따옴표 내부 단어 우선 추출
        quote_match = re.search(r"['\"]([^'\"]+)['\"]", title)
        if quote_match and len(quote_match.group(1)) >= 2:
            return quote_match.group(1).strip()
        # [말머리] 제거 후 첫 번째 주요 명사구
        clean = re.sub(r"\[[^\]]+\]", "", title).strip()
        words = [w for w in re.split(r"[\s,‥…]+", clean) if len(w) >= 2 and w not in ["오늘", "결국", "왜", "논란", "충격", "발표", "주장"]]
        return words[0] if words else "주요이슈"

    def build_economy_story(self, general_news: list, mega_issue: dict) -> dict:
        """1️⃣ 🌐 [경제·사회 딥다이브] 스토리 생성"""
        # 1. 주제 선정 (메가 핫토픽 또는 거시경제/세계 1위 기사)
        target_item = mega_issue
        if not target_item or not target_item.get("기사제목"):
            econ_candidates = [n for n in general_news if n.get("분야") in ["거시경제/비즈니스", "세계/국제", "정치"]]
            target_item = econ_candidates[0] if econ_candidates else (general_news[0] if general_news else {})

        raw_title = target_item.get("기사제목", "글로벌 경제·산업 재편 이슈")
        raw_summary = target_item.get("요약내용", "주요 정책 및 산업 지형도 변화가 감지되고 있습니다.")
        link = target_item.get("링크") or target_item.get("link", "")
        source = target_item.get("언론사", "주요언론")

        entity = self.extract_core_entity(raw_title)
        deep_contexts = self.search_deep_context(entity)

        # 4단 서사 구축
        hook = f"오늘 언론을 도배한 '{entity}' 뉴스, 겉보기엔 단순한 갈등 같지만 사실은 수년 전부터 시작된 거대한 판의 충돌입니다."
        
        stage1 = f"오늘 언론사들이 일제히 보도한 사건: **[{raw_title}]** 입니다. {raw_summary}"
        
        if deep_contexts:
            ctx_summary = " ".join([c["summary"] for c in deep_contexts[:2]])
            stage2 = f"사실 이 이슈는 오늘 갑자기 터진 게 아닙니다. 과거부터 누적된 타임라인을 살펴보면: {ctx_summary[:200]}..."
        else:
            stage2 = f"사실 이 문제는 과거 수년 전부터 시장과 정책 당국 간에 누적되어 온 해묵은 과제가 특정 계기를 맞아 수면 위로 폭발한 것입니다."

        stage3 = f"언론 헤드라인이 말해주지 않는 진짜 흑막(돈과 권력의 흐름)은 따로 있습니다. 표면적인 명분 뒤에는 이해관계자들의 치열한 득실 계산과 법·제도의 맹점을 파고든 치밀한 수싸움이 숨겨져 있습니다."

        stage4 = f"이 사건은 일회성 해프닝으로 끝나지 않습니다. 앞으로 한국 경제와 관련 산업의 판도를 바꿀 중요한 분수령이 될 것이며, 우리는 이해관계자들의 다음 행보를 면밀히 주시해야 합니다."

        formatted_title = f"🌐 [경제·사회 딥다이브] \"아! 이래서 그런 거였어\": {entity}의 숨겨진 비하인드"

        return {
            "track": "ECONOMY",
            "track_name": "경제·사회 딥다이브",
            "badge": "아! 이래서 그런 거였어",
            "title": formatted_title,
            "entity": entity,
            "hook": hook,
            "stage1": stage1,
            "stage2": stage2,
            "stage3": stage3,
            "stage4": stage4,
            "link": link,
            "source": source,
            "deep_contexts": deep_contexts[:2]
        }

    def build_trend_story(self, general_news: list) -> dict:
        """2️⃣ 🔥 [트렌드·유행·신상품 딥다이브] 스토리 생성"""
        trend_candidates = self.fetch_trend_candidates()
        if not trend_candidates:
            # 폴백: IT/신상품 또는 연예 기사에서 발췌
            it_candidates = [n for n in general_news if n.get("분야") in ["IT/과학/신상품", "연예/대중문화"]]
            if it_candidates:
                target_item = it_candidates[0]
                target_item = {
                    "title": target_item.get("기사제목", ""),
                    "summary": target_item.get("요약내용", ""),
                    "link": target_item.get("링크") or target_item.get("link", ""),
                    "source": target_item.get("언론사", "")
                }
            else:
                target_item = {
                    "title": "요즘 MZ세대가 열광하는 새로운 디저트·러닝 소비 트렌드",
                    "summary": "SNS 숏폼과 입소문을 타고 품절 대란과 오픈런이 확산되고 있습니다.",
                    "link": "",
                    "source": "트렌드포커스"
                }
        else:
            target_item = trend_candidates[0]

        raw_title = target_item["title"]
        raw_summary = target_item["summary"]
        link = target_item["link"]
        source = target_item["source"]

        entity = self.extract_core_entity(raw_title)
        deep_contexts = self.search_deep_context(entity)

        hook = f"요즘 SNS와 거리에서 난리 난 '{entity}', 사람들은 도대체 왜 여기에 줄을 서고 열광하는 걸까요?"

        stage1 = f"지금 번화가와 온라인 쇼핑몰에서 가장 뜨거운 화두는 단연 **[{raw_title}]** 입니다. {raw_summary}"

        if deep_contexts:
            ctx_summary = " ".join([c["summary"] for c in deep_contexts[:2]])
            stage2 = f"이 유행의 시초를 거슬러 올라가면 인플루언서와 숏폼(틱톡/릴스) 바이럴이 결정적 계기였습니다: {ctx_summary[:200]}..."
        else:
            stage2 = f"처음에는 소수의 마니아와 얼리어답터들 사이에서 시작되었으나, 숏폼 콘텐츠와 인증샷 문화가 결합되면서 순식간에 전국적인 '오픈런 대란'으로 번졌습니다."

        stage3 = f"사람들이 지갑을 여는 진짜 심리는 무엇일까요? 단순한 맛이나 디자인을 넘어, '나도 경험해 봤다'는 즉각적인 소속감과 디토(Ditto) 소비 심리가 강력한 기폭제가 되었습니다."

        stage4 = f"이 유행은 단순한 반짝 인기에 그칠까요, 아니면 새로운 일상의 표준이 될까요? 빠르게 바뀌는 트렌드 주기 속에서 관련 업계는 벌써 다음 먹거리 선점에 나섰습니다."

        formatted_title = f"🔥 [트렌드·유행 딥다이브] \"요즘 왜 이게 유행할까?\": {entity} 품절 대란의 비밀"

        return {
            "track": "TREND",
            "track_name": "트렌드·유행 딥다이브",
            "badge": "요즘 왜 이게 유행할까?",
            "title": formatted_title,
            "entity": entity,
            "hook": hook,
            "stage1": stage1,
            "stage2": stage2,
            "stage3": stage3,
            "stage4": stage4,
            "link": link,
            "source": source,
            "deep_contexts": deep_contexts[:2]
        }

    def generate_two_track_stories(self, general_news: list, mega_issue: dict = None) -> dict:
        """경제·사회 1건 + 트렌드·유행 1건 투 트랙 스토리 일괄 생성"""
        print(f"\n[슈카식 스토리 엔진] 🎙️ 오늘의 2대 딥다이브(경제·사회 & 트렌드·유행) 스토리 연구 및 서사 작성 중...")
        economy_story = self.build_economy_story(general_news, mega_issue)
        trend_story = self.build_trend_story(general_news)

        print(f" - 🌐 [경제·사회]: {economy_story['title'][:45]}...")
        print(f" - 🔥 [트렌드·유행]: {trend_story['title'][:45]}...")

        return {
            "economy_story": economy_story,
            "trend_story": trend_story,
            "stories": [economy_story, trend_story]
        }
