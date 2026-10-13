"""
report_generator.py
7대 분야별 데이터(정치, 사회, 거시경제, 주식, 세계, IT, 연예) 및
주가 분석 & 매수/매도 추천 다중 시트 엑셀 및 마크다운 리포트 생성기
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

    def generate_excel(self, general_news: list, market_news: list, exchange_rates: list, stock_indices: list, stock_advice: dict, date_str: str) -> str:
        """3개 시트(7대 분야 종합이슈, 주식/환율 및 리서치, 종목분석/매매추천) 엑셀 생성"""
        file_path = os.path.join(self.output_dir, f"{date_str}_데일리_이슈_및_금융동향_브리핑.xlsx")

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            # 1. 7대 분야 종합이슈 시트
            df_general = pd.DataFrame(general_news)
            if df_general.empty:
                df_general = pd.DataFrame([{"안내": "수집된 신규 이슈가 없습니다."}])
            else:
                # 불필요한 내부 키 제거
                cols = [c for c in ["분야", "상태", "기사제목", "요약내용", "언론사", "링크", "발행일시"] if c in df_general.columns]
                df_general = df_general[cols]
            df_general.to_excel(writer, sheet_name="7대분야_종합이슈", index=False)

            # 2. 주식 및 환율 동향 & 증권사 리서치 시트
            df_indices = pd.DataFrame(stock_indices)
            df_fx = pd.DataFrame(exchange_rates)
            df_stock_news = pd.DataFrame(market_news)

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

            start_row = len(combined_rows) + 2
            if not df_stock_news.empty:
                cols = [c for c in ["구분", "상태", "관련기업/기관", "기사제목", "영향/전망", "언론사", "요약", "링크"] if c in df_stock_news.columns]
                df_stock_clean = df_stock_news[cols]
                df_stock_clean.to_excel(writer, sheet_name="주식_환율_경제동향", index=False, startrow=start_row)

            # 3. 종목분석 및 매수/매도 추천 시트
            if stock_advice and "all_evaluations" in stock_advice:
                df_advice = pd.DataFrame(stock_advice["all_evaluations"])
                df_advice.to_excel(writer, sheet_name="종목분석_매매추천", index=False)

            self._style_workbook(writer.book)

        return file_path

    @staticmethod
    def _style_workbook(wb):
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

            for col in sheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.value:
                        val_str = str(cell.value)
                        length = sum(2 if ord(c) > 127 else 1 for c in val_str[:50])
                        max_len = max(max_len, length)
                sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 65)

    def generate_markdown(self, general_news: list, market_news: list, exchange_rates: list, stock_indices: list, stock_advice: dict, news_result: dict, date_str: str) -> str:
        """구글 문서/마크다운 뷰어용 종합 브리핑 리포트 생성"""
        file_path = os.path.join(self.output_dir, f"{date_str}_데일리_이슈_및_금융동향_브리핑.md")

        lines = [
            f"# 📰 대한민국 데일리 종합 이슈 & 주가 분석/매매 추천 브리핑 ({date_str})",
            "",
            "> 7대 핵심 분야(정치, 사회, 거시경제, 주식, 세계, IT, 연예)별 대표 헤드라인과 실시간 주가·환율·기술적 지표 및 뉴스 모멘텀 결합 매매 추천 리포트입니다.",
            "",
            "---",
            "",
        ]

        # 🔥 메가 핫토픽
        mega = news_result.get("mega_issue")
        if mega:
            lines.extend([
                f"## 🔥 오늘의 메가 핫토픽: [언론사 {mega['media_count']}개사 집중 보도]",
                f"### **[{mega['기사제목']}]({mega['링크']})** ({mega['언론사']})",
                f"> 💡 **1줄 핵심 요약**: {mega['요약내용']}",
                "",
                "---",
                "",
            ])

        # 🎯 오늘의 핵심 주식 매매 추천
        lines.append("## 🎯 1. 오늘의 핵심 주식 매매 추천 (Action Signals)\n")
        today_buys = stock_advice.get("today_buy_picks", [])
        lines.append("### 🟢 [오늘 사면 좋을 주식 - 단기 반등 / 모멘텀 매수]")
        if today_buys:
            for b in today_buys:
                lines.append(f"- **{b['name']}** ({b['ticker']}) - 현재가: `{b['price']}`")
                lines.append(f"  - 💡 **추천 근거**: {b['reason']}")
        else:
            lines.append("- 현재 기준 극단적 단기 과매도 또는 돌파 종목 없음 (보수적 접근 추천)")
        lines.append("")

        long_buys = stock_advice.get("longterm_buy_picks", [])
        lines.append("### ⭐ [장기적으로 사면 좋을 주식 - 성장 주도주 분할 매수]")
        if long_buys:
            for lb in long_buys:
                lines.append(f"- **{lb['name']}** ({lb['ticker']}) - 현재가: `{lb['price']}`")
                lines.append(f"  - 💡 **선정 근거**: {lb['reason']}")
        else:
            lines.append("- 고점 과열 또는 추세 조정 중인 종목이 많아 관망 추천")
        lines.append("")

        sells = stock_advice.get("sell_warning_picks", [])
        lines.append("### 🔴 [주의 / 팔면 좋은 주식 - 과열 차익실현 & 리스크 관리]")
        if sells:
            for s in sells:
                lines.append(f"- **{s['name']}** ({s['ticker']}) - `[{s['type']}]`")
                lines.append(f"  - ⚠️ **경고 사유**: {s['reason']}")
        else:
            lines.append("- 현재 과열권 진입 종목 또는 급격한 악재 종목 없음")
        lines.append("")

        # 2. 주요 종목별 상세 기술 지표 표
        lines.extend([
            "---",
            "",
            "## 📊 2. 주요 종목별 상세 기술 지표 및 매매 신호 분석표",
            "",
            "| 종목명 (섹터) | 현재가 (등락률) | RSI(14) | 20일선 이격도 | 52주 위치 | 단기 신호 | 장기 신호 | 핵심 이유 |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])

        for ev in stock_advice.get("all_evaluations", []):
            lines.append(
                f"| **{ev['종목명']}**<br>({ev['섹터']}) | {ev['현재가']}<br>({ev['전일대비']}) | "
                f"{ev['RSI(14)']} | {ev['20일선이격도']} | {ev['52주위치']} | "
                f"{ev['단기신호']} | {ev['장기신호']} | {ev['단기근거']} |"
            )

        # 3. 실시간 시장 지표
        lines.extend([
            "",
            "---",
            "",
            "## 📈 3. 실시간 금융 시장 지표 (증시 & 환율)",
            "",
            "### 🇰🇷 주요 증시 지수",
            "| 지수명 | 현재 지수 | 전일 대비 등락 |",
            "| :--- | :--- | :--- |",
        ])

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

        # 4. 7대 분야별 대표 헤드라인
        lines.extend([
            "",
            "---",
            "",
            "## 🌐 4. 7대 분야별 핵심 헤드라인",
            "",
        ])

        top_picks = news_result.get("category_top_picks", {})
        for cat, item in top_picks.items():
            if item:
                tag = f" `[{item['상태']}]`" if "집중" in item['상태'] else ""
                lines.append(f"### 📌 {cat}{tag}")
                lines.append(f"- **[{item['기사제목']}]({item['링크']})** ({item['언론사']})")
                lines.append(f"  - 💡 *1줄 요약*: {item['요약내용']}\n")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return file_path
