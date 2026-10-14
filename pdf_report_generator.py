"""
pdf_report_generator.py
Microsoft Edge Headless 인쇄 엔진을 활용한 초고해상도 A4 정식 PDF 보고서 자동 편찬 모듈
1. 데일리 심층 종합분석 보고서 (6~8페이지: 도표, 주가 변화 SVG 차트, 2차 조사 자료 전면 수록)
2. 주간 글로벌 금융시장 및 전략 백서 (12~15페이지: 정식 표지, 목차, 챕터별 종합 결산 수록)
"""

import os
import sys
import re
import html
import datetime
import subprocess

try:
    from intelligence_dossier_engine import IntelligenceDossierEngine
except ImportError:
    IntelligenceDossierEngine = None

# Windows cp949 인코딩 에러 방지
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def safe_print(msg: str):
    """Windows 콘솔 인코딩 에러를 방지하는 안전 출력 함수"""
    try:
        print(msg)
    except Exception:
        try:
            print(msg.encode("ascii", errors="replace").decode("ascii"))
        except Exception:
            pass


class PdfReportGenerator:
    def __init__(self, edge_path=None):
        if edge_path and os.path.exists(edge_path):
            self.edge_path = edge_path
        else:
            candidates = [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
            self.edge_path = next((p for p in candidates if os.path.exists(p)), None)

    @staticmethod
    def generate_svg_sparkline(prices: list, width: int = 140, height: int = 34) -> str:
        """주가 배열을 바탕으로 아름다운 벡터 인라인 SVG 스파크라인 차트 생성"""
        if not prices or len(prices) < 2:
            return f'<div style="font-size: 11px; color: #94a3b8; line-height: {height}px; text-align: center;">(차트 데이터 준비 중)</div>'

        min_p = min(prices)
        max_p = max(prices)
        p_range = max_p - min_p if max_p > min_p else 1.0

        pad_x = 6
        pad_y = 5
        usable_w = width - (pad_x * 2)
        usable_h = height - (pad_y * 2)

        pts = []
        n = len(prices)
        for i, p in enumerate(prices):
            x = pad_x + (i / (n - 1)) * usable_w
            y = height - pad_y - ((p - min_p) / p_range) * usable_h
            pts.append((round(x, 1), round(y, 1)))

        is_up = prices[-1] >= prices[0]
        line_color = "#16A34A" if is_up else "#DC2626"
        fill_color = "#DCFCE7" if is_up else "#FEE2E2"
        pct_change = ((prices[-1] - prices[0]) / prices[0]) * 100 if prices[0] else 0.0

        points_str = " ".join([f"{x},{y}" for x, y in pts])
        poly_points = f"{pts[0][0]},{height} {points_str} {pts[-1][0]},{height}"

        svg = f"""
        <svg width="{width}" height="{height}" style="overflow: visible; vertical-align: middle;">
            <polygon points="{poly_points}" fill="{fill_color}" opacity="0.6" />
            <polyline fill="none" stroke="{line_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" points="{points_str}" />
            <circle cx="{pts[0][0]}" cy="{pts[0][1]}" r="2.5" fill="#64748B" />
            <circle cx="{pts[-1][0]}" cy="{pts[-1][1]}" r="3" fill="{line_color}" />
            <text x="{width - 2}" y="{height - 2}" font-size="9" font-family="'Malgun Gothic', sans-serif" fill="{line_color}" font-weight="bold" text-anchor="end">{pct_change:+.1f}%</text>
        </svg>
        """
        return svg

    def _convert_html_to_pdf(self, html_path: str, pdf_path: str) -> bool:
        """Microsoft Edge Headless를 호출하여 HTML을 출판용 고해상도 A4 PDF로 변환"""
        if not self.edge_path or not os.path.exists(self.edge_path):
            print(f"[경고] Edge/Chrome 브라우저를 찾을 수 없어 PDF 변환을 건너뜁니다.")
            return False

        try:
            cmd = [
                self.edge_path,
                "--headless",
                "--disable-gpu",
                "--run-all-compositor-stages-before-draw",
                f"--print-to-pdf={pdf_path}",
                html_path,
            ]
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=45,
            )
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
                return True
            else:
                print(f"[경고] PDF 생성 실패 (반환 코드: {res.returncode}, Stderr: {res.stderr[:200]})")
                return False
        except Exception as e:
            print(f"[경고] PDF 변환 실행 중 오류: {e}")
            return False

    def generate_daily_pdf(self, date_str: str, stock_indices: list, exchange_rates: list,
                           stock_advice: dict, crypto_advice: dict, official_reports: list,
                           news_result: dict, performance_data: dict, special_disclosures: list,
                           story_dive_data: dict, output_pdf_path: str) -> str:
        """
        [경영진 보고용] 8페이지 규모 The Executive Intelligence Herald (나만의 심층 인텔리전스 신문) A4 PDF 편찬
        """
        html_path = output_pdf_path.replace(".pdf", "_temp.html")

        # 도시에 데이터 확보 (기존 데이터 없으면 온디맨드 심층 탐색)
        nd = story_dive_data.get("newspaper_dossier") if isinstance(story_dive_data, dict) else None
        if not nd and IntelligenceDossierEngine:
            try:
                engine = IntelligenceDossierEngine()
                mega_dossier = engine.expand_mega_issue_story(news_result.get("mega_issue"), news_result.get("general_news", []))
                trend_item = story_dive_data.get("trend_item") if isinstance(story_dive_data, dict) else None
                trend_dossier = engine.expand_trend_story(trend_item) if trend_item else {}
                exp_reports = [engine.expand_analyst_report(r) for r in official_reports[:2]]
                exp_discs = [engine.expand_special_disclosure(d) for d in special_disclosures[:2]]
                nd = {
                    "mega_dossier": mega_dossier,
                    "trend_dossier": trend_dossier,
                    "expanded_reports": exp_reports,
                    "expanded_disclosures": exp_discs
                }
            except Exception as e:
                safe_print(f"[경고] 도시에 온디맨드 확장 중 오류: {e}")
                nd = {}
        elif not nd:
            nd = {}

        mega_d = nd.get("mega_dossier", {})
        trend_d = nd.get("trend_dossier", {})
        exp_reps = nd.get("expanded_reports", [])
        exp_discs = nd.get("expanded_disclosures", [])

        # 1. 환율 및 지수 테이블 구성
        idx_rows = ""
        for idx in stock_indices:
            col = "#16A34A" if "+" in idx["전일대비"] else "#DC2626"
            idx_rows += f"""
            <tr>
                <td style="font-weight: bold;">{idx['지수명']}</td>
                <td style="text-align: right; font-weight: bold;">{idx['현재지수']}</td>
                <td style="text-align: right; color: {col}; font-weight: bold;">{idx['전일대비']}</td>
            </tr>
            """

        fx_rows = ""
        for fx in exchange_rates:
            fx_rows += f"""
            <tr>
                <td>{fx['통화명']}</td>
                <td style="text-align: right; font-weight: bold;">{fx['환율(원)']}원</td>
                <td style="text-align: right; color: #64748B; font-size: 11px;">{fx['변동/기준']}</td>
            </tr>
            """

        # 2. 추천 종목 테이블 (주가 변화 차트 포함)
        stock_cards = ""
        today_buys = stock_advice.get("today_buy_picks", [])
        for b in today_buys[:4]:
            sparkline = self.generate_svg_sparkline(b.get("recent_closes", []))
            stock_cards += f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 8px 6px; font-weight: bold; color: #0F172A;">
                    {b.get('name')}<br><span style="font-size: 10px; color: #64748B;">{b.get('ticker')}</span>
                </td>
                <td style="padding: 8px 6px; text-align: right;">{b.get('cur_price')}</td>
                <td style="padding: 8px 6px; text-align: right; font-weight: bold; color: #16A34A;">{b.get('buy_price')}</td>
                <td style="padding: 8px 6px; text-align: right; font-weight: bold; color: #1D4ED8;">{b.get('sell_price')}</td>
                <td style="padding: 8px 6px; text-align: center; font-weight: bold; color: #16A34A;">{b.get('expected_yield')}</td>
                <td style="padding: 8px 6px; text-align: center;">{sparkline}</td>
                <td style="padding: 8px 6px; font-size: 11px; color: #334155;">{b.get('reason')}</td>
            </tr>
            """

        # 3. 미국 빅테크 4대장
        us_rows = ""
        for u in stock_advice.get("us_bigtech_picks", []):
            sparkline = self.generate_svg_sparkline(u.get("recent_closes", []))
            col = "#16A34A" if "+" in u.get('전일대비', '') else "#DC2626"
            us_rows += f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 8px; font-weight: bold;">{u.get('종목명')} ({u.get('티커')})</td>
                <td style="padding: 8px; text-align: right;">{u.get('현재가')}</td>
                <td style="padding: 8px; text-align: right; color: {col}; font-weight: bold;">{u.get('전일대비')}</td>
                <td style="padding: 8px; text-align: right; color: #1E40AF; font-weight: bold;">{u.get('매수_추천금액')} ➔ {u.get('목표_매도금액')}</td>
                <td style="padding: 8px; text-align: center;">{u.get('단기신호')}</td>
                <td style="padding: 8px; text-align: center;">{sparkline}</td>
            </tr>
            """

        # 4. 가상자산 3대장 표
        coin_rows = ""
        for c in crypto_advice.get("coins", []):
            col = "#16A34A" if "+" in c.get('change_rate', '') else "#DC2626"
            coin_rows += f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 7px 8px; font-weight: bold;">{c.get('icon', '🪙')} {c.get('name')} <span style="font-size: 10px; color: #64748B;">({c.get('symbol')})</span></td>
                <td style="padding: 7px 8px; text-align: right; font-weight: bold;">{c.get('cur_price')}</td>
                <td style="padding: 7px 8px; text-align: right; color: {col}; font-weight: bold;">{c.get('change_rate')}</td>
                <td style="padding: 7px 8px; text-align: right; color: #7E22CE; font-weight: bold;">{c.get('buy_price')}</td>
                <td style="padding: 7px 8px; text-align: right; color: #1E40AF; font-weight: bold;">{c.get('sell_price')}</td>
                <td style="padding: 7px 8px; text-align: center; color: #16A34A; font-weight: bold;">{c.get('expected_yield')}</td>
                <td style="padding: 7px 8px; font-size: 11px; color: #475569;">{c.get('outlook')}</td>
            </tr>
            """

        # 5. 사후 검증(Backtesting) 테이블
        backtest_rows = ""
        p_records = performance_data.get("records", []) if isinstance(performance_data, dict) else []
        for r in p_records[:8]:
            res = r.get("검증결과", "")
            if "달성" in res:
                badge_bg, badge_fg = "#DCFCE7", "#166534"
            elif "손절" in res:
                badge_bg, badge_fg = "#FEE2E2", "#991B1B"
            else:
                badge_bg, badge_fg = "#DBEAFE", "#1E40AF"
            backtest_rows += f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 7px 8px; font-weight: bold;">{r.get('종목명')} <span style="font-size: 10px; color: #64748B;">({r.get('티커')})</span></td>
                <td style="padding: 7px 8px; text-align: center; font-size: 11px; color: #64748B;">{r.get('추천일자')}</td>
                <td style="padding: 7px 8px; text-align: right;">{r.get('매수추천가')}</td>
                <td style="padding: 7px 8px; text-align: right; font-weight: bold; color: #1E40AF;">{r.get('목표매도가')}</td>
                <td style="padding: 7px 8px; text-align: center;"><span style="background: {badge_bg}; color: {badge_fg}; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 8px;">{res}</span></td>
                <td style="padding: 7px 8px; text-align: right; font-weight: bold;">{r.get('실현수익률')}</td>
                <td style="padding: 7px 8px; text-align: center; font-size: 11px; color: #64748B;">{r.get('소요일수')}</td>
            </tr>
            """

        # 6. 3면: 기업 심층 해부 (Equity Research Dossier) HTML
        rep_dossier_html = ""
        if exp_reps:
            for r in exp_reps[:2]:
                rep_dossier_html += f"""
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-top: 4px solid #16A34A; border-radius: 6px; padding: 12px 14px; margin-bottom: 12px; page-break-inside: avoid;">
                    <div style="font-size: 15px; font-weight: bold; color: #166534; margin-bottom: 4px;">
                        {r.get('headline')}
                    </div>
                    <div style="font-size: 11.5px; color: #475569; margin-bottom: 8px; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px;">
                        {r.get('subhead')} &nbsp;|&nbsp; 📁 원본 PDF: {r.get('pdf_filename', '')}
                    </div>
                    <div style="font-size: 11px; color: #1E293B; line-height: 1.6;">
                        <div style="margin-bottom: 6px; background: #F8FAFC; padding: 8px 10px; border-radius: 4px;">{r.get('sec_business')}</div>
                        <div style="margin-bottom: 6px; background: #F8FAFC; padding: 8px 10px; border-radius: 4px;">{r.get('sec_thesis')}</div>
                        <div style="margin-bottom: 6px; background: #F0FDF4; border: 1px solid #DCFCE7; padding: 8px 10px; border-radius: 4px; color: #14532D;">{r.get('sec_financials')}</div>
                        <div style="margin-bottom: 6px; background: #FFF1F2; border: 1px solid #FFE4E6; padding: 8px 10px; border-radius: 4px; color: #9F1239;">{r.get('sec_risks')}</div>
                        <div style="background: #EFF6FF; border: 1px solid #DBEAFE; padding: 8px 10px; border-radius: 4px; color: #1E40AF;">{r.get('sec_action')}</div>
                    </div>
                </div>
                """
        else:
            for r in official_reports[:3]:
                tp = r.get("target_price")
                tp_str = f"{int(tp):,}원" if tp else "-"
                rep_dossier_html += f"""
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-left: 4px solid #16A34A; border-radius: 6px; padding: 10px 14px; margin-bottom: 10px;">
                    <div style="font-size: 13px; font-weight: bold; color: #166534;">[{r.get('broker')}] {r.get('item_name')}: {r.get('title')}</div>
                    <div style="font-size: 11px; color: #334155; margin: 4px 0;">🎯 목표가: <b>{tp_str}</b> | 의견: <b>{r.get('opinion', 'BUY')}</b> | 신뢰도: ⭐ {r.get('credibility_score')}점</div>
                    <div style="font-size: 11px; color: #475569; line-height: 1.5;">💡 {r.get('summary_text', '')}</div>
                </div>
                """

        # 7. 4면: DART 특수공시 심층 행간 읽기 (Regulatory & Governance Intelligence) HTML
        disc_dossier_html = ""
        if exp_discs:
            for d in exp_discs[:2]:
                disc_dossier_html += f"""
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-top: 4px solid #D97706; border-radius: 6px; padding: 12px 14px; margin-bottom: 12px; page-break-inside: avoid;">
                    <div style="font-size: 14.5px; font-weight: bold; color: #92400E; margin-bottom: 6px;">
                        {d.get('headline')}
                    </div>
                    <div style="font-size: 11px; color: #1E293B; line-height: 1.6;">
                        <div style="margin-bottom: 6px; background: #FFFBEB; border: 1px solid #FEF3C7; padding: 8px 10px; border-radius: 4px; color: #78350F;">{d.get('sec_context')}</div>
                        <div style="margin-bottom: 6px; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 8px 10px; border-radius: 4px; color: #334155;">{d.get('sec_governance')}</div>
                        <div style="background: #F0FDF4; border: 1px solid #DCFCE7; padding: 8px 10px; border-radius: 4px; color: #166534;">{d.get('sec_strategy')}</div>
                    </div>
                </div>
                """
        # 특수공시 요약 표
        disc_table_rows = ""
        for d in special_disclosures[:5]:
            disc_table_rows += f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 6px 8px; font-weight: bold; color: #1E40AF;"><span style="background: #DBEAFE; color: #1E40AF; padding: 1px 5px; border-radius: 3px; font-size: 10px;">{d.get('공시배지')}</span> {d.get('관련기업', '상장사')}</td>
                <td style="padding: 6px 8px; font-size: 11px;"><a href="{d.get('링크')}" style="color: #0F172A; text-decoration: none;">{d.get('공시제목')}</a></td>
                <td style="padding: 6px 8px; font-size: 11px; color: #475569;">{d.get('영향전망')}</td>
                <td style="padding: 6px 8px; font-size: 11px; color: #166534; font-weight: bold;">{d.get('투자전략')}</td>
            </tr>
            """

        # 8. 7대 분야별 헤드라인 아카이브
        cat_news_html = ""
        cat_order = [
            ("거시경제/비즈니스", "💼 거시경제 & 비즈니스"),
            ("정치", "🏛️ 정치 핵심 이슈"),
            ("IT/과학/신상품", "💻 IT·과학 & 테크/신상품"),
            ("세계/국제", "🌍 세계·국제 뉴스"),
            ("사회/사건사고", "🚨 사회·사건사고 이슈"),
            ("연예/대중문화", "🎬 연예·문화 트렌드"),
        ]
        top_picks = news_result.get("category_top_picks", {})
        for cat_k, cat_label in cat_order:
            items = top_picks.get(cat_k, [])
            if items:
                items_li = ""
                for idx, it in enumerate(items[:5]):
                    it_link = it.get("링크") or it.get("link", "#")
                    tag = f" <span style='background: #FEE2E2; color: #DC2626; font-size: 9px; padding: 1px 4px; border-radius: 3px;'>{it.get('상태')}</span>" if "집중" in str(it.get('상태', '')) else ""
                    content_sum = it.get('content_summary') or it.get('요약내용', '')
                    expanded_ins = it.get('expanded_insight', '')
                    if not expanded_ins and IntelligenceDossierEngine:
                        expanded_ins = f"<b>💡 확장 인사이트:</b> 관련 산업계 및 정책 환경의 후속 변화와 공급망 파급 효과를 지속적으로 모니터링해야 합니다."

                    if idx < 2:
                        items_li += f"""
                        <div style="margin-bottom: 8px; font-size: 11px; background: #FFFFFF; border: 1px solid #E2E8F0; padding: 8px 10px; border-radius: 4px;">
                            <div>
                                <span style="font-weight: bold; color: #1D4ED8;">[{idx + 1}]</span> 
                                <a href="{it_link}" style="color: #1D4ED8; text-decoration: none; font-weight: bold;">{it.get('기사제목')}</a>
                                <span style="color: #64748B; font-size: 10px;">({it.get('언론사')})</span>{tag}
                            </div>
                            <div style="color: #334155; font-size: 10.5px; margin-top: 3px; padding-left: 8px; border-left: 2px solid #3B82F6; line-height: 1.45;">
                                <b>📰 기사 본문 요약:</b> {content_sum}
                            </div>
                            <div style="color: #1E40AF; background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 3px; padding: 4px 8px; font-size: 10px; margin-top: 3px; line-height: 1.4;">
                                {expanded_ins}
                            </div>
                        </div>
                        """
                    else:
                        items_li += f"""
                        <div style="margin-bottom: 4px; font-size: 10.5px; color: #334155;">
                            • <a href="{it_link}" style="color: #334155; text-decoration: none; font-weight: 500;">{it.get('기사제목')}</a>
                            <span style="color: #94A3B8; font-size: 9px;">({it.get('언론사')})</span>{tag}
                            <div style="color: #64748B; font-size: 10px; padding-left: 10px; line-height: 1.35;">- {content_sum[:90]}</div>
                        </div>
                        """
                cat_news_html += f"""
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px 12px; margin-bottom: 8px; page-break-inside: avoid;">
                    <div style="font-size: 12px; font-weight: bold; color: #1E293B; margin-bottom: 6px; border-bottom: 1px solid #CBD5E1; padding-bottom: 2px;">
                        {cat_label}
                    </div>
                    {items_li}
                </div>
                """

        # 9. HTML 조립 (My Daily Intelligence Briefing 8-Page Edition)
        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>My Daily Intelligence Briefing ({date_str})</title>
<style>
  @page {{
    size: A4;
    margin: 12mm 15mm 15mm 15mm;
    @bottom-right {{
      content: counter(page) " / " counter(pages);
      font-size: 9pt;
      color: #64748b;
    }}
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif;
    color: #1e293b;
    line-height: 1.5;
    margin: 0;
    padding: 0;
    background: #ffffff;
  }}
  .masthead {{
    border-bottom: 3px double #0F172A;
    padding-bottom: 8px;
    margin-bottom: 12px;
    text-align: center;
  }}
  .masthead-dateline {{
    display: flex;
    justify-content: space-between;
    font-size: 10px;
    font-weight: bold;
    color: #475569;
    border-bottom: 1px solid #CBD5E1;
    padding-bottom: 4px;
    margin-bottom: 6px;
    letter-spacing: 0.8px;
  }}
  .masthead-title {{
    font-size: 26px;
    font-weight: 900;
    letter-spacing: 2px;
    color: #0F172A;
    font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', serif;
    margin: 2px 0;
  }}
  .masthead-tagline {{
    font-size: 11px;
    color: #1E3A8A;
    font-weight: 600;
    letter-spacing: 0.5px;
  }}
  .sec-banner {{
    color: #ffffff;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: bold;
    border-radius: 4px;
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 10.5px;
    margin-bottom: 10px;
  }}
  th, td {{
    border: 1px solid #E2E8F0;
    padding: 6px 8px;
    text-align: left;
  }}
  th {{
    background-color: #F1F5F9;
    color: #475569;
    font-weight: bold;
  }}
  .page-break {{
    page-break-after: always;
  }}
</style>
</head>
<body>

  <!-- ============================================================ -->
  <!-- 📰 [Page 1] 1면 톱 기획특집 기사 (The Lead Story) -->
  <!-- ============================================================ -->
  <div class="masthead">
    <div class="masthead-dateline">
      <span>MY DAILY INTELLIGENCE BRIEFING</span>
      <span>나만의 데일리 금융 & 심층 이슈 브리핑 • 개인 맞춤형 리포트</span>
      <span>기준일자: {date_str}</span>
    </div>
    <div class="masthead-title">MY DAILY BRIEFING</div>
    <div class="masthead-tagline">단순 요약을 탈피한 2차 심층 교차 취재 & 밸류체인 전방위 해부 에디션</div>
  </div>

  <div class="sec-banner" style="background: #1E3A8A;">
    <span>🌐 1면 톱 기획특집 • MEGA ISSUE FOCUS</span>
    <span style="font-size: 10px; opacity: 0.9;">취재원: {mega_d.get('source', '주요 언론')} | 심층 2차 확장 취재 완료</span>
  </div>

  <div style="font-size: 18px; font-weight: 900; color: #0F172A; line-height: 1.35; margin-bottom: 6px;">
    {mega_d.get('headline', '글로벌 공급망 및 산업 재편 이슈')}
  </div>
  <div style="font-size: 12px; font-weight: bold; color: #2563EB; margin-bottom: 10px; border-bottom: 1px solid #E2E8F0; padding-bottom: 6px;">
    {mega_d.get('subhead', '')}
  </div>

  <div style="background: #F8FAFC; border-left: 4px solid #1E3A8A; padding: 10px 14px; font-size: 11px; color: #1E293B; line-height: 1.6; margin-bottom: 12px; font-style: italic;">
    {mega_d.get('lead', '')}
  </div>

  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 10.5px; line-height: 1.55; color: #334155;">
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px;">
      {mega_d.get('chapter1', '')}
    </div>
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px;">
      {mega_d.get('chapter2', '')}
    </div>
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px;">
      {mega_d.get('chapter3', '')}
    </div>
    <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 10px; color: #1E3A8A;">
      {mega_d.get('chapter4', '')}
    </div>
  </div>

  <div style="margin-top: 10px; font-size: 10px; color: #64748B; text-align: right;">
    • 원문 보도: <a href="{mega_d.get('link', '#')}" style="color: #64748B; text-decoration: none;">{mega_d.get('raw_title', '')}</a>
  </div>

  <div class="page-break"></div>

  <!-- ============================================================ -->
  <!-- 🛍️ [Page 2] 2면 소비자 & 트렌드 심층 르포 (Consumer Intelligence) -->
  <!-- ============================================================ -->
  <div class="sec-banner" style="background: #9D174D;">
    <span>🛍️ 2면 기획 르포 • CONSUMER & TREND INTELLIGENCE</span>
    <span style="font-size: 10px; opacity: 0.9;">2030 라이프스타일 & 소비 심리 심층 르포</span>
  </div>

  <div style="font-size: 17px; font-weight: 900; color: #0F172A; line-height: 1.35; margin-bottom: 6px;">
    {trend_d.get('headline', 'MZ세대 소비 트렌드 및 품절 대란')}
  </div>
  <div style="font-size: 12px; font-weight: bold; color: #BE185D; margin-bottom: 10px; border-bottom: 1px solid #FCE7F3; padding-bottom: 6px;">
    {trend_d.get('subhead', '')}
  </div>

  <div style="background: #FDF2F8; border-left: 4px solid #DB2777; padding: 10px 14px; font-size: 11px; color: #1E293B; line-height: 1.6; margin-bottom: 12px; font-style: italic;">
    {trend_d.get('lead', '')}
  </div>

  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 10.5px; line-height: 1.55; color: #334155;">
    <div style="background: #FFFFFF; border: 1px solid #FCE7F3; border-radius: 6px; padding: 10px;">
      {trend_d.get('chapter1', '')}
    </div>
    <div style="background: #FFFFFF; border: 1px solid #FCE7F3; border-radius: 6px; padding: 10px;">
      {trend_d.get('chapter2', '')}
    </div>
    <div style="background: #FFFFFF; border: 1px solid #FCE7F3; border-radius: 6px; padding: 10px;">
      {trend_d.get('chapter3', '')}
    </div>
    <div style="background: #FFF1F2; border: 1px solid #FECDD3; border-radius: 6px; padding: 10px; color: #9F1239;">
      {trend_d.get('chapter4', '')}
    </div>
  </div>

  <div style="margin-top: 14px; background: #FEF9C3; border: 1px solid #FDE047; padding: 8px 12px; border-radius: 6px; font-size: 11px; color: #713F12; line-height: 1.5;">
    💡 <b>1분 핵심 용어 사전:</b> <b>디토(Ditto) 소비</b>는 특정 인물이나 채널의 취향을 추종하여 제품을 구매하는 현대적 소비 행태를 뜻하며, <b>스몰 럭셔리(Small Luxury)</b>는 불황기 속에서 고가 대형 상품 대신 고급 디저트나 니치 향수 등 소액 프리미엄을 통해 심리적 만족을 극대화하는 행동 경제학적 선택입니다.
  </div>

  <div class="page-break"></div>

  <!-- ============================================================ -->
  <!-- 📘 [Page 3] 3면 기업 심층 해부 (Equity Research Dossier) -->
  <!-- ============================================================ -->
  <div class="sec-banner" style="background: #166534;">
    <span>📘 3면 기업 정밀 해부 • EQUITY RESEARCH DOSSIER</span>
    <span style="font-size: 10px; opacity: 0.9;">증권사 공식 Top 애널리스트 리포트 정밀 해부 (2026/2027 실적 표 수록)</span>
  </div>

  {rep_dossier_html}

  <div class="page-break"></div>

  <!-- ============================================================ -->
  <!-- 🏛️ [Page 4] 4면 DART 특수공시 심층 행간 읽기 (Regulatory Intelligence) -->
  <!-- ============================================================ -->
  <div class="sec-banner" style="background: #B45309;">
    <span>🏛️ 4면 공시 행간 읽기 • REGULATORY & GOVERNANCE INTELLIGENCE</span>
    <span style="font-size: 10px; opacity: 0.9;">금융감독원(DART) 특수공시 이면의 지배구조와 실질 재무 건전성</span>
  </div>

  {disc_dossier_html}

  <div style="font-size: 12px; font-weight: bold; color: #92400E; margin: 12px 0 6px;">📋 당일 금융감독원(DART) & KIND 특수공시 종합 일람표</div>
  <table>
    <tr>
      <th style="width: 22%;">공시 기업</th>
      <th style="width: 38%;">공시 제목</th>
      <th style="width: 20%;">영향 전망</th>
      <th style="width: 20%;">투자 전략</th>
    </tr>
    {disc_table_rows}
  </table>

  <div class="page-break"></div>

  <!-- ============================================================ -->
  <!-- 📊 [Page 5] 5면 글로벌 매크로 & 퀀트 주식 매트릭스 -->
  <!-- ============================================================ -->
  <div class="sec-banner" style="background: #1E3A8A;">
    <span>📊 5면 글로벌 매크로 & 퀀트 주식 매트릭스 • QUANTITATIVE SIGNALS</span>
    <span style="font-size: 10px; opacity: 0.9;">실시간 지수, 환율 및 20일 주가 추이 SVG 차트</span>
  </div>

  <div style="display: flex; gap: 12px; margin-bottom: 12px;">
    <div style="flex: 1;">
      <table>
        <tr><th>주요 지수명</th><th style="text-align: right;">현재지수</th><th style="text-align: right;">전일대비</th></tr>
        {idx_rows}
      </table>
    </div>
    <div style="flex: 1;">
      <table>
        <tr><th>통화명</th><th style="text-align: right;">환율(원)</th><th style="text-align: right;">변동 기준</th></tr>
        {fx_rows}
      </table>
    </div>
  </div>

  <div style="font-size: 12px; font-weight: bold; color: #16A34A; margin-bottom: 6px;">🎯 국내 주식 하이브리드 추천 매트릭스 (20일 주가 변화 SVG 차트 포함)</div>
  <table>
    <tr>
      <th>종목명 (티커)</th>
      <th style="text-align: right;">현재가</th>
      <th style="text-align: right;">추천 매수가</th>
      <th style="text-align: right;">목표 매도가</th>
      <th style="text-align: center;">기대수익</th>
      <th style="text-align: center;">20일 주가 변화</th>
      <th>선정 근거 및 전략</th>
    </tr>
    {stock_cards}
  </table>

  <div style="font-size: 12px; font-weight: bold; color: #1E40AF; margin-top: 12px; margin-bottom: 6px;">🇺🇸 미국 글로벌 빅테크 4대장 집중 분석 (20일 주가 변화 SVG 차트)</div>
  <table>
    <tr>
      <th>종목명 (티커)</th>
      <th style="text-align: right;">현재가</th>
      <th style="text-align: right;">전일대비</th>
      <th style="text-align: right;">매수가 ➔ 목표가</th>
      <th style="text-align: center;">신호</th>
      <th style="text-align: center;">20일 주가 추이</th>
    </tr>
    {us_rows}
  </table>

  <div style="font-size: 12px; font-weight: bold; color: #7E22CE; margin-top: 12px; margin-bottom: 6px;">🪙 가상자산 3대장(BTC, ETH, SOL) 실시간 시세 및 매매 추천금액</div>
  <table>
    <tr>
      <th>코인명 (심볼)</th>
      <th style="text-align: right;">현재가</th>
      <th style="text-align: right;">등락률</th>
      <th style="text-align: right;">추천 매수가</th>
      <th style="text-align: right;">목표 매도가</th>
      <th style="text-align: center;">기대수익</th>
      <th>시장 전망</th>
    </tr>
    {coin_rows}
  </table>

  <div class="page-break"></div>

  <!-- ============================================================ -->
  <!-- 🎯 [Page 6] 6면 추천 종목 사후 검증(Backtesting) 성과 백서 -->
  <!-- ============================================================ -->
  <div class="sec-banner" style="background: #1E40AF;">
    <span>🎯 6면 사후 검증(Backtesting) 성과 백서 • AUDIT & PERFORMANCE</span>
    <span style="font-size: 10px; opacity: 0.9;">투명한 실전 적중 승률 및 누적 수익률 전수 감사</span>
  </div>

  <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 14px; margin-bottom: 14px; display: flex; justify-content: space-around; text-align: center;">
    <div>
      <div style="font-size: 11px; color: #1E40AF;">누적 적중 승률</div>
      <div style="font-size: 22px; font-weight: bold; color: #1D4ED8;">{performance_data.get('summary', {}).get('win_rate', 0)}%</div>
    </div>
    <div style="border-left: 1px solid #DBEAFE;"></div>
    <div>
      <div style="font-size: 11px; color: #1E40AF;">총 검증 건수</div>
      <div style="font-size: 22px; font-weight: bold; color: #0F172A;">{performance_data.get('summary', {}).get('total_picks', 0)}건</div>
    </div>
    <div style="border-left: 1px solid #DBEAFE;"></div>
    <div>
      <div style="font-size: 11px; color: #166534;">목표가 달성</div>
      <div style="font-size: 22px; font-weight: bold; color: #16A34A;">{performance_data.get('summary', {}).get('success_count', 0)}건</div>
    </div>
    <div style="border-left: 1px solid #DBEAFE;"></div>
    <div>
      <div style="font-size: 11px; color: #991B1B;">손절 리스크 관리</div>
      <div style="font-size: 22px; font-weight: bold; color: #DC2626;">{performance_data.get('summary', {}).get('stoploss_count', 0)}건</div>
    </div>
    <div style="border-left: 1px solid #DBEAFE;"></div>
    <div>
      <div style="font-size: 11px; color: #1E40AF;">평균 수익률</div>
      <div style="font-size: 22px; font-weight: bold; color: #2563EB;">{performance_data.get('summary', {}).get('avg_return', 0):+.2f}%</div>
    </div>
  </div>

  <div style="font-size: 12px; font-weight: bold; color: #0F172A; margin-bottom: 6px;">📊 AI 추천 종목 사후 실적 추적 감사 일람표</div>
  <table>
    <tr>
      <th>종목명 (티커)</th>
      <th style="text-align: center;">추천일자</th>
      <th style="text-align: right;">매수추천가</th>
      <th style="text-align: right;">목표매도가</th>
      <th style="text-align: center;">검증결과</th>
      <th style="text-align: right;">실현수익률</th>
      <th style="text-align: center;">소요일수</th>
    </tr>
    {backtest_rows}
  </table>

  <div class="page-break"></div>

  <!-- ============================================================ -->
  <!-- 🌐 [Page 7~8] 7~8면 7대 분야별 인텔리전스 헤드라인 아카이브 -->
  <!-- ============================================================ -->
  <div class="sec-banner" style="background: #334155;">
    <span>🌐 7~8면 7대 분야별 인텔리전스 헤드라인 아카이브 • INTELLIGENCE WIRE</span>
    <span style="font-size: 10px; opacity: 0.9;">언론사 동시집중보도 클러스터링 및 분야별 5선</span>
  </div>

  {cat_news_html}

  <div style="margin-top: 24px; padding-top: 10px; border-top: 1px solid #CBD5E1; font-size: 10px; color: #64748B; text-align: center;">
    본 보고서는 개인 맞춤형 인텔리전스 리서치 자동화 파이프라인(My Daily Briefing)에 의해 매일 07:00 자동 발행되며, 구글 드라이브(월별 폴더)에 영구 보존됩니다.
  </div>

</body>
</html>
"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        success = self._convert_html_to_pdf(html_path, output_pdf_path)
        if os.path.exists(html_path):
            try:
                os.remove(html_path)
            except Exception:
                pass

        if success:
            safe_print(f"📄 ✅ [데일리 심층 PDF 편찬 완료] {output_pdf_path} (크기: {os.path.getsize(output_pdf_path):,} bytes)")
            return output_pdf_path
        else:
            safe_print(f"📄 ❌ 데일리 PDF 편찬 실패")
            return None

    def generate_weekly_pdf(self, date_str: str, weekly_data: dict, output_pdf_path: str) -> str:
        """
        [경영진 보고용] 12~15페이지 규모 주간 글로벌 금융시장 및 전략 백서 PDF 편찬 (정식 표지 & 목차 포함)
        """
        html_path = output_pdf_path.replace(".pdf", "_temp.html")
        week_label = weekly_data.get("week_label", f"{date_str} 주간 총결산")

        # 주간 집계 데이터 (한글/영문 키 호환)
        picks = weekly_data.get("weekly_picks") or weekly_data.get("top_stocks") or []
        issues = weekly_data.get("top_issues") or weekly_data.get("weekly_issues") or []
        coins = weekly_data.get("weekly_coins") or []
        reports = weekly_data.get("weekly_reports") or []
        stats = weekly_data.get("stats") or weekly_data.get("performance_data", {}).get("summary") or {}

        # 주간 도시에 데이터 추출
        nd = weekly_data.get("newspaper_dossier") or weekly_data.get("story_dive_data", {}).get("newspaper_dossier")
        if not nd and IntelligenceDossierEngine and issues:
            try:
                engine = IntelligenceDossierEngine()
                top_iss = issues[0] if issues else {}
                mega_d = engine.expand_mega_issue_story(top_iss)
                trend_d = engine.expand_trend_story({"title": top_iss.get("기사제목", "소비 트렌드"), "summary": top_iss.get("요약내용", "")})
                exp_reps = [engine.expand_analyst_report(r) for r in reports[:2]] if reports else []
                nd = {"mega_dossier": mega_d, "trend_dossier": trend_d, "expanded_reports": exp_reps}
            except Exception:
                nd = {}
        elif not nd:
            nd = {}

        mega_d = nd.get("mega_dossier", {})
        trend_d = nd.get("trend_dossier", {})
        exp_reps = nd.get("expanded_reports", [])

        # 주간 메가 기획 기사 HTML
        weekly_lead_story_html = ""
        if mega_d and mega_d.get("chapter1"):
            weekly_lead_story_html = f"""
            <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-top: 4px solid #1E3A8A; border-radius: 8px; padding: 14px 16px; margin-bottom: 16px; page-break-inside: avoid;">
                <div style="font-size: 15px; font-weight: bold; color: #0F172A; margin-bottom: 4px;">{mega_d.get('headline')}</div>
                <div style="font-size: 11.5px; color: #2563EB; font-weight: bold; margin-bottom: 8px;">{mega_d.get('subhead')}</div>
                <div style="background: #F8FAFC; border-left: 3px solid #1E3A8A; padding: 8px 10px; font-size: 11px; color: #1E293B; line-height: 1.6; margin-bottom: 10px; font-style: italic;">{mega_d.get('lead')}</div>
                <div style="font-size: 10.5px; line-height: 1.55; color: #334155;">
                    <div style="margin-bottom: 6px;">{mega_d.get('chapter1')}</div>
                    <div style="margin-bottom: 6px;">{mega_d.get('chapter2')}</div>
                    <div style="margin-bottom: 6px;">{mega_d.get('chapter3')}</div>
                    <div style="background: #EFF6FF; padding: 6px 10px; border-radius: 4px; color: #1E40AF;">{mega_d.get('chapter4')}</div>
                </div>
            </div>
            """

        # 주간 트렌드 기획 르포 HTML
        weekly_trend_story_html = ""
        if trend_d and trend_d.get("chapter1"):
            weekly_trend_story_html = f"""
            <div style="background: #FFFFFF; border: 1px solid #FBCFE8; border-top: 4px solid #DB2777; border-radius: 8px; padding: 14px 16px; margin-bottom: 16px; page-break-inside: avoid;">
                <div style="font-size: 15px; font-weight: bold; color: #9D174D; margin-bottom: 4px;">{trend_d.get('headline')}</div>
                <div style="font-size: 11.5px; color: #BE185D; font-weight: bold; margin-bottom: 8px;">{trend_d.get('subhead')}</div>
                <div style="background: #FDF2F8; border-left: 3px solid #DB2777; padding: 8px 10px; font-size: 11px; color: #1E293B; line-height: 1.6; margin-bottom: 10px; font-style: italic;">{trend_d.get('lead')}</div>
                <div style="font-size: 10.5px; line-height: 1.55; color: #334155;">
                    <div style="margin-bottom: 6px;">{trend_d.get('chapter1')}</div>
                    <div style="margin-bottom: 6px;">{trend_d.get('chapter2')}</div>
                    <div style="margin-bottom: 6px;">{trend_d.get('chapter3')}</div>
                    <div style="background: #FFF1F2; padding: 6px 10px; border-radius: 4px; color: #9F1239;">{trend_d.get('chapter4')}</div>
                </div>
            </div>
            """

        # 주간 추천 종목 표 (20일 주가 변화 SVG 스파크라인 포함)
        picks_rows = ""
        for p in picks[:10]:
            name = p.get('종목명') or p.get('name', '')
            ticker = p.get('티커') or p.get('ticker', '')
            cur_p = p.get('현재가') or p.get('cur_price', '-')
            buy_p = p.get('매수_추천금액') or p.get('buy_price', '-')
            sell_p = p.get('목표_매도금액') or p.get('sell_price', '-')
            exp_y = p.get('기대_수익률') or p.get('expected_yield', '-')
            reason = p.get('단기근거') or p.get('reason', '')
            sparkline = self.generate_svg_sparkline(p.get("recent_closes", []))
            picks_rows += f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 8px; font-weight: bold;">{name} <span style="font-size: 10px; color: #64748B;">({ticker})</span></td>
                <td style="padding: 8px; text-align: right;">{cur_p}</td>
                <td style="padding: 8px; text-align: right; color: #16A34A; font-weight: bold;">{buy_p}</td>
                <td style="padding: 8px; text-align: right; color: #1E40AF; font-weight: bold;">{sell_p}</td>
                <td style="padding: 8px; text-align: center; color: #16A34A; font-weight: bold;">{exp_y}</td>
                <td style="padding: 8px; text-align: center;">{sparkline}</td>
                <td style="padding: 8px; font-size: 11px; color: #334155;">{reason[:70]}</td>
            </tr>
            """

        # 주간 메가 이슈
        issues_html = ""
        for idx, iss in enumerate(issues[:5], 1):
            title = iss.get('기사제목') or iss.get('title', '')
            media = iss.get('언론사') or iss.get('media', '')
            cat = iss.get('분야') or iss.get('category', '종합')
            summary = iss.get('요약내용') or iss.get('summary', '')
            issues_html += f"""
            <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-left: 4px solid #1E3A8A; border-radius: 6px; padding: 12px 14px; margin-bottom: 12px; page-break-inside: avoid;">
                <div style="font-size: 13px; font-weight: bold; color: #1E3A8A; margin-bottom: 4px;">
                    {idx}. [{cat}] {title} <span style="font-size: 11px; color: #64748B;">({media})</span>
                </div>
                <div style="font-size: 11px; color: #334155; line-height: 1.5; background: #F8FAFC; padding: 8px 12px; border-radius: 4px;">
                    💡 <b>주간 핵심 분석:</b> {summary}
                </div>
            </div>
            """

        # 주간 가상자산 3대장 표
        coins_rows = ""
        for c in coins:
            coins_rows += f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 8px; font-weight: bold;">{c.get('icon', '🪙')} {c.get('name')} <span style="font-size: 10px; color: #64748B;">({c.get('symbol')})</span></td>
                <td style="padding: 8px; text-align: right; font-weight: bold;">{c.get('cur_price')}</td>
                <td style="padding: 8px; text-align: right; color: #7E22CE; font-weight: bold;">{c.get('weekly_buy_price')}</td>
                <td style="padding: 8px; text-align: right; color: #1E40AF; font-weight: bold;">{c.get('weekly_sell_price')}</td>
                <td style="padding: 8px; text-align: center; color: #16A34A; font-weight: bold;">{c.get('expected_yield')}</td>
                <td style="padding: 8px; font-size: 11px; color: #334155;">{c.get('signal')} - {c.get('outlook')}</td>
            </tr>
            """

        # 주간 증권사 공식 리포트 카드
        rep_cards_html = ""
        if exp_reps:
            for r in exp_reps[:2]:
                rep_cards_html += f"""
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-top: 4px solid #0EA5E9; border-radius: 6px; padding: 12px 14px; margin-bottom: 12px; page-break-inside: avoid;">
                    <div style="font-size: 14.5px; font-weight: bold; color: #0369A1; margin-bottom: 4px;">{r.get('headline')}</div>
                    <div style="font-size: 11px; color: #0284C7; margin-bottom: 6px;">{r.get('subhead')}</div>
                    <div style="font-size: 10.5px; color: #334155; line-height: 1.55;">
                        <div style="margin-bottom: 4px;">{r.get('sec_business')}</div>
                        <div style="margin-bottom: 4px;">{r.get('sec_thesis')}</div>
                        <div style="margin-bottom: 4px; background: #F0FDF4; padding: 6px; border-radius: 4px;">{r.get('sec_financials')}</div>
                        <div style="background: #EFF6FF; padding: 6px; border-radius: 4px;">{r.get('sec_action')}</div>
                    </div>
                </div>
                """
        for r in reports[:4]:
            tp = r.get("target_price", "-")
            tp_str = f"{int(tp):,}원" if str(tp).replace(",", "").isdigit() else str(tp)
            rep_cards_html += f"""
            <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-left: 4px solid #0EA5E9; border-radius: 6px; padding: 10px 14px; margin-bottom: 10px; page-break-inside: avoid;">
                <div style="font-size: 13px; font-weight: bold; color: #0369A1;">
                    📘 [{r.get('broker')}] {r.get('item_name')}: {r.get('title')}
                </div>
                <div style="font-size: 11px; color: #0284C7; margin: 4px 0;">
                    🎯 <b>공인 목표가:</b> {tp_str} &nbsp;|&nbsp; 📌 <b>투자의견:</b> {r.get('opinion', 'BUY')} &nbsp;|&nbsp; ⭐ <b>신뢰도:</b> {r.get('score', 85)}점
                </div>
                <div style="font-size: 11px; color: #475569; line-height: 1.5;">
                    💡 <b>핵심 요약:</b> {r.get('summary', '')}
                </div>
            </div>
            """

        # 사후 검증 지표
        win_rate = stats.get('win_rate', 0)
        total_p = stats.get('total_picks', 0)
        succ_p = stats.get('success_count', 0)
        stop_p = stats.get('stoploss_count', 0)
        hold_p = stats.get('holding_count', 0)
        avg_ret = stats.get('avg_return', 0.0)

        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>주간 글로벌 금융시장 및 전략 백서 ({week_label})</title>
<style>
  @page {{
    size: A4;
    margin: 15mm;
    @bottom-right {{
      content: counter(page) " / " counter(pages);
      font-size: 9pt;
      color: #64748b;
    }}
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
    color: #1e293b;
    line-height: 1.6;
    margin: 0;
    padding: 0;
  }}
  .cover-page {{
    height: 92vh;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    background: linear-gradient(145deg, #0A0F1D 0%, #0F172A 40%, #1E3A8A 100%);
    color: #ffffff;
    padding: 40px;
    border-radius: 12px;
    box-sizing: border-box;
    page-break-after: always;
  }}
  .toc-box {{
    background: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 24px;
    margin-top: 20px;
  }}
  .toc-item {{
    display: flex;
    justify-content: space-between;
    border-bottom: 1px dashed #CBD5E1;
    padding: 10px 0;
    font-size: 13px;
    color: #0F172A;
  }}
  .sec-h1 {{
    font-size: 17px;
    font-weight: bold;
    color: #0F172A;
    border-bottom: 3px solid #1E3A8A;
    padding-bottom: 6px;
    margin-top: 20px;
    margin-bottom: 12px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
    margin-bottom: 14px;
  }}
  th, td {{
    border: 1px solid #CBD5E1;
    padding: 8px 10px;
    text-align: left;
  }}
  th {{
    background-color: #F1F5F9;
    color: #334155;
    font-weight: bold;
  }}
  .page-break {{
    page-break-after: always;
  }}
</style>
</head>
<body>

  <!-- [표지] Personal Weekly Briefing Cover Page -->
  <div class="cover-page">
    <div>
      <div style="font-size: 12px; letter-spacing: 2px; color: #93C5FD; text-transform: uppercase;">Weekly Strategic Intelligence Report</div>
      <div style="display: inline-block; background: #2563EB; color: #ffffff; font-size: 11px; font-weight: bold; padding: 2px 10px; border-radius: 4px; margin-top: 14px;">
        나만의 주간 브리핑 • 한 주간의 금융 & 이슈 총결산
      </div>
    </div>

    <div>
      <h1 style="font-size: 32px; font-weight: bold; margin: 0; line-height: 1.3;">
        주간 글로벌 금융시장 및<br>핵심 전략 산업 종합 백서
      </h1>
      <div style="font-size: 16px; color: #93C5FD; margin-top: 12px;">
        My Weekly Strategic Briefing & Asset Allocation Report
      </div>
      <div style="margin-top: 24px; font-size: 13px; opacity: 0.85; line-height: 1.6;">
        한 주간의 매크로 경제 지표, 7대 분야 메가 이슈, 증권사 공식 리포트 실적 추정치 및<br>
        AI 퀀트 기반 포트폴리오 성과와 차주 투자 전략을 집대성한 정식 전략 백서입니다.
      </div>
    </div>

    <div style="border-top: 1px solid rgba(255,255,255,0.2); padding-top: 20px; display: flex; justify-content: space-between; font-size: 12px; opacity: 0.9;">
      <div>결산 기간: <b>{week_label}</b></div>
      <div>발행처: <b>나만의 인텔리전스 리서치팀</b></div>
    </div>
  </div>

  <!-- [목차] Table of Contents -->
  <div style="padding: 20px 0;">
    <div class="sec-h1">📑 정식 보고서 목차 (Table of Contents)</div>
    <div class="toc-box">
      <div class="toc-item">
        <span><b>Chapter 1. 한 주간 글로벌 매크로 & 금융시장 총결산</b> (주요 메가 이슈 5선 & 가상자산 3대장 동향)</span>
        <span style="font-weight: bold; color: #1E3A8A;">Section 01</span>
      </div>
      <div class="toc-item">
        <span><b>Chapter 2. 주간 트렌드 & 라이프스타일 소비 종합 리뷰</b> (SNS 바이럴, 소비 심리, 유통가 판도)</span>
        <span style="font-weight: bold; color: #1E3A8A;">Section 02</span>
      </div>
      <div class="toc-item">
        <span><b>Chapter 3. AI 추천 종목 주간 사후 검증(Backtesting) 성과 백서</b> (누적 승률, 수익률, 20일 주가 추이 차트)</span>
        <span style="font-weight: bold; color: #1E3A8A;">Section 03</span>
      </div>
      <div class="toc-item">
        <span><b>Chapter 4. 증권사 공식 리포트 주간 베스트 & 2026/2027 실적 추정치</b> (Top 공인 리서치)</span>
        <span style="font-weight: bold; color: #1E3A8A;">Section 04</span>
      </div>
      <div class="toc-item">
        <span><b>Chapter 5. 차주 시장 전망 및 섹터별 자산 배분 전략 가이드</b> (주요 경제 일정 및 포지션 제언)</span>
        <span style="font-weight: bold; color: #1E3A8A;">Section 05</span>
      </div>
    </div>
  </div>

  <div class="page-break"></div>

  <!-- Chapter 1 -->
  <div class="sec-h1">🌐 Chapter 1. 한 주간 글로벌 매크로 & 금융시장 총결산</div>
  <div style="font-size: 12px; color: #475569; margin-bottom: 12px;">
    한 주간 국내외 금융시장에서 가장 파장이 컸던 메가 이슈 심층 분석 및 가상자산 3대장 주간 결산입니다.
  </div>
  {weekly_lead_story_html}
  {issues_html}

  <div style="font-weight: bold; color: #0F172A; font-size: 13px; margin: 14px 0 8px;">🪙 3대 가상자산(BTC, ETH, SOL) 주간 총결산 및 차주 매매 밴드</div>
  <table>
    <tr>
      <th>자산명 (심볼)</th>
      <th style="text-align: right;">현재가</th>
      <th style="text-align: right;">차주 매수 밴드</th>
      <th style="text-align: right;">주간 목표가</th>
      <th style="text-align: center;">기대수익</th>
      <th>주간 평가 및 전망</th>
    </tr>
    {coins_rows}
  </table>

  <div class="page-break"></div>

  <!-- Chapter 2 -->
  <div class="sec-h1">🛍️ Chapter 2. 주간 트렌드 & 라이프스타일 소비 종합 리뷰</div>
  {weekly_trend_story_html}
  <div style="background: #FDF2F8; border: 1px solid #FBCFE8; border-left: 4px solid #DB2777; border-radius: 6px; padding: 14px 16px; margin-bottom: 16px;">
    <div style="font-size: 14px; font-weight: bold; color: #9D174D; margin-bottom: 6px;">
      🔥 2030 트렌드 및 유통가 소비 심리 변화 요약
    </div>
    <div style="font-size: 12px; color: #374151; line-height: 1.6;">
      • <b>가치 소비 및 디토(Ditto) 소비의 일상화:</b> 유명 인플루언서 및 알고리즘 추천 기반의 '품귀 현상'이 식품, 뷰티, 패션 전반으로 즉각 확산되는 양상입니다.<br>
      • <b>불황형 프리미엄의 양극화:</b> 일상 소비재는 PB 및 초저가를 지향하는 반면, 스몰 럭셔리(향수, 디저트 팝업, 한정판 굿즈)에는 지출을 아끼지 않는 이중적 소비 형태가 뚜렷합니다.<br>
      • <b>기업 실전 대응 제언:</b> 기존의 대규모 매스 마케팅보다는 타깃 세그먼트별 핀셋 팝업 스토어 및 숏폼 챌린지 중심의 기동성 있는 마케팅 집행이 필수적입니다.
    </div>
  </div>

  <!-- Chapter 3 -->
  <div class="sec-h1">🎯 Chapter 3. AI 추천 종목 주간 사후 검증(Backtesting) 성과 백서</div>
  <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 14px; margin-bottom: 14px; display: flex; justify-content: space-around; text-align: center;">
    <div>
      <div style="font-size: 11px; color: #1E40AF;">누적 적중 승률</div>
      <div style="font-size: 20px; font-weight: bold; color: #1D4ED8;">{win_rate}%</div>
    </div>
    <div style="border-left: 1px solid #DBEAFE;"></div>
    <div>
      <div style="font-size: 11px; color: #1E40AF;">총 검증 모수</div>
      <div style="font-size: 20px; font-weight: bold; color: #0F172A;">{total_p}건</div>
    </div>
    <div style="border-left: 1px solid #DBEAFE;"></div>
    <div>
      <div style="font-size: 11px; color: #166534;">목표가 달성</div>
      <div style="font-size: 20px; font-weight: bold; color: #16A34A;">{succ_p}건</div>
    </div>
    <div style="border-left: 1px solid #DBEAFE;"></div>
    <div>
      <div style="font-size: 11px; color: #991B1B;">손절 리스크 관리</div>
      <div style="font-size: 20px; font-weight: bold; color: #DC2626;">{stop_p}건</div>
    </div>
    <div style="border-left: 1px solid #DBEAFE;"></div>
    <div>
      <div style="font-size: 11px; color: #1E40AF;">평균 수익률</div>
      <div style="font-size: 20px; font-weight: bold; color: #2563EB;">{avg_ret:+.2f}%</div>
    </div>
  </div>

  <div style="font-weight: bold; color: #0F172A; font-size: 13px; margin: 10px 0 6px;">📈 주간 유망 추천 종목 및 20일 주가 변화 차트</div>
  <table>
    <tr>
      <th>종목명 (티커)</th>
      <th style="text-align: right;">현재가</th>
      <th style="text-align: right;">추천 매수가</th>
      <th style="text-align: right;">목표 매도가</th>
      <th style="text-align: center;">기대수익</th>
      <th style="text-align: center;">20일 주가 차트</th>
      <th>차주 투자 포인트</th>
    </tr>
    {picks_rows}
  </table>

  <div class="page-break"></div>

  <!-- Chapter 4 -->
  <div class="sec-h1">📄 Chapter 4. 증권사 공식 리포트 주간 베스트 & 실적 추정치</div>
  <div style="font-size: 12px; color: #475569; margin-bottom: 12px;">
    여의도 주요 증권사 공식 애널리스트 리포트 중 신뢰도 5대 지표를 통과한 핵심 보고서입니다.
  </div>
  {rep_cards_html}

  <div class="page-break"></div>

  <!-- Chapter 5 -->
  <div class="sec-h1">🔮 Chapter 5. 차주 시장 전망 및 경영진 투자 전략 제언</div>
  <div style="background: #F8FAFC; border: 1px solid #CBD5E1; border-left: 4px solid #1E3A8A; border-radius: 8px; padding: 18px; font-size: 12px; line-height: 1.8;">
    <div style="font-weight: bold; color: #1E3A8A; font-size: 14px; margin-bottom: 8px;">
      💼 [전략기획실 종합 제언] 최고경영진을 위한 차주 자산배분 및 리스크 가이드
    </div>
    • <b>거시 매크로 환경:</b> 미 연준 통화정책 기조와 원달러 환율 1,390~1,410원대 밴드를 감안하여, 공격적 레버리지보다는 현금 비중 20~25%의 방어적 유동성을 유지하십시오.<br>
    • <b>핵심 주도 섹터:</b> 공식 리포트상 2026F/2027F 영업이익이 큰 폭으로 턴어라운드하는 AI 반도체 밸류체인 및 수주 잔고가 확정된 K-방산/원전 섹터의 눌림목 분할 매수가 유효합니다.<br>
    • <b>가상자산 포트폴리오:</b> 비트코인은 주요 이동평균선 지지선 안착 여부를 확인하며 분할 적립하고, 솔라나/알트코인은 변동성 확대를 고려해 목표가 도달 시 철저한 분할 익절을 권고합니다.<br>
    • <b>위험 관리 수칙:</b> 20일선 이격도가 115% 이상 과열된 급등 테마주는 신규 진입을 전면 차단하고, 손절 기준가(-4.5%) 터치 시 즉각적인 기계적 리스크 관리를 실행하십시오.
  </div>

</body>
</html>
"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        success = self._convert_html_to_pdf(html_path, output_pdf_path)
        if os.path.exists(html_path):
            try:
                os.remove(html_path)
            except Exception:
                pass

        if success:
            safe_print(f"📄 🏆 [주간 전략 종합 백서 PDF 편찬 완료] {output_pdf_path} (크기: {os.path.getsize(output_pdf_path):,} bytes)")
            return output_pdf_path
        else:
            safe_print(f"📄 ❌ 주간 PDF 편찬 실패")
            return None
