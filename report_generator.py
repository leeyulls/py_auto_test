"""
report_generator.py
수집된 데이터를 다중 시트 엑셀(.xlsx), 마크다운(.md), CSV 파일로 정갈하게 생성하는 모듈
"""

import datetime
import os
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class ReportGenerator:
    def __init__(self, output_dir=None):
        if output_dir is None:
            self.output_dir = os.path.join(os.path.dirname(__file__), "reports")
        else:
            self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_excel(self, general_news: list, market_news: list, exchange_rates: list, stock_indices: list, date_str: str) -> str:
        """구글 드라이브 업로드용 2개 시트(종합이슈, 주식/환율) 엑셀 파일 생성"""
        file_path = os.path.join(self.output_dir, f"{date_str}_데일리_이슈_및_금융동향_브리핑.xlsx")

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            # 1. 종합이슈 시트
            df_general = pd.DataFrame(general_news)
            if df_general.empty:
                df_general = pd.DataFrame([{"안내": "수집된 신규 이슈가 없습니다."}])
            df_general.to_excel(writer, sheet_name="종합이슈_브리핑", index=False)

            # 2. 주식 및 환율 동향 시트
            df_indices = pd.DataFrame(stock_indices)
            df_fx = pd.DataFrame(exchange_rates)
            df_stock_news = pd.DataFrame(market_news)

            # 지수 및 환율을 상단에 요약 배치하고, 아래에 뉴스 배치
            combined_rows = []
            if not df_indices.empty:
                combined_rows.append({"구분": "=== [국내 증시 지수] ===", "세부내용": "", "수치/등락": "", "참고": ""})
                for idx in stock_indices:
                    combined_rows.append({
                        "구분": idx["지수명"],
                        "세부내용": "현재 지수",
                        "수치/등락": f"{idx['현재지수']} ({idx['전일대비']})",
                        "참고": "실시간 마켓 데이터"
                    })
                combined_rows.append({"구분": "", "세부내용": "", "수치/등락": "", "참고": ""})

            if not df_fx.empty:
                combined_rows.append({"구분": "=== [주요 환율 정보] ===", "세부내용": "", "수치/등락": "", "참고": ""})
                for fx in exchange_rates:
                    combined_rows.append({
                        "구분": fx["통화명"],
                        "세부내용": fx["변동/기준"],
                        "수치/등락": f"{fx['환율(원)']}원",
                        "참고": "실시간 외환 데이터"
                    })
                combined_rows.append({"구분": "", "세부내용": "", "수치/등락": "", "참고": ""})

            df_summary = pd.DataFrame(combined_rows)
            df_summary.to_excel(writer, sheet_name="주식_환율_경제동향", index=False, startrow=0)

            # 주식 뉴스 테이블은 8번째 줄부터 이어서 작성
            start_row = len(combined_rows) + 2
            if not df_stock_news.empty:
                df_stock_news.to_excel(writer, sheet_name="주식_환율_경제동향", index=False, startrow=start_row)

            # 시트 서식 적용 (헤더 색상, 너비 자동 조절)
            self._style_workbook(writer.book)

        return file_path

    @staticmethod
    def _style_workbook(wb):
        """엑셀 시트 헤더 배경색 및 너비 스타일링"""
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(name="맑은 고딕", size=10, bold=True, color="FFFFFF")
        regular_font = Font(name="맑은 고딕", size=9)
        thin_border = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0")
        )

        for sheet in wb.worksheets:
            for row_idx, row in enumerate(sheet.iter_rows()):
                is_header = (row_idx == 0)
                for cell in row:
                    if is_header:
                        cell.fill = header_fill
                        cell.font = header_font
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    else:
                        cell.font = regular_font
                        cell.border = thin_border
                        if cell.column_letter in ["A", "B", "E"]:
                            cell.alignment = Alignment(horizontal="center", vertical="center")
                        else:
                            cell.alignment = Alignment(vertical="center")

            # 컬럼 자동 너비 조절
            for col in sheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.value:
                        val_str = str(cell.value)
                        # 한글 폭 고려 (한글 1자 약 1.8폭)
                        length = sum(2 if ord(c) > 127 else 1 for c in val_str[:50])
                        max_len = max(max_len, length)
                sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 65)

    def generate_markdown(self, general_news: list, market_news: list, exchange_rates: list, stock_indices: list, date_str: str) -> str:
        """구글 문서/마크다운 뷰어용 종합 브리핑 리포트 생성"""
        file_path = os.path.join(self.output_dir, f"{date_str}_데일리_이슈_및_금융동향_브리핑.md")

        lines = [
            f"# 📰 대한민국 데일리 종합 이슈 & 금융/환율 브리핑 ({date_str})",
            "",
            "> 이 리포트는 주요 사건·사회·경제·세계·연예·신상품 이슈 및 주식/환율 특화 정보를 자동 수집하여 작성되었습니다.",
            "",
            "---",
            "",
            "## 📈 1. 실시간 금융 시장 지표 (주식 & 환율)",
            "",
            "### 🇰🇷 주요 증시 지수",
            "| 지수명 | 현재 지수 | 전일 대비 등락 |",
            "| :--- | :--- | :--- |",
        ]

        for idx in stock_indices:
            lines.append(f"| {idx['지수명']} | **{idx['현재지수']}** | {idx['전일대비']} |")

        lines.extend([
            "",
            "### 💱 주요 통화 환율 (매매기준율)",
            "| 통화 | 환율 | 비고 |",
            "| :--- | :--- | :--- |",
        ])

        for fx in exchange_rates:
            lines.append(f"| {fx['통화명']} | **{fx['환율(원)']}원** | {fx['변동/기준']} |")

        lines.extend([
            "",
            "---",
            "",
            "## 💼 2. 주식·기업 발표 & 주가 영향 전망 뉴스",
            "",
            "| 구분 | 관련 기업/기관 | 기사 제목 | 영향/전망 | 언론사 |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ])

        for m in market_news:
            status_tag = f" `[{m['상태']}]`" if m['상태'] != "신규" else ""
            title_link = f"[{m['기사제목']}]({m['링크']})"
            lines.append(f"| {m['구분']}{status_tag} | **{m['관련기업/기관']}** | {title_link} | {m['영향/전망']} | {m['언론사']} |")

        lines.extend([
            "",
            "---",
            "",
            "## 🌐 3. 분야별 종합 이슈 & 핫토픽 (사회/경제/세계/연예/신상품)",
            "",
        ])

        categories = sorted(list(set(item["분야"] for item in general_news)))
        for cat in categories:
            lines.append(f"### 📌 {cat}")
            cat_items = [item for item in general_news if item["분야"] == cat]
            for item in cat_items:
                conn_info = f" *(이전 연결 이슈: {item['연결된전일이슈']})*" if item.get("연결된전일이슈") else ""
                tag = f" `[{item['상태']}]`" if item["상태"] != "신규 이슈" else ""
                lines.append(f"- **[{item['기사제목']}]({item['링크']})**{tag}{conn_info}")
                lines.append(f"  - *{item['언론사']}* | {item['요약내용']}")
            lines.append("")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return file_path
