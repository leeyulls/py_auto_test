"""
story_dive_engine.py
오늘의 심층 테마 리포트 (Deep-Dive Theme Report) 엔진
1) 🌐 [경제·사회 심층 리포트] 숨겨진 배경과 구조 분석 (역사, 지정학, 제도, 정책 이해관계)
2) 🔥 [트렌드 & 소비 인사이트] 요즘 왜 유행할까? 심층 분석 (발단 비화, 소비 심리, 마케팅 구조, 용어 해설)
"""

import datetime
import html
import re
import feedparser
from urllib.parse import quote


class StoryDiveEngine:
    """오늘의 심층 테마 리포트 생성 엔진 (구 StoryDiveEngine)"""
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

    @staticmethod
    def _split_into_sentences(text: str) -> list:
        """온전한 문장 단위로 분절"""
        if not text:
            return []
        raw_sentences = re.split(r'(?<=[.!?다함음])\s+', text.strip())
        sentences = []
        for s in raw_sentences:
            s_clean = s.strip()
            if len(s_clean) >= 15:
                if not s_clean.endswith(('.', '!', '?')):
                    s_clean += '.'
                sentences.append(s_clean)
        return sentences

    def fetch_trend_candidates(self) -> list:
        """트렌드/유행/신상품 특화 뉴스 후보 수집"""
        candidates = []
        try:
            parsed = feedparser.parse(self.trend_feed_url)
            for entry in parsed.entries[:15]:
                raw_title = self._clean_text(entry.get("title", ""))
                summary = self._clean_text(entry.get("summary", ""))
                link = entry.get("link", "")
                source = "트렌드포커스"
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

    def search_deep_context(self, keyword: str, aspect: str = "배경") -> list:
        """키워드에 대한 과거 배경, 비하인드, 타임라인 심층 기사 다각도 크롤링"""
        results = []
        if not keyword:
            return results
        if aspect == "배경":
            query_str = f'"{keyword}" (배경 OR 이유 OR 시초 OR 언제부터 OR 원인 OR 역사)'
        else:
            query_str = f'"{keyword}" (쟁점 OR 영향 OR 파장 OR 이해관계 OR 전망 OR 심리)'

        query = quote(query_str)
        search_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            parsed = feedparser.parse(search_url)
            for entry in parsed.entries[:8]:
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
        quote_match = re.search(r"['\"]([^'\"]+)['\"]", title)
        if quote_match and len(quote_match.group(1)) >= 2:
            return quote_match.group(1).strip()
        clean = re.sub(r"\[[^\]]+\]|\(.*?\)|\<.*?\>", "", title).strip()
        words = [w for w in re.split(r"[\s,‥…·]+", clean) if len(w) >= 2 and w not in ["오늘", "결국", "왜", "논란", "충격", "발표", "주장", "전망", "속보", "단독"]]
        return words[0] if words else "주요이슈"

    def _infer_term_explanation(self, entity: str, title: str, summary: str, is_trend: bool = False) -> str:
        """주제에 걸맞은 1분 핵심 용어 사전 팁 생성"""
        full_text = f"{entity} {title} {summary}"
        
        dict_db = {
            "관세": "📌 **상호주의 관세(Reciprocal Tariff)**: 상대국이 자국 상품에 매기는 관세율과 동일한 수준으로 보복 관세를 부과하여 무역 불균형을 시정하려는 강력한 통상 압박 정책입니다.",
            "트럼프": "📌 **리쇼어링(Reshoring)**: 해외로 이전했던 자국 기업의 생산 기지를 세제 혜택이나 관세 압박을 통해 다시 본국으로 복귀시키는 제조업 부흥 전략입니다.",
            "금리": "📌 **피벗(Pivot)**: 중앙은행이 기존의 긴축적 통화 정책 기조를 끝내고 금리 인하 등 통화 완화로 통화 정책의 방향을 180도 전환하는 것을 의미합니다.",
            "반도체": "📌 **HBM(고대역폭 메모리)**: D램을 수직으로 높게 쌓아 데이터 처리 속도를 획기적으로 끌어올린 인공지능(AI) 그래픽처리장치(GPU) 필수 탑재 메모리입니다.",
            "자사주": "📌 **자사주 소각(Cancellation)**: 기업이 사들인 자기 회사 주식을 소멸시켜 전체 유통 주식 수를 줄임으로써, 주당순이익(EPS)을 끌어올리고 주가를 부양하는 강력한 주주환원책입니다.",
            "오픈런": "📌 **오픈런(Open Run)**: 매장 영업이 시작되자마자 한정판이나 희소 상품을 선점하기 위해 새벽부터 줄을 서서 달려가는 소비 현상입니다.",
            "팝업": "📌 **팝업스토어(Pop-up Store)**: 짧은 기간 동안 임시로 운영되는 매장으로, 단순 물건 판매를 넘어 소비자에게 특별한 브랜드 체험과 인증샷을 유도하는 현대 유통의 핵심 집객 전략입니다.",
            "디토": "📌 **디토(Ditto) 소비**: '나도 마찬가지'라는 뜻처럼, 특정 인플루언서나 인기 콘텐츠의 취향을 신뢰하고 그대로 따라 구매하는 요즘 세대의 대표적 소비 형태입니다.",
            "블루 아카이브": "📌 **서브컬처 팬덤 비즈니스**: 만화·게임 등 탄탄한 마니아층을 보유한 지식재산권(IP)이 편의점, 패션, F&B와 결합하여 대중적 품절 대란을 유발하는 IP 확장 모델입니다.",
            "숏폼": "📌 **숏폼 바이럴(Short-form Viral)**: 1분 미만의 틱톡, 릴스, 쇼츠 영상을 통해 폭발적으로 입소문이 번져 오프라인 매장의 실물 상품 구매로 직결되는 유행 확산 구조입니다."
        }
        
        for k, v in dict_db.items():
            if k in full_text:
                return v

        if is_trend:
            return "📌 **희소성 마케팅(Scarcity Marketing)**: 수량이나 판매 기간을 극도로 제한하여 '지금 구매하지 않으면 품절된다'는 조급함(FOMO)을 자극하고 소장 가치를 극대화하는 소비 심리 기법입니다."
        else:
            return "📌 **구조적 수혜(Structural Beneficiary)**: 단기적 유행이 아닌, 국가 정책이나 글로벌 지정학적 공급망 재편에 따라 수년간 장기적인 성장을 누리게 되는 산업 생태계 현상입니다."

    def build_economy_story(self, general_news: list, mega_issue: dict) -> dict:
        """1️⃣ 🌐 [경제·사회 심층 리포트] 완성형 미니 보고서 생성"""
        target_item = mega_issue
        if not target_item or not target_item.get("기사제목"):
            econ_candidates = [n for n in general_news if n.get("분야") in ["거시경제/비즈니스", "세계/국제", "정치"]]
            target_item = econ_candidates[0] if econ_candidates else (general_news[0] if general_news else {})

        raw_title = target_item.get("기사제목", "글로벌 경제·산업 재편 이슈")
        raw_summary = target_item.get("요약내용", "주요 정책 및 산업 지형도 변화가 감지되고 있습니다.")
        link = target_item.get("링크") or target_item.get("link", "")
        source = target_item.get("언론사", "주요언론")

        entity = self.extract_core_entity(raw_title)
        deep_backgrounds = self.search_deep_context(entity, aspect="배경")
        deep_stakes = self.search_deep_context(entity, aspect="쟁점")

        # 1. 이슈 개요 및 현황 (구체적 사건 기술)
        stage1_sentences = [
            f"오늘 주요 언론을 통해 집중 조명된 핵심 사안은 바로 **[{raw_title}]** 입니다.",
            raw_summary if raw_summary.endswith('.') else raw_summary + '.',
            f"이번 사건은 단순한 단발성 해프닝이 아니라 관련 정책 당국과 글로벌 기업 간의 실질적 조치가 맞물려 시장에 직접적인 파장을 일으키고 있습니다."
        ]
        stage1 = " ".join(stage1_sentences)

        # 2. 발단과 누적 타임라인 (왜, 언제부터 시작되었나?)
        if deep_backgrounds:
            bg_snippets = []
            for bg in deep_backgrounds[:3]:
                sents = self._split_into_sentences(bg["summary"])
                if sents:
                    bg_snippets.append(sents[0])
            bg_context = " ".join(bg_snippets)
            stage2 = (
                f"이 문제는 오늘 갑자기 촉발된 사안이 아닙니다. 과거 전개 과정과 축적된 타임라인을 살펴보면: {bg_context} "
                f"즉, 과거 수년간 누적되어 온 구조적 요인과 정책적 이해관계가 특정한 정책 계기나 시장 환경을 맞아 본격적으로 수면 위로 표출된 것입니다."
            )
        else:
            stage2 = (
                f"이 사안은 과거 수년간 시장과 정책 당국 간에 누적되어 온 제도적 과제가 특정 계기를 맞아 수면 위로 표출된 결과입니다. "
                f"국내외 정책 기조의 급격한 전환과 이해관계자들의 상반된 입장이 누적되면서, 이번 사안을 기점으로 피할 수 없는 정면 승부 국면에 접어들었습니다."
            )

        # 3. 이면의 구조와 이해관계 (누가 왜 움직이는가?)
        if deep_stakes:
            stk_snippets = []
            for st in deep_stakes[:2]:
                sents = self._split_into_sentences(st["summary"])
                if sents:
                    stk_snippets.append(sents[0])
            stk_context = " ".join(stk_snippets)
            stage3 = (
                f"표면적인 명분 뒤에 숨겨진 본질적인 득실 계산을 들여다볼 필요가 있습니다. {stk_context} "
                f"겉으로는 원칙과 공공성을 앞세우고 있지만, 실제로는 각국 정부의 주도권 확보 수싸움과 기업들의 실익 지키기가 치열하게 격돌하고 있습니다."
            )
        else:
            stage3 = (
                f"언론 헤드라인 이면에는 각 주체들의 치열한 손익 계산이 숨겨져 있습니다. "
                f"정부 및 규제 당국은 시장 통제권과 정책 레버리지를 확보하려 하고, 관련 산업계는 수익성 방어와 규제 비용 최소화를 위해 치밀한 수싸움을 벌이고 있는 구조입니다."
            )

        # 4. 시장 파장과 향후 관전 포인트
        stage4 = (
            f"향후 시장 참여자들은 이번 사태가 가져올 제도적 변화와 주요 일정에 주목해야 합니다. "
            f"단기적인 가격 변동성을 넘어 중장기 산업 지형도를 재편하는 기폭제가 될 것이며, 관련 기업들의 실적과 주주가치에 미칠 영향을 면밀히 모니터링할 필요가 있습니다."
        )

        term_tip = self._infer_term_explanation(entity, raw_title, raw_summary, is_trend=False)
        formatted_title = f"🌐 [경제·사회 심층 리포트] {entity}의 숨겨진 배경과 구조적 쟁점"

        return {
            "track": "ECONOMY",
            "track_name": "경제·사회 심층 분석",
            "badge": "심층 분석",
            "title": formatted_title,
            "entity": entity,
            "hook": f"단순 뉴스 헤드라인을 넘어선 전후 맥락: '{entity}' 이슈가 촉발된 진짜 배경과 이해관계자들의 득실 계산을 분석합니다.",
            "stage1": stage1,
            "stage2": stage2,
            "stage3": stage3,
            "stage4": stage4,
            "term_tip": term_tip,
            "link": link,
            "source": source,
            "deep_contexts": deep_backgrounds[:2]
        }

    def build_trend_story(self, general_news: list) -> dict:
        """2️⃣ 🔥 [트렌드 & 소비 인사이트] 완성형 미니 보고서 생성"""
        trend_candidates = self.fetch_trend_candidates()
        if not trend_candidates:
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
        deep_backgrounds = self.search_deep_context(entity, aspect="배경")
        deep_psychology = self.search_deep_context(entity, aspect="쟁점")

        # 1. 트렌드 현상 및 화제
        stage1_sentences = [
            f"지금 오프라인 거리와 온라인 커뮤니티에서 가장 뜨거운 화두는 단연 **[{raw_title}]** 입니다.",
            raw_summary if raw_summary.endswith('.') else raw_summary + '.',
            f"매장 오픈 전부터 길게 늘어선 줄과 온라인 쇼핑몰의 연이은 품절 사태는 단순한 일시적 인기를 넘어 하나의 강력한 문화적 현상으로 자리 잡았습니다."
        ]
        stage1 = " ".join(stage1_sentences)

        # 2. 유행의 시초와 바이럴 계기
        if deep_backgrounds:
            bg_snippets = []
            for bg in deep_backgrounds[:3]:
                sents = self._split_into_sentences(bg["summary"])
                if sents:
                    bg_snippets.append(sents[0])
            bg_context = " ".join(bg_snippets)
            stage2 = (
                f"이 유행의 발단을 추적해 보면 숏폼 콘텐츠와 인플루언서의 체험 인증이 결정적 기폭제 역할을 했습니다: {bg_context} "
                f"초기에는 특정 마니아층 사이에서 소비되던 아이템이었으나, 시각적 호기심을 자극하는 리뷰 영상이 알고리즘을 타며 대중적인 열풍으로 급격히 번져나갔습니다."
            )
        else:
            stage2 = (
                f"이 유행은 초기에 소수의 얼리어답터들 사이에서 자발적으로 시작되었습니다. "
                f"이후 틱톡, 릴스 등 숏폼 플랫폼을 통해 짧고 강렬한 시각적 후기가 공유되면서, '나도 경험해 보지 않으면 안 된다'는 입소문이 전국 단위의 오픈런으로 확산되었습니다."
            )

        # 3. 소비 심리와 마케팅 구조
        if deep_psychology:
            psy_snippets = []
            for ps in deep_psychology[:2]:
                sents = self._split_into_sentences(ps["summary"])
                if sents:
                    psy_snippets.append(sents[0])
            psy_context = " ".join(psy_snippets)
            stage3 = (
                f"사람들이 열광하며 지갑을 여는 진짜 심리적 기제는 무엇일까요? {psy_context} "
                f"단순한 제품의 기능성이나 맛을 넘어, '희소한 트렌드를 직접 경험하고 인증했다'는 심리적 만족감과 소속감이 핵심 소비 동기로 작용하고 있습니다."
            )
        else:
            stage3 = (
                f"사람들이 지갑을 여는 진짜 이유는 단순한 제품 구매를 넘어선 '소속감'과 '성취감'입니다. "
                f"한정된 수량과 시간이라는 희소성 마케팅에, '나도 이 트렌드에 동참했다'는 인증 문화(디토 소비)가 결합되면서 강력한 자발적 바이럴 루프를 만들어냈습니다."
            )

        # 4. 향후 전망과 비즈니스 시사점
        stage4 = (
            f"관련 업계는 이 열풍이 일회성 유행에 그칠지, 아니면 새로운 일상의 표준으로 안착할지 예의주시하고 있습니다. "
            f"유행 주기가 극도로 짧아진 현대 소비 시장에서 발 빠른 브랜드 협업과 희소성 관리가 향후 유통·소비재 기업들의 핵심 경쟁력으로 부각되고 있습니다."
        )

        term_tip = self._infer_term_explanation(entity, raw_title, raw_summary, is_trend=True)
        formatted_title = f"🔥 [트렌드 & 소비 인사이트] {entity} 열풍의 배경과 소비 심리 분석"

        return {
            "track": "TREND",
            "track_name": "트렌드 & 소비 인사이트",
            "badge": "트렌드 포커스",
            "title": formatted_title,
            "entity": entity,
            "hook": f"요즘 왜 난리일까? '{entity}' 품절 대란과 오픈런 이면에 숨은 소비 심리와 바이럴 구조를 짚어봅니다.",
            "stage1": stage1,
            "stage2": stage2,
            "stage3": stage3,
            "stage4": stage4,
            "term_tip": term_tip,
            "link": link,
            "source": source,
            "deep_contexts": deep_backgrounds[:2]
        }

    def generate_two_track_stories(self, general_news: list, mega_issue: dict = None) -> dict:
        """경제·사회 1편 + 트렌드·소비 1편 심층 리포트 일괄 생성"""
        print(f"\n[심층 테마 리포트 엔진] 📌 오늘의 2대 심층 리포트(경제·사회 & 트렌드·소비) 연구 및 서사 작성 중...")
        economy_story = self.build_economy_story(general_news, mega_issue)
        trend_story = self.build_trend_story(general_news)

        print(f" - 🌐 [경제·사회]: {economy_story['title'][:48]}...")
        print(f" - 🔥 [트렌드·소비]: {trend_story['title'][:48]}...")

        return {
            "economy_story": economy_story,
            "trend_story": trend_story,
            "stories": [economy_story, trend_story]
        }
