"""
email_sender.py
네이버 SMTP를 활용하여 7대 분야별 헤드라인 + 주식 추천가 +
비트코인·이더리움·솔라나 3대 코인 매수/매도 추천금액 +
증권사 공식 애널리스트 Top 리포트 심층 분석 & 일요일 주간 총결산 브리핑 발송 모듈
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


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

    def build_html_body(self, date_str: str, stock_indices: list, exchange_rates: list, stock_advice: dict, crypto_advice: dict, official_reports: list, news_result: dict, top_research_list: list = None, performance_data: dict = None, special_disclosures: list = None) -> str:
        """스마트폰과 PC에서 가독성 극대화된 모던 카드형 데일리 HTML 이메일 템플릿 생성"""
        today_buys = stock_advice.get("today_buy_picks", [])
        long_buys = stock_advice.get("longterm_buy_picks", [])
        sells = stock_advice.get("sell_warning_picks", [])

        # ---------------------------------------------------------
        # 1. 📄 증권사 공식 애널리스트 Top 리포트 심층 분석 카드 섹션
        # ---------------------------------------------------------
        reports_cards_html = ""
        if official_reports:
            for rep in official_reports[:5]:
                tp = rep.get("target_price")
                tp_str = f"{int(tp):,}원" if tp else "-"
                ft = rep.get("financial_table", {})
                ft_box = ""
                if ft.get("has_table"):
                    ft_box = f"""
                    <div style="margin: 6px 0; background: #DCFCE7; border: 1px dashed #16A34A; padding: 6px 10px; border-radius: 4px; font-size: 11px; color: #14532D;">
                        📊 <b>PDF 핵심 실적 표:</b> 2026F 매출 {ft.get('rev_2026', '-')} / 영익 {ft.get('op_2026', '-')} &nbsp;|&nbsp; 2027F 매출 {ft.get('rev_2027', '-')} / 영익 {ft.get('op_2027', '-')}
                        <div style="color: #166534; margin-top: 3px;">📈 <i>{ft.get('yoy_summary', '')[:95]}</i></div>
                    </div>
                    """
                reports_cards_html += f"""
                <div style="background: #F0FDF4; border-left: 4px solid #16A34A; padding: 12px 14px; margin-bottom: 10px; border-radius: 6px;">
                    <div style="font-weight: bold; color: #15803D; font-size: 14px;">
                        🏛️ [{rep.get('broker')}] <b>{rep.get('item_name')}</b>: {rep.get('title')}
                        <span style="font-size: 11px; background: #DCFCE7; color: #166534; padding: 1px 6px; border-radius: 10px; margin-left: 6px;">
                            신뢰도 ⭐ {rep.get('credibility_score')}점
                        </span>
                    </div>
                    <div style="margin: 6px 0; background: #DCFCE7; padding: 6px 10px; border-radius: 4px; font-size: 12px; color: #14532D;">
                        🎯 <b>공인 목표주가:</b> <span style="font-weight: bold; color: #166534;">{tp_str}</span> &nbsp;|&nbsp; 
                        📌 <b>투자의견:</b> <span style="font-weight: bold;">{rep.get('opinion', 'BUY')}</span> &nbsp;|&nbsp;
                        👀 <b>시장 조회수:</b> {rep.get('read_count', 0)}회
                    </div>
                    {ft_box}
                    <div style="color: #374151; font-size: 12px; margin-top: 4px; line-height: 1.4;">
                        💡 <b>핵심 요지:</b> {rep.get('summary_text', '')[:140]}...
                    </div>
                    <div style="font-size: 11px; color: #6B7280; margin-top: 4px;">
                        📁 <i>구글 드라이브(공식_리서치_PDF) 원본 보관: {rep.get('pdf_filename', '')}</i>
                    </div>
                </div>
                """

        # ---------------------------------------------------------
        # 2. 🪙 3대 코인(BTC, ETH, SOL) 카드 섹션
        # ---------------------------------------------------------
        coins = crypto_advice.get("coins", [])
        coin_cards_html = ""
        for c in coins:
            coin_cards_html += f"""
            <div style="background: #FAF5FF; border-left: 4px solid #A855F7; padding: 12px 14px; margin-bottom: 10px; border-radius: 6px;">
                <div style="font-weight: bold; color: #7E22CE; font-size: 15px;">
                    {c['icon']} {c['name']} <span style="font-size: 13px; color: #6B7280;">({c['symbol']})</span> - <span style="color: #111827;">현재가: {c['cur_price']}</span> 
                    <span style="font-size: 12px; color: {'#16A34A' if '+' in c['change_rate'] else '#DC2626'}; font-weight: bold;">({c['change_rate']})</span>
                </div>
                <div style="margin: 6px 0; background: #F3E8FF; padding: 6px 10px; border-radius: 4px; font-size: 13px; color: #581C87;">
                    💰 <b>매수 추천가:</b> <span style="font-weight: bold;">{c['buy_price']}</span> &nbsp;|&nbsp; 
                    🎯 <b>목표 매도가:</b> <span style="font-weight: bold; color: #7E22CE;">{c['sell_price']}</span> 
                    <span style="font-size: 12px; background: #E9D5FF; padding: 1px 6px; border-radius: 3px; font-weight: bold;">(기대수익 {c['expected_yield']})</span>
                </div>
                <div style="color: #374151; font-size: 12px; margin-top: 4px;">
                    💡 <b>전망 및 근거:</b> {c['outlook']} &nbsp;|&nbsp; 🛑 <b>손절가:</b> {c['stop_loss']} &nbsp;|&nbsp; 📊 <b>RSI:</b> {c['rsi']}
                </div>
            </div>
            """

        crypto_news_html = ""
        c_news = crypto_advice.get("crypto_news", [])
        if c_news:
            crypto_news_html = "<div style='font-size: 12px; color: #6B7280; margin-top: 8px;'><b>📰 코인 시장 헤드라인:</b> " + " | ".join([f"<a href='{cn['link']}' style='color: #4B5563; text-decoration: none;'>{cn['title']}</a>" for cn in c_news[:2]]) + "</div>"

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

        # 지수 및 환율 테이블
        indices_rows = ""
        for idx in stock_indices:
            color = "#16A34A" if "+" in idx["전일대비"] else "#DC2626"
            indices_rows += f"""
            <tr>
                <td style="padding: 6px 10px; border: 1px solid #E5E7EB; font-weight: bold;">{idx['지수명']}</td>
                <td style="padding: 6px 10px; border: 1px solid #E5E7EB; text-align: right; font-weight: bold;">{idx['현재지수']}</td>
                <td style="padding: 6px 10px; border: 1px solid #E5E7EB; text-align: right; color: {color}; font-weight: bold;">{idx['전일대비']}</td>
            </tr>
            """

        rates_rows = ""
        for fx in exchange_rates:
            rates_rows += f"""
            <tr>
                <td style="padding: 6px 10px; border: 1px solid #E5E7EB;">{fx['통화명']}</td>
                <td style="padding: 6px 10px; border: 1px solid #E5E7EB; text-align: right; font-weight: bold;">{fx['환율(원)']}원</td>
                <td style="padding: 6px 10px; border: 1px solid #E5E7EB; text-align: right; color: #6B7280; font-size: 12px;">{fx['변동/기준']}</td>
            </tr>
            """

        # 7대 분야별 헤드라인
        headlines_html = ""
        top_picks = news_result.get("category_top_picks", {})
        cat_order = [
            ("정치", "🏛️ 정치 핵심 이슈"),
            ("사회/사건사고", "🚨 사회·사건사고 이슈"),
            ("거시경제/비즈니스", "💼 거시경제 & 비즈니스"),
            ("세계/국제", "🌍 세계·국제 뉴스"),
            ("IT/과학/신상품", "💻 IT·과학 & 테크/신상품"),
            ("연예/대중문화", "🎬 연예·문화 트렌드"),
        ]

        for cat_key, icon_title in cat_order:
            items = top_picks.get(cat_key, [])
            if items:
                cat_items_html = ""
                for it in items[:3]:
                    it_link = it.get("링크") or it.get("link", "")
                    tag = f" <span style='background: #FEE2E2; color: #DC2626; padding: 1px 5px; border-radius: 3px; font-size: 11px;'>{it['상태']}</span>" if "집중" in it['상태'] else ""
                    cat_items_html += f"""
                    <div style="margin-bottom: 8px; font-size: 13px; line-height: 1.4;">
                        • <a href="{it_link}" style="color: #1E40AF; text-decoration: none; font-weight: 500;">{it['기사제목']}</a>
                        <span style="font-size: 11px; color: #6B7280;">({it['언론사']})</span>{tag}
                    </div>
                    """

                headlines_html += f"""
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; margin-bottom: 16px;">
                    <div style="font-size: 14px; font-weight: bold; color: #1E293B; margin-bottom: 10px; border-bottom: 2px solid #E2E8F0; padding-bottom: 4px;">
                        {icon_title} <span style="font-size: 12px; color: #64748B; font-weight: normal;">(주요 뉴스 {len(items[:3])}건)</span>
                    </div>
                    {cat_items_html}
                </div>
                """

        # 메가 핫토픽
        mega = news_result.get("mega_issue")
        mega_html = ""
        if mega:
            mega_html = f"""
            <div style="background: #FFF1F2; border: 2px solid #F43F5E; border-radius: 8px; padding: 16px; margin-bottom: 24px;">
                <div style="font-size: 13px; font-weight: bold; color: #E11D48; margin-bottom: 4px;">
                    🔥 오늘의 메가 핫토픽 [언론사 {mega['media_count']}개사 집중 보도]
                </div>
                <div style="font-size: 16px; font-weight: bold; color: #881337; margin-bottom: 8px;">
                    <a href="{mega.get('링크') or mega.get('link', '')}" style="color: #881337; text-decoration: none;">{mega['기사제목']}</a>
                    <span style="font-size: 12px; color: #9F1239; font-weight: normal;">({mega['언론사']})</span>
                </div>
                <div style="font-size: 13px; color: #4C0519; line-height: 1.5; background: #FFE4E6; padding: 8px 12px; border-radius: 6px;">
                    💡 <b>1줄 요약:</b> {mega['요약내용']}
                </div>
            </div>
            """

        # ---------------------------------------------------------
        # 🎯 추천 종목 사후 검증 (Backtesting) & 누적 적중률 카드 (Feature 1)
        # ---------------------------------------------------------
        perf_html = ""
        if performance_data and performance_data.get("summary"):
            s = performance_data["summary"]
            rec_rows = ""
            for r in performance_data.get("records", [])[:5]:
                res_col = "#16A34A" if "달성" in r.get("검증결과", "") else ("#DC2626" if "손절" in r.get("검증결과", "") else "#2563EB")
                rec_rows += f"""
                <tr style="border-bottom: 1px solid #E2E8F0;">
                    <td style="padding: 6px 8px; font-size: 11px;">{r.get('추천일자')}</td>
                    <td style="padding: 6px 8px; font-size: 12px; font-weight: bold;">{r.get('종목명')}</td>
                    <td style="padding: 6px 8px; font-size: 11px; color: #475569;">{r.get('매수추천가')} ➔ {r.get('목표매도가')}</td>
                    <td style="padding: 6px 8px; font-size: 11px; font-weight: bold; color: {res_col};">{r.get('검증결과')}</td>
                    <td style="padding: 6px 8px; font-size: 11px; font-weight: bold; text-align: right; color: {res_col};">{r.get('실현수익률')}</td>
                    <td style="padding: 6px 8px; font-size: 11px; color: #64748B; text-align: center;">{r.get('소요일수')}</td>
                </tr>
                """
            perf_html = f"""
            <div style="background: #F8FAFC; border: 2px solid #3B82F6; border-radius: 8px; padding: 14px; margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #CBD5E1; padding-bottom: 8px; margin-bottom: 10px;">
                    <div style="font-size: 15px; font-weight: bold; color: #1E3A8A;">🎯 AI 추천 종목 사후 검증(Backtesting) & 누적 적중률</div>
                    <div style="background: #1E3A8A; color: #FFFFFF; font-weight: bold; padding: 3px 10px; border-radius: 12px; font-size: 12px;">누적 승률: {s.get('win_rate', 0)}%</div>
                </div>
                <div style="margin-bottom: 10px; font-size: 12px; color: #334155; line-height: 1.6;">
                    📊 <b>검증 총계:</b> {s.get('total_picks', 0)}건 &nbsp;|&nbsp; 
                    🎯 <b>목표가 달성:</b> <span style="color: #16A34A; font-weight: bold;">{s.get('success_count', 0)}건</span> &nbsp;|&nbsp; 
                    🛑 <b>손절:</b> <span style="color: #DC2626; font-weight: bold;">{s.get('stoploss_count', 0)}건</span> &nbsp;|&nbsp; 
                    ⏳ <b>진행 중:</b> {s.get('holding_count', 0)}건 &nbsp;|&nbsp; 
                    💰 <b>평균 수익률:</b> <span style="color: #2563EB; font-weight: bold;">{s.get('avg_return', 0.0):+.2f}%</span>
                </div>
                <table style="width: 100%; border-collapse: collapse; background: #FFFFFF; border-radius: 4px; overflow: hidden;">
                    <tr style="background: #F1F5F9; color: #475569; font-size: 11px; font-weight: bold; text-align: left;">
                        <th style="padding: 6px 8px;">추천일</th>
                        <th style="padding: 6px 8px;">종목</th>
                        <th style="padding: 6px 8px;">추천가 ➔ 목표가</th>
                        <th style="padding: 6px 8px;">검증 상태</th>
                        <th style="padding: 6px 8px; text-align: right;">수익률</th>
                        <th style="padding: 6px 8px; text-align: center;">소요</th>
                    </tr>
                    {rec_rows}
                </table>
            </div>
            """

        # ---------------------------------------------------------
        # 🏛️ 금융감독원(DART) & KIND 기업 핵심 특수 공시 카드 (Feature 3)
        # ---------------------------------------------------------
        disclosures_html = ""
        if special_disclosures:
            d_cards = ""
            for d in special_disclosures[:4]:
                badge = d.get("공시배지", "")
                badge_bg = "#DCFCE7" if "자사주" in badge else ("#DBEAFE" if "내부자" in badge else ("#FEF3C7" if "수주" in badge else "#F3E8FF"))
                badge_fg = "#166534" if "자사주" in badge else ("#1E40AF" if "내부자" in badge else ("#92400E" if "수주" in badge else "#6B21A8"))
                corp = d.get("관련기업") or "상장사"
                d_cards += f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid {badge_fg}; padding: 10px 12px; margin-bottom: 8px; border-radius: 6px;">
                    <div style="font-size: 13px; font-weight: bold; color: #1E293B;">
                        <span style="background: {badge_bg}; color: {badge_fg}; padding: 1px 6px; border-radius: 4px; font-size: 11px; margin-right: 6px;">{badge}</span>
                        <b>{corp}</b> | <a href="{d.get('링크')}" style="color: #1E293B; text-decoration: none;">{d.get('공시제목')}</a>
                    </div>
                    <div style="font-size: 12px; color: #475569; margin-top: 4px;">
                        💡 <b>투자 시사점:</b> {d.get('영향전망')} <span style="color: #94A3B8; font-size: 11px;">({d.get('언론사')})</span>
                    </div>
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
        # 🇺🇸 미국 글로벌 빅테크 4대장 (NVDA, TSLA, AAPL, MSFT) 카드 (Feature 4)
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

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>07시 모닝 브리핑</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; background-color: #F8FAFC; margin: 0; padding: 20px; line-height: 1.6; color: #1E293B;">
            <div style="max-width: 680px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border: 1px solid #E2E8F0;">
                
                <!-- 헤더 -->
                <div style="background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%); color: #FFFFFF; padding: 24px; text-align: center;">
                    <div style="font-size: 13px; letter-spacing: 1px; opacity: 0.9; text-transform: uppercase;">Daily Morning 07:00 Briefing</div>
                    <h1 style="margin: 8px 0 0; font-size: 22px;">☕ 아침 7시 모닝 브리핑 ({date_str})</h1>
                    <p style="margin: 6px 0 0; font-size: 13px; opacity: 0.85;">주식 & 코인(BTC/ETH/SOL) 추천가 & 증권사 공식 Top 10 리포트 & DART 특수공시</p>
                </div>

                <div style="padding: 24px;">
                    
                    <!-- 🔥 메가 핫토픽 -->
                    {mega_html}

                    <!-- 🎯 AI 추천 종목 사후 검증 (Backtesting) 섹션 -->
                    {perf_html}

                    <!-- 🏛️ 금융감독원 특수 공시 섹션 -->
                    {disclosures_html}

                    <!-- 🇺🇸 미국 글로벌 빅테크 4대장 섹션 -->
                    {us_bigtech_html}

                    <!-- 1. 📄 증권사 공식 리포트 섹션 -->
                    <div style="margin-bottom: 24px;">
                        <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #16A34A; padding-bottom: 6px; margin-top: 0;">
                            📄 증권사 공식 애널리스트 Top 리포트 심층 분석 (공인 목표가 & 2026/2027 실적 표)
                        </h2>
                        <div style="margin-top: 14px;">
                            {reports_cards_html}
                        </div>
                    </div>

                    <!-- 2. 🪙 3대 코인(비트코인, 이더리움, 솔라나) 섹션 -->
                    <div style="margin-bottom: 24px;">
                        <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #A855F7; padding-bottom: 6px;">
                            🪙 3대 코인(BTC, ETH, SOL) 시세 & 매매 추천금액
                        </h2>
                        <div style="margin-top: 14px;">
                            {coin_cards_html}
                            {crypto_news_html}
                        </div>
                    </div>

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
                    </div>

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
                    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 12px; font-size: 12px; color: #64748B;">
                        📎 <b>첨부 파일 안내:</b> 주식/코인 매매 추천표와 공식 리포트 분석이 정리된 엑셀 파일(<code>.xlsx</code>)이 첨부되어 있습니다.<br>
                        📁 <b>구글 드라이브 안내:</b> 월별 폴더(<code>YYYY-MM/</code>) 및 증권사 원본 리포트(<code>공식_리서치_PDF/</code>)에 자동 누적 축적 중입니다.
                    </div>

                </div>

                <!-- 푸터 -->
                <div style="background: #F1F5F9; color: #64748B; font-size: 12px; text-align: center; padding: 14px; border-top: 1px solid #E2E8F0;">
                    자동 발송 시스템: py_auto_test • 매일 아침 07:00 정기 발행
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

        # 📄 공식 리포트 하이라이트
        report_cards_html = ""
        for r in weekly_reports:
            report_cards_html += f"""
            <div style="background: #F8FAFC; border-left: 4px solid #0EA5E9; padding: 10px 14px; margin-bottom: 8px; border-radius: 6px;">
                <div style="font-weight: bold; color: #0369A1; font-size: 14px;">
                    📘 [{r.get('broker')}] {r.get('item_name')}: {r.get('title')}
                </div>
                <div style="font-size: 12px; color: #0284C7; margin: 4px 0;">
                    🎯 <b>공인 목표가:</b> {r.get('target_price')} | 투자의견: {r.get('opinion')} | 신뢰도: ⭐ {r.get('score')}점
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

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>주간 금융·이슈 총결산 브리핑</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; background-color: #F8FAFC; margin: 0; padding: 20px; line-height: 1.6; color: #1E293B;">
            <div style="max-width: 680px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border: 1px solid #E2E8F0;">
                
                <!-- 주간 전용 프리미엄 네이비&골드 헤더 -->
                <div style="background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 50%, #B45309 100%); color: #FFFFFF; padding: 28px; text-align: center;">
                    <div style="font-size: 12px; letter-spacing: 2px; color: #FCD34D; font-weight: bold; text-transform: uppercase;">Weekly Special Briefing</div>
                    <h1 style="margin: 8px 0 0; font-size: 23px;">📊 {week_label} 주간 금융 & 이슈 총결산</h1>
                    <p style="margin: 6px 0 0; font-size: 13px; opacity: 0.9;">7일간 축적 데이터 분석 • 차주 주식/코인 투자전략 & 공식 리서치</p>
                </div>

                <div style="padding: 24px;">

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
                            📄 3. 금주 증권사 공식 리포트 하이라이트 (공인 목표가)
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

                    <!-- 안내 박스 -->
                    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 12px; font-size: 12px; color: #64748B;">
                        📎 <b>첨부 파일 안내:</b> 한 주간의 누적 데이터를 모두 집계한 주간 총결산 엑셀 파일(<code>.xlsx</code>)이 첨부되어 있습니다.<br>
                        📁 <b>구글 드라이브 안내:</b> 월별 폴더(<code>YYYY-MM/</code>)에 안전하게 보관되어 있습니다.
                    </div>

                </div>

                <!-- 푸터 -->
                <div style="background: #F1F5F9; color: #64748B; font-size: 12px; text-align: center; padding: 14px; border-top: 1px solid #E2E8F0;">
                    자동 발송 시스템: py_auto_test • 매주 일요일 아침 07:00 주간 스페셜 발행
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def send_report(self, date_str: str, stock_indices: list, exchange_rates: list, stock_advice: dict, crypto_advice: dict, official_reports: list, news_result: dict, top_research_list: list = None, attachment_path: str = None, performance_data: dict = None, special_disclosures: list = None) -> bool:
        """평일/토요일 데일리 모닝 브리핑 이메일 발송"""
        if not self.is_configured():
            print("\n⚠️ [이메일 발송 건너뜀] NAVER_USER 또는 NAVER_PASSWORD가 설정되지 않았습니다.")
            return False

        try:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = f"☕ [07시 모닝 브리핑] {date_str} 주식·코인(BTC/ETH/SOL)·글로벌 빅테크 & 공식리포트 & DART 특수공시"
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
            )
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            if attachment_path and os.path.exists(attachment_path):
                filename = os.path.basename(attachment_path)
                with open(attachment_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=filename)
                part["Content-Disposition"] = f'attachment; filename="{filename}"'
                msg.attach(part)

            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=15) as server:
                server.login(self.naver_user, self.naver_password)
                server.send_message(msg)

            print(f"📧 ✅ 데일리 모닝 브리핑 이메일 발송 완료! 수신자: {self.receiver_email}")
            return True
        except Exception as e:
            print(f"📧 ❌ 이메일 발송 실패: {e}")
            return False

    def send_weekly_report(self, date_str: str, weekly_data: dict, attachment_path: str = None) -> bool:
        """매주 일요일 주간 총결산 스페셜 이메일 발송"""
        if not self.is_configured():
            print("\n⚠️ [이메일 발송 건너뜀] NAVER_USER 또는 NAVER_PASSWORD가 설정되지 않았습니다.")
            return False

        week_label = weekly_data.get("week_label", "금주 주간 결산")
        try:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = f"📊 [주간 총결산 브리핑] {week_label} 주식·코인 동향 & 차주 투자 전략"
            msg["From"] = f"{self.naver_user}@naver.com"
            msg["To"] = self.receiver_email

            html_content = self.build_weekly_html_body(date_str=date_str, weekly_data=weekly_data)
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            if attachment_path and os.path.exists(attachment_path):
                filename = os.path.basename(attachment_path)
                with open(attachment_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=filename)
                part["Content-Disposition"] = f'attachment; filename="{filename}"'
                msg.attach(part)

            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=15) as server:
                server.login(self.naver_user, self.naver_password)
                server.send_message(msg)

            print(f"📧 🏆 주간 총결산 스페셜 이메일 발송 완료! 수신자: {self.receiver_email}")
            return True
        except Exception as e:
            print(f"📧 ❌ 주간 이메일 발송 실패: {e}")
            return False
