"""
main.py
대한민국 7대 분야별(정치, 사회, 거시경제, 주식, 세계, IT, 연예) 뉴스 수집,
실시간 주가/환율 분석 & 매수·매도 추천금액 산출 & 일자별 구글 드라이브 누적 & 7대 분야 균형 메일링 시스템
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
    # 0. 설정 파일 로드
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
    print("🚀 [7대 분야별 정밀 브리핑 & 매수·매도 추천금액 & 일자별 누적 저장 시스템]")
    print(f"⏰ 실행 시각: {now_str}")
    print("=" * 70)

    # 1. 히스토리 매니저 초기화
    print("\n[1/7] 🔍 이전 수집 이력 로드 및 중복 필터 준비...")
    history_mgr = HistoryManager()

    # 2. 주식 및 환율 시장 지표 + 증권사 리서치 리포트 수집
    print("\n[2/7] 📈 실시간 증시/환율 지표 및 네이버 증권 리서치 리포트 수집 중...")
    market_collector = MarketCollector(history_mgr=history_mgr)
    exchange_rates = market_collector.get_exchange_rates()
    stock_indices = market_collector.get_stock_indices()
    market_news = market_collector.get_stock_news(limit_per_topic=10)

    # 증권사 리서치 리포트 목록 추출
    top_research_list = [m for m in market_news if m["구분"] == "증권사 리서치"]

    print(f" - 수집된 환율 정보: {len(exchange_rates)}개 통화")
    print(f" - 수집된 증시 지수: {len(stock_indices)}개 지수")
    print(f" - 증권사 리서치 리포트: {len(top_research_list)}건")

    # 3. 7대 분야별 뉴스 수집 (분야별 최소 3~10건 수집 보장)
    print("\n[3/7] 🌐 7대 분야별 뉴스 수집 및 언론사 동시집중보도(클러스터링) 분석 중...")
    news_collector = NewsCollector(history_mgr=history_mgr)
    news_result = news_collector.collect_all_categories(limit_per_feed=15, top_n_per_category=8)
    general_news = news_result["all_articles"]
    mega_issue = news_result.get("mega_issue")
    category_top_picks = news_result.get("category_top_picks", {})

    print(f" - 수집된 종합 기사: {len(general_news)}건")
    if mega_issue:
        print(f" - 🔥 감지된 메가 핫토픽: [{mega_issue['media_count']}개사 집중] {mega_issue['기사제목']}")

    # 신규 수집 건 이력에 등록
    history_mgr.record_collected([
        {"title": n["기사제목"], "link": n.get("링크") or n.get("link", ""), "category": n["분야"]} for n in general_news
    ] + [
        {"title": m["기사제목"], "link": m["링크"], "category": m["구분"]} for m in market_news
    ])

    # 4. 주가 기술적 지표 및 매수 추천금액 / 목표 매도금액 산출
    print("\n[4/7] 🧠 실시간 주가 분석 및 '매수 추천금액' & '목표 매도금액' 산출 중...")
    advisor = StockAdvisor()
    combined_news_for_analysis = general_news + market_news
    stock_advice = advisor.analyze_universe(combined_news_for_analysis)

    eval_count = len(stock_advice["all_evaluations"])
    today_buys = len(stock_advice["today_buy_picks"])
    long_buys = len(stock_advice["longterm_buy_picks"])
    sells = len(stock_advice["sell_warning_picks"])
    print(f" - 총 분석 종목 수: {eval_count}개")
    print(f" - 오늘 단기 매수 유망 (추천금액 포함): {today_buys}개")
    print(f" - 장기 적립/매수 추천 (추천금액 포함): {long_buys}개")
    print(f" - 매도/과열 주의 종목 (권고 매도가 포함): {sells}개")

    # 5. 리포트 생성 (당일 엑셀 + 일자별 누적 마스터 엑셀 + 마크다운)
    print("\n[5/7] 📊 당일 엑셀 리포트 및 '일자별 누적 마스터 파일' 업데이트 중...")
    report_gen = ReportGenerator()
    excel_paths = report_gen.generate_excel(
        general_news=general_news,
        market_news=market_news,
        exchange_rates=exchange_rates,
        stock_indices=stock_indices,
        stock_advice=stock_advice,
        date_str=today_str,
    )
    daily_excel_path = excel_paths["daily_path"]
    master_excel_path = excel_paths["master_path"]

    md_path = report_gen.generate_markdown(
        general_news=general_news,
        market_news=market_news,
        exchange_rates=exchange_rates,
        stock_indices=stock_indices,
        stock_advice=stock_advice,
        news_result=news_result,
        date_str=today_str,
    )
    print(f" - 당일 엑셀 리포트: {daily_excel_path}")
    print(f" - 📚 일자별 누적 마스터: {master_excel_path}")
    print(f" - 마크다운 브리핑: {md_path}")

    # 6. 구글 드라이브 동기화 (당일 리포트 + 누적 마스터 동시 보관)
    print("\n[6/7] ☁️ 구글 드라이브 동기화 점검 (당일 파일 + 누적 마스터)...")
    drive_sync = GoogleDriveSync()
    drive_sync.sync_file(daily_excel_path, is_master=False)
    drive_sync.sync_file(master_excel_path, is_master=True)
    drive_sync.sync_file(md_path, is_master=False)

    # 7. 7대 분야 다수 헤드라인 & 매수/매도 추천금액 포함 이메일 발송
    print("\n[7/7] 📧 매수/매도 추천금액 & 다수 헤드라인 모닝 브리핑 이메일 발송 중...")
    sender = EmailSender()
    sender.send_report(
        date_str=today_str,
        stock_indices=stock_indices,
        exchange_rates=exchange_rates,
        stock_advice=stock_advice,
        news_result=news_result,
        top_research_list=top_research_list,
        attachment_path=daily_excel_path,
    )

    # 8. 최종 요약 콘솔 출력
    print("\n" + "=" * 70)
    print("✨ [오늘의 주식 매수/매도 추천금액 하이라이트]")
    for b in stock_advice["today_buy_picks"][:3]:
        print(f" • 🟢 {b['name']} ({b['ticker']}) | 현재가: {b['cur_price']} ➔ 매수가: {b['buy_price']} | 목표가: {b['sell_price']} ({b['expected_yield']})")
    for s in stock_advice["sell_warning_picks"][:2]:
        print(f" • 🔴 {s['name']} ({s['ticker']}) | 현재가: {s['cur_price']} ➔ 권고 매도가: {s['sell_price']} [{s['type']}]")

    print("\n✨ [오늘 아침 7대 분야별 주요 뉴스 수집 현황]")
    for cat, items in category_top_picks.items():
        print(f" • [{cat}]: {len(items)}건 선별 완료")
    print("=" * 70)
    print("🎉 일자별 누적 저장, 추천금액 산출, 다수 헤드라인 메일링이 완료되었습니다!")


if __name__ == "__main__":
    main()
