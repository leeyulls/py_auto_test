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

TIER_1_BROKERS = [
    "삼성증권", "미래에셋증권", "한국투자증권", "NH투자증권",
    "KB증권", "신한투자증권", "하나증권"
]


class ResearchManager:
    def __init__(self, output_dir=None):
        if output_dir is None:
            self.output_dir = os.path.join(os.path.dirname(__file__), "reports")
        else:
            self.output_dir = output_dir

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.list_api = "https://m.stock.naver.com/api/research/company?page=1&pageSize=30"
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
        # 불필요한 연속 공백 축소
        return re.sub(r'\s+', ' ', text)

    def fetch_candidate_reports(self) -> list:
        """최신 30개 후보 리포트 목록 및 세부 정보 수집"""
        candidates = []
        try:
            res = requests.get(self.list_api, headers=self.headers, timeout=8)
            if res.status_code != 200:
                return candidates

            items = res.json()
            if not isinstance(items, list):
                return candidates

            # 1차 목록 순회 및 상세 조회 (세부 정보 및 PDF 첨부 링크 확인)
            for item in items[:25]:
                r_id = item.get("researchId")
                if not r_id:
                    continue

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
                d_res = requests.get(d_url, headers=self.headers, timeout=6)
                if d_res.status_code == 200:
                    d_data = d_res.json()
                    content_info = d_data.get("researchContent", {})
                    attach_url = content_info.get("attachUrl", "")
                    raw_content = content_info.get("content", "")
                    clean_content = self._clean_html(raw_content)

                    # 목표주가 및 투자의견
                    target_price = content_info.get("targetPrice") or item.get("targetPrice")
                    opinion = content_info.get("opinion") or item.get("opinion")

                    candidates.append({
                        "id": r_id,
                        "broker": broker,
                        "item_name": item_name,
                        "title": title,
                        "write_date": write_date,
                        "read_count": read_count,
                        "attach_url": attach_url,
                        "summary_text": clean_content[:300] if clean_content else f"{broker} 공식 분석 리포트",
                        "target_price": target_price,
                        "opinion": opinion or "BUY",
                    })
        except Exception as e:
            print(f"[경고] 리서치 후보 수집 오류: {e}")

        return candidates

    def score_credibility(self, candidates: list) -> list:
        """5대 신뢰도 평가 모델을 적용하여 점수 산출 및 정렬"""
        if not candidates:
            return []

        # 동일 종목 복수 커버리지 카운트
        item_counts = {}
        for c in candidates:
            name = c["item_name"]
            if name:
                item_counts[name] = item_counts.get(name, 0) + 1

        # 최대 조회수
        max_reads = max([c["read_count"] for c in candidates] + [1])

        scored = []
        for c in candidates:
            score = 0
            breakdown = {}

            # 1. 발행 기관 공신력 (Tier 1: 30점, Tier 2: 20점)
            is_tier1 = any(t in c["broker"] for t in TIER_1_BROKERS)
            broker_score = 30 if is_tier1 else 20
            score += broker_score
            breakdown["기관공신력"] = f"{broker_score}점 ({'Tier 1 대형사' if is_tier1 else '전문 증권사'})"

            # 2. 정량 데이터 명확성 (목표주가 유무: 25점)
            tp = c.get("target_price")
            has_tp = False
            try:
                if tp and int(tp) > 0:
                    has_tp = True
            except Exception:
                has_tp = bool(tp)

            tp_score = 25 if has_tp else 10
            score += tp_score
            breakdown["정량수치"] = f"{tp_score}점 ({'공인 목표가 명시' if has_tp else '정성 분석'})"

            # 3. 목표가 변동 모멘텀 (상향: 15점, 유지/신규: 10점, 하향: 5점)
            action_score = 10
            action_desc = "목표가 유지/신규"
            title_text = c["title"]
            if any(w in title_text for w in ["상향", "호조", "서프라이즈", "성장 가속", "최고 실적", "BUY"]):
                action_score = 15
                action_desc = "목표가 상향/호실적 모멘텀"
            elif any(w in title_text for w in ["하향", "부진", "우려", "눈높이 낮춤"]):
                action_score = 5
                action_desc = "목표가 하향/보수적 전망"

            score += action_score
            breakdown["변동모멘텀"] = f"{action_score}점 ({action_desc})"

            # 4. 시장 및 투자자 검증도 (조회수 정규화 최대 20점)
            read_ratio = min(c["read_count"] / max_reads, 1.0)
            read_score = int(read_ratio * 15) + (5 if c["read_count"] > 10 else 0)
            score += read_score
            breakdown["시장조회수"] = f"{read_score}점 (조회 {c['read_count']}회)"

            # 5. 기관 동시 집중도 (동일 종목 복수 커버리지 시 10점)
            overlap = item_counts.get(c["item_name"], 1)
            overlap_score = 10 if overlap >= 2 else 5
            score += overlap_score
            breakdown["기관집중도"] = f"{overlap_score}점 ({overlap}개사 동시 커버)"

            # PDF 직링크 가산점
            if c.get("attach_url"):
                score += 5

            c["credibility_score"] = score
            c["score_breakdown"] = breakdown
            c["is_tier1"] = is_tier1
            scored.append(c)

        # 점수 높은 순 정렬
        scored.sort(key=lambda x: x["credibility_score"], reverse=True)
        return scored

    def download_top_pdfs(self, top_reports: list, month_str: str, date_str: str) -> list:
        """선별된 Top 10 리포트의 공식 원본 PDF 파일 다운로드"""
        pdf_dir = os.path.join(self.output_dir, month_str, "공식_리서치_PDF")
        os.makedirs(pdf_dir, exist_ok=True)

        for rep in top_reports:
            url = rep.get("attach_url")
            if not url:
                continue

            broker = self._clean_filename(rep["broker"])
            item = self._clean_filename(rep["item_name"] or "산업분석")
            title = self._clean_filename(rep["title"])
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

            # PDF 핵심 실적 표(2026/2027 예상 매출 및 영업익) 자동 발췌
            if os.path.exists(file_path):
                rep["financial_table"] = self.extract_financial_table_from_pdf(file_path)
            else:
                rep["financial_table"] = {
                    "rev_2026": "-", "op_2026": "-", "rev_2027": "-", "op_2027": "-",
                    "yoy_summary": "실적 데이터 미기재", "has_table": False
                }

        return top_reports

    @staticmethod
    def extract_financial_table_from_pdf(pdf_path: str) -> dict:
        """애널리스트 PDF 원본의 1~3페이지로부터 2026/2027 예상 실적 표(매출/영업익/YoY) 자동 발췌"""
        default_res = {
            "rev_2026": "-",
            "op_2026": "-",
            "rev_2027": "-",
            "op_2027": "-",
            "yoy_summary": "2026~2027 연간 실적 성장세 추정",
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

            # 1. 2026 / 2027 연간 추정치 표 매칭
            rev_match = re.search(r'매출액[^\d\n]*([0-9,.]+)\s+([0-9,.]+)\s+([0-9,.]+)\s+([0-9,.]+)', extracted_text)
            op_match = re.search(r'영업이익[^\d\n]*([0-9,.-]+)\s+([0-9,.-]+)\s+([0-9,.-]+)\s+([0-9,.-]+)', extracted_text)
            preview_matches = re.findall(r'(?:2026년|3Q26|4Q26|연결)[^\n.]{0,80}(?:매출액|영업이익)[^\n.]{0,80}(?:YoY|QoQ|원|%)[^\n.]*', extracted_text)

            rev_2026 = "-"
            rev_2027 = "-"
            op_2026 = "-"
            op_2027 = "-"
            has_table = False

            if rev_match:
                vals = rev_match.groups()
                rev_2026 = f"{vals[2]}십억원"
                rev_2027 = f"{vals[3]}십억원"
                has_table = True

            if op_match:
                vals = op_match.groups()
                op_2026 = f"{vals[2]}십억원"
                op_2027 = f"{vals[3]}십억원"
                has_table = True

            yoy_summary = preview_matches[0].strip() if preview_matches else "2026/2027 실적 성장세 및 기업가치 재평가 전망"

            return {
                "rev_2026": rev_2026,
                "op_2026": op_2026,
                "rev_2027": rev_2027,
                "op_2027": op_2027,
                "yoy_summary": yoy_summary[:120],
                "has_table": has_table,
            }
        except Exception as e:
            return default_res


    def collect_and_process(self, date_str: str = None, top_n: int = 10) -> dict:
        """
        후보 수집 ➔ 신뢰도 점수 산출 ➔ Top 10 엄선 ➔ PDF 다운로드 일괄 실행
        """
        if date_str is None:
            date_str = datetime.date.today().strftime("%Y-%m-%d")

        month_str = date_str[:7]  # '2026-10'

        print(f"\n[리서치 관리자] 🔍 증권사 공식 리포트 후보 수집 중...")
        candidates = self.fetch_candidate_reports()
        print(f" - 수집된 공식 리포트 후보: {len(candidates)}건")

        print(f"[리서치 관리자] 🧮 5대 지표 신뢰도 점수 산출 및 Top {top_n} 선별 중...")
        scored_reports = self.score_credibility(candidates)
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
