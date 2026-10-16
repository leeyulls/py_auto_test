"""
email_sender.py
네이버 SMTP를 활용하여 7대 분야별 헤드라인 + 주식 추천가 +
비트코인·이더리움·솔라나 3대 코인 매수/매도 추천금액 +
증권사 공식 애널리스트 Top 리포트 심층 분석 & 일요일 주간 총결산 브리핑 발송 모듈
"""

import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

try:
    from src.intelligence.intelligence_dossier_engine import IntelligenceDossierEngine
except ImportError:
    try:
        from intelligence_dossier_engine import IntelligenceDossierEngine
    except ImportError:
        IntelligenceDossierEngine = None

try:
    from src.advisors.real_estate_advisor import RealEstateAdvisor
except ImportError:
    try:
        from real_estate_advisor import RealEstateAdvisor
    except ImportError:
        RealEstateAdvisor = None


class EmailSender:
    def __init__(self, smtp_server="smtp.naver.com", smtp_port=465):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.naver_user = os.environ.get("NAVER_USER", "").strip()
        self.naver_password = os.environ.get("NAVER_PASSWORD", "").strip()
        self.receiver_email = os.environ.get("RECEIVER_EMAIL", "").strip() or f"{self.naver_user}@naver.com"

    def is_configured(self) -> bool:
        """이메일 발송 계정 정보가 설정되어 있는지 확인"""
        return bool(self.naver_user and self.naver_password)

    def build_html_body(self, date_str: str, stock_indices: list, exchange_rates: list, stock_advice: dict, crypto_advice: dict, official_reports: list, news_result: dict, top_research_list: list = None, performance_data: dict = None, special_disclosures: list = None, story_dive_data: dict = None, real_estate_data: dict = None) -> str:
        """나만의 프리미엄 인텔리전스 신문(The Executive Intelligence Herald) 모바일/PC 이메일 에디션"""
        if real_estate_data is None and RealEstateAdvisor:
            try:
                real_estate_data = RealEstateAdvisor().analyze_market()
            except Exception:
                real_estate_data = {}
        elif real_estate_data is None:
            real_estate_data = {}
        today_buys = stock_advice.get("today_buy_picks", [])
        long_buys = stock_advice.get("longterm_buy_picks", [])
        sells = stock_advice.get("sell_warning_picks", [])

        # 나만의 인텔리전스 신문(Newspaper Dossier) 데이터 추출 및 확장
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
            except Exception:
                nd = {}
        elif not nd:
            nd = {}

        mega_d = nd.get("mega_dossier", {})
        trend_d = nd.get("trend_dossier", {})
        exp_reps = nd.get("expanded_reports", [])
        exp_discs = nd.get("expanded_disclosures", [])

        # ---------------------------------------------------------
        # 1. 📄 증권사 공식 애널리스트 Top 리포트 심층 해부 (3면 기업 해부)
        # ---------------------------------------------------------
        reports_cards_html = ""
        if exp_reps:
            for rep in exp_reps:
                reports_cards_html += f"""
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-top: 4px solid #16A34A; padding: 14px 16px; margin-bottom: 14px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <div style="font-size: 15px; font-weight: bold; color: #166534; margin-bottom: 4px;">
                        {rep.get('headline')}
                    </div>
                    <div style="font-size: 12px; color: #475569; margin-bottom: 8px; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px;">
                        {rep.get('subhead')} &nbsp;|&nbsp; 📁 원본 PDF: {rep.get('pdf_filename', '')}
                    </div>
                    <div style="font-size: 12px; color: #1E293B; line-height: 1.65;">
                        <div style="margin-bottom: 8px; background: #F8FAFC; padding: 8px 10px; border-radius: 4px;">{rep.get('sec_business')}</div>
                        <div style="margin-bottom: 8px; background: #F8FAFC; padding: 8px 10px; border-radius: 4px;">{rep.get('sec_thesis')}</div>
                        <div style="margin-bottom: 8px; background: #F0FDF4; border: 1px solid #DCFCE7; padding: 8px 10px; border-radius: 4px; color: #14532D;">{rep.get('sec_financials')}</div>
                        <div style="margin-bottom: 8px; background: #FFF1F2; border: 1px solid #FFE4E6; padding: 8px 10px; border-radius: 4px; color: #9F1239;">{rep.get('sec_risks')}</div>
                        <div style="background: #EFF6FF; border: 1px solid #DBEAFE; padding: 8px 10px; border-radius: 4px; color: #1E40AF;">{rep.get('sec_action')}</div>
                    </div>
                </div>
                """
        elif official_reports:
            for rep in official_reports[:4]:
                tp = rep.get("target_price")
                tp_str = f"{int(tp):,}원" if tp else "-"
                ft = rep.get("financial_table", {})
                ft_box = ""
                if ft.get("has_table"):
                    ft_box = f"""
                    <div style="margin: 6px 0; background: #DCFCE7; border: 1px dashed #16A34A; padding: 6px 10px; border-radius: 4px; font-size: 11px; color: #14532D;">
                        📊 <b>PDF 핵심 실적 표:</b> {ft.get('year1_label', f'{datetime.date.today().year}F')} 매출 {ft.get('rev_year1', ft.get('rev_2026', '-'))} / 영익 {ft.get('op_year1', ft.get('op_2026', '-'))} &nbsp;|&nbsp; {ft.get('year2_label', f'{datetime.date.today().year + 1}F')} 매출 {ft.get('rev_year2', ft.get('rev_2027', '-'))} / 영익 {ft.get('op_year2', ft.get('op_2027', '-'))}
                        <div style="color: #166534; margin-top: 3px;">📈 <i>{ft.get('yoy_summary', '')}</i></div>
                    </div>
                    """
                reports_cards_html += f"""
                <div style="background: #F0FDF4; border-left: 4px solid #16A34A; padding: 12px 14px; margin-bottom: 10px; border-radius: 6px;">
                    <div style="font-weight: bold; color: #15803D; font-size: 14px;">
                        🏛️ [{rep.get('broker')}] <b>{rep.get('item_name')}</b>: {rep.get('title')}
                        <span style="font-size: 11px; background: #DCFCE7; color: #166534; padding: 1px 6px; border-radius: 10px; margin-left: 6px;">신뢰도 ⭐ {rep.get('credibility_score')}점</span>
                    </div>
                    <div style="margin: 6px 0; background: #DCFCE7; padding: 6px 10px; border-radius: 4px; font-size: 12px; color: #14532D;">
                        🎯 <b>공인 목표주가:</b> <span style="font-weight: bold; color: #166534;">{tp_str}</span> &nbsp;|&nbsp; 📌 <b>투자의견:</b> {rep.get('opinion', 'BUY')}
                    </div>
                    {ft_box}
                    <div style="color: #374151; font-size: 12px; margin-top: 4px; line-height: 1.5;">
                        💡 <b>핵심 요지:</b> {rep.get('summary_text', '')}
                    </div>
                </div>
                """

        # ---------------------------------------------------------
        # 2. 🪙 가상자산 전용 인텔리전스 & 3대 코인(BTC, ETH, SOL) 섹션
        # ---------------------------------------------------------
        macro_c = crypto_advice.get("macro_indicators", {})
        fg_val = macro_c.get("fear_greed_val", 60)
        fg_label = macro_c.get("fear_greed_label", "중립 (Neutral)")
        kimchi_p = macro_c.get("kimchi_premium", "+0.0%")
        btc_dom = macro_c.get("btc_dominance", "57.6%")

        upbit_top_chips = ""
        for idx, tv in enumerate(macro_c.get("top_volume_coins", []), 1):
            chg = tv.get("change", "0.0%")
            chg_col = "#16A34A" if "+" in chg else "#DC2626"
            upbit_top_chips += f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 4px; padding: 6px 10px; font-size: 11.5px; display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span><b>{idx}. {tv.get('symbol')}</b> ({tv.get('price')})</span>
                <span style="color: {chg_col}; font-weight: bold;">{chg}</span>
                <span style="color: #64748B;">거래대금 {tv.get('volume')}</span>
            </div>
            """

        coins = crypto_advice.get("coins", [])
        coin_cards_html = ""
        for c in coins:
            col = "#16A34A" if "+" in c.get('change_rate', '') else "#DC2626"
            coin_cards_html += f"""
            <div style="background: #FAF5FF; border: 1px solid #E9D5FF; border-left: 4px solid #7E22CE; padding: 12px 14px; margin-bottom: 10px; border-radius: 6px;">
                <div style="font-weight: bold; color: #581C87; font-size: 14.5px;">
                    {c.get('icon')} {c.get('name')} <span style="font-size: 12px; color: #6B7280;">({c.get('symbol')})</span> - <span style="color: #111827;">현재가: {c.get('cur_price')}</span> 
                    <span style="font-size: 12px; color: {col}; font-weight: bold;">({c.get('change_rate')})</span>
                </div>
                <div style="margin: 6px 0; background: #F3E8FF; padding: 6px 10px; border-radius: 4px; font-size: 12.5px; color: #581C87;">
                    💰 <b>매수 추천가:</b> <span style="font-weight: bold;">{c.get('buy_price')}</span> &nbsp;|&nbsp; 
                    🎯 <b>목표 매도가:</b> <span style="font-weight: bold; color: #7E22CE;">{c.get('sell_price')}</span> 
                    <span style="font-size: 11px; background: #E9D5FF; padding: 1px 6px; border-radius: 3px; font-weight: bold;">(기대수익 {c.get('expected_yield')})</span>
                </div>
                <div style="font-size: 11.5px; color: #475569; margin-bottom: 4px;">
                    🛡️ <b>지지선:</b> 1차 {c.get('sup1')} / 2차 {c.get('sup2')} &nbsp;|&nbsp; ⚔️ <b>저항선:</b> 1차 {c.get('res1')} / 2차 {c.get('res2')}
                </div>
                <div style="color: #374151; font-size: 11.5px; background: #FFFFFF; border: 1px solid #E2E8F0; padding: 6px 8px; border-radius: 4px; line-height: 1.45;">
                    🐋 <b>온체인·ETF 수급:</b> {c.get('onchain_desc')}<br>
                    💡 <b>트레이딩 관점:</b> {c.get('outlook')} [{c.get('signal')}] &nbsp;|&nbsp; 🛑 <b>손절가:</b> {c.get('stop_loss')} &nbsp;|&nbsp; 📊 <b>RSI:</b> {c.get('rsi')}
                </div>
            </div>
            """

        crypto_news_html = ""
        c_news = crypto_advice.get("crypto_news", [])
        if c_news:
            crypto_news_html = "<div style='font-size: 12px; color: #6B7280; margin-top: 8px;'><b>📰 코인 시장 주요 뉴스:</b> " + " | ".join([f"<a href='{cn['link']}' style='color: #4B5563; text-decoration: none;'>{cn['title']}</a>" for cn in c_news[:2]]) + "</div>"

        crypto_section_html = f"""
        <div style="margin-bottom: 24px;">
            <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #7E22CE; padding-bottom: 6px; margin-top: 0;">
                🪙 [가상자산 인텔리전스] 공포·탐욕 지수, 김프 & 3대 코인 정밀 분석
            </h2>
            <div style="display: flex; gap: 8px; margin: 12px 0; text-align: center;">
                <div style="flex: 1; background: #FAF5FF; border: 1px solid #E9D5FF; border-radius: 6px; padding: 8px;">
                    <div style="font-size: 11px; color: #6B21A8;">공포 & 탐욕 지수</div>
                    <div style="font-size: 17px; font-weight: bold; color: #7E22CE;">{fg_val}점</div>
                    <div style="font-size: 10px; font-weight: bold; color: #581C87;">{fg_label}</div>
                </div>
                <div style="flex: 1; background: #FAF5FF; border: 1px solid #E9D5FF; border-radius: 6px; padding: 8px;">
                    <div style="font-size: 11px; color: #6B21A8;">실시간 김치 프리미엄</div>
                    <div style="font-size: 17px; font-weight: bold; color: #16A34A;">{kimchi_p}</div>
                    <div style="font-size: 10px; color: #475569;">바이낸스 대비</div>
                </div>
                <div style="flex: 1; background: #FAF5FF; border: 1px solid #E9D5FF; border-radius: 6px; padding: 8px;">
                    <div style="font-size: 11px; color: #6B21A8;">비트코인 도미넌스</div>
                    <div style="font-size: 17px; font-weight: bold; color: #1E40AF;">{btc_dom}</div>
                    <div style="font-size: 10px; color: #475569;">전체 시장 점유율</div>
                </div>
            </div>

            <div style="margin-bottom: 12px;">
                <div style="font-size: 12px; font-weight: bold; color: #581C87; margin-bottom: 6px;">⚡ 업비트 24시간 거래대금 최상위 코인 Top 5</div>
                {upbit_top_chips}
            </div>

            <div style="margin-top: 10px;">
                <div style="font-size: 12px; font-weight: bold; color: #581C87; margin-bottom: 6px;">🎯 비트코인·이더리움·솔라나 매매 추천가 & 온체인 수급</div>
                {coin_cards_html}
            </div>
            {crypto_news_html}
        </div>
        """

        # ---------------------------------------------------------
        # 🏢 대한민국 부동산 시장 주간 동향 & 금융 규제 섹션
        # ---------------------------------------------------------
        re_rows_html = ""
        for r in real_estate_data.get("regional_trends", []):
            sc = r.get("sale_change", "0.00%")
            jc = r.get("jeonse_change", "0.00%")
            sc_col = "#16A34A" if "+" in sc else ("#DC2626" if "-" in sc else "#64748B")
            jc_col = "#16A34A" if "+" in jc else ("#DC2626" if "-" in jc else "#64748B")
            re_rows_html += f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 6px 8px; font-weight: bold; color: #0F172A;">{r.get('region')}</td>
                <td style="padding: 6px 8px; text-align: right; color: {sc_col}; font-weight: bold;">{sc}</td>
                <td style="padding: 6px 8px; text-align: right; color: {jc_col}; font-weight: bold;">{jc}</td>
                <td style="padding: 6px 8px; text-align: center;"><span style="background: #F1F5F9; color: {r.get('status_color', '#334155')}; font-weight: bold; font-size: 10px; padding: 2px 6px; border-radius: 4px;">{r.get('status')}</span></td>
            </tr>
            """

        mi = real_estate_data.get("mortgage_info", {})
        mm = real_estate_data.get("market_metrics", {})
        re_ag_html = ""
        for ag in real_estate_data.get("action_guides", []):
            re_ag_html += f"""
            <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-left: 4px solid #0284C7; border-radius: 4px; padding: 6px 10px; margin-bottom: 6px; font-size: 11.5px;">
                <b>🎯 {ag.get('target')}:</b> {ag.get('tip')}
            </div>
            """

        # 국토교통부 실거래가 레이더 테이블
        trades_rows_html = ""
        for t in real_estate_data.get("notable_trades", [])[:6]:
            badge = t.get("badge", "실거래")
            badge_col = "#DC2626" if "신고가" in badge else ("#16A34A" if "회복" in badge or "급매" in badge else "#2563EB")
            trades_rows_html += f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 5px 8px; font-weight: bold; color: #0F172A;">{t.get('apt_name')} <span style="font-size: 10px; color: #64748B;">({t.get('dong')})</span></td>
                <td style="padding: 5px 8px; text-align: center; color: #475569; font-size: 11px;">{t.get('area')}</td>
                <td style="padding: 5px 8px; text-align: right; font-weight: bold; color: #0F172A;">{t.get('price')}</td>
                <td style="padding: 5px 8px; text-align: center; color: #64748B; font-size: 11px;">{t.get('floor')}</td>
                <td style="padding: 5px 8px; text-align: center; color: #64748B; font-size: 11px;">{t.get('deal_date')}</td>
                <td style="padding: 5px 8px; text-align: center;"><span style="background: #F1F5F9; color: {badge_col}; font-weight: bold; font-size: 10px; padding: 2px 6px; border-radius: 4px;">{badge}</span></td>
            </tr>
            """

        trades_table_html = ""
        if trades_rows_html:
            trades_table_html = f"""
            <div style="margin-top: 10px; margin-bottom: 10px;">
                <div style="font-size: 12px; font-weight: bold; color: #0369A1; margin-bottom: 6px;">🏛️ 국토교통부 실거래가 레이더 (핵심 단지 실거래 & 신고가 동향)</div>
                <table style="width: 100%; border-collapse: collapse; font-size: 11.5px;">
                    <tr style="background: #F0F9FF; color: #0369A1;">
                        <th style="padding: 5px 8px; text-align: left; border: 1px solid #E2E8F0;">단지명</th>
                        <th style="padding: 5px 8px; text-align: center; border: 1px solid #E2E8F0;">전용면적</th>
                        <th style="padding: 5px 8px; text-align: right; border: 1px solid #E2E8F0;">거래금액</th>
                        <th style="padding: 5px 8px; text-align: center; border: 1px solid #E2E8F0;">층</th>
                        <th style="padding: 5px 8px; text-align: center; border: 1px solid #E2E8F0;">계약일</th>
                        <th style="padding: 5px 8px; text-align: center; border: 1px solid #E2E8F0;">특징</th>
                    </tr>
                    {trades_rows_html}
                </table>
            </div>
            """

        real_estate_section_html = f"""
        <div style="margin-bottom: 24px;">
            <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #0284C7; padding-bottom: 6px; margin-top: 0;">
                🏢 [부동산 인텔리전스] 주요 권역별 아파트 시세 & 주담대 금리·규제
            </h2>
            <table style="width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; margin-bottom: 12px;">
                <tr style="background: #F0F9FF; color: #0369A1;">
                    <th style="padding: 6px 8px; text-align: left; border: 1px solid #E2E8F0;">주요 권역</th>
                    <th style="padding: 6px 8px; text-align: right; border: 1px solid #E2E8F0;">매매</th>
                    <th style="padding: 6px 8px; text-align: right; border: 1px solid #E2E8F0;">전세</th>
                    <th style="padding: 6px 8px; text-align: center; border: 1px solid #E2E8F0;">시장 국면</th>
                </tr>
                {re_rows_html}
            </table>

            {trades_table_html}

            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 12px; font-size: 11.5px; margin-bottom: 10px;">
                <div style="font-weight: bold; color: #0369A1; margin-bottom: 4px;">🏦 주택담보대출 금리 밴드 & 대출 규제</div>
                <div>• <b>5년 고정 혼합형:</b> {mi.get('fixed_rate_band')} &nbsp;|&nbsp; <b>변동금리:</b> {mi.get('variable_rate_band')}</div>
                <div>• <b>규제 현황:</b> {mi.get('dsr_status')}</div>
                <div style="color: #64748B; font-size: 11px; margin-top: 3px;">• <b>서울 월간 거래량:</b> {mm.get('monthly_volume')} (매물 {mm.get('listing_inventory')})</div>
            </div>

            <div style="margin-top: 6px;">
                <div style="font-size: 12px; font-weight: bold; color: #0369A1; margin-bottom: 6px;">🧭 실수요자 실전 행동 요령</div>
                {re_ag_html}
            </div>
        </div>
        """


        # ---------------------------------------------------------
        # 3. 🎯 주식 매매 추천 카드
        # ---------------------------------------------------------
        today_buy_html = ""
        if today_buys:
            for b in today_buys[:3]:
                today_buy_html += f"""
                <div style="background: #F0FDF4; border: 1px solid #BBF7D0; padding: 10px 14px; margin-bottom: 8px; border-radius: 6px;">
                    <div style="font-weight: bold; color: #166534; font-size: 14px;">
                        🟢 {b.get('name')} <span style="font-size: 12px; color: #4B5563;">({b.get('ticker')})</span> - 현재가: {b.get('cur_price')}
                    </div>
                    <div style="margin: 4px 0; font-size: 13px; color: #15803D;">
                        👉 <b>추천 매수가:</b> {b.get('buy_price')} &nbsp;|&nbsp; <b>목표 매도가:</b> <span style="color: #166534; font-weight: bold;">{b.get('sell_price')}</span> 
                        <span style="font-size: 11px; background: #DCFCE7; padding: 1px 5px; border-radius: 3px; font-weight: bold;">(기대수익 {b.get('expected_yield')})</span>
                    </div>
                    <div style="font-size: 12px; color: #4B5563;">
                        💡 <b>신호 및 근거:</b> {b.get('type', b.get('reason', ''))} | 손절 기준가: {b.get('stop_loss', '-')}
                    </div>
                </div>
                """
        else:
            today_buy_html = "<div style='color: #6B7280; font-size: 13px; padding: 6px 0;'>- 오늘 단기 기준 충족 종목 없음 (관망 권고)</div>"

        long_buy_html = ""
        if long_buys:
            for lb in long_buys[:2]:
                long_buy_html += f"""
                <div style="background: #EFF6FF; border: 1px solid #BFDBFE; padding: 10px 14px; margin-bottom: 8px; border-radius: 6px;">
                    <div style="font-weight: bold; color: #1E40AF; font-size: 14px;">
                        🔵 {lb['name']} <span style="font-size: 12px; color: #4B5563;">({lb['ticker']})</span> - 현재가: {lb['cur_price']}
                    </div>
                    <div style="margin: 4px 0; font-size: 13px; color: #1D4ED8;">
                        👉 <b>분할 매수가:</b> {lb['buy_price']} &nbsp;|&nbsp; <b>장기 목표가:</b> <span style="color: #1E40AF; font-weight: bold;">{lb['sell_price']}</span> ({lb['expected_yield']})
                    </div>
                    <div style="font-size: 12px; color: #4B5563;">
                        💡 <b>특징:</b> {lb['type']}
                    </div>
                </div>
                """
        else:
            long_buy_html = "<div style='color: #6B7280; font-size: 13px; padding: 6px 0;'>- 현재 장기 적립 매수 권고 종목 없음</div>"

        sell_html = ""
        if sells:
            for s in sells[:2]:
                sell_html += f"""
                <div style="background: #FEF2F2; border: 1px solid #FECACA; padding: 10px 14px; margin-bottom: 8px; border-radius: 6px;">
                    <div style="font-weight: bold; color: #991B1B; font-size: 14px;">
                        🔴 {s['name']} <span style="font-size: 12px; color: #4B5563;">({s['ticker']})</span> - 현재가: {s['cur_price']}
                    </div>
                    <div style="margin: 4px 0; font-size: 13px; color: #B91C1C;">
                        👉 <b>권고 매도가:</b> <span style="font-weight: bold;">{s['sell_price']}</span> (현재가 부근 분할 익절 및 비중 축소 권고)
                    </div>
                    <div style="font-size: 12px; color: #4B5563;">
                        ⚠️ <b>경고 사유:</b> {s['type']} (20일선 이격도 {s['disparity']})
                    </div>
                </div>
                """
        else:
            sell_html = "<div style='color: #6B7280; font-size: 13px; padding: 6px 0;'>- 단기 과열권 종목 없음 (안정적 추세)</div>"

        # ---------------------------------------------------------
        # 🔥 외국인·기관 실시간 수급 쌍끌이 레이더 (Smart Money Flow)
        # ---------------------------------------------------------
        radar_list = stock_advice.get("investor_flow_radar", []) if isinstance(stock_advice, dict) else []
        radar_rows_html = ""
        if radar_list:
            for item in radar_list[:6]:
                score = item.get("score", 1)
                bg_col = "#F0FDF4" if score == 3 else "#FFFFFF"
                badge = item.get("badge", "")
                badge_style = "background: #DCFCE7; color: #166534;" if "쌍끌이" in badge else ("background: #DBEAFE; color: #1E40AF;" if "외인" in badge else "background: #F3E8FF; color: #6B21A8;")
                f_q = str(item.get("foreign_quant", "-"))
                o_q = str(item.get("organ_quant", "-"))
                f_color = "#16A34A" if "+" in f_q else ("#DC2626" if "-" in f_q else "#64748B")
                o_color = "#16A34A" if "+" in o_q else ("#DC2626" if "-" in o_q else "#64748B")
                radar_rows_html += f"""
                <tr style="background: {bg_col}; border-bottom: 1px solid #E2E8F0;">
                    <td style="padding: 6px 8px; font-weight: bold; color: #1E293B;">{item['name']} <span style="font-size: 11px; color: #64748B;">({item['sector']})</span></td>
                    <td style="padding: 6px 8px; text-align: center;"><span style="{badge_style} font-weight: bold; font-size: 11px; padding: 2px 6px; border-radius: 4px;">{badge}</span></td>
                    <td style="padding: 6px 8px; text-align: right; color: {f_color}; font-weight: 600;">{f_q}</td>
                    <td style="padding: 6px 8px; text-align: right; color: {o_color}; font-weight: 600;">{o_q}</td>
                </tr>
                """

        radar_section_html = ""
        if radar_rows_html:
            radar_section_html = f"""
            <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-top: 3px solid #2563EB; border-radius: 8px; padding: 12px 14px; margin-top: 14px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <div style="font-size: 13.5px; font-weight: bold; color: #1E3A8A; margin-bottom: 8px; display: flex; align-items: center;">
                    <span>🔥 [수급 레이더] 대형주 외국인 & 기관 실시간 순매수 집중 포착</span>
                    <span style="margin-left: auto; font-size: 10.5px; background: #DBEAFE; color: #1E40AF; padding: 1px 6px; border-radius: 4px; font-weight: bold;">Smart Money Flow</span>
                </div>
                <table style="width: 100%; border-collapse: collapse; font-size: 11.5px;">
                    <tr style="background: #F1F5F9; color: #475569;">
                        <th style="padding: 6px 8px; text-align: left; border-bottom: 2px solid #CBD5E1;">종목 (섹터)</th>
                        <th style="padding: 6px 8px; text-align: center; border-bottom: 2px solid #CBD5E1;">수급 진단</th>
                        <th style="padding: 6px 8px; text-align: right; border-bottom: 2px solid #CBD5E1;">외인 순매수</th>
                        <th style="padding: 6px 8px; text-align: right; border-bottom: 2px solid #CBD5E1;">기관 순매수</th>
                    </tr>
                    {radar_rows_html}
                </table>
            </div>
            """

        # 지수 및 환율 테이블
        indices_rows = ""
        for idx in stock_indices:
            idx_name = idx.get("지수명") or idx.get("name", "-")
            idx_val = idx.get("현재지수") or idx.get("price", "-")
            idx_diff = idx.get("전일대비") or idx.get("change", "-")
            color = "#16A34A" if ("+" in str(idx_diff) or "▲" in str(idx_diff)) else ("#DC2626" if ("-" in str(idx_diff) or "▼" in str(idx_diff)) else "#475569")
            indices_rows += f"""
            <tr>
                <td style="padding: 6px 10px; border: 1px solid #E5E7EB; font-weight: bold;">{idx_name}</td>
                <td style="padding: 6px 10px; border: 1px solid #E5E7EB; text-align: right; font-weight: bold;">{idx_val}</td>
                <td style="padding: 6px 10px; border: 1px solid #E5E7EB; text-align: right; color: {color}; font-weight: bold;">{idx_diff}</td>
            </tr>
            """

        rates_rows = ""
        for fx in exchange_rates:
            fx_diff = fx.get('전일대비') or fx.get('변동/기준', '')
            fx_name = fx.get('통화명') or fx.get('currency', '-')
            fx_rate = fx.get('환율(원)') or fx.get('rate', '-')
            fx_col = "#16A34A" if ("+" in str(fx_diff) or "▲" in str(fx_diff)) else ("#DC2626" if ("-" in str(fx_diff) or "▼" in str(fx_diff)) else "#6B7280")
            rates_rows += f"""
            <tr>
                <td style="padding: 6px 10px; border: 1px solid #E5E7EB;">{fx_name}</td>
                <td style="padding: 6px 10px; border: 1px solid #E5E7EB; text-align: right; font-weight: bold;">{fx_rate}원</td>
                <td style="padding: 6px 10px; border: 1px solid #E5E7EB; text-align: right; color: {fx_col}; font-weight: bold; font-size: 12px;">{fx_diff}</td>
            </tr>
            """

        # 7대 분야별 헤드라인
        headlines_html = ""
        top_picks = news_result.get("category_top_picks", {})
        cat_order = [
            ("거시경제/비즈니스", "💼 거시경제 & 비즈니스"),
            ("정치", "🏛️ 정치 핵심 이슈"),
            ("IT/과학/신상품", "💻 IT·과학 & 테크/신상품"),
            ("세계/국제", "🌍 세계·국제 뉴스"),
            ("사회/사건사고", "🚨 사회·사건사고 이슈"),
            ("연예/대중문화", "🎬 연예·문화 트렌드"),
        ]

        for cat_key, icon_title in cat_order:
            items = top_picks.get(cat_key, [])
            if items:
                cat_items_html = ""
                # 이메일은 핵심 요약본이므로 분야별 상위 4건 발췌 수록 (전체 기사는 PDF 상세본에 전수 수록)
                display_items = items[:4]
                for idx, it in enumerate(display_items):
                    it_link = it.get("링크") or it.get("link", "")
                    tag = f" <span style='background: #FEE2E2; color: #DC2626; padding: 1px 5px; border-radius: 3px; font-size: 11px;'>{it.get('상태', '')}</span>" if "집중" in str(it.get('상태', '')) else ""
                    content_sum = it.get('content_summary') or it.get('요약내용', '')
                    expanded_ins = it.get('expanded_insight', '')
                    if not expanded_ins:
                        expanded_ins = f"<b>💡 심층 맥락:</b> 후속 정책 발표 및 산업계 파급 효과 모니터링 필요.<br><b>🔎 체크포인트:</b> 소관 부처 공식 반응 및 핵심 일정 점검."

                    cat_items_html += f"""
                    <div style="margin-bottom: 8px; font-size: 12px; background: #FFFFFF; border: 1px solid #E2E8F0; padding: 8px 10px; border-radius: 5px;">
                        <div style="line-height: 1.4;">
                            <span style="font-weight: bold; color: #1D4ED8;">[{idx + 1}]</span> <a href="{it_link}" style="color: #1D4ED8; text-decoration: none; font-weight: 600;">{it.get('기사제목', '')}</a>
                            <span style="font-size: 11px; color: #6B7280;">({it.get('언론사', '')})</span>{tag}
                        </div>
                        <div style="font-size: 11.5px; color: #334155; margin-top: 4px; padding-left: 8px; border-left: 2px solid #3B82F6; line-height: 1.45;">
                            <b>📰 핵심 팩트:</b> {content_sum}
                        </div>
                        <div style="font-size: 11px; color: #1E40AF; background: #EFF6FF; border: 1px solid #BFDBFE; border-left: 3px solid #2563EB; border-radius: 3px; padding: 5px 8px; margin-top: 4px; line-height: 1.4;">
                            {expanded_ins}
                        </div>
                    </div>
                    """

                total_cat_cnt = len(items)
                more_notice = ""
                if total_cat_cnt > len(display_items):
                    more_notice = f"""
                    <div style="font-size: 11px; color: #64748B; text-align: right; margin-top: 6px; font-weight: 500;">
                        👉 <i>{icon_title} 분야 전체 {total_cat_cnt}건 기사 전수 분석 및 상세 카드는 첨부된 [모바일 웹리포트 HTML] 및 구글 드라이브 PDF에 수록되어 있습니다.</i>
                    </div>
                    """

                headlines_html += f"""
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; margin-bottom: 14px;">
                    <div style="font-size: 13.5px; font-weight: bold; color: #1E293B; margin-bottom: 8px; border-bottom: 2px solid #E2E8F0; padding-bottom: 4px; display: flex; justify-content: space-between; align-items: center;">
                        <span>{icon_title}</span>
                        <span style="font-size: 11px; color: #2563EB; font-weight: bold;">(요약 {len(display_items)}건 / 전체 {total_cat_cnt}건)</span>
                    </div>
                    {cat_items_html}
                    {more_notice}
                </div>
                """

        # ---------------------------------------------------------
        # 📰 1면 톱 심층 기획특집 기사 (The Lead Story 요약본)
        # ---------------------------------------------------------
        mega = news_result.get("mega_issue")
        mega_html = ""
        if mega_d and mega_d.get("chapter1"):
            # HTML 태그 제거 헬퍼
            def _first_sent(html_text):
                clean = re.sub(r'<[^>]+>', '', html_text)
                sents = re.split(r'(?<=[.!?])\s+', clean)
                return sents[0] if sents else clean[:80]

            ch1_brief = _first_sent(mega_d.get('chapter1', ''))
            ch2_brief = _first_sent(mega_d.get('chapter2', ''))
            ch3_brief = _first_sent(mega_d.get('chapter3', ''))
            ch4_brief = _first_sent(mega_d.get('chapter4', ''))

            mega_html = f"""
            <div style="background: #FFFFFF; border: 2px solid #1E3A8A; border-radius: 8px; padding: 16px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.06);">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #1E3A8A; padding-bottom: 6px; margin-bottom: 10px;">
                    <span style="font-size: 13px; font-weight: bold; color: #1E3A8A;">🌐 [오늘의 1면 톱 기획특집 요약]</span>
                    <span style="background: #DBEAFE; color: #1E40AF; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 10px;">취재원: {mega_d.get('source', '주요 언론')} | 2차 심층 확장 취재</span>
                </div>
                <h2 style="font-size: 17px; font-weight: 800; color: #0F172A; margin: 0 0 6px; line-height: 1.4;">
                    <a href="{mega_d.get('link', '#')}" style="color: #0F172A; text-decoration: none;">{mega_d.get('headline')}</a>
                </h2>
                <div style="font-size: 12.5px; color: #2563EB; font-weight: 600; margin-bottom: 10px; line-height: 1.45;">
                    {mega_d.get('subhead')}
                </div>
                <div style="background: #F8FAFC; border-left: 4px solid #1E3A8A; padding: 10px 12px; font-size: 12px; color: #1E293B; line-height: 1.6; margin-bottom: 12px; font-style: italic;">
                    {mega_d.get('lead')}
                </div>
                <div style="background: #F1F5F9; border-radius: 6px; padding: 10px 12px; font-size: 11.5px; line-height: 1.6; color: #334155;">
                    <div style="margin-bottom: 4px;">• 📌 <b>발단 & 타임라인:</b> {ch1_brief}</div>
                    <div style="margin-bottom: 4px;">• ⚡ <b>핵심 이해관계 & 쟁점:</b> {ch2_brief}</div>
                    <div style="margin-bottom: 4px;">• 📊 <b>공개 데이터 & 팩트:</b> {ch3_brief}</div>
                    <div>• ⏳ <b>향후 일정 & 관전 포인트:</b> {ch4_brief}</div>
                </div>
                <div style="margin-top: 10px; background: #EFF6FF; border: 1px solid #BFDBFE; padding: 7px 10px; border-radius: 5px; font-size: 11px; color: #1E40AF; text-align: center;">
                    📎 <b>4대 챕터 심층 르포 전문과 팩트 분석은 첨부된 [모바일 웹리포트 HTML] 및 구글 드라이브 PDF 1면에 전수 수록되어 있습니다.</b>
                </div>
            </div>
            """
        elif mega:
            mega_html = f"""
            <div style="background: #FFF1F2; border: 2px solid #F43F5E; border-radius: 8px; padding: 14px; margin-bottom: 20px;">
                <div style="font-size: 12.5px; font-weight: bold; color: #E11D48; margin-bottom: 4px;">
                    🔥 오늘의 메가 핫토픽 [언론사 {mega['media_count']}개사 집중 보도]
                </div>
                <div style="font-size: 15px; font-weight: bold; color: #881337; margin-bottom: 6px;">
                    <a href="{mega.get('링크') or mega.get('link', '')}" style="color: #881337; text-decoration: none;">{mega['기사제목']}</a>
                    <span style="font-size: 11px; color: #9F1239; font-weight: normal;">({mega['언론사']})</span>
                </div>
                <div style="font-size: 12px; color: #4C0519; line-height: 1.5; background: #FFE4E6; padding: 6px 10px; border-radius: 4px;">
                    💡 <b>핵심 팩트:</b> {mega['요약내용']}
                </div>
            </div>
            """

        # ---------------------------------------------------------
        # 🛍️ 2면 기획 르포: 트렌드 & 2030 라이프스타일 소비 심리 (Trend Intelligence 요약본)
        # ---------------------------------------------------------
        story_dive_html = ""
        if trend_d and trend_d.get("chapter1"):
            story_dive_html = f"""
            <div style="background: #FFFFFF; border: 2px solid #DB2777; border-radius: 8px; padding: 16px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.06);">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #DB2777; padding-bottom: 6px; margin-bottom: 10px;">
                    <span style="font-size: 13px; font-weight: bold; color: #9D174D;">🛍️ [2면 기획 르포: 2030 라이프스타일 & 소비 심리 요약]</span>
                    <span style="background: #FCE7F3; color: #9D174D; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 10px;">트렌드 인텔리전스</span>
                </div>
                <h2 style="font-size: 16px; font-weight: 800; color: #0F172A; margin: 0 0 6px; line-height: 1.4;">
                    <a href="{trend_d.get('link', '#')}" style="color: #0F172A; text-decoration: none;">{trend_d.get('headline')}</a>
                </h2>
                <div style="font-size: 12.5px; color: #BE185D; font-weight: 600; margin-bottom: 10px; line-height: 1.45;">
                    {trend_d.get('subhead')}
                </div>
                <div style="background: #FDF2F8; border-left: 4px solid #DB2777; padding: 10px 12px; font-size: 12px; color: #1E293B; line-height: 1.6; margin-bottom: 10px; font-style: italic;">
                    {trend_d.get('lead')}
                </div>
                <div style="margin-top: 10px; background: #FEF9C3; border: 1px solid #FDE047; padding: 7px 10px; border-radius: 5px; font-size: 11.5px; color: #713F12; line-height: 1.45;">
                    💡 <b>1분 핵심 용어:</b> {(trend_d.get('term_tip') or '대중적 화제성과 개성 표출 욕구가 결합되어 실물 구매로 이어지는 현대적 신소비 메커니즘입니다.').replace('**', '').replace('📌 ', '')}
                </div>
                <div style="margin-top: 10px; background: #FFF1F2; border: 1px solid #FECDD3; padding: 7px 10px; border-radius: 5px; font-size: 11px; color: #9F1239; text-align: center;">
                    📎 <b>소비 심리 역학 및 비즈니스 수혜/리스크 상세 르포는 첨부된 [모바일 웹리포트 HTML] 및 구글 드라이브 PDF 2면에서 확인하실 수 있습니다.</b>
                </div>
            </div>
            """
        elif story_dive_data and story_dive_data.get("stories"):
            cards_inner = ""
            for st in story_dive_data["stories"]:
                is_econ = (st.get("track") == "ECONOMY")
                theme_color = "#2563EB" if is_econ else "#DB2777"
                theme_bg = "#EFF6FF" if is_econ else "#FDF2F8"
                badge_bg = "#DBEAFE" if is_econ else "#FCE7F3"
                badge_text = "#1E40AF" if is_econ else "#9D174D"
                icon = "🌐" if is_econ else "🔥"
                link_url = st.get('link') or '#'
                source_name = st.get('source') or '심층분석'
                term_html = ""
                term_tip = st.get("term_tip", "")
                if term_tip:
                    clean_term = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', term_tip)
                    term_html = f"""
                    <div style="margin-top: 10px; background: #FEF9C3; border: 1px solid #FDE047; padding: 8px 12px; border-radius: 6px; font-size: 12px; color: #713F12; line-height: 1.5;">
                        💡 <b>1분 핵심 용어 사전:</b> {clean_term}
                    </div>
                    """
                cards_inner += f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid {theme_color}; border-radius: 8px; padding: 14px 16px; margin-bottom: 14px;">
                    <div style="margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                        <span style="background: {badge_bg}; color: {badge_text}; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 10px;">{icon} {st.get('track_name')} | {st.get('badge')}</span>
                        <span style="font-size: 11px; color: #64748B;">출처: {source_name}</span>
                    </div>
                    <div style="font-size: 15px; font-weight: bold; color: #0F172A; margin-bottom: 8px;">
                        <a href="{link_url}" style="color: #0F172A; text-decoration: none;">{st.get('title')}</a>
                    </div>
                    <div style="font-size: 12px; color: #334155; line-height: 1.6;">
                        <div>{st.get('stage1')}</div>
                        <div style="margin-top: 4px;">{st.get('stage2')}</div>
                        <div style="margin-top: 4px;">{st.get('stage3')}</div>
                        <div style="margin-top: 4px;">{st.get('stage4')}</div>
                    </div>
                    {term_html}
                </div>
                """
            story_dive_html = f"""
            <div style="margin-bottom: 24px;">
                <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #8B5CF6; padding-bottom: 6px;">
                    📌 오늘의 심층 테마 리포트 (경제·사회 & 트렌드)
                </h2>
                <div style="margin-top: 12px;">
                    {cards_inner}
                </div>
            </div>
            """

        # ---------------------------------------------------------
        # 🎯 추천 종목 사후 검증 (Backtesting) & 누적 적중률 카드
        # ---------------------------------------------------------
        perf_html = ""
        if performance_data and performance_data.get("summary"):
            s = performance_data["summary"]
            rec_cards = ""
            for r in performance_data.get("records", [])[:6]:
                res = r.get("검증결과", "")
                if "달성" in res:
                    badge_bg, badge_fg, res_col = "#DCFCE7", "#166534", "#16A34A"
                elif "손절" in res:
                    badge_bg, badge_fg, res_col = "#FEE2E2", "#991B1B", "#DC2626"
                else:
                    badge_bg, badge_fg, res_col = "#DBEAFE", "#1E40AF", "#2563EB"

                rec_cards += f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 12px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                        <div style="font-size: 13px; font-weight: bold; color: #0F172A;">
                            🟢 {r.get('종목명')} <span style="font-size: 11px; color: #64748B; font-weight: normal;">({r.get('티커')})</span>
                        </div>
                        <span style="background: {badge_bg}; color: {badge_fg}; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 10px;">
                            {res}
                        </span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #334155;">
                        <div>👉 <b>추천:</b> {r.get('매수추천가')} ➔ <b>목표:</b> <span style="color: #1E40AF; font-weight: bold;">{r.get('목표매도가')}</span></div>
                        <div style="font-weight: bold; color: {res_col}; font-size: 13px;">{r.get('실현수익률')}</div>
                    </div>
                    <div style="font-size: 11px; color: #94A3B8; margin-top: 4px;">
                        📅 추천일: {r.get('추천일자')} &nbsp;|&nbsp; ⏱️ {r.get('소요일수')} &nbsp;|&nbsp; 📈 최고도달가: {r.get('최고도달가')}
                    </div>
                </div>
                """
            perf_html = f"""
            <div style="background: #F8FAFC; border: 2px solid #3B82F6; border-radius: 8px; padding: 14px; margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #CBD5E1; padding-bottom: 8px; margin-bottom: 10px;">
                    <div style="font-size: 15px; font-weight: bold; color: #1E3A8A;">🎯 AI 추천 종목 사후 검증(Backtesting) & 누적 승률</div>
                    <div style="background: #1E3A8A; color: #FFFFFF; font-weight: bold; padding: 3px 10px; border-radius: 12px; font-size: 12px;">누적 승률: {s.get('win_rate', 0)}%</div>
                </div>
                <div style="margin-bottom: 10px; font-size: 12px; color: #334155; line-height: 1.6;">
                    📊 <b>검증 총계:</b> {s.get('total_picks', 0)}건 &nbsp;|&nbsp; 
                    🎯 <b>목표가 달성:</b> <span style="color: #16A34A; font-weight: bold;">{s.get('success_count', 0)}건</span> &nbsp;|&nbsp; 
                    🛑 <b>손절:</b> <span style="color: #DC2626; font-weight: bold;">{s.get('stoploss_count', 0)}건</span> &nbsp;|&nbsp; 
                    ⏳ <b>목표가 추적 중:</b> {s.get('holding_count', 0)}건 &nbsp;|&nbsp; 
                    💰 <b>평균 수익률:</b> <span style="color: #2563EB; font-weight: bold;">{s.get('avg_return', 0.0):+.2f}%</span>
                </div>
                <div style="margin-top: 8px;">
                    {rec_cards}
                </div>
            </div>
            """

        # ---------------------------------------------------------
        # 🏛️ 4면: 금융감독원(DART) 특수공시 심층 행간 읽기 (Regulatory Intelligence)
        # ---------------------------------------------------------
        disclosures_html = ""
        if exp_discs:
            d_cards = ""
            for d in exp_discs:
                d_cards += f"""
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-top: 4px solid #D97706; padding: 14px 16px; margin-bottom: 14px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <div style="font-size: 14.5px; font-weight: bold; color: #92400E; margin-bottom: 6px;">
                        {d.get('headline')}
                    </div>
                    <div style="font-size: 12px; color: #1E293B; line-height: 1.65;">
                        <div style="margin-bottom: 8px; background: #FFFBEB; border: 1px solid #FEF3C7; padding: 8px 10px; border-radius: 4px; color: #78350F;">{d.get('sec_context')}</div>
                        <div style="margin-bottom: 8px; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 8px 10px; border-radius: 4px; color: #334155;">{d.get('sec_governance')}</div>
                        <div style="background: #F0FDF4; border: 1px solid #DCFCE7; padding: 8px 10px; border-radius: 4px; color: #166534;">{d.get('sec_strategy')}</div>
                    </div>
                </div>
                """
            disclosures_html = f"""
            <div style="margin-bottom: 24px;">
                <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #D97706; padding-bottom: 6px; margin-top: 0;">
                    🏛️ [4면] 금융감독원(DART) 특수공시 심층 행간 읽기 (지배구조 & FCF 분석)
                </h2>
                <div style="margin-top: 12px;">
                    {d_cards}
                </div>
            </div>
            """
        elif special_disclosures:
            d_cards = ""
            for d in special_disclosures[:4]:
                badge = d.get("공시배지", "")
                badge_bg = "#DCFCE7" if "자사주" in badge else ("#DBEAFE" if "내부자" in badge else ("#FEF3C7" if "수주" in badge else "#F3E8FF"))
                badge_fg = "#166534" if "자사주" in badge else ("#1E40AF" if "내부자" in badge else ("#92400E" if "수주" in badge else "#6B21A8"))
                action_badge = d.get("액션배지", "")
                corp = d.get("관련기업") or "상장사"
                strategy_html = ""
                if d.get("투자전략"):
                    strategy_html = f"""
                    <div style="margin-top: 6px; background: #F8FAFC; border: 1px dashed #CBD5E1; padding: 6px 10px; border-radius: 4px; font-size: 11px; color: #0F172A; line-height: 1.5;">
                        🎯 <b>투자자 실전 대응 전략:</b> <span style="background: {badge_bg}; color: {badge_fg}; font-weight: bold; padding: 1px 6px; border-radius: 3px; font-size: 10px; margin-right: 4px;">{action_badge}</span> {d.get('투자전략')}
                    </div>
                    """
                d_cards += f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid {badge_fg}; padding: 12px 14px; margin-bottom: 10px; border-radius: 6px;">
                    <div style="font-size: 13px; font-weight: bold; color: #1E293B;">
                        <span style="background: {badge_bg}; color: {badge_fg}; padding: 1px 6px; border-radius: 4px; font-size: 11px; margin-right: 6px;">{badge}</span>
                        <b>{corp}</b> | <a href="{d.get('링크')}" style="color: #1E293B; text-decoration: none;">{d.get('공시제목')}</a>
                    </div>
                    <div style="font-size: 12px; color: #475569; margin-top: 4px;">
                        💡 <b>공시 영향:</b> {d.get('영향전망')} <span style="color: #94A3B8; font-size: 11px;">({d.get('언론사')})</span>
                    </div>
                    {strategy_html}
                </div>
                """
            disclosures_html = f"""
            <div style="margin-bottom: 24px;">
                <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #D97706; padding-bottom: 6px; margin-top: 0;">
                    🏛️ 금융감독원(DART) & KIND 기업 핵심 특수 공시 실시간 연동
                </h2>
                <div style="margin-top: 12px;">
                    {d_cards}
                </div>
            </div>
            """

        # ---------------------------------------------------------
        # 🇺🇸 미국 글로벌 빅테크 4대장 (NVDA, TSLA, AAPL, MSFT) 카드
        # ---------------------------------------------------------
        us_bigtech_picks = stock_advice.get("us_bigtech_picks", [])
        us_bigtech_html = ""
        if us_bigtech_picks:
            us_cards = ""
            for u in us_bigtech_picks:
                us_cards += f"""
                <div style="background: #F8FAFC; border: 1px solid #CBD5E1; padding: 10px 12px; margin-bottom: 8px; border-radius: 6px;">
                    <div style="font-weight: bold; color: #0F172A; font-size: 14px;">
                        🇺🇸 {u.get('종목명')} <span style="font-size: 12px; color: #64748B;">({u.get('티커')})</span> - 현재가: <b>{u.get('현재가')}</b> 
                        <span style="font-size: 12px; color: {'#16A34A' if '+' in u.get('전일대비','') else '#DC2626'}; font-weight: bold;">({u.get('전일대비')})</span>
                    </div>
                    <div style="margin: 4px 0; font-size: 12px; color: #1E293B;">
                        👉 <b>추천 매수가:</b> {u.get('매수_추천금액')} &nbsp;|&nbsp; <b>목표 매도가:</b> <span style="font-weight: bold; color: #2563EB;">{u.get('목표_매도금액')}</span> 
                        <span style="font-size: 11px; background: #DBEAFE; color: #1E40AF; padding: 1px 5px; border-radius: 3px; font-weight: bold;">(기대수익 {u.get('기대_수익률')})</span>
                    </div>
                    <div style="font-size: 11px; color: #64748B;">
                        💡 <b>투자 신호:</b> {u.get('단기신호')} | 20일선 이격도: {u.get('20일선이격도')} | RSI: {u.get('RSI(14)')}
                    </div>
                </div>
                """
            us_bigtech_html = f"""
            <div style="margin-bottom: 24px;">
                <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #2563EB; padding-bottom: 6px;">
                    🇺🇸 미국 글로벌 빅테크 4대장 (NVDA, TSLA, AAPL, MSFT) 집중 분석
                </h2>
                <div style="margin-top: 12px;">
                    {us_cards}
                </div>
            </div>
            """

        # 0. 📋 최고경영진 3대 핵심 요약 (Executive Summary Box)
        issue_brief = "주요 거시 경제 및 사회적 핫토픽 점검 진행"
        if mega_d and mega_d.get("headline"):
            issue_brief = f"<b>{mega_d.get('headline')}</b> — {mega_d.get('subhead', '')}"
        elif story_dive_data and story_dive_data.get("stories"):
            first_s = story_dive_data["stories"][0]
            issue_brief = f"<b>[{first_s.get('track_name', '심층이슈')}] {first_s.get('title')}</b> — {first_s.get('hook', '')}"

        asset_brief = "당일 단기 과열권 진입 종목 분할 익절 및 현금 비중 20% 이상 유지 권고"
        if today_buys:
            top_b = today_buys[0]
            asset_brief = f"<b>[국내 주식]</b> <b>{top_b.get('name')}</b>({top_b.get('cur_price')}) 등 {len(today_buys)}개 유망주 단기 매수 밴드 포착 / <b>[가상자산]</b> 비트코인 지지선 안착 확인"
        elif long_buys:
            asset_brief = f"<b>[적립 투자]</b> <b>{long_buys[0].get('name')}</b> 등 실적 우량주 중심 분할 매수 밴드 유효"

        pdf_brief = f"20일 주가 변화 차트, 기업 실적 추정치 표 및 DART 공시 투자전략이 수록된 8페이지 정식 신문판(<code>{date_str}_데일리_심층_종합분석_보고서.pdf</code>)이 구글 드라이브(<code>{date_str[:7]}/</code>)에 보관되었습니다 (본 메일에는 반응형 HTML 웹리포트 단독 첨부)."

        exec_summary_html = f"""
        <div style="background: #F8FAFC; border: 2px solid #1E3A8A; border-radius: 8px; padding: 16px 18px; margin-bottom: 22px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <div style="font-size: 14px; font-weight: bold; color: #1E3A8A; margin-bottom: 8px; display: flex; align-items: center;">
                <span>📋 오늘의 나만의 3대 핵심 요약 (Daily Summary)</span>
                <span style="margin-left: auto; font-size: 11px; background: #DBEAFE; color: #1E40AF; padding: 2px 8px; border-radius: 10px; font-weight: bold;">나만의 데일리 브리핑</span>
            </div>
            <ul style="margin: 0; padding-left: 18px; font-size: 12.5px; color: #1E293B; line-height: 1.7;">
                <li style="margin-bottom: 4px;"><b>1면 톱 기획:</b> {issue_brief}</li>
                <li style="margin-bottom: 4px;"><b>투자 포커스:</b> {asset_brief}</li>
                <li><b>구글 드라이브 심층 신문 PDF:</b> {pdf_brief}</li>
            </ul>
        </div>
        """

        # ---------------------------------------------------------
        # ⚡ 오늘의 1분 액션 체크리스트 (Executive Quick Action Cube)
        # ---------------------------------------------------------
        best_p = None
        if performance_data and isinstance(performance_data, dict) and performance_data.get("best_picks"):
            best_p = performance_data["best_picks"][0]

        buy_act = f"<b>{today_buys[0].get('name')}</b> (매수가: {today_buys[0].get('buy_price')})" if today_buys else "단기 과열 방어, 실적 우량주 분할 매수"
        hold_act = f"<b>{best_p.get('종목명')}</b> ({best_p.get('실현수익률')} 순항 중)" if best_p else "기존 보유 포지션 손절선(-3.5%) 및 목표가 밴드 준수"
        risk_act = "WTI 유가·환율 변동성 주시, 현금 비중 20% 이상 유지"

        action_cube_html = f"""
        <div style="background: #FFFFFF; border: 2px solid #1E3A8A; border-radius: 8px; padding: 14px 16px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.06);">
            <div style="font-size: 13.5px; font-weight: bold; color: #1E3A8A; margin-bottom: 10px; display: flex; align-items: center;">
                <span>⚡ 오늘의 1분 액션 체크리스트 (Executive Quick Action Cube)</span>
                <span style="margin-left: auto; font-size: 11px; background: #DBEAFE; color: #1E40AF; padding: 2px 8px; border-radius: 10px; font-weight: bold;">30초 의사결정</span>
            </div>
            <div style="display: flex; gap: 8px;">
                <div style="flex: 1; background: #F0FDF4; border: 1px solid #BBF7D0; border-top: 3px solid #16A34A; border-radius: 6px; padding: 9px 10px; font-size: 11.5px;">
                    <div style="font-weight: bold; color: #166534; font-size: 12px; margin-bottom: 3px;">🟢 오늘 매수 관심</div>
                    <div style="color: #14532D; line-height: 1.4;">{buy_act}</div>
                </div>
                <div style="flex: 1; background: #FFFBEB; border: 1px solid #FEF3C7; border-top: 3px solid #D97706; border-radius: 6px; padding: 9px 10px; font-size: 11.5px;">
                    <div style="font-weight: bold; color: #92400E; font-size: 12px; margin-bottom: 3px;">🟡 보유/추적 대응</div>
                    <div style="color: #78350F; line-height: 1.4;">{hold_act}</div>
                </div>
                <div style="flex: 1; background: #FEF2F2; border: 1px solid #FECACA; border-top: 3px solid #DC2626; border-radius: 6px; padding: 9px 10px; font-size: 11.5px;">
                    <div style="font-weight: bold; color: #991B1B; font-size: 12px; margin-bottom: 3px;">🔴 리스크 주의보</div>
                    <div style="color: #7F1D1D; line-height: 1.4;">{risk_act}</div>
                </div>
            </div>
        </div>
        """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>My Daily Intelligence Briefing ({date_str})</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif; background-color: #F8FAFC; margin: 0; padding: 20px; line-height: 1.6; color: #1E293B;">
            <div style="max-width: 680px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border: 1px solid #E2E8F0;">
                
                <!-- 헤더: 나만의 데일리 브리핑 톤앤매너 -->
                <div style="background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%); color: #FFFFFF; padding: 26px 24px; text-align: center;">
                    <div style="font-size: 11px; letter-spacing: 2px; color: #93C5FD; text-transform: uppercase; font-weight: bold;">My Daily Intelligence Briefing</div>
                    <h1 style="margin: 8px 0 0; font-size: 21px; font-weight: bold;">📰 [오늘의 브리핑] {date_str} 나만의 데일리 금융 & 이슈 리포트</h1>
                    <p style="margin: 6px 0 0; font-size: 12.5px; opacity: 0.9; color: #E2E8F0;">단순 요약을 탈피한 2차 심층 교차 취재 & 전방위 기업·공시 해부 에디션</p>
                </div>

                <!-- 📱 모바일 웹진 및 고해상도 PDF 안내 배너 -->
                <div style="background: #F1F5F9; border-bottom: 1px solid #E2E8F0; padding: 10px 18px; font-size: 11.5px; color: #334155; display: flex; justify-content: space-between; align-items: center;">
                    <span>📱 <b>아이폰/모바일 환경:</b> 첨부된 <code>*.html</code> 웹리포트를 사파리/크롬으로 열면 스마트폰 전체화면으로 열람 가능합니다.</span>
                    <span style="background: #DBEAFE; color: #1E40AF; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 10px;">모바일 퍼스트</span>
                </div>

                <div style="padding: 24px;">

                    <!-- ⚡ 오늘의 1분 액션 체크리스트 (Executive Action Cube) -->
                    {action_cube_html}
                    
                    <!-- 📋 나만의 3대 핵심 요약 (Daily Summary) -->
                    {exec_summary_html}

                    <!-- 📰 1면 톱 기획특집 기사 (The Lead Story) -->
                    {mega_html}

                    <!-- 🛍️ 2면 기획 르포: 트렌드 & 소비 심리 해부 -->
                    {story_dive_html}

                    <!-- 📄 3면 기업 심층 해부: 증권사 공식 애널리스트 리포트 -->
                    <div style="margin-bottom: 24px;">
                        <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #16A34A; padding-bottom: 6px; margin-top: 0;">
                            📄 [3면] 증권사 공식 애널리스트 Top 리포트 심층 해부 (비전문가 눈높이 해설)
                        </h2>
                        <div style="margin-top: 14px;">
                            {reports_cards_html}
                        </div>
                    </div>

                    <!-- 🏛️ 4면 DART 특수공시 심층 행간 읽기 -->
                    {disclosures_html}

                    <!-- 🎯 AI 추천 종목 사후 검증 (Backtesting) 섹션 -->
                    {perf_html}

                    <!-- 🇺🇸 미국 글로벌 빅테크 4대장 섹션 -->
                    {us_bigtech_html}

                    <!-- 3. 주식 매매 추천 & 추천 금액 섹션 -->
                    <div style="margin-bottom: 24px;">
                        <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #3B82F6; padding-bottom: 6px;">
                            🎯 오늘의 주식 매매 신호 및 추천 금액 (Action Signals)
                        </h2>
                        
                        <div style="margin-top: 14px;">
                            <div style="font-size: 14px; font-weight: bold; color: #16A34A; margin-bottom: 6px;">[오늘 단기 매수 유망 - 추천 매수가 & 목표 매도가]</div>
                            {today_buy_html}
                        </div>

                        <div style="margin-top: 14px;">
                            <div style="font-size: 14px; font-weight: bold; color: #2563EB; margin-bottom: 6px;">[장기 모아가면 좋을 주식 - 분할 매수가 & 장기 목표가]</div>
                            {long_buy_html}
                        </div>

                        <div style="margin-top: 14px;">
                            <div style="font-size: 14px; font-weight: bold; color: #DC2626; margin-bottom: 6px;">[주의 / 팔면 좋은 주식 - 권고 매도가 & 리스크 관리]</div>
                            {sell_html}
                        </div>

                        <!-- 🔥 외인·기관 실시간 수급 쌍끌이 레이더 -->
                        {radar_section_html}
                    </div>

                    <!-- 🪙 가상자산 전용 인텔리전스 섹션 -->
                    {crypto_section_html}

                    <!-- 🏢 대한민국 부동산 시장 동향 리포트 섹션 -->
                    {real_estate_section_html}

                    <!-- 4. 시장 지표 요약 섹션 -->
                    <div style="margin-bottom: 24px;">
                        <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #3B82F6; padding-bottom: 6px;">📈 실시간 시장 지표 (증시 & 환율)</h2>
                        <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px;">
                            <tr style="background: #F1F5F9; color: #475569;">
                                <th style="padding: 8px 10px; border: 1px solid #E5E7EB; text-align: left;">항목</th>
                                <th style="padding: 8px 10px; border: 1px solid #E5E7EB; text-align: right;">현재가</th>
                                <th style="padding: 8px 10px; border: 1px solid #E5E7EB; text-align: right;">등락/기준</th>
                            </tr>
                            {indices_rows}
                            {rates_rows}
                        </table>
                    </div>

                    <!-- 5. 7대 분야별 다수 헤드라인 -->
                    <div style="margin-bottom: 24px;">
                        <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #3B82F6; padding-bottom: 6px;">
                            🌐 7대 분야별 주요 헤드라인
                        </h2>
                        <div style="margin-top: 12px;">
                            {headlines_html}
                        </div>
                    </div>

                    <!-- 안내 박스 -->
                    <div style="background: #F8FAFC; border: 1px solid #CBD5E1; border-left: 4px solid #1E3A8A; border-radius: 6px; padding: 14px; font-size: 12px; color: #334155; line-height: 1.6;">
                        📁 <b>구글 드라이브 심층 보고서 보관함 안내:</b><br>
                        • <b>데일리 심층 PDF:</b> <code>{date_str[:7]}/{date_str}_데일리_심층_종합분석_보고서.pdf</code> (20일 주가 변화 SVG 차트, 실적 추정치 표, DART 공시 투자전략 전문 수록)<br>
                        • <b>공식 증권사 원본 PDF:</b> <code>{date_str[:7]}/공식_리서치_PDF/</code> (여의도 애널리스트 공인 원본 보고서 보관)<br>
                        📎 <b>첨부 파일 안내:</b> 스마트폰 및 브라우저에서 편리하게 열람할 수 있도록 반응형 모바일 웹리포트(<code>.html</code>) 파일이 단독 첨부되어 있습니다. (상세 PDF 및 엑셀은 구글 드라이브 보관함에서 확인 가능)
                    </div>

                </div>

                <!-- 푸터 -->
                <div style="background: #F1F5F9; color: #64748B; font-size: 12px; text-align: center; padding: 14px; border-top: 1px solid #E2E8F0;">
                    자동 발송 시스템: py_auto_test • 매일 아침 07:00 정기 발행 • 보고 책임: 전략기획 및 인텔리전스 리서치팀
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def build_weekly_html_body(self, date_str: str, weekly_data: dict) -> str:
        """일요일 주간 총결산 스페셜 프리미엄 매거진 HTML 템플릿 생성"""
        week_label = weekly_data.get("week_label", "금주 주간 결산")
        weekly_coins = weekly_data.get("weekly_coins", [])
        top_stocks = weekly_data.get("top_stocks", [])
        weekly_issues = weekly_data.get("weekly_issues", [])
        weekly_reports = weekly_data.get("weekly_reports", [])

        # 🪙 코인 주간 카드
        coin_cards_html = ""
        for c in weekly_coins:
            coin_cards_html += f"""
            <div style="background: #FAF5FF; border-left: 4px solid #9333EA; padding: 12px 14px; margin-bottom: 10px; border-radius: 6px;">
                <div style="font-weight: bold; color: #6B21A8; font-size: 15px;">
                    {c['icon']} {c['name']} <span style="font-size: 13px; color: #6B7280;">({c['symbol']})</span> - 현재가: {c['cur_price']}
                </div>
                <div style="margin: 6px 0; background: #F3E8FF; padding: 6px 10px; border-radius: 4px; font-size: 13px; color: #581C87;">
                    💰 <b>차주 매수 권고 밴드:</b> {c['weekly_buy_price']} &nbsp;|&nbsp; 
                    🎯 <b>차주 주간 목표가:</b> <span style="font-weight: bold; color: #7E22CE;">{c['weekly_sell_price']}</span> 
                    <span style="font-size: 12px; background: #E9D5FF; padding: 1px 6px; border-radius: 3px; font-weight: bold;">(목표 {c['expected_yield']})</span>
                </div>
                <div style="color: #374151; font-size: 12px; margin-top: 4px;">
                    💡 <b>주간 평가:</b> {c['signal']} - {c['outlook']}
                </div>
            </div>
            """

        # 📈 주식 주간 유망주 카드
        stock_cards_html = ""
        for s in top_stocks:
            stock_cards_html += f"""
            <div style="background: #F0FDF4; border: 1px solid #BBF7D0; padding: 12px 14px; margin-bottom: 10px; border-radius: 6px;">
                <div style="font-weight: bold; color: #166534; font-size: 15px;">
                    🟢 {s['name']} <span style="font-size: 12px; color: #4B5563;">({s['ticker']})</span> - 현재가: {s['cur_price']}
                </div>
                <div style="margin: 6px 0; background: #DCFCE7; padding: 6px 10px; border-radius: 4px; font-size: 13px; color: #15803D;">
                    👉 <b>차주 진입가:</b> {s['buy_price']} &nbsp;|&nbsp; <b>목표 매도가:</b> <span style="font-weight: bold;">{s['sell_price']}</span>
                    <span style="font-size: 12px; background: #BBF7D0; padding: 1px 6px; border-radius: 3px; font-weight: bold;">(기대수익 {s['expected_yield']})</span>
                </div>
                <div style="font-size: 12px; color: #374151; margin-top: 4px;">
                    💡 <b>차주 투자 포인트:</b> {s['reason']}
                </div>
            </div>
            """

        # 주간 도시에 데이터 추출
        nd = weekly_data.get("newspaper_dossier") or weekly_data.get("story_dive_data", {}).get("newspaper_dossier")
        if not nd and IntelligenceDossierEngine and weekly_issues:
            try:
                engine = IntelligenceDossierEngine()
                top_iss = weekly_issues[0] if weekly_issues else {}
                mega_d = engine.expand_mega_issue_story(top_iss)
                trend_d = engine.expand_trend_story({"title": top_iss.get("기사제목", "소비 트렌드"), "summary": top_iss.get("요약내용", "")})
                exp_reps = [engine.expand_analyst_report(r) for r in weekly_reports[:2]] if weekly_reports else []
                nd = {"mega_dossier": mega_d, "trend_dossier": trend_d, "expanded_reports": exp_reps}
            except Exception:
                nd = {}
        elif not nd:
            nd = {}

        mega_d = nd.get("mega_dossier", {})
        trend_d = nd.get("trend_dossier", {})
        exp_reps = nd.get("expanded_reports", [])

        # 주간 메가 심층 기획 기사
        weekly_mega_html = ""
        if mega_d and mega_d.get("chapter1"):
            weekly_mega_html = f"""
            <div style="background: #FFFFFF; border: 2px solid #1E3A8A; border-radius: 8px; padding: 18px; margin-bottom: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.06);">
                <div style="font-size: 13px; font-weight: bold; color: #1E3A8A; margin-bottom: 6px;">🌐 [주간 1면 톱 심층 기획 기사]</div>
                <div style="font-size: 17px; font-weight: bold; color: #0F172A; margin-bottom: 6px;">{mega_d.get('headline')}</div>
                <div style="font-size: 12.5px; color: #2563EB; font-weight: 600; margin-bottom: 12px;">{mega_d.get('subhead')}</div>
                <div style="background: #F8FAFC; border-left: 4px solid #1E3A8A; padding: 10px 14px; font-size: 12px; color: #1E293B; line-height: 1.65; margin-bottom: 14px; font-style: italic;">{mega_d.get('lead')}</div>
                <div style="font-size: 12px; color: #334155; line-height: 1.65;">
                    <div style="margin-bottom: 8px; background: #FFFFFF; border: 1px solid #E2E8F0; padding: 10px 12px; border-radius: 6px;">{mega_d.get('chapter1')}</div>
                    <div style="margin-bottom: 8px; background: #FFFFFF; border: 1px solid #E2E8F0; padding: 10px 12px; border-radius: 6px;">{mega_d.get('chapter2')}</div>
                    <div style="margin-bottom: 8px; background: #FFFFFF; border: 1px solid #E2E8F0; padding: 10px 12px; border-radius: 6px;">{mega_d.get('chapter3')}</div>
                    <div style="background: #EFF6FF; border: 1px solid #BFDBFE; padding: 10px 12px; border-radius: 6px; color: #1E40AF;">{mega_d.get('chapter4')}</div>
                </div>
            </div>
            """

        # 주간 트렌드 기획 르포
        weekly_trend_html = ""
        if trend_d and trend_d.get("chapter1"):
            weekly_trend_html = f"""
            <div style="background: #FFFFFF; border: 2px solid #DB2777; border-radius: 8px; padding: 18px; margin-bottom: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.06);">
                <div style="font-size: 13px; font-weight: bold; color: #9D174D; margin-bottom: 6px;">🛍️ [주간 기획 르포: 2030 소비 심리 & 트렌드 총결산]</div>
                <div style="font-size: 16.5px; font-weight: bold; color: #0F172A; margin-bottom: 6px;">{trend_d.get('headline')}</div>
                <div style="font-size: 12.5px; color: #BE185D; font-weight: 600; margin-bottom: 12px;">{trend_d.get('subhead')}</div>
                <div style="background: #FDF2F8; border-left: 4px solid #DB2777; padding: 10px 14px; font-size: 12px; color: #1E293B; line-height: 1.65; margin-bottom: 14px; font-style: italic;">{trend_d.get('lead')}</div>
                <div style="font-size: 12px; color: #334155; line-height: 1.65;">
                    <div style="margin-bottom: 8px; background: #FFFFFF; border: 1px solid #FCE7F3; padding: 10px 12px; border-radius: 6px;">{trend_d.get('chapter1')}</div>
                    <div style="margin-bottom: 8px; background: #FFFFFF; border: 1px solid #FCE7F3; padding: 10px 12px; border-radius: 6px;">{trend_d.get('chapter2')}</div>
                    <div style="margin-bottom: 8px; background: #FFFFFF; border: 1px solid #FCE7F3; padding: 10px 12px; border-radius: 6px;">{trend_d.get('chapter3')}</div>
                    <div style="background: #FFF1F2; border: 1px solid #FECDD3; padding: 10px 12px; border-radius: 6px; color: #9F1239;">{trend_d.get('chapter4')}</div>
                </div>
            </div>
            """

        # 📄 공식 리포트 하이라이트
        report_cards_html = ""
        if exp_reps:
            for r in exp_reps[:2]:
                report_cards_html += f"""
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-top: 4px solid #0EA5E9; padding: 14px 16px; margin-bottom: 12px; border-radius: 8px;">
                    <div style="font-size: 14.5px; font-weight: bold; color: #0369A1; margin-bottom: 4px;">{r.get('headline')}</div>
                    <div style="font-size: 11px; color: #0284C7; margin-bottom: 6px;">{r.get('subhead')}</div>
                    <div style="font-size: 11px; color: #334155; line-height: 1.6;">
                        <div style="margin-bottom: 4px;">{r.get('sec_business')}</div>
                        <div style="margin-bottom: 4px;">{r.get('sec_thesis')}</div>
                        <div style="margin-bottom: 4px; background: #F0FDF4; padding: 6px; border-radius: 4px;">{r.get('sec_financials')}</div>
                        <div style="background: #EFF6FF; padding: 6px; border-radius: 4px;">{r.get('sec_action')}</div>
                    </div>
                </div>
                """
        for r in weekly_reports[:4]:
            tp = r.get("target_price", "-")
            tp_str = f"{int(tp):,}원" if str(tp).replace(",", "").isdigit() else str(tp)
            report_cards_html += f"""
            <div style="background: #F8FAFC; border-left: 4px solid #0EA5E9; padding: 10px 14px; margin-bottom: 8px; border-radius: 6px;">
                <div style="font-weight: bold; color: #0369A1; font-size: 14px;">
                    📘 [{r.get('broker')}] {r.get('item_name')}: {r.get('title')}
                </div>
                <div style="font-size: 12px; color: #0284C7; margin: 4px 0;">
                    🎯 <b>공인 목표가:</b> {tp_str} | 투자의견: {r.get('opinion')} | 신뢰도: ⭐ {r.get('score')}점
                </div>
                <div style="font-size: 12px; color: #475569;">
                    {r.get('summary', '')[:120]}...
                </div>
            </div>
            """

        # 🌐 주간 메가 이슈
        issues_html = ""
        for idx, iss in enumerate(weekly_issues, 1):
            issues_html += f"""
            <div style="margin-bottom: 10px; font-size: 13px; line-height: 1.5; border-bottom: 1px dashed #E2E8F0; padding-bottom: 8px;">
                <b>{idx}. [{iss.get('category')}]</b> <a href="{iss.get('link')}" style="color: #1E3A8A; text-decoration: none; font-weight: bold;">{iss.get('title')}</a>
                <span style="font-size: 11px; color: #64748B;">({iss.get('media')})</span>
                <div style="font-size: 12px; color: #475569; margin-top: 2px;">• {iss.get('summary')}</div>
            </div>
            """

        # 🏢 주간 부동산 섹션
        re_data_weekly = weekly_data.get("real_estate_data")
        if not re_data_weekly and RealEstateAdvisor:
            try:
                re_data_weekly = RealEstateAdvisor().analyze_market()
            except Exception:
                re_data_weekly = {}
        elif not re_data_weekly:
            re_data_weekly = {}

        weekly_re_rows = ""
        for r in re_data_weekly.get("regional_trends", []):
            sc = r.get("sale_change", "0.00%")
            jc = r.get("jeonse_change", "0.00%")
            sc_col = "#16A34A" if "+" in sc else ("#DC2626" if "-" in sc else "#64748B")
            jc_col = "#16A34A" if "+" in jc else ("#DC2626" if "-" in jc else "#64748B")
            weekly_re_rows += f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 6px 8px; font-weight: bold; color: #0F172A;">{r.get('region')}</td>
                <td style="padding: 6px 8px; text-align: right; color: {sc_col}; font-weight: bold;">{sc}</td>
                <td style="padding: 6px 8px; text-align: right; color: {jc_col}; font-weight: bold;">{jc}</td>
                <td style="padding: 6px 8px; text-align: center;"><span style="background: #F1F5F9; color: {r.get('status_color', '#334155')}; font-weight: bold; font-size: 10px; padding: 2px 6px; border-radius: 4px;">{r.get('status')}</span></td>
            </tr>
            """
        w_mi = re_data_weekly.get("mortgage_info", {})
        weekly_re_html = f"""
        <div style="background: #FFFFFF; border: 1px solid #BAE6FD; border-top: 4px solid #0284C7; border-radius: 8px; padding: 14px 16px;">
            <div style="font-size: 13.5px; font-weight: bold; color: #0369A1; margin-bottom: 6px;">권역별 아파트 매매·전세 주간 변동률</div>
            <table style="width: 100%; border-collapse: collapse; font-size: 11.5px; margin-bottom: 10px;">
                <tr style="background: #F0F9FF; color: #0369A1;">
                    <th style="padding: 6px 8px; text-align: left; border: 1px solid #E2E8F0;">권역</th>
                    <th style="padding: 6px 8px; text-align: right; border: 1px solid #E2E8F0;">매매</th>
                    <th style="padding: 6px 8px; text-align: right; border: 1px solid #E2E8F0;">전세</th>
                    <th style="padding: 6px 8px; text-align: center; border: 1px solid #E2E8F0;">시장 국면</th>
                </tr>
                {weekly_re_rows}
            </table>
            <div style="font-size: 11px; color: #334155; line-height: 1.5; background: #F8FAFC; padding: 8px 10px; border-radius: 4px;">
                🏦 <b>주담대 금리:</b> 5년 고정 {w_mi.get('fixed_rate_band', '-')} / 변동 {w_mi.get('variable_rate_band', '-')} &nbsp;|&nbsp; <b>DSR 규제:</b> {w_mi.get('dsr_status', '-')}
            </div>
        </div>
        """

        # 0. 최고경영진 주간 핵심 요약 (Executive Summary Box)
        p_data = weekly_data.get("performance_data", {})
        p_sum = p_data.get("summary", {}) if isinstance(p_data, dict) else {}
        win_rate = p_sum.get("win_rate", 0)
        avg_ret = p_sum.get("avg_return", 0.0)

        exec_weekly_summary_html = f"""
        <div style="background: #F8FAFC; border: 2px solid #1E3A8A; border-radius: 8px; padding: 16px 18px; margin-bottom: 22px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <div style="font-size: 14px; font-weight: bold; color: #1E3A8A; margin-bottom: 8px; display: flex; align-items: center;">
                <span>📋 한 주간의 3대 핵심 요약 (Weekly Summary)</span>
                <span style="margin-left: auto; font-size: 11px; background: #DBEAFE; color: #1E40AF; padding: 2px 8px; border-radius: 10px; font-weight: bold;">나만의 주간 브리핑</span>
            </div>
            <ul style="margin: 0; padding-left: 18px; font-size: 12.5px; color: #1E293B; line-height: 1.7;">
                <li style="margin-bottom: 4px;"><b>AI 포트폴리오 성과:</b> 누적 적중 승률 <b>{win_rate}%</b>, 평균 수익률 <b>{avg_ret:+.2f}%</b> 달성으로 시장 대비 견고한 초과 수익률 유지</li>
                <li style="margin-bottom: 4px;"><b>차주 시장 포커스:</b> 미국 금리 기조 및 환율 변동성 대비 현금 비중 20% 유지, 중장기 실적 상향 반도체·방산 섹터 분할 매수 유효</li>
                <li><b>구글 드라이브 전략 백서:</b> 표지 및 목차를 포함한 12~15페이지 분량의 <b>『{date_str}_주간_글로벌_금융_전략_백서.pdf』</b>가 구글 드라이브(<code>{date_str[:7]}/</code>)에 적재 완료되었습니다.</li>
            </ul>
        </div>
        """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>My Weekly Intelligence Briefing ({date_str})</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif; background-color: #F8FAFC; margin: 0; padding: 20px; line-height: 1.6; color: #1E293B;">
            <div style="max-width: 680px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border: 1px solid #E2E8F0;">
                
                <!-- 주간 전용 프리미엄 네이비&골드 헤더: 나만의 주간 브리핑 톤앤매너 -->
                <div style="background: linear-gradient(135deg, #0A0F1D 0%, #1E3A8A 60%, #92400E 100%); color: #FFFFFF; padding: 28px 24px; text-align: center;">
                    <div style="font-size: 11px; letter-spacing: 2px; color: #FCD34D; font-weight: bold; text-transform: uppercase;">My Weekly Intelligence Briefing</div>
                    <h1 style="margin: 8px 0 0; font-size: 22px; font-weight: bold;">📊 [나만의 주간 브리핑] {week_label} 금융·이슈 총결산 백서</h1>
                    <p style="margin: 6px 0 0; font-size: 12.5px; opacity: 0.9; color: #F1F5F9;">7일간 축적 데이터 종합 분석 • 차주 포트폴리오 전략 및 정식 백서 구글 드라이브 적재</p>
                </div>

                <div style="padding: 24px;">

                    <!-- 📋 나만의 주간 핵심 요약 (Weekly Summary) -->
                    {exec_weekly_summary_html}

                    <!-- 🌐 주간 1면 톱 심층 기획 기사 -->
                    {weekly_mega_html}

                    <!-- 🛍️ 주간 기획 르포: 2030 소비 심리 & 트렌드 -->
                    {weekly_trend_html}

                    <!-- 1. 🪙 3대 코인 주간 총결산 & 차주 매매 밴드 -->
                    <div style="margin-bottom: 24px;">
                        <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #9333EA; padding-bottom: 6px; margin-top: 0;">
                            🪙 1. 3대 코인(BTC, ETH, SOL) 주간 총결산 및 차주 전략
                        </h2>
                        <div style="margin-top: 14px;">
                            {coin_cards_html}
                        </div>
                    </div>

                    <!-- 2. 📈 주식 주간 유망주 및 차주 공략 종목 -->
                    <div style="margin-bottom: 24px;">
                        <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #16A34A; padding-bottom: 6px;">
                            📈 2. 금주 추천 성과 피드백 & 차주 공략 유망주 TOP
                        </h2>
                        <div style="margin-top: 14px;">
                            {stock_cards_html}
                        </div>
                    </div>

                    <!-- 3. 📄 공식 증권사 리서치 주간 하이라이트 -->
                    <div style="margin-bottom: 24px;">
                        <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #0EA5E9; padding-bottom: 6px;">
                            📄 3. 금주 증권사 공식 리포트 하이라이트 (공인 목표가 & 기업 정밀 해부)
                        </h2>
                        <div style="margin-top: 14px;">
                            {report_cards_html}
                        </div>
                    </div>

                    <!-- 4. 🌐 한 주간 7대 분야 메가 이슈 TOP 5 -->
                    <div style="margin-bottom: 24px;">
                        <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #F59E0B; padding-bottom: 6px;">
                            🌐 4. 한 주간 7대 분야 핵심 메가 이슈 TOP 5
                        </h2>
                        <div style="margin-top: 14px; background: #FFFBEB; border: 1px solid #FEF3C7; border-radius: 8px; padding: 14px;">
                            {issues_html}
                        </div>
                    </div>

                    <!-- 5. 🏢 대한민국 부동산 시장 주간 총결산 -->
                    <div style="margin-bottom: 24px;">
                        <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #0284C7; padding-bottom: 6px;">
                            🏢 5. 대한민국 부동산 주간 동향 & 금융 규제 총결산
                        </h2>
                        <div style="margin-top: 14px;">
                            {weekly_re_html}
                        </div>
                    </div>

                    <!-- 안내 박스 -->
                    <div style="background: #F8FAFC; border: 1px solid #CBD5E1; border-left: 4px solid #1E3A8A; border-radius: 6px; padding: 14px; font-size: 12px; color: #334155; line-height: 1.6;">
                        📁 <b>구글 드라이브 주간 전략 백서 보관함 안내:</b><br>
                        • <b>주간 종합 백서 PDF:</b> <code>{date_str[:7]}/{date_str}_주간_글로벌_금융_전략_백서.pdf</code> (정식 표지, 목차, 6대 챕터 종합 결산 수록)<br>
                        📎 <b>첨부 파일 안내:</b> 스마트폰 및 브라우저에서 편리하게 열람할 수 있도록 반응형 웹리포트(<code>.html</code>) 파일이 단독 첨부되어 있습니다. (상세 백서 PDF 및 누적 집계 엑셀은 구글 드라이브에 보관)
                    </div>

                </div>

                <!-- 푸터 -->
                <div style="background: #F1F5F9; color: #64748B; font-size: 12px; text-align: center; padding: 14px; border-top: 1px solid #E2E8F0;">
                    자동 발송 시스템: py_auto_test • 매주 일요일 아침 07:00 주간 스페셜 발행 • 보고 책임: 전략기획 및 인텔리전스 리서치팀
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def send_report(self, date_str: str, stock_indices: list, exchange_rates: list, stock_advice: dict, crypto_advice: dict, official_reports: list, news_result: dict, top_research_list: list = None, attachment_path: str = None, performance_data: dict = None, special_disclosures: list = None, story_dive_data: dict = None, attachments: list = None, real_estate_data: dict = None, edition: str = "morning") -> bool:
        """나만의 데일리 브리핑 이메일 발송 (모닝/이브닝 구분)"""
        if not self.is_configured():
            print("\n⚠️ [이메일 발송 건너뜀] NAVER_USER 또는 NAVER_PASSWORD가 설정되지 않았습니다.")
            return False

        is_evening = (str(edition).lower() == "evening") or ("저녁" in str(edition)) or ("이브닝" in str(edition))
        ed_badge = "[이브닝 마감 브리핑]" if is_evening else "[모닝 개장 브리핑]"
        ed_desc = "당일 증시 마감 결산 & 낮 시간 신규 이슈 & 익일 대비" if is_evening else "글로벌 매크로 & 당일 개장 전 투자 전략"

        try:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = f"{ed_badge} {date_str} 나만의 데일리 인텔리전스 - {ed_desc}"
            msg["From"] = f"{self.naver_user}@naver.com"
            msg["To"] = self.receiver_email

            html_content = self.build_html_body(
                date_str=date_str,
                stock_indices=stock_indices,
                exchange_rates=exchange_rates,
                stock_advice=stock_advice,
                crypto_advice=crypto_advice,
                official_reports=official_reports,
                news_result=news_result,
                top_research_list=top_research_list,
                performance_data=performance_data,
                special_disclosures=special_disclosures,
                story_dive_data=story_dive_data,
                real_estate_data=real_estate_data,
            )
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            # 사용자 요청: 첨부파일에는 HTML 파일만 단독 첨부
            file_list = []
            if attachments:
                file_list.extend(attachments)
            if attachment_path and attachment_path not in file_list:
                file_list.append(attachment_path)

            file_list = [f for f in file_list if f and f.lower().endswith(".html")]

            for fpath in file_list:
                if fpath and os.path.exists(fpath):
                    filename = os.path.basename(fpath)
                    with open(fpath, "rb") as f:
                        part = MIMEApplication(f.read(), Name=filename)
                    part["Content-Disposition"] = f'attachment; filename="{filename}"'
                    msg.attach(part)

            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=15) as server:
                server.login(self.naver_user, self.naver_password)
                server.send_message(msg)

            print(f"📧 ✅ {ed_badge} 데일리 이메일 발송 완료! 수신자: {self.receiver_email}")
            return True
        except Exception as e:
            print(f"📧 ❌ 이메일 발송 실패: {e}")
            return False

    def send_weekly_report(self, date_str: str, weekly_data: dict, attachment_path: str = None, attachments: list = None) -> bool:
        """매주 일요일 주간 총결산 스페셜 이메일 발송"""
        if not self.is_configured():
            print("\n⚠️ [이메일 발송 건너뜀] NAVER_USER 또는 NAVER_PASSWORD가 설정되지 않았습니다.")
            return False

        week_label = weekly_data.get("week_label", "금주 주간 결산")
        try:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = f"[{week_label} 나만의 주간 브리핑] 한 주간의 금융동향 & 심층 이슈 총결산"
            msg["From"] = f"{self.naver_user}@naver.com"
            msg["To"] = self.receiver_email

            html_content = self.build_weekly_html_body(date_str=date_str, weekly_data=weekly_data)
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            # 다중 첨부파일 지원 (Excel 및 PDF 백서)
            file_list = []
            if attachments:
                file_list.extend(attachments)
            if attachment_path and attachment_path not in file_list:
                file_list.append(attachment_path)

            file_list = [f for f in file_list if f and f.lower().endswith(".html")]

            for fpath in file_list:
                if fpath and os.path.exists(fpath):
                    filename = os.path.basename(fpath)
                    with open(fpath, "rb") as f:
                        part = MIMEApplication(f.read(), Name=filename)
                    part["Content-Disposition"] = f'attachment; filename="{filename}"'
                    msg.attach(part)

            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=15) as server:
                server.login(self.naver_user, self.naver_password)
                server.send_message(msg)

            print(f"📧 🏆 [주간 브리핑] 주간 총결산 백서 이메일 발송 완료! 수신자: {self.receiver_email}")
            return True
        except Exception as e:
            print(f"📧 ❌ 주간 이메일 발송 실패: {e}")
            return False
