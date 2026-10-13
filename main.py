"""
main.py
대한민국 7대 분야별(정치, 사회, 거시경제, 주식, 세계, IT, 연예) 뉴스 수집,
실시간 주가/환율 분석 & 오늘/장기 매매 추천 & 7대 분야 균형 메일링 자동화 메인 시스템
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
    """외부 라이브러리 없이 설정 파일을 읽어 환경 변수로 로드"""
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()


def main():
    # 0. 설정 파일 로드 (email_config.txt 우선, 없으면 .env)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    txt_config = os.path.join(base_dir, "email_config.txt")
    env_config = os.path.join(base_dir, ".env")
    if os.path.exists(txt_config):
        load_env(txt_config)
    elif os.path.exists(env_config):
        load_env(env_config)

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 70)
    print("🚀 [7대 분야별 정밀 브리핑 & 주가 분석 / 매수·매도 추천 시스템]")
    print(f"⏰ 실행 시각: {now_str}")
    print("=" * 70)

    # 1. 히스토리 매니저 초기화
    print("\n[1/7] 🔍 이전 수집 이력 로드 및 중복 필터 준비...")
    history_mgr = HistoryManager()

    # 2. 주식 및 환율 시장 지표 + 증권사 리서치 리포트(우선순위 3) 수집
    print("\n[2/7] 📈 실시간 증시/환율 지표 및 네이버 증권 리서치 리포트 수집 중...")
    market_collector = MarketCollector(history_mgr=history_mgr)
    exchange_rates = market_collector.get_exchange_rates()
    stock_indices = market_collector.get_stock_indices()
    market_news = market_collector.get_stock_news(limit_per_topic=10)

    # 상위 1위 증권사 리서치 리포트 추출
    top_research = next((m for m in market_news if m["구분"] == "증권사 리서치"), None)

    print(f" - 수집된 환율 정보: {len(exchange_rates)}개 통화")
    print(f" - 수집된 증시 지수: {len(stock_indices)}개 지수")
    print(f" - 주식/증권사 리서치/전망 뉴스: {len(market_news)}건")

    # 3. 7대 분야별(정치, 사회, 거시경제, 세계, IT, 연예) 수집 (2>1 알고리즘 적용)
    print("\n[3/7] 🌐 7대 분야별 뉴스 수집 및 언론사 동시집중보도(클러스터링) 분석 중...")
    news_collector = NewsCollector(history_mgr=history_mgr)
    news_result = news_collector.collect_all_categories(limit_per_feed=8)
    general_news = news_result["all_articles"]
    mega_issue = news_result.get("mega_issue")
    category_top_picks = news_result.get("category_top_picks", {})

    print(f" - 수집된 종합 기사: {len(general_news)}건")
    if mega_issue:
        print(f" - 🔥 감지된 메가 핫토픽: [{mega_issue['media_count']}개사 집중] {mega_issue['기사제목']}")

    # 신규 수집 건 이력에 등록
    history_mgr.record_collected([
        {"title": n["기사제목"], "link": n["링크"], "category": n["분야"]} for n in general_news
    ] + [
        {"title": m["기사제목"], "link": m["링크"], "category": m["구분"]} for m in market_news
    ])

    # 4. 주가 기술적 지표(이동평균, RSI, 이격도) 및 뉴스 결합 매매 추천 분석
    print("\n[4/7] 🧠 실시간 주가 데이터 분석 및 오늘/장기 매수·매도 신호 산출 중...")
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

    # 5. 리포트 생성 (엑셀 3개 시트 & 마크다운 문서)
    print("\n[5/7] 📊 7대 분야 엑셀 리포트 및 마크다운 브리핑 생성 중...")
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
        news_result=news_result,
        date_str=today_str,
    )
    print(f" - 엑셀 리포트: {excel_path}")
    print(f" - 마크다운 브리핑: {md_path}")

    # 6. 구글 드라이브 동기화
    print("\n[6/7] ☁️ 구글 드라이브 동기화 점검...")
    drive_sync = GoogleDriveSync()
    drive_sync.sync_file(excel_path)
    drive_sync.sync_file(md_path)

    # 7. 7대 분야 균형 메일링 발송
    print("\n[7/7] 📧 7대 분야 균형 모닝 브리핑 이메일 발송 중...")
    sender = EmailSender()
    sender.send_report(
        date_str=today_str,
        stock_indices=stock_indices,
        exchange_rates=exchange_rates,
        stock_advice=stock_advice,
        news_result=news_result,
        top_research=top_research,
        attachment_path=excel_path,
    )

    # 8. 최종 출력
    print("\n" + "=" * 70)
    print("✨ [오늘 아침 7대 분야별 대표 헤드라인]")
    for cat, item in category_top_picks.items():
        if item:
            print(f" • [{cat}] {item['기사제목']} ({item['언론사']})")
    print("=" * 70)
    print("🎉 7대 분야 정밀 수집 및 이메일 발송이 성공적으로 완료되었습니다!")


if __name__ == "__main__":
    main()
