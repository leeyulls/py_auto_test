"""
email_sender.py
네이버 SMTP를 활용하여 7대 분야별 헤드라인 + 주식 추천가 +
비트코인·이더리움·솔라나 3대 코인 매수/매도 추천금액 포함 브리핑 HTML 메일 발송 모듈
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

    def build_html_body(self, date_str: str, stock_indices: list, exchange_rates: list, stock_advice: dict, crypto_advice: dict, news_result: dict, top_research_list: list = None) -> str:
        """스마트폰과 PC에서 가독성 극대화된 모던 카드형 HTML 이메일 템플릿 생성"""
        today_buys = stock_advice.get("today_buy_picks", [])
        long_buys = stock_advice.get("longterm_buy_picks", [])
        sells = stock_advice.get("sell_warning_picks", [])

        # ---------------------------------------------------------
        # 1. 🪙 3대 코인(BTC, ETH, SOL) 카드 섹션
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
        # 2. 주식 매매 추천 카드
        # ---------------------------------------------------------
        today_buy_html = ""
        if today_buys:
            for b in today_buys[:3]:
                today_buy_html += f"""
                <div style="background: #F0FDF4; border-left: 4px solid #16A34A; padding: 12px 14px; margin-bottom: 10px; border-radius: 6px;">
                    <div style="font-weight: bold; color: #15803D; font-size: 15px;">
                        🟢 {b['name']} <span style="font-size: 13px; color: #4B5563;">({b['ticker']})</span> - <span style="color: #111827;">현재가: {b['cur_price']}</span>
                    </div>
                    <div style="margin: 6px 0; background: #DCFCE7; padding: 6px 10px; border-radius: 4px; font-size: 13px; color: #166534;">
                        💰 <b>매수 추천가:</b> <span style="font-weight: bold;">{b['buy_price']}</span> &nbsp;|&nbsp; 
                        🎯 <b>목표 매도가:</b> <span style="font-weight: bold; color: #15803D;">{b['sell_price']}</span> 
                        <span style="font-size: 12px; background: #BBF7D0; padding: 1px 6px; border-radius: 3px; font-weight: bold;">(기대수익 {b['expected_yield']})</span>
                    </div>
                    <div style="color: #374151; font-size: 12px; margin-top: 4px;">💡 <b>판단 근거:</b> {b['reason']}</div>
                </div>
                """
        else:
            today_buy_html = "<p style='color: #6B7280; font-size: 13px;'>현재 극단적 단기 과매도 또는 급등 돌파 종목 없음 (보수적 접근 추천)</p>"

        long_buy_html = ""
        if long_buys:
            for lb in long_buys[:3]:
                long_buy_html += f"""
                <div style="background: #EFF6FF; border-left: 4px solid #2563EB; padding: 12px 14px; margin-bottom: 10px; border-radius: 6px;">
                    <div style="font-weight: bold; color: #1D4ED8; font-size: 15px;">
                        ⭐ {lb['name']} <span style="font-size: 13px; color: #4B5563;">({lb['ticker']})</span> - <span style="color: #111827;">현재가: {lb['cur_price']}</span>
                    </div>
                    <div style="margin: 6px 0; background: #DBEAFE; padding: 6px 10px; border-radius: 4px; font-size: 13px; color: #1E40AF;">
                        💰 <b>분할 매수가:</b> <span style="font-weight: bold;">{lb['buy_price']}</span> &nbsp;|&nbsp; 
                        🎯 <b>장기 목표가:</b> <span style="font-weight: bold; color: #1D4ED8;">{lb['sell_price']}</span> 
                        <span style="font-size: 12px; background: #BFDBFE; padding: 1px 6px; border-radius: 3px; font-weight: bold;">(기대수익 {lb['expected_yield']})</span>
                    </div>
                    <div style="color: #374151; font-size: 12px; margin-top: 4px;">💡 <b>성장 모멘텀:</b> {lb['reason']}</div>
                </div>
                """
        else:
            long_buy_html = "<p style='color: #6B7280; font-size: 13px;'>지수 조정 진행 중, 지지선 확인 후 분할 매수 추천</p>"

        sell_html = ""
        if sells:
            for s in sells[:3]:
                sell_html += f"""
                <div style="background: #FEF2F2; border-left: 4px solid #DC2626; padding: 12px 14px; margin-bottom: 10px; border-radius: 6px;">
                    <div style="font-weight: bold; color: #B91C1C; font-size: 15px;">
                        🔴 {s['name']} <span style="font-size: 13px; color: #4B5563;">({s['ticker']})</span> - <span style="color: #111827;">현재가: {s['cur_price']}</span>
                        <span style="background: #FEE2E2; color: #DC2626; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-left: 6px;">{s['type']}</span>
                    </div>
                    <div style="margin: 6px 0; background: #FEE2E2; padding: 5px 10px; border-radius: 4px; font-size: 12px; color: #991B1B;">
                        🎯 <b>권고 매도가:</b> <span style="font-weight: bold;">{s['sell_price']}</span>
                    </div>
                    <div style="color: #374151; font-size: 12px; margin-top: 4px;">⚠️ <b>주의 사유:</b> {s['reason']}</div>
                </div>
                """
        else:
            sell_html = "<p style='color: #6B7280; font-size: 13px;'>현재 특별한 과열 또는 급락 경고 종목 없음</p>"

        # 3. 시장 지표 요약표
        indices_rows = "".join([f"<tr><td style='padding: 6px 10px; border: 1px solid #E5E7EB; font-weight: bold;'>{i['지수명']}</td><td style='padding: 6px 10px; border: 1px solid #E5E7EB; text-align: right; color: #1D4ED8; font-weight: bold;'>{i['현재지수']}</td><td style='padding: 6px 10px; border: 1px solid #E5E7EB; text-align: right;'>{i['전일대비']}</td></tr>" for i in stock_indices])
        rates_rows = "".join([f"<tr><td style='padding: 6px 10px; border: 1px solid #E5E7EB; font-weight: bold;'>{r['통화명']}</td><td style='padding: 6px 10px; border: 1px solid #E5E7EB; text-align: right; color: #047857; font-weight: bold;'>{r['환율(원)']}원</td><td style='padding: 6px 10px; border: 1px solid #E5E7EB; text-align: right;'>{r['변동/기준']}</td></tr>" for r in exchange_rates[:3]])

        # 4. 🔥 메가 핫토픽
        mega_issue = news_result.get("mega_issue")
        mega_html = ""
        if mega_issue:
            mega_link = mega_issue.get("링크") or mega_issue.get("link", "")
            mega_html = f"""
            <div style="background: #FFF1F2; border: 2px solid #F43F5E; border-radius: 8px; padding: 14px 16px; margin-bottom: 24px;">
                <div style="display: inline-block; background: #E11D48; color: #FFFFFF; font-size: 12px; font-weight: bold; padding: 2px 8px; border-radius: 12px; margin-bottom: 6px;">
                    🔥 언론사 {mega_issue['media_count']}개사 집중 보도 메가 토픽
                </div>
                <div style="font-size: 16px; font-weight: bold; margin-bottom: 6px;">
                    <a href="{mega_link}" style="color: #9F1239; text-decoration: none;">{mega_issue['기사제목']}</a>
                    <span style="font-size: 12px; color: #64748B; font-weight: normal;">({mega_issue['언론사']})</span>
                </div>
                <div style="font-size: 13px; color: #475569; line-height: 1.4;">
                    💡 <b>1줄 요약:</b> {mega_issue['요약내용']}
                </div>
            </div>
            """

        # 5. 📌 7대 분야별 다수 헤드라인
        top_picks = news_result.get("category_top_picks", {})
        category_order = [
            ("🏛️ 정치", "정치"),
            ("🚨 사회 / 사건사고", "사회/사건사고"),
            ("💼 거시경제 / 비즈니스", "거시경제/비즈니스"),
            ("📈 주식 / 기업분석 (증권사 리서치)", "주식/기업분석"),
            ("🌍 세계 / 국제", "세계/국제"),
            ("✨ IT / 과학 / 신상품", "IT/과학/신상품"),
            ("🎬 연예 / 대중문화", "연예/대중문화"),
        ]

        headlines_html = ""
        for icon_title, cat_key in category_order:
            if cat_key == "주식/기업분석" and top_research_list:
                research_items_html = ""
                for rep in top_research_list[:3]:
                    research_items_html += f"""
                    <div style="margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px dashed #E2E8F0;">
                        <div style="font-size: 13px; font-weight: 600;">
                            <a href="{rep['링크']}" style="color: #0F172A; text-decoration: none;">{rep['기사제목']}</a>
                        </div>
                        <div style="font-size: 12px; color: #64748B; margin-top: 2px;">
                            📊 <b>의견/목표가:</b> {rep['요약']}
                        </div>
                    </div>
                    """
                headlines_html += f"""
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; margin-bottom: 16px;">
                    <div style="font-size: 14px; font-weight: bold; color: #2563EB; margin-bottom: 10px; border-bottom: 2px solid #DBEAFE; padding-bottom: 4px;">
                        {icon_title}
                    </div>
                    {research_items_html}
                </div>
                """
            else:
                items = top_picks.get(cat_key, [])
                if items:
                    cat_items_html = ""
                    for it in items[:3]:
                        it_link = it.get("링크") or it.get("link", "")
                        tag = f" <span style='background: #FEE2E2; color: #DC2626; padding: 1px 5px; border-radius: 3px; font-size: 11px;'>{it['상태']}</span>" if "집중" in it['상태'] else ""
                        cat_items_html += f"""
                        <div style="margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px dashed #E2E8F0;">
                            <div style="font-size: 13px; font-weight: 600;">
                                <a href="{it_link}" style="color: #0F172A; text-decoration: none;">{it['기사제목']}</a>{tag}
                                <span style="font-size: 11px; color: #94A3B8; font-weight: normal;">({it['언론사']})</span>
                            </div>
                            <div style="font-size: 12px; color: #64748B; margin-top: 2px;">
                                💡 {it['요약내용']}
                            </div>
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

        html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Malgun Gothic', '맑은 고딕', sans-serif; background-color: #F8FAFC; margin: 0; padding: 20px; line-height: 1.5;">
            <div style="max-width: 660px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #E2E8F0;">
                
                <!-- 헤더 -->
                <div style="background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%); color: #FFFFFF; padding: 24px; text-align: center;">
                    <div style="font-size: 13px; letter-spacing: 1px; opacity: 0.9; text-transform: uppercase;">Daily Morning 07:00 Stock, Crypto & News Briefing</div>
                    <h1 style="margin: 8px 0 0; font-size: 22px;">☕ 아침 7시 모닝 브리핑 ({date_str})</h1>
                    <p style="margin: 6px 0 0; font-size: 13px; opacity: 0.85;">주식 & 3대 코인(BTC/ETH/SOL) 추천금액 & 7대 분야별 헤드라인</p>
                </div>

                <div style="padding: 24px;">

                    <!-- 🔥 메가 핫토픽 -->
                    {mega_html}

                    <!-- 1. 🪙 3대 코인(비트코인, 이더리움, 솔라나) 섹션 -->
                    <div style="margin-bottom: 24px;">
                        <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #A855F7; padding-bottom: 6px; margin-top: 0;">
                            🪙 3대 코인(BTC, ETH, SOL) 시세 & 매매 추천금액
                        </h2>
                        <div style="margin-top: 14px;">
                            {coin_cards_html}
                            {crypto_news_html}
                        </div>
                    </div>

                    <!-- 2. 주식 매매 추천 & 추천 금액 섹션 -->
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

                    <!-- 3. 시장 지표 요약 섹션 -->
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

                    <!-- 4. 7대 분야별 다수 헤드라인 -->
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
                        📎 <b>첨부 파일 안내:</b> 주식/코인 매매 추천표와 전체 기사가 정리된 엑셀 파일(<code>.xlsx</code>)이 첨부되어 있습니다.<br>
                        📊 <b>구글 드라이브 안내:</b> 일자별 데이터가 매일 누적으로 축적되어 기록되고 있습니다.
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

    def send_report(self, date_str: str, stock_indices: list, exchange_rates: list, stock_advice: dict, crypto_advice: dict, news_result: dict, top_research_list: list = None, attachment_path: str = None) -> bool:
        """이메일 조립 및 네이버 SMTP 발송"""
        if not self.is_configured():
            print("\n⚠️ [이메일 발송 건너뜀] NAVER_USER 또는 NAVER_PASSWORD가 설정되지 않았습니다.")
            return False

        try:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = f"☕ [07시 모닝 브리핑] {date_str} 주식·코인(BTC/ETH/SOL) 추천금액 & 주요 뉴스"
            msg["From"] = f"{self.naver_user}@naver.com"
            msg["To"] = self.receiver_email

            html_content = self.build_html_body(
                date_str=date_str,
                stock_indices=stock_indices,
                exchange_rates=exchange_rates,
                stock_advice=stock_advice,
                crypto_advice=crypto_advice,
                news_result=news_result,
                top_research_list=top_research_list
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

            print(f"📧 ✅ 이메일 발송 완료! 수신자: {self.receiver_email}")
            return True
        except Exception as e:
            print(f"📧 ❌ 이메일 발송 실패: {e}")
            return False
