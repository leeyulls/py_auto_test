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
import shutil

try:
    from intelligence_dossier_engine import IntelligenceDossierEngine
except ImportError:
    IntelligenceDossierEngine = None

try:
    from real_estate_advisor import RealEstateAdvisor
except ImportError:
    RealEstateAdvisor = None

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
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
            ]
            for bin_name in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium", "msedge"]:
                which_p = shutil.which(bin_name)
                if which_p and which_p not in candidates:
                    candidates.insert(0, which_p)
            self.edge_path = next((p for p in candidates if p and os.path.exists(p)), None)

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
                "--headless=new" if sys.platform != "win32" else "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
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
                timeout=60,
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
                           story_dive_data: dict, output_pdf_path: str, real_estate_data: dict = None,
                           edition: str = "morning", market_drivers: dict = None) -> str:
        """
        [경영진 보고용] 10~11페이지 규모 The Executive Intelligence Herald (나만의 심층 인텔리전스 신문) A4 PDF 편찬
        """
        html_path = output_pdf_path.replace(".pdf", "_temp.html")

        if not market_drivers:
            market_drivers = {
                "domestic_reason": "대외 거시경제 지표 및 글로벌 긴축 경계감 속에서 외국인·기관의 현선물 매물 출회 및 반도체 등 주도 섹터 차익 실현",
                "us_reason": "미 국채 금리 변동성 및 인플레이션 지표 발표에 따른 빅테크 기술주 중심의 차익 매물과 실적 관망세",
                "fx_reason": "글로벌 위험회피 심리 및 미 달러화 강약세 흐름에 연동된 완만한 환율 변동성"
            }

        # 부동산 데이터 확보 (없을 시 자동 분석)
        if real_estate_data is None and RealEstateAdvisor:
            try:
                real_estate_data = RealEstateAdvisor().analyze_market()
            except Exception as e:
                safe_print(f"[경고] 부동산 데이터 수집 실패: {e}")
                real_estate_data = {}
        elif real_estate_data is None:
            real_estate_data = {}

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

        # 2. 추천 종목 테이블 (단기 매수, 장기 적립 및 매도/과열 주의 종목 전수 수록)
        stock_cards = ""
        today_buys = stock_advice.get("today_buy_picks", [])
        long_buys = stock_advice.get("longterm_buy_picks", [])
        sell_picks = stock_advice.get("sell_warning_picks", [])

        # 1) 단기 매수 유망 종목
        for b in today_buys:
            sparkline = self.generate_svg_sparkline(b.get("recent_closes", []))
            badge = "<span style='background: #DCFCE7; color: #166534; padding: 2px 5px; border-radius: 3px; font-size: 9px; font-weight: bold;'>🟢 단기 매수</span>"
            stock_cards += f"""
            <tr style="border-bottom: 1px solid #E2E8F0; background: #F0FDF4;">
                <td style="padding: 7px 6px; font-weight: bold; color: #0F172A;">
                    {badge} <b>{b.get('name')}</b><br><span style="font-size: 10px; color: #64748B;">{b.get('ticker')}</span>
                </td>
                <td style="padding: 7px 6px; text-align: right;">{b.get('cur_price')}</td>
                <td style="padding: 7px 6px; text-align: right; font-weight: bold; color: #166534;">{b.get('buy_price')}</td>
                <td style="padding: 7px 6px; text-align: right; font-weight: bold; color: #1D4ED8;">{b.get('sell_price')}</td>
                <td style="padding: 7px 6px; text-align: center; font-weight: bold; color: #166534;">{b.get('expected_yield')}</td>
                <td style="padding: 7px 6px; text-align: center;">{sparkline}</td>
                <td style="padding: 7px 6px; font-size: 10.5px; color: #334155;">{b.get('reason', b.get('type', ''))}</td>
            </tr>
            """

        # 2) 장기 적립 매수 유망 종목
        for lb in long_buys:
            sparkline = self.generate_svg_sparkline(lb.get("recent_closes", []))
            badge = "<span style='background: #DBEAFE; color: #1E40AF; padding: 2px 5px; border-radius: 3px; font-size: 9px; font-weight: bold;'>🔵 장기 적립</span>"
            stock_cards += f"""
            <tr style="border-bottom: 1px solid #E2E8F0; background: #EFF6FF;">
                <td style="padding: 7px 6px; font-weight: bold; color: #0F172A;">
                    {badge} <b>{lb.get('name')}</b><br><span style="font-size: 10px; color: #64748B;">{lb.get('ticker')}</span>
                </td>
                <td style="padding: 7px 6px; text-align: right;">{lb.get('cur_price')}</td>
                <td style="padding: 7px 6px; text-align: right; font-weight: bold; color: #1E40AF;">{lb.get('buy_price')}</td>
                <td style="padding: 7px 6px; text-align: right; font-weight: bold; color: #2563EB;">{lb.get('sell_price')}</td>
                <td style="padding: 7px 6px; text-align: center; font-weight: bold; color: #1E40AF;">{lb.get('expected_yield')}</td>
                <td style="padding: 7px 6px; text-align: center;">{sparkline}</td>
                <td style="padding: 7px 6px; font-size: 10.5px; color: #334155;">{lb.get('reason', lb.get('type', ''))}</td>
            </tr>
            """

        if not today_buys and not long_buys:
            stock_cards += """
            <tr style="background: #F8FAFC; border-bottom: 1px solid #E2E8F0;">
                <td colspan="7" style="text-align: center; padding: 10px 8px; color: #64748B; font-size: 10.5px;">
                    ⚠️ <b>시장 급변동 및 과열 장세 알림:</b> 오늘 단기 지표상 안전마진을 충족하는 신규 매수 종목이 없습니다. 무리한 추격 매수를 지양하고 관망을 권고합니다.
                </td>
            </tr>
            """

        # 3) 매도 권고 및 과열 주의 종목 (Sell & Overheated Warnings)
        for s in sell_picks[:5]:
            sparkline = self.generate_svg_sparkline(s.get("recent_closes", []))
            badge = "<span style='background: #FEE2E2; color: #991B1B; padding: 2px 5px; border-radius: 3px; font-size: 9px; font-weight: bold;'>🔴 매도/과열 주의</span>"
            disp = s.get('disparity', '')
            reason_text = f"{s.get('type', '')} (이격도 {disp})" if disp else s.get('type', '')
            stock_cards += f"""
            <tr style="border-bottom: 1px solid #FECACA; background: #FEF2F2;">
                <td style="padding: 7px 6px; font-weight: bold; color: #991B1B;">
                    {badge} <b>{s.get('name')}</b><br><span style="font-size: 10px; color: #991B1B;">{s.get('ticker')}</span>
                </td>
                <td style="padding: 7px 6px; text-align: right; color: #7F1D1D; font-weight: bold;">{s.get('cur_price')}</td>
                <td style="padding: 7px 6px; text-align: center; color: #64748B;">- (신규매수금지)</td>
                <td style="padding: 7px 6px; text-align: right; font-weight: bold; color: #DC2626;">{s.get('sell_price')}</td>
                <td style="padding: 7px 6px; text-align: center; font-weight: bold; color: #DC2626;">비중 축소</td>
                <td style="padding: 7px 6px; text-align: center;">{sparkline}</td>
                <td style="padding: 7px 6px; font-size: 10.5px; color: #991B1B; font-weight: 500;">⚠️ {reason_text}</td>
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

        # 4. 가상자산 전용 데이터 (독립 7면)
        macro_c = crypto_advice.get("macro_indicators", {})
        fg_val = macro_c.get("fear_greed_val", 60)
        fg_label = macro_c.get("fear_greed_label", "중립 (Neutral)")
        kimchi_p = macro_c.get("kimchi_premium", "+0.0%")
        btc_dom = macro_c.get("btc_dominance", "57.6%")

        upbit_top_rows = ""
        for idx, tv in enumerate(macro_c.get("top_volume_coins", []), 1):
            chg = tv.get("change", "0.0%")
            chg_col = "#16A34A" if "+" in chg else "#DC2626"
            upbit_top_rows += f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 6px 8px; text-align: center; font-weight: bold; color: #475569;">{idx}</td>
                <td style="padding: 6px 8px; font-weight: bold; color: #0F172A;">{tv.get('symbol')}</td>
                <td style="padding: 6px 8px; text-align: right; font-weight: bold;">{tv.get('price')}</td>
                <td style="padding: 6px 8px; text-align: right; color: {chg_col}; font-weight: bold;">{chg}</td>
                <td style="padding: 6px 8px; text-align: right; color: #64748B;">{tv.get('volume')}</td>
            </tr>
            """

        coin_cards_detailed = ""
        for c in crypto_advice.get("coins", []):
            sparkline = self.generate_svg_sparkline(c.get("recent_closes", []))
            col = "#16A34A" if "+" in c.get('change_rate', '') else "#DC2626"
            coin_cards_detailed += f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 3px solid #7E22CE; border-radius: 6px; padding: 10px 12px; margin-bottom: 10px; page-break-inside: avoid;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div style="font-size: 13.5px; font-weight: bold; color: #581C87;">
                        {c.get('icon')} {c.get('name')} <span style="font-size: 11px; color: #64748B;">({c.get('symbol')})</span>
                        &nbsp;|&nbsp; 현재가: <b>{c.get('cur_price')}</b> <span style="color: {col}; font-size: 12px;">({c.get('change_rate')})</span>
                    </div>
                    <div>{sparkline}</div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 11px; margin-bottom: 6px;">
                    <div style="background: #FAF5FF; padding: 6px 8px; border-radius: 4px; color: #581C87;">
                        💰 <b>추천 매수가:</b> {c.get('buy_price')} &nbsp;|&nbsp; 🎯 <b>목표가:</b> {c.get('sell_price')} ({c.get('expected_yield')})<br>
                        🛑 <b>손절가:</b> {c.get('stop_loss')} &nbsp;|&nbsp; 📊 <b>RSI(14):</b> {c.get('rsi')}
                    </div>
                    <div style="background: #F8FAFC; padding: 6px 8px; border-radius: 4px; color: #334155;">
                        🛡️ <b>지지선:</b> 1차 {c.get('sup1')} / 2차 {c.get('sup2')}<br>
                        ⚔️ <b>저항선:</b> 1차 {c.get('res1')} / 2차 {c.get('res2')}
                    </div>
                </div>
                <div style="font-size: 10.5px; color: #475569; background: #F1F5F9; padding: 6px 8px; border-radius: 4px; line-height: 1.45;">
                    🐋 <b>온체인·ETF 수급:</b> {c.get('onchain_desc')}<br>
                    💡 <b>트레이딩 관점:</b> {c.get('outlook')} [{c.get('signal')}]
                </div>
            </div>
            """

        # 5. 부동산 전용 데이터 (독립 8면)
        re_rows = ""
        for r in real_estate_data.get("regional_trends", []):
            sc = r.get("sale_change", "0.00%")
            jc = r.get("jeonse_change", "0.00%")
            sc_col = "#16A34A" if "+" in sc else ("#DC2626" if "-" in sc else "#64748B")
            jc_col = "#16A34A" if "+" in jc else ("#DC2626" if "-" in jc else "#64748B")
            re_rows += f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 7px 8px; font-weight: bold; color: #0F172A;">{r.get('region')}</td>
                <td style="padding: 7px 8px; text-align: right; color: {sc_col}; font-weight: bold;">{sc}</td>
                <td style="padding: 7px 8px; text-align: right; color: {jc_col}; font-weight: bold;">{jc}</td>
                <td style="padding: 7px 8px; text-align: center;"><span style="background: #F1F5F9; color: {r.get('status_color', '#334155')}; font-weight: bold; font-size: 10px; padding: 2px 6px; border-radius: 4px;">{r.get('status')}</span></td>
                <td style="padding: 7px 8px; font-size: 10.5px; color: #475569;">{r.get('summary')}</td>
            </tr>
            """

        mi = real_estate_data.get("mortgage_info", {})
        mm = real_estate_data.get("market_metrics", {})
        ag_cards = ""
        for ag in real_estate_data.get("action_guides", []):
            ag_cards += f"""
            <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-left: 4px solid #0284C7; border-radius: 4px; padding: 6px 10px; margin-bottom: 6px; font-size: 11px;">
                <b>🎯 {ag.get('target')}:</b> {ag.get('tip')}
            </div>
            """

        # 6. 사후 검증(Backtesting) 테이블
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

        # 7. 3면: 기업 심층 해부 (Equity Research Dossier) HTML
        rep_dossier_html = ""
        if exp_reps:
            for r in exp_reps[:2]:
                sec_boxes = ""
                if r.get('sec_business'):
                    sec_boxes += f"<div style='margin-bottom: 6px; background: #F8FAFC; padding: 8px 10px; border-radius: 4px;'>{r['sec_business']}</div>"
                if r.get('sec_thesis'):
                    sec_boxes += f"<div style='margin-bottom: 6px; background: #F8FAFC; padding: 8px 10px; border-radius: 4px;'>{r['sec_thesis']}</div>"
                if r.get('sec_financials'):
                    sec_boxes += f"<div style='margin-bottom: 6px; background: #F0FDF4; border: 1px solid #DCFCE7; padding: 8px 10px; border-radius: 4px; color: #14532D;'>{r['sec_financials']}</div>"
                if r.get('sec_risks'):
                    sec_boxes += f"<div style='margin-bottom: 6px; background: #FFF1F2; border: 1px solid #FFE4E6; padding: 8px 10px; border-radius: 4px; color: #9F1239;'>{r['sec_risks']}</div>"
                if r.get('sec_action'):
                    sec_boxes += f"<div style='background: #EFF6FF; border: 1px solid #DBEAFE; padding: 8px 10px; border-radius: 4px; color: #1E40AF;'>{r['sec_action']}</div>"

                pdf_fn = r.get('pdf_filename') or ''
                fn_str = f" &nbsp;|&nbsp; 📁 원본 PDF: {pdf_fn}" if pdf_fn else ""
                rep_dossier_html += f"""
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-top: 4px solid #16A34A; border-radius: 6px; padding: 12px 14px; margin-bottom: 12px; page-break-inside: avoid;">
                    <div style="font-size: 15px; font-weight: bold; color: #166534; margin-bottom: 4px;">
                        {r.get('headline', '')}
                    </div>
                    <div style="font-size: 11.5px; color: #475569; margin-bottom: 8px; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px;">
                        {r.get('subhead', '')}{fn_str}
                    </div>
                    <div style="font-size: 11px; color: #1E293B; line-height: 1.6;">
                        {sec_boxes}
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

        # 8. 4면: DART 특수공시 심층 행간 읽기 (Regulatory & Governance Intelligence) HTML
        disc_dossier_html = ""
        if exp_discs:
            for d in exp_discs[:2]:
                disc_boxes = ""
                if d.get('sec_context'):
                    disc_boxes += f"<div style='margin-bottom: 6px; background: #FFFBEB; border: 1px solid #FEF3C7; padding: 8px 10px; border-radius: 4px; color: #78350F;'>{d['sec_context']}</div>"
                if d.get('sec_governance'):
                    disc_boxes += f"<div style='margin-bottom: 6px; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 8px 10px; border-radius: 4px; color: #334155;'>{d['sec_governance']}</div>"
                if d.get('sec_strategy'):
                    disc_boxes += f"<div style='background: #F0FDF4; border: 1px solid #DCFCE7; padding: 8px 10px; border-radius: 4px; color: #166534;'>{d['sec_strategy']}</div>"

                disc_dossier_html += f"""
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-top: 4px solid #D97706; border-radius: 6px; padding: 12px 14px; margin-bottom: 12px; page-break-inside: avoid;">
                    <div style="font-size: 14.5px; font-weight: bold; color: #92400E; margin-bottom: 6px;">
                        {d.get('headline', '')}
                    </div>
                    <div style="font-size: 11px; color: #1E293B; line-height: 1.6;">
                        {disc_boxes}
                    </div>
                </div>
                """
        # 특수공시 요약 표 (독립 5면 전용 - 1페이지 완결 조판)
        disc_table_rows = ""
        for d in special_disclosures[:7]:
            corp_name = d.get('관련기업') or '상장사'
            disc_table_rows += f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 5px 6px; font-weight: bold; color: #1E40AF; font-size: 10px;"><span style="background: #DBEAFE; color: #1E40AF; padding: 1px 5px; border-radius: 3px; font-size: 9px;">{d.get('공시배지')}</span> {corp_name}</td>
                <td style="padding: 5px 6px; font-size: 10px; font-weight: bold;"><a href="{d.get('링크')}" style="color: #0F172A; text-decoration: none;">{d.get('공시제목')}</a></td>
                <td style="padding: 5px 6px; font-size: 10px; color: #475569; line-height: 1.35;">{d.get('영향전망')}</td>
                <td style="padding: 5px 6px; font-size: 10px; color: #166534; font-weight: bold; line-height: 1.35;">{d.get('투자전략')}</td>
            </tr>
            """

        # 8. 7대 분야별 헤드라인 아카이브 (전수 심층 본문 요약 & 확장 인사이트 수록)
        def _render_cat_block(cat_k, cat_label, top_picks_dict):
            items = top_picks_dict.get(cat_k, [])
            if not items:
                return ""
            items_li = ""
            for idx, it in enumerate(items):
                it_link = it.get("링크") or it.get("link", "#")
                tag = f" <span style='background: #FEE2E2; color: #DC2626; font-size: 9px; padding: 1px 4px; border-radius: 3px;'>{it.get('상태')}</span>" if "집중" in str(it.get('상태', '')) else ""
                content_sum = it.get('content_summary') or it.get('요약내용', '')
                expanded_ins = it.get('expanded_insight', '')
                if not expanded_ins:
                    expanded_ins = f"<b>💡 심층 맥락 & 전략적 시사점:</b> 관련 산업계 및 정책 환경의 후속 변화와 공급망 파급 효과를 지속적으로 모니터링해야 합니다.<br><b>🔎 핵심 체크포인트:</b> 소관 부처 및 시장의 공식 반응 추이를 선행 지표로 삼아야 합니다."

                items_li += f"""
                <div style="margin-bottom: 7px; font-size: 10px; background: #FFFFFF; border: 1px solid #E2E8F0; padding: 6px 9px; border-radius: 4px; page-break-inside: avoid;">
                    <div style="line-height: 1.35; margin-bottom: 3px;">
                        <span style="font-weight: bold; color: #1D4ED8;">[{idx + 1}]</span> 
                        <a href="{it_link}" style="color: #0F172A; text-decoration: none; font-weight: bold; font-size: 10.5px;">{it.get('기사제목')}</a>
                        <span style="color: #64748B; font-size: 9px;">({it.get('언론사')})</span>{tag}
                    </div>
                    <div style="color: #334155; font-size: 9.8px; margin-top: 3px; padding-left: 8px; border-left: 2px solid #3B82F6; line-height: 1.45;">
                        <b>📰 기사 본문 요약:</b> {content_sum}
                    </div>
                    <div style="color: #1E40AF; background: #EFF6FF; border: 1px solid #BFDBFE; border-left: 3px solid #2563EB; border-radius: 3px; padding: 4px 8px; font-size: 9.3px; margin-top: 4px; line-height: 1.4;">
                        {expanded_ins}
                    </div>
                </div>
                """
            return f"""
            <div style="background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 5px; padding: 7px 10px; margin-bottom: 10px;">
                <div style="font-size: 12px; font-weight: bold; color: #1E293B; margin-bottom: 6px; border-bottom: 2px solid #3B82F6; padding-bottom: 3px; display: flex; justify-content: space-between; align-items: center;">
                    <span>{cat_label}</span>
                    <span style="font-size: 9.5px; color: #64748B; font-weight: normal;">총 {len(items)}건 전수 수록</span>
                </div>
                {items_li}
            </div>
            """

        top_picks = news_result.get("category_top_picks", {})
        cat_group_1 = [
            ("거시경제/비즈니스", "💼 거시경제 & 비즈니스"),
            ("정치", "🏛️ 정치 핵심 이슈"),
            ("IT/과학/신상품", "💻 IT·과학 & 테크/신상품"),
        ]
        cat_group_2 = [
            ("세계/국제", "🌍 세계·국제 뉴스"),
            ("사회/사건사고", "🚨 사회·사건사고 이슈"),
            ("연예/대중문화", "🎬 연예·문화 트렌드"),
        ]
        cat_news_page1 = "".join([_render_cat_block(k, lbl, top_picks) for k, lbl in cat_group_1])
        cat_news_page2 = "".join([_render_cat_block(k, lbl, top_picks) for k, lbl in cat_group_2])

        # 9. HTML 조립 (My Daily Intelligence Briefing)
        is_evening = (str(edition).lower() == "evening") or ("저녁" in str(edition)) or ("이브닝" in str(edition))
        edition_label = "이브닝 마감 에디션" if is_evening else "모닝 개장 에디션"
        tagline_text = "당일 국내 증시 마감 결산 & 낮 시간 신규 이슈 & 익일 글로벌 전망" if is_evening else "단순 요약을 탈피한 2차 심층 교차 취재 & 밸류체인 전방위 해부 에디션"

        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>My Daily Intelligence Briefing - {edition_label} ({date_str})</title>
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
      <span>나만의 데일리 금융 & 심층 이슈 브리핑 • 개인 맞춤형 리포트 ({edition_label})</span>
      <span>기준일자: {date_str}</span>
    </div>
    <div class="masthead-title">MY DAILY BRIEFING</div>
    <div class="masthead-tagline">{tagline_text}</div>
  </div>

  <div style="background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 4px; padding: 4px 8px; margin-bottom: 8px; font-size: 9px; color: #334155; display: flex; justify-content: space-between; align-items: center;">
    <span style="font-weight: bold; color: #1E3A8A;">🧭 21면 섹션 퀵 맵:</span>
    <span><b>1~2면</b> 기획특집·소비자르포</span>
    <span>|</span>
    <span><b>3~4면</b> 기업정밀해부</span>
    <span>|</span>
    <span><b>5~6면</b> DART특수공시</span>
    <span>|</span>
    <span><b>7면</b> 퀀트증시</span>
    <span>|</span>
    <span><b>8면</b> 가상자산</span>
    <span>|</span>
    <span><b>9면</b> 부동산</span>
    <span>|</span>
    <span><b>10면</b> 사후검증</span>
    <span>|</span>
    <span><b>11~21면</b> 7대분야 전수뉴스</span>
  </div>

  <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-left: 4px solid #1D4ED8; border-radius: 4px; padding: 6px 10px; margin-bottom: 8px; font-size: 9.5px; color: #1E3A8A; line-height: 1.45;">
    <div style="font-weight: bold; margin-bottom: 3px;">🎯 오늘의 핵심 경영 & 투자 결단 체크포인트 (Executive Action Checklist)</div>
    <div>1. <b>거시 리스크 관리:</b> 당일 글로벌 증시 및 환율 변동성 확대 국면에서 무리한 추격 매수를 지양하고 방어적 현금 유동성 25% 유지</div>
    <div>2. <b>실적 기반 선별 압축:</b> 2026/2027 공인 실적 턴어라운드 및 확정 수주 모멘텀이 확인된 섹터(방산·원전·AI 전력망) 중심 분할 매수 대응</div>
    <div>3. <b>자산 양극화 방어:</b> 대출 규제 환경 속에서 서울 핵심지(강남·마용성·여의도/영등포) 및 1기 신도시 재건축 선도지구 위주 압축 보유 지속</div>
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

  {f'''<div style="margin-top: 8px; background: #F0FDF4; border: 1px solid #BBF7D0; border-left: 4px solid #16A34A; border-radius: 4px; padding: 7px 10px; font-size: 10px; color: #166534; line-height: 1.45;">
    <b>🎯 [핵심 투자 밸류체인 & 수혜주]:</b> {mega_d.get('value_chain')}
  </div>''' if mega_d.get('value_chain') else ''}

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
  <!-- 🏛️ [Page 4] 4면 DART 특수공시 심층 행간 읽기 (Top 2 정밀 분석) -->
  <!-- ============================================================ -->
  <div class="sec-banner" style="background: #B45309;">
    <span>🏛️ 4면 공시 행간 읽기 • REGULATORY & GOVERNANCE INTELLIGENCE</span>
    <span style="font-size: 10px; opacity: 0.9;">금융감독원(DART) 특수공시 이면의 지배구조와 실질 재무 체력 심층 해부</span>
  </div>

  {disc_dossier_html}

  <div class="page-break"></div>

  <!-- ============================================================ -->
  <!-- 📋 [Page 5] 5면 DART 특수공시 종합 일람표 & 투자전략 캘린더 (독립 전용 페이지) -->
  <!-- ============================================================ -->
  <div class="sec-banner" style="background: #92400E;">
    <span>📋 5면 특수공시 종합 일람표 • DART & KIND REGULATORY MONITOR</span>
    <span style="font-size: 10px; opacity: 0.9;">당일 금융감독원 & 거래소 공시 전수 분석 및 실전 투자 행동 전략</span>
  </div>

  <div style="font-size: 12.5px; font-weight: bold; color: #92400E; margin-bottom: 6px;">📋 당일 금융감독원(DART) & KIND 특수공시 종합 일람표</div>
  <table>
    <tr>
      <th style="width: 20%;">공시 기업</th>
      <th style="width: 38%;">공시 제목</th>
      <th style="width: 22%;">영향 전망</th>
      <th style="width: 20%;">투자 전략</th>
    </tr>
    {disc_table_rows}
  </table>

  <div style="margin-top: 8px; background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 5px; padding: 8px 12px; font-size: 10px; color: #78350F; line-height: 1.45;">
    💡 <b>DART 특수공시 투자자 핵심 가이드:</b><br>
    • <b>자사주 소각:</b> 유통 주식 수를 영구 소멸시켜 주당순이익(EPS)을 즉각 향상시키는 최상급 주주환원 호재입니다.<br>
    • <b>자사주 취득 신탁계약:</b> 증권사에 위탁 분할 취득하므로 실제 공시 집행율(체결율)을 정기 점검해야 합니다.<br>
    • <b>대규모 공급계약:</b> 최근 매출액 대비 계약금 비중(통상 10% 이상 권고)과 계약 상대방의 신용도를 확인해야 합니다.
  </div>

  <div class="page-break"></div>

  <!-- ============================================================ -->
  <!-- 📊 [Page 6] 6면 글로벌 매크로 & 퀀트 주식 매트릭스 -->
  <!-- ============================================================ -->
  <div class="sec-banner" style="background: #1E3A8A;">
    <span>📊 6면 글로벌 매크로 & 퀀트 주식 매트릭스 • QUANTITATIVE SIGNALS</span>
    <span style="font-size: 10px; opacity: 0.9;">실시간 지수, 환율 및 20일 주가 추이 SVG 차트</span>
  </div>

  <div style="display: flex; gap: 12px; margin-bottom: 8px;">
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

  <div style="background: #F8FAFC; border: 1px solid #CBD5E1; border-left: 4px solid #2563EB; border-radius: 4px; padding: 7px 10px; margin-bottom: 10px; font-size: 10px; line-height: 1.45; color: #1E293B;">
    <div style="font-weight: bold; color: #1E40AF; margin-bottom: 3px; display: flex; justify-content: space-between;">
      <span>💡 당일 글로벌 증시 및 외환시장 등락 핵심 원인 분석</span>
      <span style="font-size: 9px; color: #64748B; font-weight: normal;">실시간 수급 및 시황 인텔리전스</span>
    </div>
    <div style="margin-bottom: 2px;">• <b>국내 증시 (코스피/코스닥):</b> {market_drivers.get('domestic_reason', '')}</div>
    <div style="margin-bottom: 2px;">• <b>미국 증시 (나스닥/S&P):</b> {market_drivers.get('us_reason', '')}</div>
    <div>• <b>외환 시장 (원/달러 환율):</b> {market_drivers.get('fx_reason', '')}</div>
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

  <div class="page-break"></div>

  <!-- ============================================================ -->
  <!-- 🪙 [Page 7] 7면 가상자산 전용 인텔리전스 (Crypto Intelligence) -->
  <!-- ============================================================ -->
  <div class="sec-banner" style="background: #7E22CE;">
    <span>🪙 7면 가상자산 인텔리전스 • CRYPTO ASSET INTELLIGENCE</span>
    <span style="font-size: 10px; opacity: 0.9;">공포·탐욕 지수, 실시간 김치프리미엄, 업비트 TOP 5 & 3대 코인 온체인/기술적 분석</span>
  </div>

  <div style="display: flex; gap: 10px; margin-bottom: 12px; text-align: center;">
    <div style="flex: 1; background: #FAF5FF; border: 1px solid #E9D5FF; border-radius: 6px; padding: 10px;">
      <div style="font-size: 11px; color: #6B21A8;">공포 & 탐욕 지수</div>
      <div style="font-size: 18px; font-weight: bold; color: #7E22CE; margin: 2px 0;">{fg_val}점</div>
      <div style="font-size: 10.5px; font-weight: bold; color: #581C87;">{fg_label}</div>
    </div>
    <div style="flex: 1; background: #FAF5FF; border: 1px solid #E9D5FF; border-radius: 6px; padding: 10px;">
      <div style="font-size: 11px; color: #6B21A8;">실시간 김치 프리미엄</div>
      <div style="font-size: 18px; font-weight: bold; color: #16A34A; margin: 2px 0;">{kimchi_p}</div>
      <div style="font-size: 10.5px; color: #475569;">바이낸스 대비 차이</div>
    </div>
    <div style="flex: 1; background: #FAF5FF; border: 1px solid #E9D5FF; border-radius: 6px; padding: 10px;">
      <div style="font-size: 11px; color: #6B21A8;">비트코인 도미넌스</div>
      <div style="font-size: 18px; font-weight: bold; color: #1E40AF; margin: 2px 0;">{btc_dom}</div>
      <div style="font-size: 10.5px; color: #475569;">전체 시장 점유율</div>
    </div>
  </div>

  <div style="font-size: 12px; font-weight: bold; color: #581C87; margin-bottom: 6px;">⚡ 업비트 24시간 거래대금 최상위 코인 Top 5</div>
  <table style="margin-bottom: 12px;">
    <tr>
      <th style="width: 10%; text-align: center;">순위</th>
      <th style="width: 25%;">종목 (심볼)</th>
      <th style="width: 25%; text-align: right;">현재가</th>
      <th style="width: 20%; text-align: right;">24시간 변동률</th>
      <th style="width: 20%; text-align: right;">24시간 거래대금</th>
    </tr>
    {upbit_top_rows}
  </table>

  <div style="font-size: 12px; font-weight: bold; color: #581C87; margin-bottom: 6px;">🎯 가상자산 3대장(BTC, ETH, SOL) 온체인 수급 및 지지·저항선 분석</div>
  {coin_cards_detailed}

  <div class="page-break"></div>

  <!-- ============================================================ -->
  <!-- 🏢 [Page 8] 8면 대한민국 부동산 시장 동향 (Real Estate Intelligence) -->
  <!-- ============================================================ -->
  <div class="sec-banner" style="background: #0284C7;">
    <span>🏢 8면 대한민국 부동산 시장 동향 • REAL ESTATE INTELLIGENCE</span>
    <span style="font-size: 10px; opacity: 0.9;">권역별 아파트 매매·전세 증감률, 주담대 금리 밴드, DSR 규제 & 실수요자 가이드</span>
  </div>

  <div style="font-size: 12px; font-weight: bold; color: #0369A1; margin-bottom: 6px;">📊 주요 권역별 아파트 매매·전세 주간 변동률 및 시장 국면</div>
  <table>
    <tr>
      <th style="width: 25%;">주요 권역</th>
      <th style="width: 13%; text-align: right;">주간 매매</th>
      <th style="width: 13%; text-align: right;">주간 전세</th>
      <th style="width: 18%; text-align: center;">시장 국면</th>
      <th style="width: 31%;">주요 동향 및 특징</th>
    </tr>
    {re_rows}
  </table>

  <div style="display: flex; gap: 10px; margin-bottom: 12px;">
    <div style="flex: 1; background: #F0F9FF; border: 1px solid #BAE6FD; border-radius: 6px; padding: 10px; font-size: 11px;">
      <div style="font-weight: bold; color: #0369A1; margin-bottom: 6px;">🏦 주택담보대출 금리 & 금융 규제</div>
      <div style="margin-bottom: 3px;">• <b>5년 고정(혼합형):</b> {mi.get('fixed_rate_band')}</div>
      <div style="margin-bottom: 3px;">• <b>변동금리:</b> {mi.get('variable_rate_band')} (COFIX {mi.get('cofix_rate')})</div>
      <div style="margin-bottom: 3px;">• <b>대출 규제:</b> {mi.get('dsr_status')}</div>
      <div style="color: #475569; font-size: 10px;">• {mi.get('bank_policy')}</div>
    </div>
    <div style="flex: 1; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px; font-size: 11px;">
      <div style="font-weight: bold; color: #0F172A; margin-bottom: 6px;">📈 거래량 & 수급 매트릭스</div>
      <div style="margin-bottom: 3px;">• <b>서울 월간 거래량:</b> {mm.get('monthly_volume')}</div>
      <div style="margin-bottom: 3px;">• <b>서울 아파트 매물:</b> {mm.get('listing_inventory')}</div>
      <div style="margin-bottom: 3px;">• <b>서울 평균 전세가율:</b> {mm.get('jeonse_ratio')}</div>
      <div style="color: #475569; font-size: 10px;">• <b>청약 경쟁률:</b> {mm.get('bidding_ratio')}</div>
    </div>
  </div>

  <div style="font-size: 12px; font-weight: bold; color: #0369A1; margin-bottom: 6px;">🧭 실수요자 및 자산관리 실전 행동 요령</div>
  {ag_cards}

  <div class="page-break"></div>

  <!-- ============================================================ -->
  <!-- 🎯 [Page 9] 9면 추천 종목 사후 검증(Backtesting) 성과 백서 -->
  <!-- ============================================================ -->
  <div class="sec-banner" style="background: #1E40AF;">
    <span>🎯 9면 사후 검증(Backtesting) 성과 백서 • AUDIT & PERFORMANCE</span>
    <span style="font-size: 10px; opacity: 0.9;">투명한 실전 적중 승률 및 누적 수익률 전수 감사</span>
  </div>

  <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 14px; margin-bottom: 14px; display: flex; justify-content: space-around; text-align: center;">
    <div>
      <div style="font-size: 11px; color: #1E40AF;">누적 적중 승률</div>
      <div style="font-size: 22px; font-weight: bold; color: #1D4ED8;">{performance_data.get('summary', {}).get('win_rate', 0)}%</div>
    </div>
    <div style="border-left: 1px solid #DBEAFE;"></div>
    <div>
      <div style="font-size: 11px; color: #1E40AF;">총 검증 모수</div>
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
      <div style="font-size: 11px; color: #4338CA;">목표가 추적 중</div>
      <div style="font-size: 22px; font-weight: bold; color: #4338CA;">{performance_data.get('summary', {}).get('holding_count', 0)}건</div>
      <div style="font-size: 9px; color: #6366F1;">(수익권 {performance_data.get('summary', {}).get('holding_positive_count', 0)}건)</div>
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

  <div style="margin-top: 12px; background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #1E40AF; border-radius: 6px; padding: 12px 14px; font-size: 10.5px; line-height: 1.6; color: #1E293B;">
    <div style="font-weight: bold; color: #1E40AF; font-size: 11px; margin-bottom: 4px;">💡 성과 분석 총평 및 포트폴리오 리밸런싱 가이드라인</div>
    • <b>AI 퀀트 알고리즘 사후 검증:</b> 목표가 도달 성공 종목들은 모두 실적 턴어라운드 및 기관·외국인 순매수세가 결합된 주도주였습니다. 반면 손절 기준선에 도달한 종목은 진입 후 시장 급변동성에 따른 것으로 기계적 손절매 원칙을 철저히 준수하여 자본을 보호했습니다.<br>
    • <b>실전 포트폴리오 리밸런싱:</b> 변동성 장세에서는 단일 종목 집중 투자보다 핵심 주도주(50%), 경기 방어·배당주(30%), 현금성 자산(20%)의 바벨 전략을 유지하십시오. 목표 수익률 도달 시 50% 분할 익절 후 잔여 수량으로 추세 수익을 극대화하는 전략을 권고합니다.
  </div>

  <div class="page-break"></div>

  <!-- ============================================================ -->
  <!-- 🌐 7대 분야별 인텔리전스 와이어 (Part 1: 거시경제·정치·IT과학 전수 수록) -->
  <!-- ============================================================ -->
  <div class="sec-banner" style="background: #1E3A8A; margin-bottom: 8px;">
    <span>🌐 분야별 인텔리전스 와이어 (Part 1) • INTELLIGENCE WIRE</span>
    <span style="font-size: 10px; opacity: 0.9;">💼 거시경제 & 비즈니스 • 🏛️ 정치 핵심 이슈 • 💻 IT·과학 & 테크 (심층 본문 요약 & 2차 취재 인사이트 전수 수록)</span>
  </div>

  {cat_news_page1}

  <div class="page-break"></div>

  <!-- ============================================================ -->
  <!-- 🌐 7대 분야별 인텔리전스 와이어 (Part 2: 세계·사회·문화 전수 수록) -->
  <!-- ============================================================ -->
  <div class="sec-banner" style="background: #1E3A8A; margin-bottom: 8px;">
    <span>🌐 분야별 인텔리전스 와이어 (Part 2) • INTELLIGENCE WIRE</span>
    <span style="font-size: 10px; opacity: 0.9;">🌍 세계·국제 정세 • 🚨 사회·사건사고 • 🎬 연예·문화 트렌드 (심층 본문 요약 & 2차 취재 인사이트 전수 수록)</span>
  </div>

  {cat_news_page2}

  <div style="margin-top: 14px; padding-top: 8px; border-top: 1px solid #CBD5E1; font-size: 10px; color: #64748B; text-align: center;">
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
                <td style="padding: 8px; font-size: 11px; color: #334155;">{reason}</td>
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

        # 부동산 데이터 확보
        real_estate_data = weekly_data.get("real_estate_data")
        if not real_estate_data and RealEstateAdvisor:
            try:
                real_estate_data = RealEstateAdvisor().analyze_market()
            except Exception:
                real_estate_data = {}
        elif not real_estate_data:
            real_estate_data = {}

        # 주간 부동산 테이블 및 카드
        re_rows_weekly = ""
        for r in real_estate_data.get("regional_trends", []):
            sc = r.get("sale_change", "0.00%")
            jc = r.get("jeonse_change", "0.00%")
            sc_col = "#16A34A" if "+" in sc else ("#DC2626" if "-" in sc else "#64748B")
            jc_col = "#16A34A" if "+" in jc else ("#DC2626" if "-" in jc else "#64748B")
            re_rows_weekly += f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 7px 8px; font-weight: bold; color: #0F172A;">{r.get('region')}</td>
                <td style="padding: 7px 8px; text-align: right; color: {sc_col}; font-weight: bold;">{sc}</td>
                <td style="padding: 7px 8px; text-align: right; color: {jc_col}; font-weight: bold;">{jc}</td>
                <td style="padding: 7px 8px; text-align: center;"><span style="background: #F1F5F9; color: {r.get('status_color', '#334155')}; font-weight: bold; font-size: 10px; padding: 2px 6px; border-radius: 4px;">{r.get('status')}</span></td>
                <td style="padding: 7px 8px; font-size: 10.5px; color: #475569;">{r.get('summary')}</td>
            </tr>
            """
        re_mi = real_estate_data.get("mortgage_info", {})
        re_mm = real_estate_data.get("market_metrics", {})
        re_ag_cards = ""
        for ag in real_estate_data.get("action_guides", []):
            re_ag_cards += f"""
            <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-left: 4px solid #0284C7; border-radius: 4px; padding: 6px 10px; margin-bottom: 6px; font-size: 11px;">
                <b>🎯 {ag.get('target')}:</b> {ag.get('tip')}
            </div>
            """

        # 사후 검증 지표
        win_rate = stats.get('win_rate', 0)
        total_p = stats.get('total_picks', 0)
        succ_p = stats.get('success_count', 0)
        stop_p = stats.get('stoploss_count', 0)
        hold_p = stats.get('holding_count', 0)
        hold_pos = stats.get('holding_positive_count', 0)
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
        <span><b>Chapter 5. 대한민국 부동산 주간 동향 & 주담대 금리/규제 총결산</b> (권역별 시세 & DSR 분석)</span>
        <span style="font-weight: bold; color: #1E3A8A;">Section 05</span>
      </div>
      <div class="toc-item">
        <span><b>Chapter 6. 차주 시장 전망 및 섹터별 자산 배분 전략 가이드</b> (주요 경제 일정 및 포지션 제언)</span>
        <span style="font-weight: bold; color: #1E3A8A;">Section 06</span>
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
      <div style="font-size: 11px; color: #4338CA;">목표가 추적 중</div>
      <div style="font-size: 20px; font-weight: bold; color: #4338CA;">{hold_p}건</div>
      <div style="font-size: 9px; color: #6366F1;">(수익권 {hold_pos}건)</div>
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
  <div class="sec-h1">🏢 Chapter 5. 대한민국 부동산 주간 동향 & 주담대 금리/규제 총결산</div>
  <div style="font-size: 12px; color: #475569; margin-bottom: 12px;">
    한국부동산원 및 KB 통계 기반 전국 주요 권역별 매매·전세 시세 동향 및 주담대 금리 밴드 총결산입니다.
  </div>
  <table>
    <tr>
      <th style="width: 25%;">주요 권역</th>
      <th style="width: 13%; text-align: right;">주간 매매</th>
      <th style="width: 13%; text-align: right;">주간 전세</th>
      <th style="width: 18%; text-align: center;">시장 국면</th>
      <th style="width: 31%;">주요 동향 및 특징</th>
    </tr>
    {re_rows_weekly}
  </table>

  <div style="display: flex; gap: 10px; margin-bottom: 12px;">
    <div style="flex: 1; background: #F0F9FF; border: 1px solid #BAE6FD; border-radius: 6px; padding: 10px; font-size: 11px;">
      <div style="font-weight: bold; color: #0369A1; margin-bottom: 6px;">🏦 주택담보대출 금리 & 금융 규제</div>
      <div style="margin-bottom: 3px;">• <b>5년 고정(혼합형):</b> {re_mi.get('fixed_rate_band')}</div>
      <div style="margin-bottom: 3px;">• <b>변동금리:</b> {re_mi.get('variable_rate_band')} (COFIX {re_mi.get('cofix_rate')})</div>
      <div style="margin-bottom: 3px;">• <b>대출 규제:</b> {re_mi.get('dsr_status')}</div>
    </div>
    <div style="flex: 1; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px; font-size: 11px;">
      <div style="font-weight: bold; color: #0F172A; margin-bottom: 6px;">📈 거래량 & 수급 매트릭스</div>
      <div style="margin-bottom: 3px;">• <b>서울 월간 거래량:</b> {re_mm.get('monthly_volume')}</div>
      <div style="margin-bottom: 3px;">• <b>서울 평균 전세가율:</b> {re_mm.get('jeonse_ratio')}</div>
      <div style="margin-bottom: 3px;">• <b>청약 경쟁률:</b> {re_mm.get('bidding_ratio')}</div>
    </div>
  </div>
  {re_ag_cards}

  <div class="page-break"></div>

  <!-- Chapter 6 -->
  <div class="sec-h1">🔮 Chapter 6. 차주 시장 전망 및 포트폴리오 자산 배분 전략 가이드</div>
  <div style="background: #F8FAFC; border: 1px solid #CBD5E1; border-left: 4px solid #1E3A8A; border-radius: 8px; padding: 18px; font-size: 12px; line-height: 1.8;">
    <div style="font-weight: bold; color: #1E3A8A; font-size: 14px; margin-bottom: 8px;">
      💼 [전략기획실 종합 제언] 최고경영진을 위한 차주 자산배분 및 리스크 가이드
    </div>
    • <b>거시 매크로 환경:</b> 미 연준 통화정책 기조와 원달러 환율 1,390~1,410원대 밴드를 감안하여, 공격적 레버리지보다는 현금 비중 20~25%의 방어적 유동성을 유지하십시오.<br>
    • <b>핵심 주도 섹터:</b> 공식 리포트상 2026F/2027F 영업이익이 큰 폭으로 턴어라운드하는 AI 반도체 밸류체인 및 수주 잔고가 확정된 K-방산/원전 섹터의 눌림목 분할 매수가 유효합니다.<br>
    • <b>가상자산 포트폴리오:</b> 비트코인은 주요 이동평균선 지지선 안착 여부를 확인하며 분할 적립하고, 솔라나/알트코인은 변동성 확대를 고려해 목표가 도달 시 철저한 분할 익절을 권고합니다.<br>
    • <b>부동산 자산 전략:</b> 2단계 스트레스 DSR 대출 규제 속에서는 '선 매도 후 매수' 원칙을 철저히 지키며, 서울 핵심지 및 재건축 선도지구 위주의 압축 포트폴리오를 유지하십시오.<br>
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

    def generate_mobile_html_report(self, date_str: str, stock_indices: list, exchange_rates: list,
                                   stock_advice: dict, crypto_advice: dict, official_reports: list,
                                   news_result: dict, performance_data: dict, special_disclosures: list,
                                   story_dive_data: dict, output_html_path: str, real_estate_data: dict = None,
                                   edition: str = "morning", market_drivers: dict = None) -> str:
        """
        [아이폰/스마트폰 전용] 모바일 퍼스트 100% 반응형 인터랙티브 웹진 HTML 보고서 생성
        - PDF 21면 전수 콘텐츠 1:1 완벽 미러링 (누락 0%)
        - 핀치 줌 불필요, 폰트 15~16px 고가독성, 세로 스크롤 카드 UI
        - 상단 12개 섹션 터치 점프 네비게이션, 가로 스크롤 보호 테이블, 전수 기사/리포트 수록
        """
        is_evening = (str(edition).lower() == "evening") or ("저녁" in str(edition)) or ("이브닝" in str(edition))
        edition_label = "석간 이브닝 마감 에디션" if is_evening else "조간 모닝 프리미엄 에디션"
        theme_col = "#7C3AED" if is_evening else "#1E40AF"

        if not market_drivers:
            market_drivers = {
                "domestic_reason": "대외 거시경제 지표 및 글로벌 긴축 경계감 속에서 외국인·기관의 현선물 매물 출회 및 주도 섹터 차익 실현",
                "us_reason": "미 국채 금리 변동성 및 인플레이션 지표 발표에 따른 빅테크 기술주 중심의 차익 매물과 실적 관망세",
                "fx_reason": "글로벌 위험회피 심리 및 미 달러화 강약세 흐름에 연동된 완만한 환율 변동성"
            }

        nd = story_dive_data.get("newspaper_dossier", {}) if isinstance(story_dive_data, dict) else {}
        mega_d = nd.get("mega_dossier", {})
        trend_d = nd.get("trend_dossier", {})
        exp_reps = nd.get("expanded_reports", [])
        exp_discs = nd.get("expanded_disclosures", [])

        # =========================================================================
        # 1. 📊 지수 및 환율 카드 & 등락 원인
        # =========================================================================
        idx_cards = ""
        for idx in stock_indices:
            col = "#16A34A" if "+" in idx.get("전일대비", "") else "#DC2626"
            idx_cards += f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 14px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: bold; font-size: 15px; color: #0F172A;">{idx.get('지수명')}</span>
                <div style="text-align: right;">
                    <span style="font-weight: 800; font-size: 16px; color: #0F172A;">{idx.get('현재지수')}</span>
                    <span style="color: {col}; font-weight: bold; font-size: 13.5px; margin-left: 6px;">{idx.get('전일대비')}</span>
                </div>
            </div>
            """

        fx_cards = ""
        for fx in exchange_rates:
            col = "#16A34A" if "+" in fx.get("전일대비", "") else ("#DC2626" if "-" in fx.get("전일대비", "") else "#2563EB")
            fx_diff = fx.get('전일대비') or fx.get('변동/기준', '')
            fx_cards += f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: bold; font-size: 14px; color: #0F172A;">{fx.get('통화명')}</span>
                <div style="text-align: right;">
                    <span style="font-weight: 800; font-size: 15px; color: #0F172A;">{fx.get('환율(원)')}원</span>
                    <span style="color: {col}; font-size: 12px; margin-left: 6px;">{fx_diff}</span>
                </div>
            </div>
            """

        # =========================================================================
        # 2. 📰 1면 톱 기획특집 기사 (The Lead Story)
        # =========================================================================
        mega_html = ""
        if mega_d and mega_d.get("headline"):
            vc_html = ""
            if mega_d.get("value_chain"):
                vc_html = f"""
                <div style="margin-top: 12px; background: #F0FDF4; border: 1px solid #BBF7D0; border-left: 4px solid #16A34A; border-radius: 6px; padding: 12px; font-size: 13px; color: #166534; line-height: 1.55;">
                    <b>🎯 [핵심 투자 밸류체인 & 수혜주]:</b> {mega_d.get('value_chain')}
                </div>
                """
            mega_html = f"""
            <div id="mega" class="card" style="border-top: 4px solid #1E3A8A;">
                <span style="background: #1E3A8A; color: #FFF; font-size: 11px; font-weight: bold; padding: 3px 8px; border-radius: 4px;">📰 1면 톱 기획특집 • THE LEAD STORY</span>
                <div style="font-size: 18px; font-weight: 900; margin: 10px 0 6px; line-height: 1.4; color: #0F172A;">
                    {mega_d.get('headline')}
                </div>
                <div style="font-size: 14px; font-weight: bold; color: #2563EB; margin-bottom: 12px; line-height: 1.45;">
                    {mega_d.get('subhead', '')}
                </div>
                <div style="background: #F8FAFC; border-left: 4px solid #1E3A8A; padding: 12px 14px; font-size: 13.5px; color: #1E293B; margin-bottom: 14px; line-height: 1.6; font-style: italic;">
                    {mega_d.get('lead', '')}
                </div>
                <div style="font-size: 13.5px; color: #334155; line-height: 1.65;">
                    <div style="margin-bottom: 8px;">{mega_d.get('chapter1', '')}</div>
                    <div style="margin-bottom: 8px;">{mega_d.get('chapter2', '')}</div>
                    <div style="margin-bottom: 8px;">{mega_d.get('chapter3', '')}</div>
                    <div style="background: #EFF6FF; padding: 12px; border-radius: 6px; color: #1E40AF; border: 1px solid #DBEAFE;">{mega_d.get('chapter4', '')}</div>
                </div>
                {vc_html}
            </div>
            """

        # =========================================================================
        # 3. 🛍️ 2면 기획 르포: 2030 라이프스타일 & 소비 심리 (Trend Intelligence)
        # =========================================================================
        trend_html = ""
        if trend_d and trend_d.get("headline"):
            trend_html = f"""
            <div id="trend" class="card" style="border-top: 4px solid #DB2777;">
                <span style="background: #DB2777; color: #FFF; font-size: 11px; font-weight: bold; padding: 3px 8px; border-radius: 4px;">🛍️ 2면 기획 르포 • TREND INTELLIGENCE</span>
                <div style="font-size: 18px; font-weight: 900; margin: 10px 0 6px; line-height: 1.4; color: #9D174D;">
                    {trend_d.get('headline')}
                </div>
                <div style="font-size: 14px; font-weight: bold; color: #BE185D; margin-bottom: 12px; line-height: 1.45;">
                    {trend_d.get('subhead', '')}
                </div>
                <div style="background: #FDF2F8; border-left: 4px solid #DB2777; padding: 12px 14px; font-size: 13.5px; color: #1E293B; margin-bottom: 14px; line-height: 1.6; font-style: italic;">
                    {trend_d.get('lead', '')}
                </div>
                <div style="font-size: 13.5px; color: #334155; line-height: 1.65;">
                    <div style="margin-bottom: 8px;">{trend_d.get('chapter1', '')}</div>
                    <div style="margin-bottom: 8px;">{trend_d.get('chapter2', '')}</div>
                    <div style="margin-bottom: 8px;">{trend_d.get('chapter3', '')}</div>
                    <div style="background: #FFF1F2; padding: 12px; border-radius: 6px; color: #9F1239; border: 1px solid #FECDD3;">{trend_d.get('chapter4', '')}</div>
                </div>
                <div style="margin-top: 12px; background: #FEF9C3; border: 1px solid #FDE047; padding: 10px 14px; border-radius: 6px; font-size: 12.5px; color: #713F12; line-height: 1.55;">
                    💡 <b>1분 핵심 용어 사전:</b> <b>디토(Ditto) 소비</b>는 인플루언서·전문가 취향 추종 소비 행태를 뜻하며, <b>스몰 럭셔리(Small Luxury)</b>는 불황기 소액 고품질 소비재를 통해 심리적 만족을 극대화하는 행동 경제학적 선택입니다.
                </div>
            </div>
            """

        # =========================================================================
        # 4. 📘 3면 기업 심층 해부 (증권사 공식 Top 2 리포트 도시에)
        # =========================================================================
        rep_dossier_html = ""
        if exp_reps:
            for r in exp_reps[:2]:
                sec_boxes = ""
                if r.get('sec_business'):
                    sec_boxes += f"<div style='margin-bottom: 6px; background: #F8FAFC; padding: 10px; border-radius: 6px; font-size: 13px;'>{r['sec_business']}</div>"
                if r.get('sec_thesis'):
                    sec_boxes += f"<div style='margin-bottom: 6px; background: #F8FAFC; padding: 10px; border-radius: 6px; font-size: 13px;'>{r['sec_thesis']}</div>"
                if r.get('sec_financials'):
                    sec_boxes += f"<div style='margin-bottom: 6px; background: #F0FDF4; border: 1px solid #DCFCE7; padding: 10px; border-radius: 6px; color: #14532D; font-size: 13px;'>{r['sec_financials']}</div>"
                if r.get('sec_risks'):
                    sec_boxes += f"<div style='margin-bottom: 6px; background: #FFF1F2; border: 1px solid #FFE4E6; padding: 10px; border-radius: 6px; color: #9F1239; font-size: 13px;'>{r['sec_risks']}</div>"
                if r.get('sec_action'):
                    sec_boxes += f"<div style='background: #EFF6FF; border: 1px solid #DBEAFE; padding: 10px; border-radius: 6px; color: #1E40AF; font-size: 13px;'>{r['sec_action']}</div>"

                rep_dossier_html += f"""
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-top: 4px solid #16A34A; border-radius: 8px; padding: 14px; margin-bottom: 14px;">
                    <div style="font-size: 16px; font-weight: bold; color: #166534; margin-bottom: 4px;">{r.get('headline', '')}</div>
                    <div style="font-size: 12.5px; color: #64748B; margin-bottom: 10px; border-bottom: 1px solid #E2E8F0; padding-bottom: 6px;">{r.get('subhead', '')}</div>
                    {sec_boxes}
                </div>
                """
        elif official_reports:
            for r in official_reports[:2]:
                tp = r.get("target_price")
                tp_str = f"{int(tp):,}원" if tp else "-"
                rep_dossier_html += f"""
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-left: 4px solid #16A34A; border-radius: 8px; padding: 14px; margin-bottom: 12px;">
                    <div style="font-size: 15px; font-weight: bold; color: #166534;">[{r.get('broker')}] {r.get('item_name')}: {r.get('title')}</div>
                    <div style="margin: 6px 0; background: #DCFCE7; padding: 6px 10px; border-radius: 4px; font-size: 13px; color: #14532D;">
                        🎯 <b>공인 목표주가:</b> {tp_str} &nbsp;|&nbsp; 📌 <b>투자의견:</b> {r.get('opinion', 'BUY')} &nbsp;|&nbsp; ⭐ 신뢰도: {r.get('credibility_score')}점
                    </div>
                    <div style="color: #334155; font-size: 13px; line-height: 1.55;">{r.get('summary_text', '')}</div>
                </div>
                """

        # =========================================================================
        # 5. 🏛️ 4면 & 5면 DART 특수공시 심층 행간 및 일람표
        # =========================================================================
        disc_dossier_html = ""
        if exp_discs:
            for d in exp_discs[:2]:
                disc_boxes = ""
                if d.get('sec_context'):
                    disc_boxes += f"<div style='margin-bottom: 6px; background: #FFFBEB; border: 1px solid #FEF3C7; padding: 10px; border-radius: 6px; color: #78350F; font-size: 13px;'>{d['sec_context']}</div>"
                if d.get('sec_governance'):
                    disc_boxes += f"<div style='margin-bottom: 6px; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 10px; border-radius: 6px; color: #334155; font-size: 13px;'>{d['sec_governance']}</div>"
                if d.get('sec_strategy'):
                    disc_boxes += f"<div style='background: #F0FDF4; border: 1px solid #DCFCE7; padding: 10px; border-radius: 6px; color: #166534; font-size: 13px;'>{d['sec_strategy']}</div>"

                disc_dossier_html += f"""
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-top: 4px solid #D97706; border-radius: 8px; padding: 14px; margin-bottom: 14px;">
                    <div style="font-size: 15.5px; font-weight: bold; color: #92400E; margin-bottom: 8px;">{d.get('headline', '')}</div>
                    {disc_boxes}
                </div>
                """

        disc_cards_all = ""
        for d in special_disclosures[:7]:
            corp_name = d.get('관련기업') or '상장사'
            badge = d.get('공시배지', '특수공시')
            badge_bg = "#DCFCE7" if "자사주" in badge else ("#DBEAFE" if "내부자" in badge else ("#FEF3C7" if "수주" in badge else "#F3E8FF"))
            badge_fg = "#166534" if "자사주" in badge else ("#1E40AF" if "내부자" in badge else ("#92400E" if "수주" in badge else "#6B21A8"))
            disc_cards_all += f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid {badge_fg}; border-radius: 6px; padding: 12px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-weight: bold; font-size: 14px; color: #0F172A;">{corp_name}</span>
                    <span style="background: {badge_bg}; color: {badge_fg}; font-size: 11px; font-weight: bold; padding: 2px 7px; border-radius: 4px;">{badge}</span>
                </div>
                <div style="font-size: 13.5px; font-weight: bold; color: #1E293B; margin-bottom: 6px;">
                    <a href="{d.get('링크', '#')}" style="color: #1E293B; text-decoration: none;">{d.get('공시제목')}</a>
                </div>
                <div style="font-size: 12.5px; color: #475569; margin-bottom: 4px;">💡 <b>영향 전망:</b> {d.get('영향전망')}</div>
                <div style="font-size: 12.5px; color: #166534; font-weight: 500; background: #F0FDF4; padding: 6px 8px; border-radius: 4px;">🎯 <b>투자 전략:</b> {d.get('투자전략')}</div>
            </div>
            """

        # =========================================================================
        # 6. 📈 국내 주식 퀀트 추천 매트릭스 (20일 SVG 차트 포함)
        # =========================================================================
        today_buys = stock_advice.get("today_buy_picks", [])
        long_buys = stock_advice.get("longterm_buy_picks", [])
        sell_picks = stock_advice.get("sell_warning_picks", [])

        domestic_stock_cards = ""
        if today_buys:
            for b in today_buys[:4]:
                sparkline = self.generate_svg_sparkline(b.get("recent_closes", []))
                domestic_stock_cards += f"""
                <div style="background: #FFFFFF; border: 1px solid #BBF7D0; border-top: 3px solid #16A34A; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <div>
                            <span style="background: #DCFCE7; color: #166534; font-size: 11px; font-weight: bold; padding: 2px 6px; border-radius: 4px;">🟢 단기 매수</span>
                            <b style="font-size: 15px; color: #0F172A; margin-left: 6px;">{b.get('name')}</b>
                            <span style="font-size: 11px; color: #64748B;">({b.get('ticker')})</span>
                        </div>
                        <div>{sparkline}</div>
                    </div>
                    <div style="background: #F0FDF4; padding: 8px 10px; border-radius: 4px; font-size: 13px; color: #15803D; margin-bottom: 6px;">
                        현재가: <b>{b.get('cur_price')}</b> &nbsp;|&nbsp; 매수가: <b>{b.get('buy_price')}</b> ➔ 목표가: <b>{b.get('sell_price')}</b> <span style="font-size: 11px; font-weight: bold;">({b.get('expected_yield')})</span>
                    </div>
                    <div style="font-size: 12px; color: #475569;">
                        💡 <b>근거:</b> {b.get('reason', b.get('type', ''))} &nbsp;|&nbsp; 🛑 손절 기준가: {b.get('stop_loss', '-')}
                    </div>
                </div>
                """

        if long_buys:
            for lb in long_buys[:3]:
                sparkline = self.generate_svg_sparkline(lb.get("recent_closes", []))
                domestic_stock_cards += f"""
                <div style="background: #FFFFFF; border: 1px solid #BFDBFE; border-top: 3px solid #2563EB; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <div>
                            <span style="background: #DBEAFE; color: #1E40AF; font-size: 11px; font-weight: bold; padding: 2px 6px; border-radius: 4px;">🔵 장기 적립</span>
                            <b style="font-size: 15px; color: #0F172A; margin-left: 6px;">{lb.get('name')}</b>
                            <span style="font-size: 11px; color: #64748B;">({lb.get('ticker')})</span>
                        </div>
                        <div>{sparkline}</div>
                    </div>
                    <div style="background: #EFF6FF; padding: 8px 10px; border-radius: 4px; font-size: 13px; color: #1D4ED8; margin-bottom: 6px;">
                        현재가: <b>{lb.get('cur_price')}</b> &nbsp;|&nbsp; 분할매수가: <b>{lb.get('buy_price')}</b> ➔ 장기목표: <b>{lb.get('sell_price')}</b> ({lb.get('expected_yield')})
                    </div>
                    <div style="font-size: 12px; color: #475569;">
                        💡 <b>특징:</b> {lb.get('reason', lb.get('type', ''))}
                    </div>
                </div>
                """

        if sell_picks:
            for s in sell_picks[:3]:
                sparkline = self.generate_svg_sparkline(s.get("recent_closes", []))
                domestic_stock_cards += f"""
                <div style="background: #FFFFFF; border: 1px solid #FECACA; border-top: 3px solid #DC2626; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <div>
                            <span style="background: #FEE2E2; color: #991B1B; font-size: 11px; font-weight: bold; padding: 2px 6px; border-radius: 4px;">🔴 과열 주의</span>
                            <b style="font-size: 15px; color: #991B1B; margin-left: 6px;">{s.get('name')}</b>
                            <span style="font-size: 11px; color: #991B1B;">({s.get('ticker')})</span>
                        </div>
                        <div>{sparkline}</div>
                    </div>
                    <div style="background: #FEF2F2; padding: 8px 10px; border-radius: 4px; font-size: 13px; color: #991B1B; margin-bottom: 6px;">
                        현재가: <b>{s.get('cur_price')}</b> &nbsp;|&nbsp; 권고매도가: <b>{s.get('sell_price')}</b> (비중 축소 권고)
                    </div>
                    <div style="font-size: 12px; color: #7F1D1D;">
                        ⚠️ <b>경고 사유:</b> {s.get('type', '')} (이격도 {s.get('disparity', '-')})
                    </div>
                </div>
                """

        # =========================================================================
        # 7. 🇺🇸 미국 글로벌 빅테크 4대장 집중 분석 (20일 SVG 차트)
        # =========================================================================
        us_bigtech_cards = ""
        for u in stock_advice.get("us_bigtech_picks", []):
            sparkline = self.generate_svg_sparkline(u.get("recent_closes", []))
            col = "#16A34A" if "+" in u.get('전일대비', '') else "#DC2626"
            us_bigtech_cards += f"""
            <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div>
                        <span style="font-weight: bold; font-size: 15px; color: #0F172A;">🇺🇸 {u.get('종목명')}</span>
                        <span style="font-size: 11.5px; color: #64748B;">({u.get('티커')})</span>
                    </div>
                    <div>{sparkline}</div>
                </div>
                <div style="font-size: 13.5px; margin-bottom: 6px;">
                    현재가: <b>{u.get('현재가')}</b> <span style="color: {col}; font-weight: bold;">({u.get('전일대비')})</span>
                </div>
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; padding: 8px 10px; border-radius: 4px; font-size: 12.5px; color: #1E3A8A; margin-bottom: 4px;">
                    👉 <b>매수가 ➔ 목표가:</b> {u.get('매수_추천금액')} ➔ <b>{u.get('목표_매도금액')}</b> <span style="font-size: 11px; font-weight: bold; background: #DBEAFE; color: #1E40AF; padding: 1px 5px; border-radius: 3px;">(기대수익 {u.get('기대_수익률')})</span>
                </div>
                <div style="font-size: 11.5px; color: #64748B;">
                    신호: <b>{u.get('단기신호')}</b> &nbsp;|&nbsp; 20일선 이격도: {u.get('20일선이격도')} &nbsp;|&nbsp; RSI(14): {u.get('RSI(14)')}
                </div>
            </div>
            """

        # =========================================================================
        # 8. 🪙 7면 가상자산 전용 인텔리전스 (온체인 수급, 지지/저항, 업비트 Top 5)
        # =========================================================================
        macro_c = crypto_advice.get("macro_indicators", {})
        fg_val = macro_c.get("fear_greed_val", 60)
        fg_label = macro_c.get("fear_greed_label", "중립 (Neutral)")
        kimchi_p = macro_c.get("kimchi_premium", "+0.0%")
        btc_dom = macro_c.get("btc_dominance", "57.6%")

        upbit_top_html = ""
        for idx, tv in enumerate(macro_c.get("top_volume_coins", []), 1):
            chg = tv.get("change", "0.0%")
            chg_col = "#16A34A" if "+" in chg else "#DC2626"
            upbit_top_html += f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid #F1F5F9; font-size: 13px;">
                <span><b>{idx}. {tv.get('symbol')}</b></span>
                <span><b>{tv.get('price')}</b> <span style="color: {chg_col}; font-weight: bold;">({chg})</span></span>
                <span style="color: #64748B; font-size: 11.5px;">거래대금 {tv.get('volume')}</span>
            </div>
            """

        coin_cards_html = ""
        for c in crypto_advice.get("coins", []):
            sparkline = self.generate_svg_sparkline(c.get("recent_closes", []))
            col = "#16A34A" if "+" in c.get('change_rate', '') else "#DC2626"
            coin_cards_html += f"""
            <div style="background: #FFFFFF; border: 1px solid #E9D5FF; border-top: 3px solid #7E22CE; border-radius: 8px; padding: 12px 14px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div style="font-size: 15px; font-weight: bold; color: #581C87;">
                        {c.get('icon')} {c.get('name')} <span style="font-size: 11.5px; color: #64748B;">({c.get('symbol')})</span>
                    </div>
                    <div>{sparkline}</div>
                </div>
                <div style="font-size: 13.5px; margin-bottom: 6px;">
                    현재가: <b>{c.get('cur_price')}</b> <span style="color: {col}; font-weight: bold;">({c.get('change_rate')})</span>
                </div>
                <div style="background: #FAF5FF; padding: 8px 10px; border-radius: 4px; font-size: 12.5px; color: #581C87; margin-bottom: 6px;">
                    💰 <b>매수가:</b> {c.get('buy_price')} ➔ 🎯 <b>목표가:</b> <b>{c.get('sell_price')}</b> ({c.get('expected_yield')})<br>
                    🛑 <b>손절가:</b> {c.get('stop_loss')} &nbsp;|&nbsp; 📊 <b>RSI(14):</b> {c.get('rsi')}
                </div>
                <div style="font-size: 12px; color: #475569; margin-bottom: 6px;">
                    🛡️ 지지선: 1차 {c.get('sup1')} / 2차 {c.get('sup2')} &nbsp;|&nbsp; ⚔️ 저항선: 1차 {c.get('res1')} / 2차 {c.get('res2')}
                </div>
                <div style="font-size: 12px; color: #374151; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 8px; border-radius: 4px; line-height: 1.45;">
                    🐋 <b>온체인·ETF 수급:</b> {c.get('onchain_desc')}<br>
                    💡 <b>트레이딩 관점:</b> {c.get('outlook')} [{c.get('signal')}]
                </div>
            </div>
            """

        # =========================================================================
        # 9. 🏢 8면 대한민국 부동산 시장 동향 (7대 권역, 주담대, 거래량, 실수요자 가이드)
        # =========================================================================
        re_cards = ""
        for r in (real_estate_data or {}).get("regional_trends", []):
            sc = r.get("sale_change", "0.00%")
            jc = r.get("jeonse_change", "0.00%")
            sc_col = "#16A34A" if "+" in sc else ("#DC2626" if "-" in sc else "#64748B")
            jc_col = "#16A34A" if "+" in jc else ("#DC2626" if "-" in jc else "#64748B")
            re_cards += f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-weight: bold; font-size: 14.5px; color: #0F172A;">{r.get('region')}</span>
                    <span style="background: #EFF6FF; color: {r.get('status_color', '#1E40AF')}; font-weight: bold; font-size: 11px; padding: 2px 8px; border-radius: 12px;">{r.get('status')}</span>
                </div>
                <div style="font-size: 13px; margin-bottom: 6px; color: #334155;">
                    매매 <b style="color: {sc_col};">{sc}</b> &nbsp;|&nbsp; 전세 <b style="color: {jc_col};">{jc}</b>
                </div>
                <div style="font-size: 12.5px; color: #64748B; line-height: 1.45;">
                    {r.get('summary')}
                </div>
            </div>
            """

        mi = (real_estate_data or {}).get("mortgage_info", {})
        mm = (real_estate_data or {}).get("market_metrics", {})
        ag_cards = ""
        for ag in (real_estate_data or {}).get("action_guides", []):
            ag_cards += f"""
            <div style="background: #F0F9FF; border: 1px solid #BAE6FD; border-left: 4px solid #0284C7; border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; font-size: 12.5px; line-height: 1.5;">
                <b>🎯 {ag.get('target')}:</b> {ag.get('tip')}
            </div>
            """

        # =========================================================================
        # 10. 🎯 9면 추천 종목 사후 검증(Backtesting) 성과 백서
        # =========================================================================
        p_sum = performance_data.get("summary", {}) if isinstance(performance_data, dict) else {}
        p_records = performance_data.get("records", []) if isinstance(performance_data, dict) else []
        backtest_cards_html = ""
        for r in p_records[:12]:
            res = r.get("검증결과", "")
            if "달성" in res:
                badge_bg, badge_fg = "#DCFCE7", "#166534"
            elif "손절" in res:
                badge_bg, badge_fg = "#FEE2E2", "#991B1B"
            else:
                badge_bg, badge_fg = "#DBEAFE", "#1E40AF"

            backtest_cards_html += f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 12px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-weight: bold; font-size: 13.5px; color: #0F172A;">{r.get('종목명')} <span style="font-size: 11px; color: #64748B;">({r.get('티커')})</span></span>
                    <span style="background: {badge_bg}; color: {badge_fg}; font-size: 11px; font-weight: bold; padding: 2px 7px; border-radius: 10px;">{res}</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 12.5px; color: #334155; margin-bottom: 4px;">
                    <span>추천: {r.get('매수추천가')} ➔ 목표: <b>{r.get('목표매도가')}</b></span>
                    <span style="font-weight: bold; color: {'#16A34A' if '+' in str(r.get('실현수익률','')) else '#DC2626'}; font-size: 13px;">{r.get('실현수익률')}</span>
                </div>
                <div style="font-size: 11px; color: #94A3B8;">
                    추천일: {r.get('추천일자')} &nbsp;|&nbsp; 최고도달가: {r.get('최고도달가')} &nbsp;|&nbsp; 소요일: {r.get('소요일수')}
                </div>
            </div>
            """

        # =========================================================================
        # 11. 📰 7대 분야별 주요 뉴스 와이어 (전수 기사 - 뒷부분 누락 원천 차단)
        # =========================================================================
        news_sections = ""
        top_picks = news_result.get("category_top_picks", {})
        # 정확한 카테고리 매핑 키 리스트 (뒷부분 연예, 세계, 사회 누락 방지)
        canonical_cats = [
            ("거시경제/비즈니스", "💼 거시경제 & 비즈니스"),
            ("정치", "🏛️ 정치 핵심 이슈"),
            ("IT/과학/신상품", "💻 IT·과학 & 테크/신상품"),
            ("세계/국제", "🌍 세계·국제 정세"),
            ("사회/사건사고", "🚨 사회·사건사고 이슈"),
            ("연예/대중문화", "🎬 연예·문화 트렌드"),
        ]

        # 1) 공인 6대 분야 순차 수록
        for cat_k, cat_label in canonical_cats:
            items = top_picks.get(cat_k, [])
            if not items:
                continue
            item_html = ""
            for idx, it in enumerate(items):
                link = it.get("링크") or it.get("link", "#")
                c_sum = it.get("content_summary") or it.get("요약내용", "")
                exp_in = it.get("expanded_insight", "")
                tag = f" <span style='background: #FEE2E2; color: #DC2626; font-size: 11px; padding: 1px 5px; border-radius: 3px; font-weight: bold;'>{it.get('상태')}</span>" if "집중" in str(it.get('상태', '')) else ""
                
                insight_box = ""
                if exp_in:
                    insight_box = f"""
                    <div style="font-size: 12.5px; color: #1E40AF; background: #EFF6FF; padding: 8px 10px; border-radius: 5px; line-height: 1.5; border-left: 3px solid #2563EB; margin-top: 6px;">
                        {exp_in}
                    </div>
                    """
                else:
                    insight_box = f"""
                    <div style="font-size: 12px; color: #1E40AF; background: #EFF6FF; padding: 7px 10px; border-radius: 5px; line-height: 1.45; border-left: 3px solid #2563EB; margin-top: 6px;">
                        <b>💡 심층 맥락 & 시사점:</b> 산업계 및 정책 환경 후속 변화와 공급망 파급 효과 지속 모니터링 필요.
                    </div>
                    """

                item_html += f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px;">
                    <div style="font-size: 14.5px; font-weight: bold; color: #0F172A; line-height: 1.4; margin-bottom: 5px;">
                        <a href="{link}" style="color: #0F172A; text-decoration: none;">[{idx+1}] {it.get('기사제목')}</a>
                        <span style="font-size: 11px; color: #64748B; font-weight: normal;">({it.get('언론사')})</span>{tag}
                    </div>
                    <div style="font-size: 13px; color: #334155; line-height: 1.5; background: #F8FAFC; padding: 8px 10px; border-radius: 5px; border-left: 3px solid #3B82F6;">
                        <b>📰 핵심 팩트:</b> {c_sum}
                    </div>
                    {insight_box}
                </div>
                """

            news_sections += f"""
            <div style="margin-top: 20px;">
                <div style="font-size: 16px; font-weight: 800; color: #0F172A; margin-bottom: 10px; border-bottom: 2px solid {theme_col}; padding-bottom: 5px; display: flex; justify-content: space-between;">
                    <span>{cat_label}</span>
                    <span style="font-size: 12px; color: #2563EB; font-weight: bold;">{len(items)}건 전수 수록</span>
                </div>
                {item_html}
            </div>
            """

        # 2) 혹시 canonical_cats 외에 수집된 동적 카테고리가 있다면 전수 수록 (누락 방지)
        known_keys = {k for k, _ in canonical_cats}
        for extra_k, extra_items in top_picks.items():
            if extra_k not in known_keys and extra_items:
                extra_html = ""
                for idx, it in enumerate(extra_items):
                    link = it.get("링크") or it.get("link", "#")
                    extra_html += f"""
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                        <div style="font-size: 14px; font-weight: bold;"><a href="{link}" style="color: #0F172A; text-decoration: none;">[{idx+1}] {it.get('기사제목')}</a> ({it.get('언론사')})</div>
                        <div style="font-size: 12.5px; color: #475569; margin-top: 4px;">{it.get('요약내용', '')}</div>
                    </div>
                    """
                news_sections += f"""
                <div style="margin-top: 20px;">
                    <div style="font-size: 16px; font-weight: 800; color: #0F172A; margin-bottom: 10px; border-bottom: 2px solid {theme_col}; padding-bottom: 5px;">
                        <span>🌐 {extra_k}</span>
                    </div>
                    {extra_html}
                </div>
                """

        # =========================================================================
        # 12. 📚 10~21면 증권사 공식 리포트 Top 10 전문 요약 & 재무 추정치 표
        # =========================================================================
        official_reports_html = ""
        for r in official_reports[:10]:
            tp = r.get("target_price")
            tp_str = f"{int(tp):,}원" if tp else "-"
            ft = r.get("financial_table", {})
            ft_box = ""
            if ft.get("has_table"):
                ft_box = f"""
                <div style="margin: 8px 0; background: #DCFCE7; border: 1px dashed #16A34A; padding: 8px 10px; border-radius: 6px; font-size: 12px; color: #14532D; line-height: 1.5;">
                    📊 <b>공식 실적 추정치 표:</b><br>
                    • <b>2026F:</b> 매출 {ft.get('rev_2026', '-')} / 영업이익 {ft.get('op_2026', '-')}<br>
                    • <b>2027F:</b> 매출 {ft.get('rev_2027', '-')} / 영업이익 {ft.get('op_2027', '-')}<br>
                    <span style="color: #166534; font-size: 11.5px;">📈 <i>{ft.get('yoy_summary', '')}</i></span>
                </div>
                """
            official_reports_html += f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid #16A34A; border-radius: 8px; padding: 14px; margin-bottom: 12px;">
                <div style="font-weight: bold; color: #15803D; font-size: 15px; margin-bottom: 4px;">
                    🏛️ [{r.get('broker')}] <b>{r.get('item_name')}</b>: {r.get('title')}
                    <span style="font-size: 11px; background: #DCFCE7; color: #166534; padding: 2px 7px; border-radius: 10px; margin-left: 6px;">신뢰도 ⭐ {r.get('credibility_score')}점</span>
                </div>
                <div style="background: #F0FDF4; padding: 6px 10px; border-radius: 4px; font-size: 12.5px; color: #14532D; margin-bottom: 6px;">
                    🎯 <b>공인 목표주가:</b> <span style="font-weight: bold; color: #166534;">{tp_str}</span> &nbsp;|&nbsp; 📌 <b>투자의견:</b> {r.get('opinion', 'BUY')}
                </div>
                {ft_box}
                <div style="color: #374151; font-size: 12.5px; line-height: 1.55; margin-top: 6px;">
                    💡 <b>핵심 요지:</b> {r.get('summary_text', '')}
                </div>
            </div>
            """

        # =========================================================================
        # 13. 전체 HTML 조립
        # =========================================================================
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>나만의 인텔리전스 모바일 웹리포트 ({date_str})</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
    background: #F1F5F9;
    color: #0F172A;
    margin: 0;
    padding: 0;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }}
  .container {{
    max-width: 680px;
    margin: 0 auto;
    background: #FFFFFF;
    min-height: 100vh;
    box-shadow: 0 0 20px rgba(0,0,0,0.05);
  }}
  .header {{
    background: linear-gradient(135deg, {theme_col} 0%, #0F172A 100%);
    color: #FFFFFF;
    padding: 24px 20px;
    text-align: center;
  }}
  .nav-bar {{
    position: sticky;
    top: 0;
    background: rgba(255, 255, 255, 0.96);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid #E2E8F0;
    display: flex;
    overflow-x: auto;
    white-space: nowrap;
    padding: 10px 14px;
    gap: 10px;
    z-index: 100;
    -webkit-overflow-scrolling: touch;
  }}
  .nav-bar::-webkit-scrollbar {{
    display: none;
  }}
  .nav-item {{
    color: #475569;
    text-decoration: none;
    font-size: 12.5px;
    font-weight: 700;
    padding: 5px 12px;
    background: #F1F5F9;
    border-radius: 16px;
    border: 1px solid #E2E8F0;
    flex-shrink: 0;
  }}
  .content {{
    padding: 20px 16px 40px;
  }}
  .card {{
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
  }}
  .sec-title {{
    font-size: 17px;
    font-weight: 800;
    color: #0F172A;
    margin: 0 0 12px;
    border-bottom: 2px solid {theme_col};
    padding-bottom: 6px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div style="font-size: 11px; letter-spacing: 2px; color: #93C5FD; text-transform: uppercase; font-weight: bold; margin-bottom: 4px;">MY DAILY INTELLIGENCE HERALD</div>
    <div style="font-size: 22px; font-weight: 900; letter-spacing: -0.5px;">나만의 모바일 인텔리전스 웹리포트</div>
    <div style="font-size: 13px; margin-top: 6px; opacity: 0.95;">{date_str} • {edition_label} (PDF 21면 전수 미러링)</div>
  </div>

  <div class="nav-bar">
    <a href="#action" class="nav-item">🎯 3대결단</a>
    <a href="#macro" class="nav-item">📊 증시/환율</a>
    <a href="#mega" class="nav-item">🌐 1면기획</a>
    <a href="#trend" class="nav-item">🛍️ 2면트렌드</a>
    <a href="#rep_dossier" class="nav-item">📘 3면기업해부</a>
    <a href="#dart" class="nav-item">🏛️ 4·5면공시</a>
    <a href="#stocks" class="nav-item">📈 국내주식</a>
    <a href="#bigtech" class="nav-item">🇺🇸 미국빅테크</a>
    <a href="#crypto" class="nav-item">🪙 가상자산</a>
    <a href="#re" class="nav-item">🏢 부동산(7대권역)</a>
    <a href="#backtest" class="nav-item">🎯 백테스팅</a>
    <a href="#news" class="nav-item">📰 전수기사</a>
    <a href="#official_reps" class="nav-item">📚 공식리포트10선</a>
  </div>

  <div class="content">

    <!-- 1. 3대 결단 체크리스트 -->
    <div id="action" class="card" style="background: #EFF6FF; border: 1px solid #BFDBFE; border-left: 5px solid #2563EB;">
      <div style="font-weight: 800; font-size: 15.5px; color: #1E40AF; margin-bottom: 8px;">🎯 오늘의 핵심 경영 & 투자 결단 체크포인트 (Executive Action Checklist)</div>
      <div style="font-size: 13.5px; color: #1E3A8A; line-height: 1.65;">
        1. <b>거시 리스크 관리:</b> 글로벌 증시 및 환율 변동성 국면에서 무리한 추격 매수를 지양하고 방어적 현금 25% 유지<br>
        2. <b>실적 턴어라운드 압축:</b> 2026/2027 예상 실적 급증 및 확정 수주 모멘텀 보유주 중심 분할 매수<br>
        3. <b>자산 양극화 방어:</b> 서울 핵심지(강남·마용성·여의도/영등포) 및 1기 신도시 재건축 선도지구 압축 보유 지속
      </div>
    </div>

    <!-- 2. 글로벌 증시 & 환율 및 등락 원인 -->
    <div id="macro" class="card">
      <div class="sec-title">📊 글로벌 증시 및 환율 현황</div>
      {idx_cards}
      {fx_cards}
      <div style="background: #F8FAFC; border: 1px solid #CBD5E1; border-left: 4px solid #2563EB; padding: 12px; border-radius: 6px; font-size: 13px; margin-top: 12px; line-height: 1.55;">
        <div style="font-weight: bold; color: #1E40AF; margin-bottom: 4px;">💡 당일 글로벌 증시 및 외환시장 등락 원인 분석</div>
        <div>• <b>국내 증시:</b> {market_drivers.get('domestic_reason')}</div>
        <div style="margin-top: 4px;">• <b>미국 증시:</b> {market_drivers.get('us_reason')}</div>
        <div style="margin-top: 4px;">• <b>외환 시장:</b> {market_drivers.get('fx_reason')}</div>
      </div>
    </div>

    <!-- 3. 1면 톱 기획특집 기사 -->
    {mega_html}

    <!-- 4. 2면 기획 르포: 2030 트렌드 & 소비 심리 -->
    {trend_html}

    <!-- 5. 3면 기업 심층 해부: 증권사 공식 리포트 Top 2 -->
    <div id="rep_dossier" class="card">
      <div class="sec-title">📘 [3면] 기업 정밀 해부 • EQUITY RESEARCH DOSSIER</div>
      {rep_dossier_html}
    </div>

    <!-- 6. 4면 & 5면 DART 특수공시 심층 행간 및 종합 일람표 -->
    <div id="dart" class="card">
      <div class="sec-title">🏛️ [4·5면] 금융감독원(DART) 특수공시 심층 행간 & 일람표</div>
      {disc_dossier_html}
      <div style="font-weight: bold; font-size: 14px; color: #92400E; margin: 14px 0 8px;">📋 당일 DART & KIND 특수공시 전수 카드 일람</div>
      {disc_cards_all}
    </div>

    <!-- 7. 6면 국내 주식 퀀트 하이브리드 추천 매트릭스 -->
    <div id="stocks" class="card">
      <div class="sec-title">📈 [6면] 국내 주식 하이브리드 추천 매트릭스 (20일 주가 변화 차트)</div>
      {domestic_stock_cards}
    </div>

    <!-- 8. 미국 글로벌 빅테크 4대장 집중 분석 -->
    <div id="bigtech" class="card">
      <div class="sec-title">🇺🇸 미국 글로벌 빅테크 4대장 (NVDA, TSLA, AAPL, MSFT) 집중 분석</div>
      {us_bigtech_cards}
    </div>

    <!-- 9. 7면 가상자산 전용 인텔리전스 -->
    <div id="crypto" class="card">
      <div class="sec-title">🪙 [7면] 가상자산 전용 인텔리전스 • CRYPTO ASSET INTELLIGENCE</div>
      <div style="display: flex; gap: 8px; margin-bottom: 12px; text-align: center;">
        <div style="flex: 1; background: #FAF5FF; border: 1px solid #E9D5FF; border-radius: 6px; padding: 10px;">
          <div style="font-size: 11px; color: #6B21A8;">공포 & 탐욕</div>
          <div style="font-size: 18px; font-weight: bold; color: #7E22CE;">{fg_val}점</div>
          <div style="font-size: 10.5px; font-weight: bold; color: #581C87;">{fg_label}</div>
        </div>
        <div style="flex: 1; background: #FAF5FF; border: 1px solid #E9D5FF; border-radius: 6px; padding: 10px;">
          <div style="font-size: 11px; color: #6B21A8;">김치 프리미엄</div>
          <div style="font-size: 18px; font-weight: bold; color: #16A34A;">{kimchi_p}</div>
          <div style="font-size: 10.5px; color: #475569;">차익 거래</div>
        </div>
        <div style="flex: 1; background: #FAF5FF; border: 1px solid #E9D5FF; border-radius: 6px; padding: 10px;">
          <div style="font-size: 11px; color: #6B21A8;">BTC 도미넌스</div>
          <div style="font-size: 18px; font-weight: bold; color: #1E40AF;">{btc_dom}</div>
          <div style="font-size: 10.5px; color: #475569;">시장 점유율</div>
        </div>
      </div>
      <div style="font-weight: bold; font-size: 13.5px; color: #581C87; margin-bottom: 8px;">⚡ 업비트 24시간 거래대금 최상위 코인 Top 5</div>
      <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 6px 12px; margin-bottom: 12px;">
        {upbit_top_html}
      </div>
      <div style="font-weight: bold; font-size: 13.5px; color: #581C87; margin-bottom: 8px;">🎯 3대 코인(BTC, ETH, SOL) 온체인 수급 및 지지·저항선</div>
      {coin_cards_html}
    </div>

    <!-- 10. 8면 대한민국 부동산 시장 동향 (7대 권역) -->
    <div id="re" class="card">
      <div class="sec-title">🏢 [8면] 대한민국 부동산 7대 권역 실시간 인텔리전스</div>
      {re_cards}
      <div style="background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px; margin-bottom: 12px; font-size: 12.5px;">
        <div style="font-weight: bold; color: #0369A1; margin-bottom: 4px;">🏦 주택담보대출 금리 밴드 & 대출 규제</div>
        <div>• <b>5년 고정 혼합형:</b> {mi.get('fixed_rate_band')} &nbsp;|&nbsp; <b>변동금리:</b> {mi.get('variable_rate_band')}</div>
        <div>• <b>대출 규제:</b> {mi.get('dsr_status')}</div>
        <div style="color: #64748B; font-size: 12px; margin-top: 4px;">• <b>서울 월간 거래량:</b> {mm.get('monthly_volume')} (매물 {mm.get('listing_inventory')})</div>
      </div>
      <div style="font-weight: bold; font-size: 13.5px; color: #0369A1; margin-bottom: 6px;">🧭 실수요자 실전 행동 요령</div>
      {ag_cards}
    </div>

    <!-- 11. 9면 추천 종목 사후 검증(Backtesting) 성과 백서 -->
    <div id="backtest" class="card" style="background: #EFF6FF; border: 1px solid #BFDBFE;">
      <div class="sec-title" style="color: #1E40AF; border-bottom-color: #3B82F6;">🎯 [9면] 추천 종목 사후 검증(Backtesting) 성과 백서</div>
      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; text-align: center; margin-bottom: 14px;">
        <div style="background: #FFFFFF; padding: 10px; border-radius: 6px; border: 1px solid #DBEAFE;">
          <div style="font-size: 11px; color: #1E40AF;">누적 적중 승률</div>
          <div style="font-size: 20px; font-weight: 900; color: #1D4ED8;">{p_sum.get('win_rate', 0)}%</div>
        </div>
        <div style="background: #FFFFFF; padding: 10px; border-radius: 6px; border: 1px solid #DBEAFE;">
          <div style="font-size: 11px; color: #166534;">목표가 달성</div>
          <div style="font-size: 20px; font-weight: 900; color: #16A34A;">{p_sum.get('success_count', 0)}건</div>
        </div>
        <div style="background: #FFFFFF; padding: 10px; border-radius: 6px; border: 1px solid #DBEAFE;">
          <div style="font-size: 11px; color: #4338CA;">목표가 추적 중</div>
          <div style="font-size: 20px; font-weight: 900; color: #4338CA;">{p_sum.get('holding_count', 0)}건</div>
          <div style="font-size: 9.5px; color: #6366F1;">(수익권 {p_sum.get('holding_positive_count', 0)}건)</div>
        </div>
      </div>
      <div style="font-weight: bold; font-size: 13.5px; color: #1E40AF; margin-bottom: 8px;">📊 AI 추천 종목 사후 실적 추적 감사 일람 (전수)</div>
      {backtest_cards_html}
    </div>

    <!-- 12. 10~11면 7대 분야별 심층 인텔리전스 와이어 (전수 기사) -->
    <div id="news" class="card">
      <div class="sec-title">📰 [10·11면] 7대 분야별 심층 인텔리전스 와이어 (전수 기사)</div>
      {news_sections}
    </div>

    <!-- 13. 12~21면 증권사 공식 리서치 Top 10 전문 요약 & 재무제표 -->
    <div id="official_reps" class="card">
      <div class="sec-title">📚 [12~21면] 증권사 공식 애널리스트 리포트 Top 10 전문 & 실적 추정치</div>
      {official_reports_html}
    </div>

  </div>

  <div style="background: #F8FAFC; border-top: 1px solid #E2E8F0; padding: 22px 16px; text-align: center; font-size: 12px; color: #64748B; line-height: 1.7;">
    본 모바일 인텔리전스 보고서는 Google Gemini 2026 AI & Quantitative Quant Engine에 의해 자동 편찬되었습니다.<br>
    클라우드 구글 드라이브(월별 폴더)에 초고해상도 A4 신문판 PDF가 함께 동기화 보존됩니다.<br>
    © 2026 The Executive Intelligence Herald. All Rights Reserved.
  </div>
</div>
</body>
</html>
"""
        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write(html)

        safe_print(f"📱 ✅ [모바일 100% 전수 미러링 웹리포트 생성 완료] {output_html_path} (크기: {os.path.getsize(output_html_path):,} bytes)")
        return output_html_path


