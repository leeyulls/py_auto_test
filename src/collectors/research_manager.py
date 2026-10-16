"""
research_manager.py
증권사 공식 애널리스트 리서치 리포트 수집, 5대 지표 기반 신뢰도 점수 산출,
Top 10 공식 PDF 다운로드 및 구글 드라이브(월별 공식_리서치_PDF) 동기화 모듈
"""

import os
import re
import datetime
import requests
from bs4 import BeautifulSoup

from src.config.crawler_config import REPORTS_DIR

TIER_1_BROKERS = [
    "삼성증권", "미래에셋증권", "한국투자증권", "NH투자증권",
    "KB증권", "신한투자증권", "하나증권"
]


CORE_MARKET_LEADERS = {
    # 반도체 & AI & 전력인프라
    "삼성전자", "SK하이닉스", "한미반도체", "리노공업", "이수페타시스", "HD현대일렉트릭", "일진전기", "효성중공업", "두산에너빌리티",
    # 2차전지 & 미래소재
    "LG에너지솔루션", "POSCO홀딩스", "에코프로", "에코프로비엠", "포스코퓨처엠", "엘앤에프",
    # 바이오 & 헬스케어
    "알테오젠", "셀트리온", "삼성바이오로직스", "유한양행", "한미약품", "휴젤", "리가켐바이오", "삼천당제약",
    # 자동차 & 방산 & 조선
    "현대차", "기아", "현대모비스", "한화에어로스페이스", "현대로템", "LIG넥스원", "HD현대중공업", "삼성중공업", "한화오션",
    # 플랫폼 & IT & 통신 & 엔터
    "NAVER", "카카오", "크래프톤", "하이브", "JYP Ent.", "에스엠", "SK텔레콤", "KT", "LG유플러스",
    # 금융 & 지주 & 밸류업
    "메리츠금융지주", "KB금융", "신한지주", "하나금융지주", "삼성화재", "삼성물산",
    # K-푸드 & K-뷰티 수출 소비재
    "삼양식품", "농심", "오리온", "한국콜마", "코스맥스", "실리콘투", "아모레퍼시픽"
}


