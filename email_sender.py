"""
email_sender.py
네이버 SMTP를 활용하여 데일리 이슈 & 주식 추천 브리핑 HTML 메일 발송 모듈
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

    def build_html_body(self, date_str: str, stock_indices: list, exchange_rates: list, stock_advice: dict, general_news: list) -> str:
        """스마트폰과 PC에서 깔끔하게 보이는 모던 카드형 HTML 이메일 템플릿 생성"""
        today_buys = stock_advice.get("today_buy_picks", [])
        long_buys = stock_advice.get("longterm_buy_picks", [])
        sells = stock_advice.get("sell_warning_picks", [])

        # 1. 오늘 단기 매수 카드
        today_buy_html = ""
        if today_buys:
            for b in today_buys:
                today_buy_html += f"""
                <div style="background: #F0FDF4; border-left: 4px solid #16A34A; padding: 10px 14px; margin-bottom: 8px; border-radius: 4px;">
                    <div style="font-weight: bold; color: #15803D; font-size: 15px;">🟢 {b['name']} <span style="font-size: 13px; color: #4B5563;">({b['ticker']})</span> - <span style="color: #111827;">{b['price']}</span></div>
                    <div style="color: #374151; font-size: 13px; margin-top: 4px;">💡 <b>판단 근거:</b> {b['reason']}</div>
                </div>
                """
        else:
            today_buy_html = "<p style='color: #6B7280; font-size: 13px;'>현재 극단적 단기 과매도 또는 급등 돌파 종목 없음 (보수적 접근 추천)</p>"

        # 2. 장기 매수 카드
        long_buy_html = ""
        if long_buys:
            for lb in long_buys:
                long_buy_html += f"""
                <div style="background: #EFF6FF; border-left: 4px solid #2563EB; padding: 10px 14px; margin-bottom: 8px; border-radius: 4px;">
                    <div style="font-weight: bold; color: #1D4ED8; font-size: 15px;">⭐ {lb['name']} <span style="font-size: 13px; color: #4B5563;">({lb['ticker']})</span> - <span style="color: #111827;">{lb['price']}</span></div>
                    <div style="color: #374151; font-size: 13px; margin-top: 4px;">💡 <b>성장 모멘텀:</b> {lb['reason']}</div>
                </div>
                """
        else:
            long_buy_html = "<p style='color: #6B7280; font-size: 13px;'>지수 조정 진행 중, 지지선 확인 후 분할 매수 추천</p>"

        # 3. 매도 / 주의 카드
        sell_html = ""
        if sells:
            for s in sells:
                sell_html += f"""
                <div style="background: #FEF2F2; border-left: 4px solid #DC2626; padding: 10px 14px; margin-bottom: 8px; border-radius: 4px;">
                    <div style="font-weight: bold; color: #B91C1C; font-size: 15px;">🔴 {s['name']} <span style="font-size: 13px; color: #4B5563;">({s['ticker']})</span> - <span style="background: #FEE2E2; padding: 2px 6px; border-radius: 4px; font-size: 12px;">{s['type']}</span></div>
                    <div style="color: #374151; font-size: 13px; margin-top: 4px;">⚠️ <b>주의 사유:</b> {s['reason']}</div>
                </div>
                """
        else:
            sell_html = "<p style='color: #6B7280; font-size: 13px;'>현재 특별한 과열 또는 급락 경고 종목 없음</p>"

        # 4. 시장 지표 요약표
        indices_rows = "".join([f"<tr><td style='padding: 6px 10px; border: 1px solid #E5E7EB; font-weight: bold;'>{i['지수명']}</td><td style='padding: 6px 10px; border: 1px solid #E5E7EB; text-align: right; color: #1D4ED8; font-weight: bold;'>{i['현재지수']}</td><td style='padding: 6px 10px; border: 1px solid #E5E7EB; text-align: right;'>{i['전일대비']}</td></tr>" for i in stock_indices])
        rates_rows = "".join([f"<tr><td style='padding: 6px 10px; border: 1px solid #E5E7EB; font-weight: bold;'>{r['통화명']}</td><td style='padding: 6px 10px; border: 1px solid #E5E7EB; text-align: right; color: #047857; font-weight: bold;'>{r['환율(원)']}원</td><td style='padding: 6px 10px; border: 1px solid #E5E7EB; text-align: right;'>{r['변동/기준']}</td></tr>" for r in exchange_rates[:3]])

        # 5. 주요 종합 뉴스 헤드라인 (상위 5건)
        news_items = "".join([f"<li style='margin-bottom: 6px;'><span style='color: #2563EB; font-weight: bold;'>[{n['분야']}]</span> <a href='{n['링크']}' style='text-decoration: none; color: #111827; font-weight: 500;'>{n['기사제목']}</a> <span style='color: #6B7280; font-size: 12px;'>({n['언론사']})</span></li>" for n in general_news[:6]])

        html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Malgun Gothic', '맑은 고딕', sans-serif; background-color: #F8FAFC; margin: 0; padding: 20px; line-height: 1.5;">
            <div style="max-width: 640px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #E2E8F0;">
                
                <!-- 헤더 -->
                <div style="background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%); color: #FFFFFF; padding: 24px; text-align: center;">
                    <div style="font-size: 13px; letter-spacing: 1px; opacity: 0.9; text-transform: uppercase;">Daily Morning Stock & Issue Briefing</div>
                    <h1 style="margin: 8px 0 0; font-size: 22px;">☕ 오늘의 모닝 브리핑 ({date_str})</h1>
                    <p style="margin: 6px 0 0; font-size: 13px; opacity: 0.85;">실시간 주가 분석·매매 추천 및 주요 분야별 종합 이슈</p>
                </div>

                <div style="padding: 24px;">

                    <!-- 1. 핵심 매매 추천 섹션 -->
                    <div style="margin-bottom: 24px;">
                        <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #3B82F6; padding-bottom: 6px; margin-top: 0;">🎯 오늘의 핵심 주식 매매 추천</h2>
                        
                        <div style="margin-top: 14px;">
                            <div style="font-size: 14px; font-weight: bold; color: #16A34A; margin-bottom: 6px;">[오늘 단기 매수 유망 - 낙폭과대 반등 / 모멘텀]</div>
                            {today_buy_html}
                        </div>

                        <div style="margin-top: 14px;">
                            <div style="font-size: 14px; font-weight: bold; color: #2563EB; margin-bottom: 6px;">[장기 모아가면 좋을 주식 - 성장 주도주 분할 매수]</div>
                            {long_buy_html}
                        </div>

                        <div style="margin-top: 14px;">
                            <div style="font-size: 14px; font-weight: bold; color: #DC2626; margin-bottom: 6px;">[주의 / 팔면 좋은 주식 - 과열 차익실현 & 리스크 관리]</div>
                            {sell_html}
                        </div>
                    </div>

                    <!-- 2. 시장 지표 요약 섹션 -->
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

                    <!-- 3. 주요 종합 뉴스 헤드라인 -->
                    <div style="margin-bottom: 24px;">
                        <h2 style="font-size: 17px; color: #1E293B; border-bottom: 2px solid #3B82F6; padding-bottom: 6px;">🌐 오늘 아침 주요 사건·사회·경제 헤드라인</h2>
                        <ul style="padding-left: 20px; font-size: 13px; margin-top: 10px; color: #374151;">
                            {news_items}
                        </ul>
                    </div>

                    <!-- 안내 박스 -->
                    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 12px; font-size: 12px; color: #64748B;">
                        📎 <b>첨부 파일 안내:</b> 전체 종목의 상세 기술지표(RSI, 20일선 이격도, 52주 위치) 및 전체 뉴스 데이터가 정리된 다중 시트 엑셀 파일(<code>.xlsx</code>)이 첨부되어 있습니다.
                    </div>

                </div>

                <!-- 푸터 -->
                <div style="background: #F1F5F9; color: #64748B; font-size: 12px; text-align: center; padding: 14px; border-top: 1px solid #E2E8F0;">
                    자동 발송 시스템: py_auto_test • 매일 아침 09:00 정기 발행
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def send_report(self, date_str: str, stock_indices: list, exchange_rates: list, stock_advice: dict, general_news: list, attachment_path: str = None) -> bool:
        """이메일 조립 및 네이버 SMTP 발송"""
        if not self.is_configured():
            print("\n⚠️ [이메일 발송 건너뜀] NAVER_USER 또는 NAVER_PASSWORD가 설정되지 않았습니다.")
            print("   (.env 파일에 네이버 계정 정보를 입력하시면 매일 아침 자동으로 메일이 발송됩니다.)")
            return False

        try:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = f"☕ [데일리 브리핑] {date_str} 주식 매매 추천 & 종합 이슈 리포트"
            msg["From"] = f"{self.naver_user}@naver.com"
            msg["To"] = self.receiver_email

            # 본문 (HTML)
            html_content = self.build_html_body(
                date_str=date_str,
                stock_indices=stock_indices,
                exchange_rates=exchange_rates,
                stock_advice=stock_advice,
                general_news=general_news
            )
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            # 첨부 파일 (엑셀 파일)
            if attachment_path and os.path.exists(attachment_path):
                filename = os.path.basename(attachment_path)
                with open(attachment_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=filename)
                part["Content-Disposition"] = f'attachment; filename="{filename}"'
                msg.attach(part)

            # 네이버 SMTP SSL 연결 (포트 465)
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=15) as server:
                server.login(self.naver_user, self.naver_password)
                server.send_message(msg)

            print(f"📧 ✅ 이메일 발송 완료! 수신자: {self.receiver_email}")
            return True
        except Exception as e:
            print(f"📧 ❌ 이메일 발송 실패: {e}")
            return False
