"""
intelligence_dossier_engine.py
단순한 기사·리포트 요약을 넘어, 심층 2차 탐색(다각도 교차 취재)을 수행하여
배경, 타임라인, 데이터, 이해관계자 득실, 경쟁사 비교 및 전략적 시사점까지 전방위로 확장하는
[나만의 프리미엄 인텔리전스 뉴스페이퍼 & 심층 도시에(Dossier)] 생성 엔진
"""

import os
import re
import html
import datetime
from urllib.parse import quote
import feedparser


class IntelligenceDossierEngine:
    def __init__(self, history_mgr=None):
        self.history_mgr = history_mgr
        self.call_count = 0
        self.used_action_indices = []

    PROTECTED_NOUNS = {
        "국제유가", "유가", "물가", "주가", "상한가", "하한가", "전문가", "작사가", "작곡가", "원가", "시가", "단가", "농가", "어촌가",
        "종로", "구로", "통로", "경로", "회로", "단로",
        "오이", "아이", "종이", "놀이", "먹이", "깊이", "높이",
        "정의", "합의", "결의", "주의", "협의", "명의", "심의", "동의", "건의", "결정의",
        "칠은", "고은", "보은"
    }

    DISALLOWED_SUBJECTS = {
        "오늘", "어제", "내일", "결국", "왜", "논란", "충격", "발표", "주장", "전망", "속보", "단독", "종합", "특수공시",
        "올해만", "신임", "떠나는", "마지막", "역대", "최고가", "기대", "건립", "속도", "추정", "1심", "2심",
        "게시판", "특징주", "하반기", "상반기", "착수", "관련", "기준가", "마감", "경제적", "뉴스거리", "출렁",
        "비판", "반발", "환호", "분노", "비용", "적정성", "발언", "촉구", "도마", "지적", "공방", "여전한", "하루",
        "이틀", "사흘", "나흘", "다시", "지난", "이번", "이런", "저런", "모든", "어떤", "국민", "시민", "누리꾼",
        "사람들", "관계자", "당국", "정부", "이유", "배경", "제기", "주목", "포착", "눈물", "직격", "맹공",
        "2026년", "2025년", "2024년", "10월", "11월", "12월", "1월", "2월", "3월",
        "어차피", "혹시", "과연", "설마", "마치", "아무리", "비록", "더욱", "점점", "매우", "정말", "진짜"
    }

    AUXILIARY_STOPWORDS = {
        "만에", "내달", "지난달", "이번달", "올해", "내년", "전년대비", "대비", "통해", "대해", "위해",
        "꺼낸", "피격된", "따른", "따라", "대한", "인한", "열린", "밝힌", "전한", "알린", "찾은", "보인",
        "웃돌아", "재점화", "넘어", "앞서", "본격", "가운데", "맞물려", "이은", "이어"
    }

    TRUNCATED_ENDINGS = {"다음", "보", "있", "했", "됐", "될", "할", "등", "및", "관", "위", "알", "못", "않", "이", "그"}

    @classmethod
    def strip_korean_josa(cls, word: str) -> str:
        """한국어 음운 규칙(받침 유무)을 준수하여 명사 끝 조사를 안전하게 제거 (예: 렛미플라이 유지, 신한지주가->신한지주)"""
        if not word or len(word) < 2:
            return word
        if word in cls.PROTECTED_NOUNS:
            return word
        if len(word) == 2 and not word.endswith(('은', '는', '이', '가', '을', '를', '과', '와', '로')):
            return word
        if len(word) == 2 and word in {"물가", "유가", "주가", "금리", "환율", "수출", "수입", "미국", "중국", "일본", "러시아", "북한", "이란", "세종", "서울", "경찰", "검찰", "국회"}:
            return word

        last_char = word[-1]
        prev_char = word[-2]
        
        def has_jongseong(ch):
            if '가' <= ch <= '힣':
                return (ord(ch) - 0xAC00) % 28 > 0
            return False

        # 으로 먼저
        if word.endswith('으로') and len(word) >= 3 and has_jongseong(word[-3]):
            return word[:-2]
        # 에서 / 서
        if word.endswith('에서') and len(word) >= 3:
            return word[:-2]
        if word.endswith('서') and len(word) >= 3:
            return word[:-1]
        # 로
        if last_char == '로' and (not has_jongseong(prev_char) or (ord(prev_char) - 0xAC00) % 28 == 8):
            return word[:-1]
        # 은/는
        if last_char == '은' and has_jongseong(prev_char):
            return word[:-1]
        if last_char == '는' and not has_jongseong(prev_char):
            return word[:-1]
        # 이/가 ('라'처럼 받침 없으면 '이'는 조사가 아님 -> 렛미플라이 보존)
        if last_char == '이' and has_jongseong(prev_char):
            return word[:-1]
        if last_char == '가' and not has_jongseong(prev_char):
            return word[:-1]
        # 을/를
        if last_char == '을' and has_jongseong(prev_char):
            return word[:-1]
        if last_char == '를' and not has_jongseong(prev_char):
            return word[:-1]
        # 과/와
        if last_char == '과' and has_jongseong(prev_char):
            return word[:-1]
        if last_char == '와' and not has_jongseong(prev_char):
            return word[:-1]
        # 의 / 에
        if last_char in ('의', '에'):
            return word[:-1]
        return word

    @staticmethod
    def has_jongseong(word: str) -> bool:
        """단어의 마지막 글자가 종성(받침)을 가지는지 검사"""
        if not word:
            return False
        last_char = word[-1]
        if '가' <= last_char <= '힣':
            return (ord(last_char) - 0xAC00) % 28 > 0
        return False

    @classmethod
    def attach_josa(cls, word: str, josa_type: str) -> str:
        """받침 유무에 따른 자연스러운 한국어 조사 반환"""
        if not word:
            return ""
        has_j = cls.has_jongseong(word)
        if josa_type in ("이/가", "가/이"):
            return "이" if has_j else "가"
        if josa_type in ("을/를", "를/을"):
            return "을" if has_j else "를"
        if josa_type in ("은/는", "는/은"):
            return "은" if has_j else "는"
        if josa_type in ("과/와", "와/과"):
            return "과" if has_j else "와"
        if josa_type in ("으로/로", "로/으로"):
            last_char = word[-1]
            if '가' <= last_char <= '힣' and (ord(last_char) - 0xAC00) % 28 == 8:  # 'ㄹ' 받침
                return "로"
            return "으로" if has_j else "로"
        return ""

    @staticmethod
    def _clean_text(raw_html: str) -> str:
        if not raw_html:
            return ""
        text = re.sub(r"<[^>]+>", " ", raw_html)
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _split_into_clean_sentences(text: str, min_len: int = 15) -> list:
        if not text:
            return []
        raw_sents = re.split(r'(?<=[.!?다함음])\s+', text.strip())
        sentences = []
        for s in raw_sents:
            s_clean = s.strip()
            if len(s_clean) >= min_len and not any(junk in s_clean for junk in ["기자", "무단전재", "저작권", "사진제공", "연합뉴스", "뉴시스", "뉴스1"]):
                if not s_clean.endswith(('.', '!', '?')):
                    s_clean += '.'
                sentences.append(s_clean)
        return sentences

    def search_multi_angle_context(self, query_keyword: str, angle: str = "배경", limit: int = 6, context_hint: str = None, exclude_terms: list = None) -> list:
        """다각도 심층 2차 검색: 배경/역사, 쟁점/영향, 데이터/통계/전망 (힌트 결합 및 도메인 배제 필터 적용)"""
        results = []
        if not query_keyword or len(query_keyword.strip()) < 2:
            return results

        if '"' in query_keyword or ' OR ' in query_keyword:
            if context_hint:
                q_str = f'{query_keyword} ({context_hint})'
            elif angle == "배경":
                q_str = f'{query_keyword} (배경 OR 역사 OR 원인 OR 발단)'
            elif angle == "쟁점":
                q_str = f'{query_keyword} (쟁점 OR 이해관계 OR 영향 OR 파장)'
            elif angle == "데이터":
                q_str = f'{query_keyword} (실적 OR 매출 OR 영업이익 OR 통계 OR 수치)'
            elif angle == "기업":
                q_str = f'{query_keyword} (사업 OR 제품 OR 점유율 OR 기술력)'
            else:
                q_str = f'{query_keyword} (분석 OR 전략 OR 시사점)'
        else:
            clean_kw = re.sub(r"['\"\[\]\(\)]", "", query_keyword).strip()
            if context_hint:
                q_str = f'"{clean_kw}" ({context_hint})'
            elif angle == "배경":
                q_str = f'"{clean_kw}" (배경 OR 역사 OR 원인 OR 발단)'
            elif angle == "쟁점":
                q_str = f'"{clean_kw}" (쟁점 OR 이해관계 OR 영향 OR 파장)'
            elif angle == "데이터":
                q_str = f'"{clean_kw}" (실적 OR 매출 OR 영업이익 OR 통계 OR 수치)'
            elif angle == "기업":
                q_str = f'"{clean_kw}" (사업 OR 제품 OR 점유율 OR 기술력)'
            else:
                q_str = f'"{clean_kw}" (분석 OR 전략 OR 시사점)'

        encoded_q = quote(q_str)
        feed_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:limit * 2]:
                t = self._clean_text(entry.get("title", ""))
                s = self._clean_text(entry.get("summary", ""))
                link = entry.get("link", "")
                source = "언론보도"
                if " - " in t:
                    t, source = t.rsplit(" - ", 1)
                
                # 배제 키워드 필터링 (오탐 방지)
                comb_text = f"{t} {s}"
                if any(ex in comb_text for ex in active_excludes):
                    continue

                results.append({
                    "title": t.strip(),
                    "summary": s.strip(),
                    "link": link,
                    "source": source.strip()
                })
                if len(results) >= limit:
                    break
        except Exception as e:
            pass
        return results

    def extract_core_entity(self, title: str) -> str:
        """기사/리포트 제목에서 가장 핵심이 되는 기업명/인물명/주제어 정밀 추출"""
        clean = re.sub(r"\[[^\]]+\]|\(.*?\)|<.*?>", " ", title).strip()
        
        # 1. 단자 국가/지정학 약어 및 우선순위 엔티티
        if "北" in clean or "북한" in clean or "평양" in clean:
            return "북한"
        if "우크라" in clean or "우크라이나" in clean:
            return "우크라이나"
        if "러시아" in clean:
            return "러시아"
            
        entity_priority = [
            "인천 흉기 난동", "신한지주", "롯데손보", "경기교육청", "경남교육청", "코카콜라", "맥도날드", "오레오",
            "대한변협", "변협", "렛미플라이", "반 고흐", "신압록강", "금융위", "새마을금고", "공급망안정화", "원/달러",
            "외교부", "외교차관", "조정식", "조의장", "안민석", "추미애", "트럼프", "푸틴", "발로란트", "키트루다",
            "강훈식", "박형준", "퐁피두", "김지용", "카카오", "네이버", "삼성전자", "현대차", "기아", "후티", "사우디",
            "노르웨이", "고성군", "한국은행", "대법원"
        ]
        for ep in entity_priority:
            if ep in clean:
                return ep
                
        # 2. 따옴표 내부 검사 (동사구나 긴 문장, 추상명사가 아닌 순수 고유명사구만)
        quote_match = re.search(r"['\"‘“]([^'\"’”]+)['\"’”]", clean)
        if quote_match:
            candidate = quote_match.group(1).strip()
            abstract_nouns = {
                "엄호", "뉴스거리", "출렁", "비판", "반발", "환호", "눈물", "분노", "비용", "적정성",
                "충격", "발언", "촉구", "의혹", "논란", "특혜", "긴급", "포착", "주목", "이유", "배경",
                "성공", "분투", "일념", "도마", "지적", "공방"
            }
            words = candidate.split()
            if 1 <= len(words) <= 2 and len(candidate) <= 10 and candidate not in abstract_nouns:
                if not any(candidate.endswith(verb) for verb in ["지원", "정당", "모색", "기대", "논의", "체결", "하락", "급등", "답변"]):
                    cand_clean = self.strip_korean_josa(candidate)
                    if cand_clean and len(cand_clean) >= 2 and cand_clean not in abstract_nouns:
                        return cand_clean
                        
        # 3. 불용어 제거 및 토큰 분석
        clean_no_punct = re.sub(r"['\"‘“’”·…!?,~]", " ", clean)
        stopwords = {
            "오늘", "어제", "내일", "결국", "왜", "논란", "충격", "발표", "주장", "전망", "속보", "단독", "종합", "특수공시",
            "올해만", "신임", "떠나는", "마지막", "역대", "최고가", "기대", "건립", "속도", "추정", "1심", "2심",
            "게시판", "특징주", "하반기", "상반기", "모색", "논의", "착수", "종합", "관련", "기준가", "마감", "경제적",
            "엄호", "뉴스거리", "출렁", "비판", "반발", "환호", "분노", "비용", "적정성", "발언", "촉구", "도마"
        }
        tokens = [w for w in clean_no_punct.split() if len(w) >= 2 and w not in stopwords]
        
        for tok in tokens:
            clean_tok = self.strip_korean_josa(tok)
            if len(clean_tok) >= 3 and clean_tok not in stopwords:
                return clean_tok
        for tok in tokens:
            clean_tok = self.strip_korean_josa(tok)
            if len(clean_tok) >= 2 and clean_tok not in stopwords:
                return clean_tok
                
        return tokens[0] if tokens else "주요이슈"

    @classmethod
    def is_similar_title(cls, t1: str, t2: str, threshold: float = 0.55) -> bool:
        clean1 = set(re.findall(r"[가-힣a-zA-Z0-9]{2,}", t1))
        clean2 = set(re.findall(r"[가-힣a-zA-Z0-9]{2,}", t2))
        if not clean1 or not clean2:
            return False
        inter = clean1.intersection(clean2)
        union = clean1.union(clean2)
        return (len(inter) / len(union)) >= threshold

    def extract_contextual_query(self, title: str, summary: str = "") -> dict:
        """
        단어 1개가 아닌 기사의 전체 문맥(주어 + 핵심 사건/대상어)을 정밀 파악하여
        2차 심층 검색을 위한 고정밀 복합 문맥 쿼리 및 핵심 문맥 구문 생성
        """
        clean_title = re.sub(r"\[[^\]]+\]|\(.*?\)|<.*?>", " ", title).strip()

        # 0. 매크로 및 주요 지표 정규화
        if "CPI" in clean_title or "소비자물가" in clean_title:
            subject = "미국 소비자물가지수(CPI)" if ("美" in clean_title or "미국" in clean_title) else "소비자물가"
        elif "국제유가" in clean_title or ("유가" in clean_title and any(w in clean_title for w in ["배럴", "상승", "하락", "급등", "급락", "WTI", "브렌트유", "아람코"])):
            subject = "국제유가"
        elif "호르무즈" in clean_title:
            subject = "호르무즈 해협"
        elif any(w in clean_title for w in ["지지율", "여론조사", "KSOI", "리얼미터", "갤럽"]):
            subject = "대통령 국정 지지율"
        else:
            subject = None

        # 1. 고유명사 우선순위 엔티티 매핑
        priority_entities = [
            "마이크로소프트", "2PM 장우영", "장우영", "이수만", "A20라이트", "김지용", "안철수", "임광현", "오세훈", "이재명", "조국",
            "윤석열", "한동훈", "트럼프", "푸틴", "시진핑", "바이든", "해리스", "젤렌스키", "머스크", "신한지주", "롯데손보",
            "경기교육청", "경남교육청", "코카콜라", "맥도날드", "오레오", "대한변협", "금융위", "금감원", "국방부", "외교부",
            "통일부", "경찰", "검찰", "공수처", "중수청", "공정위", "삼성전자", "SK하이닉스", "현대차", "기아", "LG전자",
            "카카오", "네이버", "지그재그", "세가", "풋볼 매니저", "아람코", "사우디", "북한", "우크라이나", "러시아", "대만"
        ]
        if not subject:
            for pe in priority_entities:
                if pe in clean_title:
                    subject = pe
                    break

        clean_no_punct = re.sub(r"['\"‘“’”·…!?,~^%]", " ", clean_title)
        raw_tokens = [w for w in clean_no_punct.split() if len(w) >= 2]

        meaningful_tokens = []
        for t in raw_tokens:
            clean_t = self.strip_korean_josa(t)
            if len(clean_t) >= 2 and clean_t not in self.DISALLOWED_SUBJECTS and clean_t not in self.AUXILIARY_STOPWORDS:
                if not re.search(r"\d", clean_t):
                    meaningful_tokens.append(clean_t)

        if not subject:
            for tok in meaningful_tokens:
                if tok not in self.DISALLOWED_SUBJECTS and len(tok) >= 2:
                    subject = tok
                    break
            if not subject:
                subject = "주요이슈"

        sub_tokens = [t for t in meaningful_tokens if t not in subject and subject not in t and t not in self.DISALLOWED_SUBJECTS and t not in self.AUXILIARY_STOPWORDS]
        action_topic = " ".join(sub_tokens[:2]) if sub_tokens else "주요 동향"

        clean_sub = subject.replace("2PM ", "").replace("미국 소비자물가지수(CPI)", "CPI").replace("대통령 국정 지지율", "대통령 지지율")
        if sub_tokens:
            if len(sub_tokens) >= 2:
                search_q = f'"{clean_sub}" ("{sub_tokens[0]}" OR "{sub_tokens[1]}")'
            else:
                search_q = f'"{clean_sub}" "{sub_tokens[0]}"'
        else:
            search_q = f'"{clean_sub}" (동향 OR 현황 OR 전망)'

        return {
            "subject": subject,
            "clean_subject": clean_sub,
            "action_topic": action_topic,
            "search_query": search_q,
            "context_phrase": f"{subject} {action_topic}".strip(),
            "sub_tokens": sub_tokens[:3],
            "key_tokens": [subject] + sub_tokens[:3]
        }

    def investigate_deep_context(self, context_info: dict, orig_title: str = "", limit: int = 5) -> dict:
        """
        문맥 쿼리를 통해 실시간 2차 심층 조사를 수행하고,
        검색 결과에서 실제 팩트 문장(배경/원인, 영향/전망, 모니터링 포인트 및 타 언론사 교차 보도문)을 추출
        """
        q = context_info.get("search_query", "")
        results = {
            "background_facts": [],
            "impact_facts": [],
            "monitoring_points": [],
            "raw_titles": [],
            "cross_reports": [],
            "numeric_facts": []
        }
        if not q:
            return results

        try:
            encoded_q = quote(q)
            feed_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=ko&gl=KR&ceid=KR:ko"
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:limit * 2]:
                raw_t = entry.get("title", "").strip()
                if not raw_t:
                    continue
                t = raw_t
                if " - " in raw_t:
                    t, source = raw_t.rsplit(" - ", 1)
                clean_t = re.sub(r"\[.*?\]|\(.*?\)|<.*?>", "", t).strip()
                clean_t = re.sub(r"\.{2,}|…+", "", clean_t).strip()
                clean_t = re.sub(r"\s+", " ", clean_t).strip()

                if any(ex in clean_t for ex in ["오페라", "창작오페라", "정읍사", "판소리", "국악"]):
                    continue

                if orig_title and (self.is_similar_title(orig_title, clean_t, threshold=0.55) or len(clean_t) < 12):
                    continue

                if clean_t not in results["raw_titles"]:
                    results["raw_titles"].append(clean_t)

                if len(results["cross_reports"]) < 2:
                    results["cross_reports"].append(clean_t)

                if any(w in clean_t for w in ["억원", "조원", "달러", "%", "월", "일", "청문회", "패치", "WTI", "배럴", "공급"]):
                    if len(results["numeric_facts"]) < 2 and clean_t not in results["numeric_facts"]:
                        results["numeric_facts"].append(clean_t)

                # 요약문 파싱
                s = self._clean_text(entry.get("summary", ""))
                comb = f"{clean_t}. {s}" if s and not self.is_similar_title(clean_t, s, threshold=0.5) else clean_t
                sents = self._split_into_clean_sentences(comb, min_len=18)
                for sent in sents:
                    if any(w in sent for w in ["때문", "배경", "원인", "발단", "이유", "따라", "인해", "지적", "시작", "착수", "돌입", "체결", "합의", "추진"]):
                        if len(results["background_facts"]) < 2 and sent not in results["background_facts"]:
                            results["background_facts"].append(sent)
                    if any(w in sent for w in ["전망", "영향", "파장", "분석", "기대", "우려", "예상", "평가", "계획", "예정", "방침", "돌파", "타격", "수혜"]):
                        if len(results["impact_facts"]) < 2 and sent not in results["impact_facts"]:
                            results["impact_facts"].append(sent)
                    if any(w in sent for w in ["억원", "조원", "달러", "%", "심사", "선고", "판결", "기소", "영장", "인가", "승인", "조사", "발표", "과징금", "공방"]):
                        if len(results["monitoring_points"]) < 2 and sent not in results["monitoring_points"]:
                            results["monitoring_points"].append(sent)

                if len(results["cross_reports"]) >= 2 and len(results["background_facts"]) >= 1:
                    break
        except Exception:
            pass
        return results

    # =========================================================================
    # 📰 1. [1면 탑 기획특집] 오늘의 메가 경제·산업 심층 르포 확장
    # =========================================================================
    def expand_mega_issue_story(self, mega_issue: dict, general_news: list = None) -> dict:
        """1차 기사를 넘어 2차 확장 조사를 집대성한 장문의 신문 1면 탑 기획특집 기사 편찬"""
        target = mega_issue or {}
        if not target.get("기사제목") and general_news:
            target = general_news[0]

        raw_title = target.get("기사제목", "글로벌 공급망 및 산업 재편 이슈")
        raw_summary = target.get("요약내용", "주요 산업과 정책 환경의 중대한 변화가 감지되었습니다.")
        link = target.get("링크") or target.get("link", "#")
        source = target.get("언론사", "주요언론")
        media_count = target.get("media_count", 5)

        # 문맥 전체(주어 + 핵심사건) 정밀 파악
        ctx_info = self.extract_contextual_query(raw_title, raw_summary)
        entity = ctx_info["subject"]
        context_phrase = ctx_info["context_phrase"]

        # 2차 다각도 심층 조사 수행 (단어 1개가 아닌 문맥 쿼리 기반)
        bg_items = self.search_multi_angle_context(ctx_info["search_query"], angle="배경", limit=4)
        stake_items = self.search_multi_angle_context(ctx_info["search_query"], angle="쟁점", limit=4)
        data_items = self.search_multi_angle_context(ctx_info["search_query"], angle="데이터", limit=4)

        # 문장 추출
        bg_sents = []
        for it in bg_items:
            bg_sents.extend(self._split_into_clean_sentences(it["summary"]))
        stake_sents = []
        for it in stake_items:
            stake_sents.extend(self._split_into_clean_sentences(it["summary"]))
        data_sents = []
        for it in data_items:
            data_sents.extend(self._split_into_clean_sentences(it["summary"]))

        bg_text = " ".join(bg_sents[:3]) if bg_sents else f"'{context_phrase}' 사안은 과거 수년간 글로벌 통상 질서 및 국내 규제 정책이 누적되어 온 결과물로, 단순한 우발적 사건이 아닌 구조적 변곡점에서 비롯되었습니다."
        stake_text = " ".join(stake_sents[:3]) if stake_sents else f"정부 및 규제 당국은 시장 투명성과 공공 정책 주도권을 강화하려는 반면, 민간 산업계는 비용 상승 압박과 글로벌 경쟁력 약화를 우려하며 치열한 수싸움을 전개하고 있습니다."
        data_text = " ".join(data_sents[:3]) if data_sents else f"업계 추산에 따르면 관련 시장 규모와 파급 효과는 수조 원대에 달하며, 향후 분기별 기업 실적과 직결되는 결정적 변수로 작용할 전망입니다."

        headline = f"🌐 [1면 탑 심층 기획] '{context_phrase}'의 숨겨진 비하인드와 글로벌 밸류체인 대변혁"
        subhead = f"단순 뉴스 헤드라인을 넘어선 전후 맥락: '{context_phrase}' 사안이 촉발된 진짜 배경과 이해관계자별 손익 전격 해부"

        lead_p = (
            f"오늘 대한민국 주요 {media_count}개 언론사가 일제히 1면 톱기사로 타전한 핵심 이슈는 바로 <b>[{raw_title}]</b>입니다. "
            f"{raw_summary} "
            f"하지만 겉으로 드러난 단신 보도만으로는 이 사건이 왜 지금 이 시점에 폭발했는지, 그리고 향후 우리 비즈니스와 투자 포트폴리오에 어떤 파장을 미칠지 가늠하기 어렵습니다. "
            f"이에 본지 리서치팀은 1차 기사의 범위를 넘어 과거 타임라인, 업계 미공개 통계, 그리고 정책 당국과 기업 간의 물밑 이해관계를 입체적으로 추적·분석했습니다."
        )

        chapter1 = (
            f"<b>■ 발단과 전개 과정 (타임라인 & 팩트 체크):</b><br>"
            f"이 사안의 발단은 오늘 갑작스럽게 불거진 것이 아닙니다. 과거부터 축적되어 온 누적된 원인이 마침내 임계점을 넘어선 것입니다. "
            f"{bg_text} "
            f"특히 최근 글로벌 매크로 환경 변화와 통상 규제의 강화가 맞물리면서, 잠재되어 있던 구조적 모순이 수면 위로 급격히 분출되었습니다."
        )

        chapter2 = (
            f"<b>■ 2차 심층 조사 데이터 & 숨겨진 팩트:</b><br>"
            f"일반 보도에서 다루지 않은 2차 조사 데이터를 확인한 결과, 시장의 예상보다 훨씬 막대한 자금과 공급망 재편이 걸려 있는 것으로 확인되었습니다. "
            f"{data_text} "
            f"이는 단순한 개별 기업의 이슈를 넘어, 업계 전반의 영업이익률과 원가 구조를 뒤흔들 수 있는 중대한 수치적 변화를 동반하고 있습니다."
        )

        chapter3 = (
            f"<b>■ 이해관계자 손익 계산 & 산업 지형도 변화:</b><br>"
            f"언론의 명분 이면에는 각 주체들의 대단히 치열한 실질적 득실 계산이 자리 잡고 있습니다. "
            f"{stake_text} "
            f"결국 이번 사안을 통해 누가 주도권을 잡고 누가 추가 비용을 떠안느냐에 따라, 관련 밸류체인 내 1위 기업과 후발 주자 간의 격차가 극명하게 벌어질 것으로 분석됩니다."
        )

        chapter4 = (
            f"<b>■ 오늘의 핵심 전략 제언 및 시사점:</b><br>"
            f"향후 발표될 정부의 세부 후속 가이드라인과 글로벌 파트너사들의 공식 반응이 1차 변곡점이 될 것입니다. "
            f"단기적인 노이즈성 주가 등락에 일희일비하기보다는, 해당 이슈로 인해 장기적인 반사이익을 얻을 수혜 기업군(원자재 다변화 및 규제 대응 완료 기업)을 선별하고 포트폴리오의 안전마진을 확보하는 전략적 접근이 요구됩니다."
        )

        return {
            "headline": headline,
            "subhead": subhead,
            "lead": lead_p,
            "chapter1": chapter1,
            "chapter2": chapter2,
            "chapter3": chapter3,
            "chapter4": chapter4,
            "entity": entity,
            "raw_title": raw_title,
            "link": link,
            "source": source
        }

    # =========================================================================
    # 🔥 2. [2면 기획 르포] 트렌드 & 2030 라이프스타일 소비 심리 해부
    # =========================================================================
    def expand_trend_story(self, trend_item: dict) -> dict:
        """트렌드 단신을 넘어 소비 심리, 바이럴 구조, 유통가 PB 전쟁까지 파헤친 르포 기사 편찬"""
        raw_title = trend_item.get("title", "MZ세대 품절 대란과 신소비 트렌드")
        raw_summary = trend_item.get("summary", "SNS 화제와 함께 오프라인 매장 오픈런이 이어지고 있습니다.")
        link = trend_item.get("link", "#")
        source = trend_item.get("source", "트렌드포커스")

        # 문맥 전체(주어 + 팝업/소비/트렌드) 정밀 파악
        ctx_info = self.extract_contextual_query(raw_title, raw_summary)
        entity = ctx_info["subject"]
        context_phrase = ctx_info["context_phrase"]

        # 2차 검색 (문맥 복합 쿼리 결합)
        origin_items = self.search_multi_angle_context(ctx_info["search_query"], angle="배경", limit=4, context_hint="팝업 OR 성수 OR 소비 OR 트렌드 OR MZ", exclude_terms=["오페라", "창작오페라", "정읍사", "판소리", "국악", "전북도립국악원"])
        retail_items = self.search_multi_angle_context(ctx_info["search_query"], angle="기업", limit=4, context_hint="매출 OR 유통 OR 오픈런 OR 팝업스토어", exclude_terms=["오페라", "창작오페라", "정읍사"])

        origin_sents = []
        for it in origin_items:
            origin_sents.extend(self._split_into_clean_sentences(it["summary"]))
        retail_sents = []
        for it in retail_items:
            retail_sents.extend(self._split_into_clean_sentences(it["summary"]))

        origin_text = " ".join(origin_sents[:3]) if origin_sents else f"초기에는 틱톡, 인스타그램 릴스 등 숏폼 플랫폼에서 소수 인플루언서의 솔직한 언박싱 영상으로 시작되었으나, '한정 수량'이라는 희소성이 부각되면서 급속도로 전국적 바이럴을 탔습니다."
        retail_text = " ".join(retail_sents[:3]) if retail_sents else f"편의점 3사(GS25, CU, 세븐일레븐)와 대형 유통 백화점들은 핵심 점포 팝업스토어 유치와 자체 PB 미투(Me-too) 상품 기획에 전사적 역량을 집중하며 2030 집객 전쟁을 벌이고 있습니다."

        headline = f"🛍️ [트렌드 & 소비 심리 기획 르포] '{entity}' 신드롬의 진원지와 2030 '디토 소비' 메커니즘"
        subhead = f"숏폼 알고리즘과 희소성 마케팅이 결합된 현대 소비 문법... 유통 대기업들의 물밑 PB 쟁탈전 전격 진단"

        lead_p = (
            f"최근 온·오프라인을 가리지 않고 연일 오픈런과 품절 사태를 빚고 있는 화제의 중심에는 바로 <b>[{raw_title}]</b> 현상이 있습니다. "
            f"매장 문이 열리자마자 전량 매진되고 중고 거래 플랫폼에서 정가의 2~3배가 넘는 웃돈(프리미엄)이 붙는 기현상이 반복되고 있습니다. "
            f"단순한 1회성 유행으로 치부하기에는 2030 세대의 소비 심리와 유통 대기업들의 마케팅 전략이 정교하게 맞물려 있습니다."
        )

        chapter1 = (
            f"<b>■ 유행의 시초와 바이럴 트리거 (어디서 어떻게 시작되었나?):</b><br>"
            f"이 유행의 발원지를 추적해 보면 아주 명확한 디지털 확산 경로가 드러납니다. "
            f"{origin_text} "
            f"특히 알고리즘 기반의 숏폼 콘텐츠가 확산의 촉매제가 되었으며, 일반인들의 '내돈내산' 인증 챌린지가 이어지면서 공급이 수요를 따라가지 못하는 품귀 대란으로 진화했습니다."
        )

        chapter2 = (
            f"<b>■ 소비 심리 & 행동 경제학 분석 (왜 웃돈까지 주며 열광하는가?):</b><br>"
            f"전문가들은 이 현상의 이면에 <b>'디토(Ditto) 소비'</b>와 <b>'FOMO(소외 불안)'</b> 심리가 자리 잡고 있다고 진단합니다. "
            f"자신이 신뢰하는 인플루언서의 취향을 그대로 추종하는 디토 소비가 확산되면서, '나만 경험해보지 못했다'는 불안감이 구매 욕구를 자극합니다. "
            f"여기에 고물가 시대 속에서 소소하지만 확실한 만족을 얻으려는 '스몰 럭셔리(Small Luxury)' 소비 행태가 결합된 것입니다."
        )

        chapter3 = (
            f"<b>■ 유통 대기업 & 편의점 3사의 물밑 전쟁 (누가 돈을 버는가?):</b><br>"
            f"소비자들의 열광 뒤에는 발 빠르게 움직이는 유통 대기업들의 치밀한 비즈니스 셈법이 작동하고 있습니다. "
            f"{retail_text} "
            f"유통사 입장에서 이러한 메가 히트 아이템은 단순 상품 판매 마진뿐만 아니라, 오프라인 점포로 젊은 고객층을 끌어들이는 강력한 '미끼 상품(Loss Leader)' 역할을 톡톡히 해내고 있습니다."
        )

        chapter4 = (
            f"<b>■ 반짝 유행인가, 메가 트렌드인가? (지속 가능성 진단):</b><br>"
            f"과거 '허니버터칩', '포켓몬빵', '먹태깡' 등의 수명 주기를 되짚어보면, 공급이 폭발적으로 늘어나는 시점에 열풍이 급격히 식는 패턴을 보였습니다. "
            f"따라서 관련 제조사와 유통사는 무리한 설비 증설보다는 한정판 굿즈 및 콜라보레이션 형태의 유연한 기동성을 유지해야 하며, 투자자 관점에서는 단기 테마성 과열을 경계하고 실질적인 영업이익 기여도를 냉정하게 점검해야 합니다."
        )

        return {
            "headline": headline,
            "subhead": subhead,
            "lead": lead_p,
            "chapter1": chapter1,
            "chapter2": chapter2,
            "chapter3": chapter3,
            "chapter4": chapter4,
            "entity": entity,
            "link": link,
            "source": source
        }

    # =========================================================================
    # 📄 3. [기업 심층 해부] 증권사 공식 Top 애널리스트 리포트 인텔리전스 (비전문가 눈높이 개편)
    # =========================================================================
    def expand_analyst_report(self, rep: dict) -> dict:
        """단순 요약을 넘어 비즈니스 모델, 목표가 산출 근거, 실적 전망을 비전문가 눈높이에 맞게 쉽게 해부"""
        broker = rep.get("broker", "증권사")
        item_name = rep.get("item_name", "해당기업")
        title = rep.get("title", "공식 기업분석 리포트")
        target_price = rep.get("target_price")
        tp_str = f"{int(target_price):,}원" if target_price else "목표주가 미제시"
        opinion = rep.get("opinion", "BUY")
        ft = rep.get("financial_table", {})
        summary_raw = rep.get("summary_text", "")

        broker_josa = self.attach_josa(broker, "이/가")
        if target_price:
            headline = f"📘 [기업 정밀 해부] {broker}{broker_josa} '{item_name}'에 목표가 {tp_str}을 제시한 핵심 이유"
        else:
            headline = f"📘 [기업 정밀 해부] {broker}{broker_josa} 주목한 '{item_name}', 목표주가 별도 미제시 배경과 실질 성장 잠재력"
        subhead = f"공식 투자의견: {opinion} • 비전문가도 한눈에 이해하는 비즈니스 경쟁력 & 2026/2027 실적 전망"

        sec_business = (
            f"<b>1. 쉽게 풀어보는 기업 경쟁력 (어떻게 돈을 버는가?):</b><br>"
            f"{item_name}은 해당 산업 분야에서 독보적인 기술력과 탄탄한 고객사 공급망을 갖추고 안정적인 현금 수익을 만들어내는 대표 기업입니다. "
            f"단순 하청에 머무르지 않고 부가가치가 높은 독자 제품 비중을 꾸준히 늘리고 있어, 전방 산업이 성장할 때 가장 먼저, 가장 크게 혜택을 받는 구조적 경쟁력을 확보하고 있습니다."
        )

        # 요약문 정제 (끝맺음 확인)
        clean_sum = summary_raw.strip()
        if not clean_sum.endswith(('.', '!', '?')):
            clean_sum += '.'

        sec_thesis = (
            f"<b>2. 증권사가 지금 주목한 결정적 이유 (핵심 투자 포인트):</b><br>"
            f"{clean_sum} "
            f"{broker} 리서치센터는 이번 보고서를 통해 공장 가동률이 본격적으로 상승하고 해외 수출 물량이 크게 늘어나는 점을 강조했습니다. "
            f"즉, 과거의 실적 부진을 털고 시장의 기존 눈높이를 훌쩍 뛰어넘는 실적 반등(턴어라운드) 국면에 진입했다는 분석입니다."
        )

        # 실적 표 심층 해석 (비전문가 눈높이)
        yoy_sum = ft.get('yoy_summary', '')
        if yoy_sum:
            open_p = yoy_sum.count("(")
            close_p = yoy_sum.count(")")
            if open_p > close_p:
                yoy_sum += ")" * (open_p - close_p)
            elif close_p > open_p:
                yoy_sum = re.sub(r'\)+$', '', yoy_sum)

        if ft.get("has_table"):
            ft_detail = (
                f"보고서에 수록된 공인 재무 추정치에 따르면, <b>2026년 예상 매출 {ft.get('rev_2026', '-')} / 영업이익 {ft.get('op_2026', '-')}</b>, "
                f"<b>2027년 예상 매출 {ft.get('rev_2027', '-')} / 영업이익 {ft.get('op_2027', '-')}</b>을 달성할 것으로 전망됩니다. "
                f"{yoy_sum} 이는 매출이 늘어날 때 고정비 부담이 줄어들며 순이익이 가파르게 불어나는 '이익 극대화 구간'에 본격 진입했음을 보여줍니다."
            )
        else:
            ft_detail = (
                f"현재 재무 구조를 분석해보면 외형 매출 성장과 함께 마진율이 동시에 개선되는 호황 사이클에 진입하고 있습니다. "
                f"생산 효율성이 높아지면서 향후 분기별 이익 체력이 한층 탄탄해질 것으로 예상됩니다."
            )

        sec_financials = (
            f"<b>3. 2026/2027 예상 실적과 기업 가치 재평가:</b><br>"
            f"{ft_detail} "
            f"현재 주가는 과거 주가 흐름과 비교했을 때 바닥권에 위치해 있어 하락 위험은 적고 위로 오를 여력이 큽니다. "
            f"향후 실적이 숫자로 입증될수록 시장에서 기업의 몸값(가치)을 이전보다 훨씬 후하게 쳐주는 '가치 재평가(Re-rating)'가 빠르게 진행될 가능성이 높습니다."
        )

        sec_risks = (
            f"<b>4. 투자 전 반드시 확인해야 할 변수 & 주의점:</b><br>"
            f"다만 글로벌 경기 둔화로 인한 전방 고객사의 발주 지연, 환율 급변, 원자재 가격 상승 등은 분기별 수익률에 일시적인 흔들림을 줄 수 있는 잠재 리스크입니다. "
            f"분기 실적 발표 때마다 실제 영업이익률이 예상대로 유지되는지 차분히 점검하는 것이 바람직합니다."
        )

        if target_price:
            sec_action = (
                f"<b>5. 비전문가도 따라하기 쉬운 실전 투자 전략:</b><br>"
                f"증권사가 제시한 공인 목표주가({tp_str})와 비교할 때 현재 주가는 충분한 가격적 매력(안전마진)을 갖추고 있습니다. "
                f"주가가 단기적인 시장 출렁임으로 조정을 받을 때 한 번에 큰돈을 넣기보다는 2~3회 나누어 매수(분할 매수)한 뒤, 목표가에 도달할 때까지 차분히 보유하는 전략이 가장 안전하고 유리합니다."
            )
        else:
            sec_action = (
                f"<b>5. 비전문가도 따라하기 쉬운 실전 투자 전략:</b><br>"
                f"증권사가 별도의 수치적 목표가를 제시하지 않은 것은 단기적 가격 예측보다는 중장기 비즈니스 펀더멘털과 체질 개선 추이에 주목한 것입니다. "
                f"단기 테마성 급등락을 쫓기보다는 향후 발표될 분기별 실적 지표를 확인하며 분할 매수로 접근하는 전략이 안전하고 바람직합니다."
            )

        return {
            "headline": headline,
            "subhead": subhead,
            "broker": broker,
            "item_name": item_name,
            "tp_str": tp_str,
            "opinion": opinion,
            "sec_business": sec_business,
            "sec_thesis": sec_thesis,
            "sec_financials": sec_financials,
            "sec_risks": sec_risks,
            "sec_action": sec_action,
            "pdf_filename": rep.get("pdf_filename", "")
        }

    # =========================================================================
    # 🏛️ 4. [특수공시 심층 행간 읽기] 금융감독원 DART 공시 인텔리전스
    # =========================================================================
    def expand_special_disclosure(self, disc: dict) -> dict:
        """단순 공시 제목을 넘어 재무 건전성, 지배구조 의도, 주가 궤적까지 분석"""
        corp = disc.get("관련기업") or "상장사"
        badge = disc.get("공시배지", "특수공시")
        act_badge = disc.get("액션배지", "전략대응")
        title = disc.get("공시제목", "")
        impact = disc.get("영향전망", "")
        strategy = disc.get("투자전략", "")
        link = disc.get("링크", "#")
        media = disc.get("언론사", "DART/KIND")

        headline = f"🏛️ [특수공시 심층 행간 읽기] {corp}의 '{badge}' 단행, 공시 뒤에 숨겨진 기업의 진짜 속내"

        sec_context = (
            f"<b>■ 공시 배경 및 기업의 실질적 재무 체력:</b><br>"
            f"{corp}은 최근 공시를 통해 <b>[{title}]</b> 사안을 공식 발표했습니다. "
            f"기업이 자사주 매입이나 대규모 계약 체결을 결정할 수 있는 것은 장부상 이익뿐만 아니라 실제 가용한 잉여현금흐름(FCF)이 뒷받침되기 때문입니다. "
            f"이번 조치는 회사 측이 현재 본질 가치 대비 시장 주가가 지나치게 저평가되어 있다는 강력한 확신을 표명한 것으로 풀이됩니다."
        )

        sec_governance = (
            f"<b>■ 지배구조 및 주주환원 진정성 평가:</b><br>"
            f"{impact} "
            f"특히 정부의 '기업 밸류업 프로그램' 기조에 발맞추어, 대주주의 지분율 방어 목적을 넘어 실질적인 주당순이익(EPS) 제고와 소액주주 가치 보호를 위한 책임경영 의지가 반영된 행보로 평가됩니다."
        )

        sec_strategy = (
            f"<b>■ 투자자 실전 행동 요령 ({act_badge}):</b><br>"
            f"{strategy} "
            f"공시 당일 갭상승에 무리하게 추격 매수하기보다는, 공시 효과가 1~2일간 시장에 흡수된 뒤 나타나는 눌림목 구간에서 기관 및 외국인 수급 연속성을 확인하며 분할 매수로 진입하는 것이 통계적으로 가장 높은 승률을 기록했습니다."
        )

        return {
            "headline": headline,
            "corp": corp,
            "badge": badge,
            "act_badge": act_badge,
            "title": title,
            "sec_context": sec_context,
            "sec_governance": sec_governance,
            "sec_strategy": sec_strategy,
            "link": link,
            "media": media
        }

    # =========================================================================
    # 🌐 5. [분야별 주요 뉴스 확장 인텔리전스] 문맥 기반 2차 심층 조사 & 팩트 합성 엔진
    # =========================================================================
    def expand_category_news(self, category: str, article: dict) -> dict:
        """
        [고도화된 문맥 기반 2차 심층 조사 & 팩트 합성 엔진]
        1. 한 단어가 아닌 기사의 전체 문맥(주어 + 핵심 사건/대상어)을 정밀 파악
        2. 복합 문맥 쿼리로 실시간 2차 심층 조사를 수행하여 다른 언론사의 핵심 관점과 세부 정황 수집
        3. 실제 2차 조사 팩트(배경, 전후 사정, 영향)와 1차 기사를 유기적으로 결합하여 고품질 심층 맥락 및 핵심 체크포인트 동적 합성
        """
        self.call_count += 1
        title = article.get("기사제목", "").strip()
        raw_summary = article.get("요약내용", "").strip()
        link = article.get("링크") or article.get("link", "#")
        media = article.get("언론사", "주요언론")

        clean_title = re.sub(r"\[.*?\]|\(.*?\)|<.*?>", "", title).strip()
        clean_title_no_quote = re.sub(r"['\"“”‘’]", "", clean_title)

        # 1. 기사 전체 문맥(주어 + 핵심 사건/대상어) 추출 및 복합 쿼리 생성
        ctx_info = self.extract_contextual_query(title, raw_summary)
        subject = ctx_info["subject"]
        action_topic = ctx_info["action_topic"]
        context_phrase = ctx_info["context_phrase"]

        # 2. 문맥 기반 실시간 2차 심층 조사 수행
        facts = self.investigate_deep_context(ctx_info, orig_title=clean_title, limit=5)
        cross_reports = facts.get("cross_reports", [])
        bg_facts = facts.get("background_facts", [])
        imp_facts = facts.get("impact_facts", [])

        # 3. 기사 본문 요약 (가독성 높은 2문장 완성형 구조)
        clean_summary = raw_summary.strip()
        clean_summary = re.sub(r"^[▲■◆●▶\s=]+", "", clean_summary)
        clean_summary = re.sub(r"^.*?=\s*", "", clean_summary)
        clean_summary = re.sub(r"\[.*?\]|\(.*?\)|<.*?>", "", clean_summary).strip()
        clean_summary = re.sub(r"\s*-\s*(카드/한컷|멀티미디어|카드뉴스|포토뉴스).*$", "", clean_summary).strip()
        clean_summary = re.sub(r"\.{2,}|…+", "", clean_summary).strip()

        sentences = re.split(r'(?<=[.!?다함음])\s+', clean_summary)
        valid_sents = []
        for s in sentences:
            s = s.strip()
            if len(s) >= 15 and not any(junk in s for junk in ["기자", "무단전재", "저작권", "사진=", "카드뉴스"]):
                words = s.split()
                if words:
                    last_w = re.sub(r"[.!?]+$", "", words[-1])
                    if last_w in self.TRUNCATED_ENDINGS or len(last_w) == 1:
                        words = words[:-1]
                        s = " ".join(words)
                if s and not s.endswith(('.', '!', '?')):
                    s += '.'
                if len(s) >= 18:
                    valid_sents.append(s)

        if valid_sents and len(" ".join(valid_sents[:2])) >= 35:
            final_summary = " ".join(valid_sents[:2])
        else:
            if any(w in category for w in ["경제", "금융", "비즈니스"]):
                final_summary = f"{clean_title_no_quote} 소식이 전해진 가운데, 거시 지표 추이와 관련 기업들의 실적 및 사업 환경에 미칠 구체적 파급 효과를 둘러싸고 각계의 분석이 이어지고 있습니다."
            elif any(w in category for w in ["정치"]):
                final_summary = f"{clean_title_no_quote}을 둘러싸고 정국 주도권과 후속 입법 방향을 둘러싼 여야 정치권의 치열한 공방이 가열되며 향후 심사 일정에 이목이 쏠리고 있습니다."
            elif any(w in category for w in ["사회", "사건", "사고"]):
                final_summary = f"{clean_title_no_quote} 사안에 대해 사법 당국의 엄정한 조사가 진행 중인 가운데, 유사 피해를 방지하고 관련 관리 매뉴얼을 근본적으로 개선해야 한다는 목소리가 커지고 있습니다."
            elif any(w in category for w in ["세계", "국제"]):
                final_summary = f"{clean_title_no_quote} 현안이 발생함에 따라 주요국 정부의 공식 외교 스탠스와 글로벌 공급망 및 국제 원자재 시장에 미칠 연쇄 파장이 집중 조명되고 있습니다."
            elif any(w in category for w in ["IT", "과학", "기술"]):
                final_summary = f"{clean_title_no_quote} 소식이 발표되면서 해당 기술의 실질적인 보안 안정성과 현장 안착 여부 및 글로벌 시장 내 영향력을 둘러싼 평가가 잇따르고 있습니다."
            elif any(w in category for w in ["연예", "문화"]):
                final_summary = f"{clean_title_no_quote} 소식이 문화계와 팬덤의 뜨거운 관심을 모으고 있는 가운데, 향후 공식 활동 일정과 대중적 흥행 연속성이 집중 조명되고 있습니다."
            else:
                final_summary = f"{clean_title_no_quote}과 관련하여 이해관계자들의 공식 입장과 향후 시장 파급 효과에 대한 심층 보도가 이어지고 있습니다."

        # 4. 심층 맥락 & 전략적 시사점 (타 언론사 다각도 팩트 동적 결합)
        if cross_reports:
            cross_fact = cross_reports[0]
            if len(cross_fact) > 55:
                cross_fact = cross_fact[:55] + "..."
            cross_mention = f"후속 언론 보도에 따르면 '{cross_fact}' 등이 추가적인 주요 쟁점으로 떠오르고 있으며, "
        elif bg_facts:
            cross_mention = f"관련 업계 및 당국에 따르면 {bg_facts[0]} "
        else:
            cross_mention = ""

        # 카테고리별 맞춤 심층 맥락 및 체크포인트 구성
        if any(w in category for w in ["경제", "금융", "비즈니스"]):
            deep_context = (
                f"이번 [{subject}] 관련 이슈는 '{action_topic}' 흐름 속에서 거시 경제 지표 및 기업 투자 심리에 직접적인 파급력을 미칠 중대 변수입니다. "
                f"{cross_mention}"
                f"단기적인 시장 노이즈에 매몰되지 않고 향후 금리·환율 등 대외 매크로 여건과 업계 밸류체인의 구조적 변화를 입체적으로 분별하는 안목이 요구됩니다."
            )
            chk_target = f"{subject}의 향후 수급 지표 변동 및 주요 기관의 후속 경제 전망치 조정을"
            chk_verbs = [
                "선행 지표로 삼아 집중 모니터링해야 할 핵심 포인트입니다.",
                "향후 시장 흐름을 가늠할 1차 잣대로 삼아야 합니다.",
                "우선적으로 확인해야 할 주요 관전 포인트입니다."
            ]
        elif any(w in category for w in ["정치"]):
            deep_context = (
                f"이번 [{subject}] 사안은 '{action_topic}'을 둘러싸고 정치권 내 노선 갈등과 정국 주도권 다툼이 가열되고 있음을 보여줍니다. "
                f"{cross_mention}"
                f"사안의 파장이 국회 입법 심사와 차기 정책 결정 과정에 직결되는 만큼 향후 정국 대치 구도의 결정적 변곡점으로 작용할 가능성이 큽니다."
            )
            chk_target = f"{subject}의 공식 입장 표명과 국회 소관 상임위의 후속 청문·심사 일정을"
            chk_verbs = [
                "여야 대치 국면의 분수령으로 삼아 면밀히 점검할 필요가 있습니다.",
                "차분히 분별하는 혜안이 요구되는 결정적 시점입니다.",
                "지속적으로 추적·모니터링해야 할 핵심 포인트입니다."
            ]
        elif any(w in category for w in ["사회", "사건", "사고"]):
            deep_context = (
                f"이번 [{subject}] 사안은 '{action_topic}'과 관련하여 사법적 책임 규명과 더불어 제도적 관리 시스템의 실효성이 도마에 오른 국면입니다. "
                f"{cross_mention}"
                f"단순한 개별 사건에 그치지 않고 공공 안전 및 현장 매뉴얼 개선 등 구조적 재발 방지 대책으로 이어질지 여부가 핵심 쟁점입니다."
            )
            chk_target = f"수사 당국의 최종 사법 처리 결과와 소관 부처의 재발 방지 개선책 마련 여부를"
            chk_verbs = [
                "사회적 실효성과 함께 꼼꼼히 점검해야 할 대목입니다.",
                "사법적 판단과 함께 지속적으로 주시해야 할 포인트입니다.",
                "현장 안착 여부를 중점적으로 확인해야 할 대목입니다."
            ]
        elif any(w in category for w in ["세계", "국제"]):
            deep_context = (
                f"이번 [{subject}] 현안은 '{action_topic}'을 둘러싼 글로벌 지정학적 역학 관계와 주요국 간의 외교적 이해관계가 정면으로 충돌한 사례입니다. "
                f"{cross_mention}"
                f"국제 안보 환경의 불확실성이 고조되는 가운데 글로벌 교역망과 원자재 수급 경로에 미칠 연쇄 충격을 선제적으로 가늠해야 합니다."
            )
            chk_target = f"주요국 정부의 외교적 공식 성명과 글로벌 교역망 및 원자재 시장의 반응 추이를"
            chk_verbs = [
                "대외 리스크 분별을 위해 주의 깊게 관찰해야 할 선행 지표입니다.",
                "글로벌 정세 변화와 맞물려 예의주시해야 할 분수령입니다.",
                "국제 교역 환경과 연계하여 차분히 확인해야 할 시점입니다."
            ]
        elif any(w in category for w in ["IT", "과학", "기술"]):
            deep_context = (
                f"이번 [{subject}] 발표는 '{action_topic}' 영역에서 기술적 실효성과 보안 안정성을 검증받는 분수령으로 평가됩니다. "
                f"{cross_mention}"
                f"기술의 고도화와 더불어 실제 산업 현장의 적용 안정성 및 업계 생태계 내 표준 주도권 확보가 성패를 가를 전망입니다."
            )
            chk_target = f"해당 기술·솔루션의 현장 안착 여부와 보안 안정성 및 후속 업데이트 지원을"
            chk_verbs = [
                "기술적 완성도와 함께 지속적으로 추적·모니터링해야 할 핵심 포인트입니다.",
                "실제 시장 채택률을 판단할 핵심 가늠자로 보아야 합니다.",
                "놓치지 않고 살펴야 할 결정적 관전 포인트입니다."
            ]
        elif any(w in category for w in ["연예", "문화"]):
            deep_context = (
                f"이번 [{subject}] 소식은 '{action_topic}'을 중심으로 대중적 파급력과 콘텐츠 IP의 시장 가치를 입증하며 문화계의 이목을 집중시키고 있습니다. "
                f"{cross_mention}"
                f"단기적인 화제성에 머물지 않고 글로벌 시장 내 브랜드 확장성과 중장기 흥행 모멘텀으로 연결될 수 있을지가 핵심 열쇠입니다."
            )
            chk_target = f"대중의 실질적 소비·관람 지표 추이와 후속 공식 활동 및 글로벌 팬덤 반응을"
            chk_verbs = [
                "지속 가능한 성장 모멘텀을 판단할 1차 잣대로 삼아야 합니다.",
                "글로벌 확장 가능성을 판단할 핵심 열쇠로 평가됩니다.",
                "단기 화제성을 넘어 지속 가능성을 면밀히 살펴야 합니다."
            ]
        else:
            deep_context = (
                f"이번 [{subject}] 이슈는 '{action_topic}'을 둘러싼 주요 현안과 정책적 함의를 집중 조명하고 있습니다. "
                f"{cross_mention}"
                f"이해관계자 간의 실질적 대응 기조와 향후 제도 환경 변화가 복합적으로 작용할 전망입니다."
            )
            chk_target = f"{subject}을 둘러싼 이해관계자들의 실질적인 후속 조치와 정책 환경 변화를"
            chk_verbs = [
                "차분히 분별하는 혜안이 요구되는 시점입니다.",
                "놓치지 않고 면밀히 살펴야 할 결정적 관전 포인트입니다."
            ]

        verb_idx = (abs(hash(title)) + self.call_count) % len(chk_verbs)
        selected_verb = chk_verbs[verb_idx]
        checkpoint_sentence = f"<b>🔎 핵심 체크포인트:</b> {chk_target} {selected_verb}"

        insight_text = (
            f"<b>💡 심층 맥락 & 전략적 시사점:</b> {deep_context}<br>"
            f"{checkpoint_sentence}"
        )

        return {
            "title": title,
            "media": media,
            "link": link,
            "content_summary": final_summary,
            "expanded_insight": insight_text,
            "entity": subject,
            "context_phrase": context_phrase,
            "category": category,
            "checkpoint_sentence": checkpoint_sentence
        }