class ResearchManager:
    def __init__(self, output_dir=None, history_mgr=None):
        if output_dir is None:
            self.output_dir = REPORTS_DIR
        else:
            self.output_dir = output_dir

        self.history_mgr = history_mgr

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.list_api = "https://m.stock.naver.com/api/research/company?page={page}&pageSize=30"
        self.detail_api = "https://m.stock.naver.com/api/research/company/{research_id}"

    @staticmethod
    def _clean_filename(text: str) -> str:
        """파일명에 사용할 수 없는 특수문자 제거"""
        cleaned = re.sub(r'[\\/*?:"<>|]', "", text)
        return cleaned.strip()[:40]

    @staticmethod
    def _clean_html(raw_html: str) -> str:
        """HTML 태그 제거 및 텍스트 정제"""
        if not raw_html:
            return ""
        soup = BeautifulSoup(raw_html, "html.parser")
        text = soup.get_text(separator=" ").strip()
        return re.sub(r'\s+', ' ', text)

    @staticmethod
    def _extract_complete_sentences(raw_text: str, max_sentences: int = 3, max_chars: int = 350) -> str:
        """글자 수 임의 절단(...) 없이 완결된 문장 단위로 마침표가 찍히는 완성형 요약문 추출"""
        if not raw_text:
            return ""
        sentences = re.split(r'(?<=[.!?다함음])\s+', raw_text.strip())
        complete = []
        cur_chars = 0
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 15 or any(s_clean.startswith(prefix) for prefix in ["목표주가", "투자의견", "작성일", "발행일", "자료:"]):
                continue
            if not s_clean.endswith(('.', '!', '?')):
                s_clean += '.'
            complete.append(s_clean)
            cur_chars += len(s_clean)
            if len(complete) >= max_sentences or cur_chars >= max_chars:
                break

        if complete:
            return " ".join(complete)
        trimmed = raw_text[:250].strip()
        if trimmed and not trimmed.endswith('.'):
            trimmed += '.'
        return trimmed

    def fetch_candidate_reports(self, max_pages: int = 2) -> list:
        """최신 2개 페이지(최대 60개) 후보 리포트 목록 및 세부 정보 수집"""
        candidates = []
        raw_items = []
        for p in range(1, max_pages + 1):
            try:
                res = requests.get(self.list_api.format(page=p), headers=self.headers, timeout=8)
                if res.status_code == 200:
                    items = res.json()
                    if isinstance(items, list):
                        raw_items.extend(items)
            except Exception as e:
                print(f"[경고] 리서치 목록(p={p}) 수집 오류: {e}")

        # 상세 조회 (중복 제거)
        seen_ids = set()
        for item in raw_items:
            r_id = item.get("researchId")
            if not r_id or r_id in seen_ids:
                continue
            seen_ids.add(r_id)

            broker = item.get("brokerName", "증권사").strip()
            item_name = item.get("itemName", "").strip()
            title = item.get("title", "").strip()
            write_date = item.get("writeDate", "")

            try:
                read_count = int(item.get("readCount", 0))
            except Exception:
                read_count = 0

            # 상세 API 호출하여 attachUrl 및 본문 추출
            d_url = self.detail_api.format(research_id=r_id)
            try:
                d_res = requests.get(d_url, headers=self.headers, timeout=5)
                if d_res.status_code == 200:
                    d_data = d_res.json()
                    content_info = d_data.get("researchContent", {})
                    attach_url = content_info.get("attachUrl", "")
                    raw_content = content_info.get("content", "")
                    clean_content = self._clean_html(raw_content)
                    complete_summary = self._extract_complete_sentences(clean_content)
                    if not complete_summary:
                        complete_summary = f"{broker}에서 발행한 {item_name} 관련 공식 기업 분석 리포트입니다."

                    target_price = content_info.get("targetPrice") or item.get("targetPrice")
                    opinion = content_info.get("opinion") or item.get("opinion")
                    item_code = item.get("itemCode", "").strip()

                    candidates.append({
                        "id": r_id,
                        "broker": broker,
                        "item_name": item_name,
                        "item_code": item_code,
                        "ticker": f"{item_code}.KS" if item_code else "",
                        "title": title,
                        "write_date": write_date,
                        "read_count": read_count,
                        "attach_url": attach_url,
                        "summary_text": complete_summary,
                        "target_price": target_price,
                        "opinion": opinion or "BUY",
                    })
            except Exception:
                pass

        return candidates

    def score_credibility(self, candidates: list, active_news: list = None) -> list:
        """
        [고도화된 리서치 선정 알고리즘]
        단순 시간순이 아닌 '시장 주도주/트렌드 일치도 + 언론 집중도 + 실투자자 관심 조회수' 다차원 가중치 평가
        """
        if not candidates:
            return []

        # 당일 뉴스 언급 기업 세트 구축
        news_company_mentions = set()
        if active_news:
            for n in active_news:
                n_title = n.get("기사제목", "") + " " + n.get("제목", "") + " " + n.get("title", "")
                for leader in CORE_MARKET_LEADERS:
                    if leader in n_title:
                        news_company_mentions.add(leader)

        # 복수 커버리지 집계
        item_counts = {}
        for c in candidates:
            name = c["item_name"]
            if name:
                item_counts[name] = item_counts.get(name, 0) + 1

        # 최대 조회수 정규화 기준 (최소 500)
        max_reads = max([c["read_count"] for c in candidates] + [500])

        scored = []
        for c in candidates:
            score = 0
            breakdown = {}
            item_name = c["item_name"]

            # 1. 핵심 시장 주도주 & 트렌드 부합도 (최대 35점)
            is_market_leader = item_name in CORE_MARKET_LEADERS
            leader_score = 35 if is_market_leader else 10
            score += leader_score
            breakdown["주도주부합도"] = f"{leader_score}점 ({'핵심 주도·성장 산업군' if is_market_leader else '일반 개별종목'})"

            # 2. 당일 언론·시장 집중도 (Media Buzz) (최대 25점)
            is_in_news = item_name in news_company_mentions
            buzz_score = 25 if is_in_news else 5
            score += buzz_score
            breakdown["언론주목도"] = f"{buzz_score}점 ({'당일 주요 뉴스 이슈 결합' if is_in_news else '통상 커버리지'})"

            # 3. 실투자자 관심도 (조회수 정규화 최대 25점)
            read_cnt = c["read_count"]
            read_score = int(min(read_cnt / max_reads, 1.0) * 20) + (5 if read_cnt >= 500 else 0)
            score += read_score
            breakdown["투자자조회수"] = f"{read_score}점 (열람 {read_cnt}회)"

            # 4. 발행 증권사 공신력 (Tier 1: 15점, 전문사: 10점)
            is_tier1 = any(t in c["broker"] for t in TIER_1_BROKERS)
            broker_score = 15 if is_tier1 else 10
            score += broker_score
            breakdown["기관공신력"] = f"{broker_score}점 ({'Tier 1 대형사' if is_tier1 else '전문사'})"

            # 5. 정량 목표주가 및 모멘텀 (최대 15점)
            tp = c.get("target_price")
            has_tp = False
            try:
                if tp and int(tp) > 0:
                    has_tp = True
            except Exception:
                has_tp = bool(tp)

            tp_score = 10 if has_tp else 5
            title_text = c["title"]
            if any(w in title_text for w in ["상향", "호조", "서프라이즈", "성장", "최고 실적", "호실적", "신고가"]):
                tp_score += 5
            elif any(w in title_text for w in ["하향", "부진", "우려", "눈높이 낮춤", "적자"]):
                tp_score -= 5
            score += tp_score
            breakdown["목표가모멘텀"] = f"{tp_score}점"

            # 6. 소외 비인기주 감점 필터 (-20점)
            # 조회수가 300회 미만이고 시장 주도주도 아니며 언론 보도도 없는 경우
            if read_cnt < 300 and not is_market_leader and not is_in_news:
                score -= 20
                breakdown["소외주필터"] = "-20점 (비인기·소외 종목 감점)"

            # PDF 원문 첨부 가산점
            if c.get("attach_url"):
                score += 5

            c["credibility_score"] = score
            c["score_breakdown"] = breakdown
            c["is_tier1"] = is_tier1
            c["is_market_leader"] = is_market_leader
            scored.append(c)

        # 점수 높은 순 정렬
        scored.sort(key=lambda x: x["credibility_score"], reverse=True)

        if self.history_mgr:
            fresh_reports = []
            seen_reports = []
            for r in scored:
                if self.history_mgr.is_research_collected(r.get("item_name"), r.get("title"), str(r.get("id"))):
                    r["is_previously_featured"] = True
                    seen_reports.append(r)
                else:
                    r["is_previously_featured"] = False
                    fresh_reports.append(r)

            # 신규 미발행 리포트를 최우선 배치하고, 10건 미만일 경우 기존 리포트로 보충
            scored = fresh_reports + seen_reports

        return scored

    def _process_single_pdf(self, rep: dict, pdf_dir: str, date_str: str) -> dict:
        """단일 PDF 다운로드 및 실적 표 파싱 워커"""
        url = rep.get("attach_url")
        cur_y = datetime.date.today().year
        default_fin = {
            "year1_label": f"{cur_y}F",
            "year2_label": f"{cur_y + 1}F",
            "rev_2026": "-", "op_2026": "-", "rev_2027": "-", "op_2027": "-",
            "yoy_summary": "실적 데이터 미기재", "has_table": False
        }
        if not url:
            rep["financial_table"] = default_fin
            return rep

        broker = self._clean_filename(rep.get("broker", "증권사"))
        item = self._clean_filename(rep.get("item_name") or "산업분석")
        title = self._clean_filename(rep.get("title", "리포트"))
        filename = f"{date_str}_{broker}_{item}_{title}.pdf"
        file_path = os.path.join(pdf_dir, filename)

        rep["pdf_filename"] = filename
        rep["pdf_local_path"] = file_path

        # 이미 다운로드되어 있지 않다면 다운로드
        if not os.path.exists(file_path):
            try:
                r = requests.get(url, headers=self.headers, timeout=15)
                if r.status_code == 200 and len(r.content) > 1000:
                    with open(file_path, "wb") as f:
                        f.write(r.content)
                    rep["pdf_downloaded"] = True
                else:
                    rep["pdf_downloaded"] = False
            except Exception as e:
                print(f"[경고] PDF 다운로드 실패 ({filename}): {e}")
                rep["pdf_downloaded"] = False
        else:
            rep["pdf_downloaded"] = True

        # PDF 핵심 실적 표(예상 매출 및 영업익) 자동 발췌
        if os.path.exists(file_path):
            rep["financial_table"] = self.extract_financial_table_from_pdf(file_path)
        else:
            rep["financial_table"] = default_fin

        return rep

    def download_top_pdfs(self, top_reports: list, month_str: str, date_str: str) -> list:
        """선별된 Top 10 리포트의 공식 원본 PDF 파일 병렬 고속 다운로드 및 파싱 (5개 스레드)"""
        from concurrent.futures import ThreadPoolExecutor

        pdf_dir = os.path.join(self.output_dir, month_str, "공식_리서치_PDF")
        os.makedirs(pdf_dir, exist_ok=True)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self._process_single_pdf, rep, pdf_dir, date_str) for rep in top_reports]
            return [f.result() for f in futures]

    @staticmethod
    def extract_financial_table_from_pdf(pdf_path: str) -> dict:
        """애널리스트 PDF 원본의 1~3페이지로부터 당해/차기 예상 실적 표(매출/영업익/YoY) 자동 발췌"""
        cur_year = datetime.date.today().year
        next_year = cur_year + 1
        y1_label = f"{cur_year}F"
        y2_label = f"{next_year}F"

        default_res = {
            "year1_label": y1_label,
            "year2_label": y2_label,
            "rev_year1": "-",
            "op_year1": "-",
            "rev_year2": "-",
            "op_year2": "-",
            "rev_2026": "-",
            "op_2026": "-",
            "rev_2027": "-",
            "op_2027": "-",
            "yoy_summary": f"{cur_year}~{next_year} 연간 실적 성장세 추정",
            "has_table": False,
        }
        if not pdf_path or not os.path.exists(pdf_path):
            return default_res

        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            extracted_text = ""
            for page in reader.pages[:3]:
                extracted_text += (page.extract_text() or "") + "\n"

            # 1. 당해 및 차기년도 추정치 표 매칭
            rev_match = re.search(r'매출액[^\d\n]*([0-9,.]+)\s+([0-9,.]+)\s+([0-9,.]+)\s+([0-9,.]+)', extracted_text)
            op_match = re.search(r'영업이익[^\d\n]*([0-9,.-]+)\s+([0-9,.-]+)\s+([0-9,.-]+)\s+([0-9,.-]+)', extracted_text)
            preview_matches = re.findall(rf'(?:{cur_year}년|3Q\d\d|4Q\d\d|연결)[^\n.]{{0,80}}(?:매출액|영업이익)[^\n.]{{0,80}}(?:YoY|QoQ|원|%)[^\n.]*', extracted_text)

            rev_y1 = "-"
            rev_y2 = "-"
            op_y1 = "-"
            op_y2 = "-"
            has_table = False

            if rev_match:
                vals = rev_match.groups()
                rev_y1 = f"{vals[2]}십억원"
                rev_y2 = f"{vals[3]}십억원"
                has_table = True

            if op_match:
                vals = op_match.groups()
                op_y1 = f"{vals[2]}십억원"
                op_y2 = f"{vals[3]}십억원"
                has_table = True

            yoy_summary = preview_matches[0].strip() if preview_matches else f"{cur_year}/{next_year} 실적 성장세 및 기업가치 재평가 전망"
            yoy_summary = yoy_summary[:120].strip()
            # 괄호 짝 맞춤 보정 (열린 괄호가 닫히지 않은 경우 자동 보정)
            open_p = yoy_summary.count("(")
            close_p = yoy_summary.count(")")
            if open_p > close_p:
                yoy_summary += ")" * (open_p - close_p)
            elif close_p > open_p:
                yoy_summary = re.sub(r'\)+$', '', yoy_summary)

            return {
                "year1_label": y1_label,
                "year2_label": y2_label,
                "rev_year1": rev_y1,
                "op_year1": op_y1,
                "rev_year2": rev_y2,
                "op_year2": op_y2,
                "rev_2026": rev_y1,
                "op_2026": op_y1,
                "rev_2027": rev_y2,
                "op_2027": op_y2,
                "yoy_summary": yoy_summary,
                "has_table": has_table,
            }
        except Exception:
            return default_res


    def collect_and_process(self, date_str: str = None, top_n: int = 10, active_news: list = None) -> dict:
        """
        후보 수집 ➔ 신뢰도 점수 산출 ➔ Top 10 엄선 ➔ PDF 다운로드 일괄 실행
        """
        if date_str is None:
            date_str = datetime.date.today().strftime("%Y-%m-%d")

        month_str = date_str[:7]  # '2026-10'

        print(f"\n[리서치 관리자] 🔍 증권사 공식 리포트 후보 수집 중 (2개 페이지 전수 조사)...")
        candidates = self.fetch_candidate_reports(max_pages=2)
        print(f" - 수집된 공식 리포트 후보: {len(candidates)}건")

        print(f"[리서치 관리자] 🧮 시장 주도주/뉴스 집중도/실투자자 조회수 다차원 점수 산출 및 Top {top_n} 선별 중...")
        scored_reports = self.score_credibility(candidates, active_news=active_news)
        top_reports = scored_reports[:top_n]

        print(f"[리서치 관리자] 📥 공식 원본 PDF 다운로드 진행 중 (월별 폴더: {month_str}/공식_리서치_PDF)...")
        top_reports_with_pdf = self.download_top_pdfs(top_reports, month_str=month_str, date_str=date_str)

        downloaded_count = sum(1 for r in top_reports_with_pdf if r.get("pdf_downloaded"))
        print(f" - 공식 원본 PDF 다운로드 완료: {downloaded_count}/{len(top_reports_with_pdf)}건")

        return {
            "top_reports": top_reports_with_pdf,
            "all_scored": scored_reports,
            "month_str": month_str,
            "downloaded_count": downloaded_count,
        }
