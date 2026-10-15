"""
gemini_intelligence_client.py
Google Gemini 1.5 Flash 기반 정밀 인텔리전스 합성 엔진
- 가짜 템플릿(Mad-libs) 및 상투적 미사여구 전면 차단
- 15 RPM(분당 15회) 무료 티어 한도 완벽 준수를 위한 카테고리별 배치(Batch) 처리
- 1면 톱 기획특집, 2면 트렌드 르포, 3면 리포트 해부, 6대 분야 뉴스 전수 정밀 합성
"""

import json
import logging
import os
import re
import time
import requests

logger = logging.getLogger("gemini_client")

class GeminiIntelligenceClient:
    MODELS = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]

    def __init__(self, api_key: str = None):
        self.api_key = (api_key or os.environ.get("GEMINI_API_KEY", "")).strip()
        self.is_active = bool(self.api_key and len(self.api_key) >= 15)

    def is_available(self) -> bool:
        return self.is_active

    def _call_api(self, prompt: str, system_prompt: str = "", temperature: float = 0.2, as_json: bool = False, max_retries: int = 3) -> str:
        """Gemini REST API 직접 호출 (다중 모델 폴백 및 자동 지수 백오프)"""
        if not self.is_active:
            return ""

        headers = {"Content-Type": "application/json"}
        contents = [{"parts": [{"text": prompt}]}]
        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 4000,
            }
        }
        if system_prompt:
            body["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }
        if as_json:
            body["generationConfig"]["responseMimeType"] = "application/json"

        for model_name in self.MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            for attempt in range(max_retries):
                try:
                    res = requests.post(url, headers=headers, json=body, timeout=35)
                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                return parts[0].get("text", "").strip()
                    elif res.status_code in (429, 503):
                        backoff = (attempt + 1) * 5
                        print(f"   [Gemini API ({model_name})] {res.status_code} 레이트리밋 감지 -> {backoff}초 대기 후 자동 재시도...")
                        time.sleep(backoff)
                    else:
                        print(f"   [Gemini API ({model_name})] Status {res.status_code}: {res.text[:120]}")
                        break
                except Exception as e:
                    print(f"   [Gemini API ({model_name}) 통신 재시도] {e}")
                    time.sleep(2)
        return ""

    # =========================================================================
    # 📰 1. [1면 톱 기획특집] 메가 이슈 4대 챕터 심층 취재 기사 편찬
    # =========================================================================
    def expand_mega_issue(self, raw_title: str, raw_summary: str, media_count: int = 5, related_articles: list = None) -> dict:
        """수집된 다수 언론사 기사 원문을 교차 분석하여 4대 챕터의 진짜 신문 1면 기획 르포 작성"""
        if not self.is_active:
            return None

        articles_text = ""
        if related_articles:
            for idx, a in enumerate(related_articles[:5], 1):
                articles_text += f"기사 {idx}: [{a.get('언론사', '언론')}] {a.get('기사제목')}\n내용: {a.get('요약내용', '')}\n\n"

        system_prompt = (
            "당신은 대한민국 최고 수준의 경제·시사 일간지 수석 기획에디터입니다.\n"
            "상투적인 미사여구('귀추가 주목된다', '면밀한 검토가 요구된다' 등)를 절대 쓰지 마십시오.\n"
            "기사 주제(정치/사회/경제/국제/문화)의 본질에 맞는 전문적이고 날카로운 논조로 작성하십시오.\n"
            "반드시 아래 JSON 포맷으로만 응답하십시오."
        )

        prompt = f"""
다음은 오늘 대한민국 다수 언론사가 일제히 보도한 1위 메가 이슈입니다.
메인 헤드라인: {raw_title}
초기 요약: {raw_summary}
보도 언론사 수: {media_count}개사

[수집된 관련 기사들]
{articles_text}

위 사실 데이터를 바탕으로 신문 1면 톱 기획특집 기사를 다음 JSON 포맷으로 작성하십시오.
반드시 모든 내용은 주어진 사건의 구체적 사실, 당사자, 쟁점에 근거해야 합니다.

{{
  "headline": "사건의 본질을 꿰뚫는 강력한 1면 메인 헤드라인 (30자 내외)",
  "subhead": "사건의 배경과 파장을 압축한 부제목 (50자 내외)",
  "lead": "오늘 언론사들이 집중 타전한 사건의 핵심과 본 기획이 추적한 의의 (3~4문장)",
  "chapter1": "<b>■ 사건의 전말과 발단 (타임라인 & 팩트):</b> 왜 지금 이 문제가 터졌는지 발단과 경과를 구체적인 사실에 근거해 3~4문장으로 서술",
  "chapter2": "<b>■ 수면 아래의 물밑 이해관계 & 갈등 구도:</b> 정부, 기업, 정당, 시민사회 등 당사자 간의 실질적 손익 계산과 충돌 지점을 3~4문장으로 서술",
  "chapter3": "<b>■ 공개된 핵심 수치 & 객관적 데이터:</b> 기사에 언급된 예산, 피해액, 인원수, 시장 점유율 등 실질적인 팩트 수치를 3~4문장으로 서술",
  "chapter4": "<b>■ 향후 공식 일정 & 실전 관전 포인트:</b> 향후 예정된 발표, 법안 심사, 청문회, 재판 등 독자가 주시해야 할 일정과 실전 시사점을 3~4문장으로 서술",
  "value_chain": "관련 핵심 수혜 산업 및 상장 종목 3개와 각각의 구체적 비즈니스 수혜 이유 (예: 한화에어로스페이스(엔진/발사체 제작 총괄), 한국항공우주(기체 구조물 제작), 쎄트렉아이(초고해상도 위성 탑재체 공급))"
}}
"""
        res_text = self._call_api(prompt, system_prompt=system_prompt, as_json=True)
        try:
            clean_res = re.sub(r"^```json\s*|\s*```$", "", res_text.strip(), flags=re.MULTILINE)
            data = json.loads(clean_res)
            return data
        except Exception:
            return None

    # =========================================================================
    # 🛍️ 2. [2면 기획 르포] 소비 심리 & 라이프스타일 트렌드 해부
    # =========================================================================
    def expand_trend_story(self, raw_title: str, raw_summary: str, related_articles: list = None) -> dict:
        """2030 트렌드 및 소비 심리의 바이럴 경로와 비즈니스 수혜/리스크 심층 르포"""
        if not self.is_active:
            return None

        system_prompt = (
            "당신은 트렌드 분석 및 행동경제학 전문 수석 칼럼니스트입니다.\n"
            "맹목적인 편의점/PB 타령을 하지 말고, 해당 트렌드 본연의 심리와 산업적 파장을 심층 해부하십시오.\n"
            "반드시 JSON 포맷으로만 응답하십시오."
        )

        prompt = f"""
트렌드 이슈 제목: {raw_title}
내용: {raw_summary}

위 트렌드 이슈에 대해 2면 기획 르포 기사를 다음 JSON 포맷으로 작성하십시오.
각 chapter 필드에는 반드시 HTML <b> 태그의 소제목 뒤에 주어진 트렌드 사건에 대한 실제 구체적 분석 내용(3문장 이상)을 직접 작성해야 합니다. 안내 문구를 그대로 복사하지 마십시오.

{{
  "headline": "트렌드의 핵심을 짚는 날카로운 르포 헤드라인 (30자 내외)",
  "subhead": "2030 소비 심리와 산업적 파장을 압축한 부제목 (50자 내외)",
  "lead": "현상 소개 및 오픈런/품절 대란/바이럴의 현주소를 생생하게 묘사 (3~4문장)",
  "chapter1": "<b>■ 유행의 시초와 바이럴 트리거:</b> [이슈가 촉발된 온라인 커뮤니티, 숏폼, 팝업스토어 등 바이럴 경위와 대중 확산 과정을 구체적으로 3문장 서술]",
  "chapter2": "<b>■ 2030 소비 심리 & 행동 경제학 분석:</b> [디토 소비, 스몰 럭셔리, 경험 공유 욕구 등 소비자들이 지갑을 여는 심리적 기제를 3문장 서술]",
  "chapter3": "<b>■ 산업 생태계 영향 & 비즈니스 수혜:</b> [해당 브랜드, 유통 채널, 협력 중소기업 등 실질적인 수익을 창출하는 기업군과 비즈니스 모델 파장을 3문장 서술]",
  "chapter4": "<b>■ 유행 수명 주기 & 지속 가능성 진단:</b> [단기 밈이나 반짝 유행에 그칠 리스크와 지속 가능한 비즈니스로 안착하기 위한 과제를 3문장 서술]"
}}
"""
        res_text = self._call_api(prompt, system_prompt=system_prompt, as_json=True)
        try:
            clean_res = re.sub(r"^```json\s*|\s*```$", "", res_text.strip(), flags=re.MULTILINE)
            return json.loads(clean_res)
        except Exception:
            return None

    # =========================================================================
    # 📘 3. [3면 기업 심층 해부] 증권사 공식 Top 애널리스트 리포트 행간 읽기
    # =========================================================================
    def expand_analyst_report(self, rep: dict) -> dict:
        """증권사 보고서 원문과 재무제표를 바탕으로 목표가 근거와 숨은 리스크 날카롭게 해부"""
        if not self.is_active:
            return None

        broker = rep.get("broker", "증권사")
        item_name = rep.get("item_name", "기업")
        title = rep.get("title", "")
        tp = rep.get("target_price")
        tp_str = f"{int(tp):,}원" if tp else "목표주가 미제시"
        summary_raw = rep.get("summary_text", "")
        ft = rep.get("financial_table", {})

        system_prompt = (
            "당신은 독립계 리서치 하우스의 냉철한 밸류에이션 심사위원입니다.\n"
            "증권사의 낙관적 편향을 걷어내고, 투자자가 알아야 할 실질적인 전제조건과 위험요인을 지적하십시오.\n"
            "반드시 JSON 포맷으로 응답하십시오."
        )

        prompt = f"""
증권사: {broker}
종목명: {item_name}
리포트 제목: {title}
공인 목표주가: {tp_str}
투자의견: {rep.get('opinion', 'BUY')}
애널리스트 요약: {summary_raw}
재무 정보: 2026F 매출 {ft.get('rev_2026', '-')}, 영익 {ft.get('op_2026', '-')}

위 보고서를 분석하여 다음 JSON으로 작성하십시오:
{{
  "headline": "리포트의 핵심 주장과 목표가의 현실성을 요약한 타이틀",
  "subhead": "비즈니스 모델의 강점과 변곡점",
  "lead": "보고서 핵심 요지 및 현재 시장 평가 요약 (2~3문장)",
  "chapter1": "<b>■ 비즈니스 모델 및 목표주가 산출 근거:</b> 애널리스트가 목표가를 제시한 주요 성장 엔진과 수치적 근거 (3문장)",
  "chapter2": "<b>■ 보고서 행간에 숨겨진 리스크 & 달성 전제 조건:</b> 목표주가 달성을 위해 반드시 충족되어야 할 전제조건과 하방 위험 (3문장)",
  "chapter3": "<b>■ 실전 투자자 진입 판단 기준:</b> 지금 바로 진입해야 하는지, 실적 확인 후 분할 매수해야 하는지 행동 기준 (2~3문장)"
}}
"""
        res_text = self._call_api(prompt, system_prompt=system_prompt, as_json=True)
        try:
            clean_res = re.sub(r"^```json\s*|\s*```$", "", res_text.strip(), flags=re.MULTILINE)
            return json.loads(clean_res)
        except Exception:
            return None

    # =========================================================================
    # 🌐 4. [6대 분야 뉴스 전수 정밀 배치 합성] 15 RPM 한도 준수를 위한 카테고리별 일괄 처리
    # =========================================================================
    def batch_synthesize_category_news(self, category: str, items: list) -> list:
        """
        1개 분야 내의 모든 기사(5~15건)를 1번의 API 호출로 묶어 정밀 합성
        - 기사별 [기사 본문 핵심 요약] + [심층 맥락 & 파장] + [핵심 체크포인트 & 일정] 생성
        - 15 RPM 한도를 완벽히 지키면서도 모든 기사에 고유한 인사이트 부여
        """
        if not self.is_active or not items:
            return items

        system_prompt = (
            f"당신은 '{category}' 분야 전문 수석 인텔리전스 에디터입니다.\n"
            "상투적인 템플릿 문장을 배제하고, 각 기사의 실제 본문 맥락에 맞는 구체적이고 날카로운 3단 요약을 작성하십시오.\n"
            "반드시 입력된 기사 개수와 순서 그대로 JSON 배열로 반환하십시오."
        )

        chunk_size = 5
        for chunk_start in range(0, len(items), chunk_size):
            chunk = items[chunk_start:chunk_start + chunk_size]
            articles_payload = []
            for idx, it in enumerate(chunk):
                articles_payload.append({
                    "id": idx,
                    "title": it.get("기사제목", ""),
                    "source": it.get("언론사", ""),
                    "summary": it.get("요약내용", "")[:350]
                })

            prompt = f"""
다음은 '{category}' 분야의 수집된 기사 목록입니다:
{json.dumps(articles_payload, ensure_ascii=False, indent=2)}

각 기사에 대해 다음 JSON 배열 형식으로 반환하십시오.
[
  {{
    "id": 0,
    "content_summary": "기사에서 일어난 구체적 사건과 사실관계를 군더더기 없이 정확히 요약한 2~3문장",
    "context_impact": "이 사건이 왜 발생했으며 누구에게 어떤 이익이나 타격을 주는가? (구체적 이해관계자 파장 2문장)",
    "checkpoint_milestone": "독자가 기억해야 할 향후 공식 일정, 재판일, 발표일, 또는 모니터링할 핵심 수치 (1~2문장)"
  }}
]
"""
            res_text = self._call_api(prompt, system_prompt=system_prompt, as_json=True)
            try:
                clean_res = re.sub(r"^```json\s*|\s*```$", "", res_text.strip(), flags=re.MULTILINE)
                synthesized_list = json.loads(clean_res)
                
                synth_map = {item.get("id"): item for item in synthesized_list if "id" in item}
                for idx, it in enumerate(chunk):
                    if idx in synth_map:
                        s = synth_map[idx]
                        it["content_summary"] = s.get("content_summary") or it.get("요약내용", "")
                        impact = s.get("context_impact", "")
                        cp = s.get("checkpoint_milestone", "")
                        it["expanded_insight"] = f"<b>💡 심층 맥락 & 파장:</b> {impact}<br><b>🔎 핵심 체크포인트 & 일정:</b> {cp}"
            except Exception as e:
                print(f"   [Gemini {category} 배치 파싱 오류] {e}")

            # 15 RPM(분당 15회) 한도 완벽 준수를 위한 안전 간격
            time.sleep(4.5)

        return items

    # =========================================================================
    # 🎯 5. [Daily Executive Action Plan] 오늘 바쁜 독자를 위한 3대 핵심 액션 제언
    # =========================================================================
    def generate_daily_executive_action_plan(self, mega_issue: dict, market_summary: str, top_stocks: list) -> str:
        """오늘 하루 독자가 반드시 머릿속에 넣고 행동해야 할 3대 결단 도출"""
        if not self.is_active:
            return ""

        prompt = f"""
당일 1위 이슈: {mega_issue.get('기사제목', '') if mega_issue else '주요 거시경제 이슈'}
시장 상황: {market_summary}
주요 포커스 종목: {', '.join([s.get('name', '') for s in top_stocks[:3]])}

바쁜 경영자 및 투자자를 위해 오늘 하루 반드시 실행하거나 점검해야 할 핵심 행동 수칙 3가지를 도출하십시오.
HTML 형식 (<div style="..."> 1. ... 2. ... 3. ... </div>)으로 간결하고 명확하게 반환하십시오.
"""
        return self._call_api(prompt, temperature=0.3)

    # =========================================================================
    # 🏠 6. [부동산 마켓 인텔리전스] 최신 뉴스 기반 실시간 시세/금리/수급 팩트 정밀 추출
    # =========================================================================
    def analyze_real_estate(self, news_articles: list) -> dict:
        """수집된 최신 부동산 기사 팩트를 분석하여 권역별 변동률, 금리, 거래량 지표 정밀 추출"""
        if not self.is_active or not news_articles:
            return None

        system_prompt = (
            "당신은 부동산 금융 및 시장 동향 전문 수석 리서치 애널리스트입니다.\n"
            "주어진 최신 부동산/금융 뉴스 기사의 실제 보도 내용에 근거하여 한국 시장의 최신 부동산 지표를 작성하십시오.\n"
            "반드시 순수한 JSON 포맷으로만 응답하십시오."
        )

        articles_summary = "\n".join([f"- [{a.get('source', '')}] {a.get('title', '')}" for a in news_articles[:8]])

        prompt = f"""
최신 부동산 관련 뉴스 헤드라인 및 동향:
{articles_summary}

위 팩트 데이터와 최신 한국 부동산 시장 환경을 반영하여 다음 JSON 구조로 작성하십시오.
수치와 코멘트는 반드시 기사 내용과 현재 시장 상황에 부합해야 합니다.

{{
  "regional_trends": [
    {{
      "region": "서울 강남3구 (강남·서초·송파)",
      "sale_change": "+0.15%",
      "jeonse_change": "+0.10%",
      "status": "신고가 경신 지속",
      "status_color": "#16A34A",
      "summary": "핵심 랜드마크 단지 중심의 매매 동향 및 신고가 거래 흐름 요약 (1~2문장)"
    }},
    {{
      "region": "서울 마용성 (마포·용산·성동)",
      "sale_change": "+0.09%",
      "jeonse_change": "+0.08%",
      "status": "강보합세 유지",
      "status_color": "#2563EB",
      "summary": "도심 직주근접 및 전세가 상승에 따른 갭메우기 흐름 요약 (1~2문장)"
    }},
    {{
      "region": "서울 노도강 / 외곽권",
      "sale_change": "+0.01%",
      "jeonse_change": "+0.03%",
      "status": "대출규제 관망세",
      "status_color": "#D97706",
      "summary": "중저가 대출 수요 위축 및 관망세 흐름 요약 (1~2문장)"
    }},
    {{
      "region": "경기 1기 신도시 / 선도지구 (분당·평촌)",
      "sale_change": "+0.12%",
      "jeonse_change": "+0.07%",
      "status": "재건축 기대감",
      "status_color": "#16A34A",
      "summary": "선도지구 통합 재건축 후보 단지 호가 및 매물 흐름 요약 (1~2문장)"
    }},
    {{
      "region": "경기 외곽 & 인천",
      "sale_change": "-0.01%",
      "jeonse_change": "+0.02%",
      "status": "약보합 / 혼조세",
      "status_color": "#DC2626",
      "summary": "입주 물량 및 전세 수요 이동 동향 요약 (1~2문장)"
    }},
    {{
      "region": "지방 5대 광역시",
      "sale_change": "-0.03%",
      "jeonse_change": "-0.02%",
      "status": "침체 / 미분양 적체",
      "status_color": "#DC2626",
      "summary": "준공 후 미분양 부담 및 수도권과의 양극화 동향 요약 (1~2문장)"
    }}
  ],
  "mortgage_info": {{
    "fixed_rate_band": "연 3.65% ~ 4.85%",
    "variable_rate_band": "연 4.15% ~ 5.75%",
    "cofix_rate": "3.36% (신규취급액 기준)",
    "dsr_status": "2단계 스트레스 DSR (수도권 가산금리 적용)",
    "bank_policy": "시중 5대 은행 주담대 모기지보험 및 다주택자 대출 관리 기조"
  }},
  "market_metrics": {{
    "monthly_volume": "약 3,900건 (서울 아파트 기준)",
    "listing_inventory": "약 8.4만건 (매수자 우위 시장)",
    "jeonse_ratio": "54.2% (서울 평균 전세가율)",
    "bidding_ratio": "수도권 분상제 120:1 vs 지방 0.4:1 (청약 양극화)"
  }},
  "action_guides": [
    {{
      "target": "무주택자 (내집마련 실수요자)",
      "tip": "대출 한도와 금리 추세를 고려한 실전 접근 팁"
    }},
    {{
      "target": "1주택자 (상급지 갈아타기)",
      "tip": "매도 선행 원칙 등 갈아타기 실전 팁"
    }},
    {{
      "target": "투자자 (자산 배분 관점)",
      "tip": "양극화 국면 자산 압축 전략 팁"
    }}
  ]
}}
"""
        res_text = self._call_api(prompt, system_prompt=system_prompt, as_json=True)
        try:
            clean_res = re.sub(r"^```json\s*|\s*```$", "", res_text.strip(), flags=re.MULTILINE)
            data = json.loads(clean_res)
            if "regional_trends" in data and "mortgage_info" in data:
                return data
            return None
        except Exception:
            return None
