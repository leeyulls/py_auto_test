"""
main.py
대한민국 종합 이슈(사건·사회·경제·세계·연예·신상품) 및 실시간 주가/환율 분석 & 오늘/장기 매매 추천 & 이메일 발송 메인 시스템
"""

import datetime
import os
import sys

from history_manager import HistoryManager
from market_collector import MarketCollector
from news_collector import NewsCollector
from stock_advisor import StockAdvisor
from report_generator import ReportGenerator
from google_drive_sync import GoogleDriveSync
from email_sender import EmailSender


def load_env(env_path):
    """외부 라이브러리 없이 .env 파일을 읽어 환경 변수로 로드"""
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()


def main():
    # 0. .env 환경 변수 로드
    base_dir = os.path.dirname(os.path.abspath(__file__))
    load_env(os.path.join(base_dir, ".env"))

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 70)
    print("🚀 [데일리 이슈 & 실시간 주가 분석 / 매수·매도 추천 & 메일 발송 시스템]")
    print(f"⏰ 실행 시각: {now_str}")
    print("=" * 70)

    # 1. 히스토리 매니저 초기화 (중복 및 연결 이슈 필터링)
    print("\n[1/7] 🔍 이전 수집 이력 로드 및 중복 필터 준비...")
    history_mgr = HistoryManager()

    # 2. 주식 및 환율 시장 지표 수집
    print("\n[2/7] 📈 실시간 증시/환율 지표 및 기업 발표/전망 뉴스 수집 중...")
    market_collector = MarketCollector(history_mgr=history_mgr)
    exchange_rates = market_collector.get_exchange_rates()
    stock_indices = market_collector.get_stock_indices()
    market_news = market_collector.get_stock_news(limit_per_topic=10)

    print(f" - 수집된 환율 정보: {len(exchange_rates)}개 통화")
    print(f" - 수집된 증시 지수: {len(stock_indices)}개 지수")
    print(f" - 주식/기업발표/전망 뉴스: {len(market_news)}건")

    # 3. 분야별 종합 이슈(사회, 경제, 세계, 연예, 신상품/IT) 수집
    print("\n[3/7] 🌐 분야별(사건사고, 사회, 경제, 세계, 연예, IT/신상품) 이슈 수집 중...")
    news_collector = NewsCollector(history_mgr=history_mgr)
    general_news = news_collector.collect_all_categories(limit_per_feed=8)
    print(f" - 수집된 종합 이슈 기사: {len(general_news)}건")

    # 신규 수집 건 이력에 등록
    history_mgr.record_collected([
        {"title": n["기사제목"], "link": n["링크"], "category": n["분야"]} for n in general_news
    ] + [
        {"title": m["기사제목"], "link": m["링크"], "category": m["구분"]} for m in market_news
    ])

    # 4. 주가 기술적 지표(이동평균, RSI, 이격도) 및 뉴스 결합 매매 추천 분석
    print("\n[4/7] 🧠 과거/현재 주가 데이터 분석 및 오늘/장기 매수·매도 신호 산출 중...")
    advisor = StockAdvisor()
    combined_news_for_analysis = general_news + market_news
    stock_advice = advisor.analyze_universe(combined_news_for_analysis)

    eval_count = len(stock_advice["all_evaluations"])
    today_buys = len(stock_advice["today_buy_picks"])
    long_buys = len(stock_advice["longterm_buy_picks"])
    sells = len(stock_advice["sell_warning_picks"])
    print(f" - 총 분석 종목 수: {eval_count}개")
    print(f" - 오늘 단기 매수 유망: {today_buys}개")
    print(f" - 장기 적립/매수 추천: {long_buys}개")
    print(f" - 매도/과열 주의 종목: {sells}개")

    # 5. 리포트 생성 (엑셀 다중 시트 & 마크다운 문서)
    print("\n[5/7] 📊 구글 드라이브/스프레드시트용 엑셀 및 마크다운 리포트 생성 중...")
    report_gen = ReportGenerator()
    excel_path = report_gen.generate_excel(
        general_news=general_news,
        market_news=market_news,
        exchange_rates=exchange_rates,
        stock_indices=stock_indices,
        stock_advice=stock_advice,
        date_str=today_str,
    )
    md_path = report_gen.generate_markdown(
        general_news=general_news,
        market_news=market_news,
        exchange_rates=exchange_rates,
        stock_indices=stock_indices,
        stock_advice=stock_advice,
        date_str=today_str,
    )
    print(f" - 엑셀 리포트 (3개 시트): {excel_path}")
    print(f" - 마크다운 브리핑: {md_path}")

    # 6. 구글 드라이브 동기화 시도
    print("\n[6/7] ☁️ 구글 드라이브 동기화 점검...")
    drive_sync = GoogleDriveSync()
    drive_sync.sync_file(excel_path)
    drive_sync.sync_file(md_path)

    # 7. 네이버 이메일 발송
    print("\n[7/7] 📧 모닝 브리핑 이메일 발송 점검...")
    sender = EmailSender()
    sender.send_report(
        date_str=today_str,
        stock_indices=stock_indices,
        exchange_rates=exchange_rates,
        stock_advice=stock_advice,
        general_news=general_news,
        attachment_path=excel_path,
    )

    # 8. 최종 하이라이트 출력
    print("\n" + "=" * 70)
    print("🎯 [오늘의 핵심 주식 투자 추천 정보]")

    print("\n🟢 [오늘 사면 좋을 주식 (단기 반등/모멘텀)]")
    if stock_advice["today_buy_picks"]:
        for p in stock_advice["today_buy_picks"]:
            print(f" • {p['name']} ({p['ticker']}) - {p['price']} | 근거: {p['reason']}")
    else:
        print(" • 단기 과열 구간으로 당일 무리한 단기 진입보다 관망 추천")

    print("\n⭐ [장기적으로 사면 좋을 주식 (성장 가치 분할 매수)]")
    if stock_advice["longterm_buy_picks"]:
        for p in stock_advice["longterm_buy_picks"]:
            print(f" • {p['name']} ({p['ticker']}) - {p['price']} | 근거: {p['reason']}")
    else:
        print(" • 고점 대비 조정 진행 중, 지지선 확인 후 분할 매수 추천")

    print("\n🔴 [주의 / 팔면 좋은 주식 (단기 과열 차익실현 or 리스크 관리)]")
    if stock_advice["sell_warning_picks"]:
        for p in stock_advice["sell_warning_picks"]:
            print(f" • {p['name']} ({p['ticker']}) [{p['type']}] | 사유: {p['reason']}")
    else:
        print(" • 특별한 과열 또는 급락 경고 종목 없음")

    print("\n" + "=" * 70)
    print("🎉 크롤링, 주가 분석, 리포트 생성 및 전송 점검이 완료되었습니다!")


if __name__ == "__main__":
    main()
