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
        # 트렌드 검색 범위를 라이프스타일, F&B, 팝업, 역주행, 신상품, 숏폼 등 전방위로 확장
        self.trend_feeds = [
            "https://news.google.com/rss/search?q=" + quote("품절대란 OR 오픈런 OR \"유행 열풍\" OR \"신상품 화제\" OR \"소비 트렌드\" OR 팝업스토어") + "&hl=ko&gl=KR&ceid=KR:ko",
            "https://news.google.com/rss/search?q=" + quote('"MZ세대" OR "핫플" OR "입소문" OR "신드롬" OR "대세" OR "SNS 화제" OR "역주행" OR "가치 소비"') + "&hl=ko&gl=KR&ceid=KR:ko",
            "https://news.google.com/rss/search?q=" + quote('"소비자 열광" OR "완판" OR "품귀" OR "줄서는" OR "인기 폭발" OR "바이럴 마케팅" OR "디저트 열풍"') + "&hl=ko&gl=KR&ceid=KR:ko"
        ]

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

    @classmethod
    def _synthesize_clean_context(cls, raw_items: list) -> str:
        """잡음을 완벽히 배제하고 매끄러운 한국어 문맥 추출"""
        clean_sentences = []
        for item in raw_items:
            summary = item.get("summary", "") if isinstance(item, dict) else str(item)
            text = cls._clean_text(summary)
            text = re.sub(r"\[.*?\]|\(.*?\)", " ", text)
            text = re.sub(r"^[가-힣a-zA-Z\s]+기자\s*=\s*", "", text)
            text = re.sub(r"\s+", " ", text).strip()
            sents = cls._split_into_sentences(text)
            for s in sents:
                if len(s) >= 20 and not any(j in s for j in ["기자", "무단", "저작권", "연합뉴스"]):
                    clean_sentences.append(s)
                    break
            if len(clean_sentences) >= 2:
                break
        return " ".join(clean_sentences)

    VIRAL_TERMS = {
        "품절": 25, "대란": 25, "오픈런": 30, "완판": 25, "웨이팅": 20, "줄서는": 20,
        "핫플": 20, "역주행": 25, "신드롬": 25, "열광": 20, "품귀": 25,
        "팝업": 20, "성수": 15, "MZ": 15, "인기폭발": 25, "소비트렌드": 20,
        "트렌드": 15, "바이럴": 20, "신상품": 15, "웃돈": 25, "품귀현상": 25,
        "완판행진": 25, "가치소비": 20, "품절대란": 30
    }
    PR_EXCLUDE_TERMS = {"출시했다", "선보인다", "공개했다", "오픈했다", "협약", "MOU", "체결했다"}

    def fetch_trend_candidates(self) -> list:
        """확장된 3대 트렌드 피드로부터 바이럴/화제성 지수 스코어링을 통해 최상위 1위 트렌드 엄선"""
        candidates = []
        seen_titles = set()
        for feed_url in self.trend_feeds:
            try:
                parsed = feedparser.parse(feed_url)
                for entry in parsed.entries[:12]:
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

                    simp_title = re.sub(r"[\s\W_]+", "", clean_title)[:20]
                    if simp_title in seen_titles:
                        continue
                    seen_titles.add(simp_title)

                    # 바이럴/소비자 열광 지수 스코어링
                    score = 0
                    comb = f"{clean_title} {summary}"
                    for term, weight in self.VIRAL_TERMS.items():
                        if term in comb:
                            score += weight
                    # 단순 기업 단발성 PR 보도자료 감점
                    if any(pr in clean_title for pr in self.PR_EXCLUDE_TERMS):
                        score -= 20

                    candidates.append({
                        "title": clean_title,
                        "summary": summary,
                        "link": link,
                        "source": source,
                        "category": "트렌드/유행",
                        "viral_score": score
                    })
            except Exception as e:
                print(f"[경고] 트렌드 후보 수집 오류 ({feed_url[:40]}...): {e}")

        # 바이럴 화제성 점수 내림차순 정렬
        candidates.sort(key=lambda x: x.get("viral_score", 0), reverse=True)
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

    @staticmethod
    def _strip_josa(word: str) -> str:
        """한국어 끝 조사를 자연스럽게 분리 제거"""
        if not word or len(word) <= 1:
            return word
        # 2글자 이상 조사 우선 제거 후 1글자 조사 제거
        josa_patterns = [
            r'(?:에서|으로|부터|까지|에게|에는|에도|과의|와의|하고|이나|이란|라는|라며)$',
            r'(?:은|는|이|가|을|를|에|의|로|와|과|도|만|서)$'
        ]
        res = word
        for pat in josa_patterns:
            trimmed = re.sub(pat, '', res)
            if len(trimmed) >= 2:
                res = trimmed
                break
        return res

    def extract_core_entity(self, title: str) -> str:
        """기사 제목에서 핵심 키워드/주제명 추출 및 조사 제거"""
        quote_match = re.search(r"['\"]([^'\"]+)['\"]", title)
        if quote_match and len(quote_match.group(1)) >= 2:
            return self._strip_josa(quote_match.group(1).strip())
        clean = re.sub(r"\[[^\]]+\]|\(.*?\)|\<.*?\>", "", title).strip()
        words = [w for w in re.split(r"[\s,‥…·]+", clean) if len(w) >= 2 and w not in ["오늘", "결국", "왜", "논란", "충격", "발표", "주장", "전망", "속보", "단독"]]
        if words:
            return self._strip_josa(words[0])
        return "주요이슈"

    def _infer_term_explanation(self, entity: str, title: str, summary: str, is_trend: bool = False) -> str:
        """주제에 걸맞은 1분 핵심 용어 사전 팁 생성"""
        full_text = f"{entity} {title} {summary}"
        
        dict_db = {
            "관세": "📌 **상호주의 관세(Reciprocal Tariff)**: 상대국이 자국 상품에 매기는 관세율과 동일한 수준으로 보복 관세를 부과하여 무역 불균형을 시정하려는 강력한 통상 압박 정책입니다.",
            "리쇼어링": "📌 **리쇼어링(Reshoring)**: 해외로 이전했던 자국 기업의 생산 기지를 세제 혜택이나 관세 압박을 통해 다시 본국으로 복귀시키는 제조업 부흥 전략입니다.",
            "금리": "📌 **피벗(Pivot)**: 중앙은행이 기존의 긴축적 통화 정책 기조를 끝내고 금리 인하 등 통화 완화로 통화 정책의 방향을 180도 전환하는 것을 의미합니다.",
            "반도체": "📌 **HBM(고대역폭 메모리)**: D램을 수직으로 높게 쌓아 데이터 처리 속도를 획기적으로 끌어올린 인공지능(AI) 그래픽처리장치(GPU) 필수 탑재 메모리입니다.",
            "자사주": "📌 **자사주 소각(Cancellation)**: 기업이 사들인 자기 회사 주식을 소멸시켜 전체 유통 주식 수를 줄임으로써, 주당순이익(EPS)을 끌어올리고 주가를 부양하는 강력한 주주환원책입니다.",
            "오픈런": "📌 **오픈런(Open Run)**: 매장 영업이 시작되자마자 한정판이나 희소 상품을 선점하기 위해 새벽부터 줄을 서서 달려가는 소비 현상입니다.",
            "팝업": "📌 **팝업스토어(Pop-up Store)**: 짧은 기간 동안 임시로 운영되는 매장으로, 단순 물건 판매를 넘어 소비자에게 특별한 브랜드 체험과 인증샷을 유도하는 현대 유통의 핵심 집객 전략입니다.",
            "가치 소비": "📌 **가치 소비(Value Consumption)**: 단순한 가격이나 브랜드보다 자신의 신념, 가치관, 심리적 만족감에 부합하는 제품에 기꺼이 지갑을 여는 소비 행태입니다.",
            "스몰 럭셔리": "📌 **스몰 럭셔리(Small Luxury)**: 경기 둔화 속에서 고가 대형 자산 대신 프리미엄 디저트나 니치 향수 등 소액의 고급 소비재로 즉각적인 심리적 만족을 얻는 소비 형태입니다.",
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

        # 1. 이슈 개요 및 현황 (누구나 이해하기 쉬운 직관적 상황 설명)
        stage1 = (
            f"오늘 주요 언론을 통해 집중 조명된 핵심 사안은 바로 **[{raw_title}]** 입니다.<br>"
            f"• <b>핵심 현황:</b> {raw_summary if raw_summary.endswith('.') else raw_summary + '.'}<br>"
            f"• <b>왜 중요한가:</b> 단순한 단발성 소식이 아니라 정부 정책, 규제 환경, 기업들의 실질적 손익과 직결되어 시장 전반에 큰 파장을 일으키고 있기 때문입니다."
        )

        # 2. 발단과 누적 타임라인 (왜, 언제부터 시작되었나?)
        bg_synth = self._synthesize_clean_context(deep_backgrounds)
        if bg_synth:
            stage2 = (
                f"이 문제는 오늘 갑자기 발생한 사안이 아니라, 과거부터 축적되어 온 구조적 원인이 있습니다.<br>"
                f"• <b>과거 배경:</b> {bg_synth}<br>"
                f"• <b>결정적 계기:</b> 잠재되어 있던 제도적 갈등과 시장 환경의 변화가 맞물리면서, 이번 계기를 통해 본격적으로 수면 위로 표출되었습니다."
            )
        else:
            stage2 = (
                f"이 사안은 과거 수년간 시장과 정책 당국 간에 누적되어 온 구조적 과제가 수면 위로 표출된 결과입니다.<br>"
                f"• <b>과거 배경:</b> 글로벌 공급망 재편과 정책 기조의 전환이 이어지며 시장의 압력이 누적되어 왔습니다.<br>"
                f"• <b>결정적 계기:</b> 최근의 제도적 변화와 주요 이해관계자들의 입장 차이가 정면으로 맞닥뜨리면서 본격적인 쟁점으로 급부상했습니다."
            )

        # 3. 이면의 구조와 이해관계 (누가 왜 움직이는가? 쉬운 원리 풀이)
        stk_synth = self._synthesize_clean_context(deep_stakes)
        if stk_synth:
            stage3 = (
                f"겉으로 보이는 명분 뒤에는 각 주체들의 아주 명확한 '실질적 손익 계산'이 숨어 있습니다.<br>"
                f"• <b>이해관계 분석:</b> {stk_synth}<br>"
                f"• <b>핵심 구조:</b> 규제 당국은 시장 통제력과 정책 주도권을 강화하려 하고, 관련 기업들은 비용 부담을 줄이고 수익성을 지키기 위해 치열한 수싸움을 벌이고 있는 구도입니다."
            )
        else:
            stage3 = (
                f"언론 헤드라인 이면에는 각 주체들의 치열한 손익 계산이 숨겨져 있습니다.<br>"
                f"• <b>이해관계 분석:</b> 정책 당국은 거시적 안정과 공공성을 명분으로 내세우고 있으나, 산업계는 규제 비용과 수익성 방어에 비상이 걸렸습니다.<br>"
                f"• <b>핵심 구조:</b> 결국 누가 비용을 부담하고 누가 장기적인 주도권을 쥐느냐를 둘러싼 치열한 헤게모니 싸움으로 해석할 수 있습니다."
            )

        # 4. 시장 파장과 향후 관전 포인트
        stage4 = (
            f"앞으로 시장과 투자자 관점에서 눈여겨보아야 할 핵심 체크포인트입니다.<br>"
            f"• <b>시장 파장:</b> 단기적인 주가 출렁임을 넘어, 관련 산업의 밸류체인과 지형도를 재편하는 기폭제가 될 수 있습니다.<br>"
            f"• <b>관전 포인트:</b> 향후 발표될 세부 가이드라인과 주요 일정에 따라 관련 기업들의 실적 희비가 크게 엇갈릴 전망이므로 면밀한 추적이 필요합니다."
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
        stage1 = (
            f"지금 거리와 SNS에서 소비자들이 가장 열광하고 있는 화제의 중심은 단연 **[{raw_title}]** 입니다.<br>"
            f"• <b>트렌드 현황:</b> {raw_summary if raw_summary.endswith('.') else raw_summary + '.'}<br>"
            f"• <b>열풍의 온도:</b> 매장 문이 열리기 전부터 줄을 서는 '오픈런'과 온라인 품절 사태가 잇따르며, 단순한 유행을 넘어 하나의 강력한 문화적 현상으로 자리 잡았습니다."
        )

        # 2. 유행의 시초와 바이럴 계기
        bg_synth = self._synthesize_clean_context(deep_backgrounds)
        if bg_synth:
            stage2 = (
                f"이 유행은 과연 어디서부터 시작되었을까요? 시작점을 추적해 보면 아주 흥미로운 바이럴 계기가 있습니다.<br>"
                f"• <b>시작 비화:</b> {bg_synth}<br>"
                f"• <b>확산 과정:</b> 초기에는 특정 매니아층 사이의 호기심으로 시작되었으나, 틱톡·릴스 등 숏폼 영상 알고리즘을 타며 '나도 경험해봐야 한다'는 대중적 열풍으로 급격히 번져나갔습니다."
            )
        else:
            stage2 = (
                f"이 유행은 초기에 소수의 얼리어답터들 사이에서 자발적인 호기심으로 시작되었습니다.<br>"
                f"• <b>시작 비화:</b> 기존의 평범한 제품에 색다른 재미와 스토리텔링이 더해지며 시각적 호기심을 강하게 자극했습니다.<br>"
                f"• <b>확산 과정:</b> 인플루언서들의 자발적 후기와 숏폼 알고리즘이 결합되면서 단숨에 전국적인 오픈런과 품절 대란으로 확산되었습니다."
            )

        # 3. 소비 심리와 마케팅 구조 (왜 사람들은 지갑을 열까?)
        psy_synth = self._synthesize_clean_context(deep_psychology)
        if psy_synth:
            stage3 = (
                f"소비자들이 기꺼이 시간과 비용을 들여 줄을 서는 심리적 이유를 쉽게 풀어보았습니다.<br>"
                f"• <b>소비 심리:</b> {psy_synth}<br>"
                f"• <b>심리적 기제:</b> 단순히 제품의 기능 때문이 아니라, '희소한 트렌드를 남들보다 빠르게 경험하고 인증했다'는 심리적 만족감과 소속감(동조 소비 및 포모(FOMO) 심리)이 지갑을 열게 만드는 핵심 동기입니다."
            )
        else:
            stage3 = (
                f"사람들이 열광하며 지갑을 여는 진짜 이유는 단순한 소비 이상의 '경험과 인증'에 있습니다.<br>"
                f"• <b>소비 심리:</b> '한정된 수량, 지금이 아니면 못 산다'는 희소성 마케팅이 소비자의 소장 욕구를 극대화했습니다.<br>"
                f"• <b>심리적 기제:</b> SNS에 인증샷을 올리며 트렌드에 뒤처지지 않았다는 안도감과 성취감을 얻는 현대인의 소비 패턴이 깊게 반영되어 있습니다."
            )

        # 4. 유통가 파장 및 지속 가능성
        stage4 = (
            f"이 열풍이 유통업계에 미친 영향과 향후 지속 가능성에 대한 전망입니다.<br>"
            f"• <b>유통가 파장:</b> 편의점, 백화점, 패션·식음료 브랜드들이 앞다퉈 컬래버레이션 팝업스토어를 유치하며 고객 유입에 사활을 걸고 있습니다.<br>"
            f"• <b>지속 가능성:</b> 반짝 유행(Fad)에 그치지 않고 장기적인 메가 트렌드로 안착하려면, 일회성 화제성을 넘어 본질적인 품질 만족도와 지속적인 팬덤 관리가 뒷받침되어야 합니다."
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
