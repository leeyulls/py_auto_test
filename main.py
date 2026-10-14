"""
main.py
대한민국 7대 분야별 뉴스 수집, 실시간 주가/환율 분석 & 매수·매도 추천금액 산출,
3대 코인(BTC/ETH/SOL) 추천가 산출, 증권사 공식 Top 10 애널리스트 리포트 PDF 수집/동기화,
구글 드라이브 월별(YYYY-MM) 적재 & 일요일 주간 총결산 스페셜 메일링 시스템
"""

import datetime
import os
import sys

# Windows 콘솔 cp949 인코딩 에러 방지
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from history_manager import HistoryManager
from market_collector import MarketCollector
from news_collector import NewsCollector
from stock_advisor import StockAdvisor
from crypto_advisor import CryptoAdvisor
from research_manager import ResearchManager
from weekly_advisor import WeeklyAdvisor
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

    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_sunday = (today.weekday() == 6) or ("--weekly" in sys.argv)
    month_str = today_str[:7]  # '2026-10'

    print("=" * 70)
    print("🚀 [7대 분야 뉴스 & 주식/코인 추천가 & 증권사 공식 Top 10 리포트 자동화]")
    print(f"⏰ 실행 시각: {now_str} (일요일 주간결산 모드: {'ON' if is_sunday else 'OFF'})")
    print(f"📁 구글 드라이브 적재 타겟: 데일리_브리핑_수집/{month_str}/")
    print("=" * 70)

    # 1. 히스토리 매니저 초기화
    print("\n[1/8] 🔍 이전 수집 이력 로드 및 중복 필터 준비...")
    history_mgr = HistoryManager()

    # 2. 증권사 공식 리서치 Top 10 수집 & 5대 신뢰도 지표 평가 & PDF 다운로드
    print("\n[2/8] 🏛️ 증권사 공식 애널리스트 리포트 수집, 5대 지표 신뢰도 점수 산출 및 Top 10 PDF 다운로드...")
    research_mgr = ResearchManager()
    research_res = research_mgr.collect_and_process(date_str=today_str, top_n=10)
    official_reports = research_res.get("top_reports", [])
    print(f" - 선별된 공인 리포트: {len(official_reports)}건")
    for r in official_reports[:3]:
        tp_str = f"{int(r['target_price']):,}원" if r.get('target_price') else "-"
        print(f"   • [{r['broker']}] {r['item_name']}: 목표가 {tp_str} | {r['opinion']} (신뢰도 ⭐ {r['credibility_score']}점)")

    # 3. 주식 및 환율 시장 지표 수집
    print("\n[3/8] 📈 실시간 증시/환율 지표 수집 중...")
    market_collector = MarketCollector(history_mgr=history_mgr)
    exchange_rates = market_collector.get_exchange_rates()
    stock_indices = market_collector.get_stock_indices()
    market_news = market_collector.get_stock_news(limit_per_topic=10)
    top_research_list = [m for m in market_news if m["구분"] == "증권사 리서치"]

    print(f" - 수집된 환율 정보: {len(exchange_rates)}개 통화")
    print(f" - 수집된 증시 지수: {len(stock_indices)}개 지수")

    # 4. 7대 분야별 뉴스 수집 (분야별 최소 3~10건 수집 보장)
    print("\n[4/8] 🌐 7대 분야별 뉴스 수집 및 언론사 동시집중보도(클러스터링) 분석 중...")
    news_collector = NewsCollector(history_mgr=history_mgr)
    news_result = news_collector.collect_all_categories(limit_per_feed=15, top_n_per_category=8)
    general_news = news_result["all_articles"]
    mega_issue = news_result.get("mega_issue")
    category_top_picks = news_result.get("category_top_picks", {})

    print(f" - 수집된 종합 기사: {len(general_news)}건")
    if mega_issue:
        print(f" - 🔥 감지된 메가 핫토픽: [{mega_issue['media_count']}개사 집중] {mega_issue['기사제목']}")

    history_mgr.record_collected([
        {"title": n["기사제목"], "link": n.get("링크") or n.get("link", ""), "category": n["분야"]} for n in general_news
    ] + [
        {"title": m["기사제목"], "link": m["링크"], "category": m["구분"]} for m in market_news
    ])

    # 5. 주가 기술적 지표 및 매수 추천금액 / 목표 매도금액 산출
    print("\n[5/8] 🧠 실시간 주가 분석 및 '매수 추천금액' & '목표 매도금액' 산출 중...")
    advisor = StockAdvisor()
    combined_news_for_analysis = general_news + market_news
    stock_advice = advisor.analyze_universe(combined_news_for_analysis)

    eval_count = len(stock_advice["all_evaluations"])
    today_buys = len(stock_advice["today_buy_picks"])
    long_buys = len(stock_advice["longterm_buy_picks"])
    sells = len(stock_advice["sell_warning_picks"])
    print(f" - 총 분석 종목 수: {eval_count}개 | 단기 매수 유망: {today_buys}개 | 장기 적립: {long_buys}개 | 과열 주의: {sells}개")

    # 6. 가상자산 3대장(BTC, ETH, SOL) 시세 분석 및 추천금액 산출
    print("\n[6/8] 🪙 가상자산 3대장(BTC, ETH, SOL) 실시간 시세 및 매매 추천금액 산출 중...")
    crypto_advisor = CryptoAdvisor()
    crypto_advice = crypto_advisor.analyze_coins()
    coins_list = crypto_advice.get("coins", [])
    for c in coins_list:
        print(f"   • {c['icon']} {c['name']} ({c['symbol']}): 현재가 {c['cur_price']} ➔ 매수가: {c['buy_price']} | 목표가: {c['sell_price']} ({c['expected_yield']})")

    # 7. 리포트 생성 (월별 폴더 적재 YYYY-MM + 누적 마스터 + 주간 결산 엑셀)
    print("\n[7/8] 📊 월별 폴더(YYYY-MM) 엑셀 리포트 및 마스터 파일 업데이트 중...")
    report_gen = ReportGenerator()
    excel_paths = report_gen.generate_excel(
        general_news=general_news,
        market_news=market_news,
        exchange_rates=exchange_rates,
        stock_indices=stock_indices,
        stock_advice=stock_advice,
        crypto_advice=crypto_advice,
        official_reports=official_reports,
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
        crypto_advice=crypto_advice,
        official_reports=official_reports,
        news_result=news_result,
        date_str=today_str,
    )
    print(f" - 📁 당일 엑셀 리포트: {daily_excel_path}")
    print(f" - 📚 일자별 누적 마스터: {master_excel_path}")
    print(f" - 📝 마크다운 브리핑: {md_path}")

    # 8. 구글 드라이브 월별(YYYY-MM) 폴더 및 공식 리서치 PDF 동기화
    print(f"\n[8/8] ☁️ 구글 드라이브 월별({month_str}) 폴더 & 공식 PDF 동기화 진행 중...")
    drive_sync = GoogleDriveSync()

    # 당일 엑셀 및 마크다운 -> YYYY-MM 폴더에 저장
    drive_sync.sync_file(daily_excel_path, is_master=False, subfolder=month_str)
    drive_sync.sync_file(md_path, is_master=False, subfolder=month_str)
    # 누적 마스터 엑셀 -> 최상위 루트 폴더에 저장
    drive_sync.sync_file(master_excel_path, is_master=True)

    # 공식 증권사 리포트 PDF -> YYYY-MM/공식_리서치_PDF 폴더에 저장
    pdf_synced_count = 0
    for rep in official_reports:
        local_pdf = rep.get("pdf_local_path")
        if local_pdf and os.path.exists(local_pdf):
            sync_res = drive_sync.sync_file(local_pdf, is_master=False, subfolder=f"{month_str}/공식_리서치_PDF")
            if sync_res.get("success"):
                pdf_synced_count += 1
    print(f" - 구글 드라이브 공식 PDF 동기화 완료: {pdf_synced_count}건")

    # 9. 메일링 발송 (일요일: 주간 총결산 스페셜 / 평일: 07시 데일리 브리핑)
    sender = EmailSender()
    if is_sunday:
        print("\n🏆 [일요일 주간 총결산 모드] 최근 7일치 데이터 주간 총결산 분석 및 스페셜 메일링 발송 중...")
        weekly_advisor = WeeklyAdvisor(master_file_path=master_excel_path)
        weekly_data = weekly_advisor.analyze_weekly_trend(today_str)
        weekly_excel_info = report_gen.generate_weekly_excel(weekly_data, today_str)
        weekly_excel_path = weekly_excel_info["weekly_path"]

        # 주간 엑셀 구글 드라이브 동기화
        drive_sync.sync_file(weekly_excel_path, is_master=False, subfolder=month_str)

        # 주간 스페셜 이메일 발송
        sender.send_weekly_report(
            date_str=today_str,
            weekly_data=weekly_data,
            attachment_path=weekly_excel_path
        )
    else:
        print("\n📧 매수/매도 추천가 & 3대 코인 & 공식 Top 10 리포트 데일리 모닝 브리핑 이메일 발송 중...")
        sender.send_report(
            date_str=today_str,
            stock_indices=stock_indices,
            exchange_rates=exchange_rates,
            stock_advice=stock_advice,
            crypto_advice=crypto_advice,
            official_reports=official_reports,
            news_result=news_result,
            top_research_list=top_research_list,
            attachment_path=daily_excel_path,
        )

    # 10. 최종 요약 콘솔 출력
    print("\n" + "=" * 70)
    print("✨ [오늘의 증권사 공식 Top 10 애널리스트 리포트 하이라이트]")
    for r in official_reports[:4]:
        tp_str = f"{int(r['target_price']):,}원" if r.get('target_price') else "-"
        print(f" • 📘 [{r['broker']}] {r['item_name']}: {r['title']} | 공인목표가: {tp_str} [{r['opinion']}] (신뢰도 {r['credibility_score']}점)")

    print("\n✨ [오늘의 3대 코인(BTC, ETH, SOL) 매수/목표 매도금액]")
    for c in coins_list:
        print(f" • {c['icon']} {c['name']} ({c['symbol']}) | 현재가: {c['cur_price']} ➔ 매수가: {c['buy_price']} | 목표가: {c['sell_price']} ({c['expected_yield']}) [{c['signal']}]")

    print("\n✨ [오늘의 주식 매수/매도 추천금액 하이라이트]")
    for b in stock_advice["today_buy_picks"][:3]:
        print(f" • 🟢 {b['name']} ({b['ticker']}) | 현재가: {b['cur_price']} ➔ 매수가: {b['buy_price']} | 목표가: {b['sell_price']} ({b['expected_yield']})")
    for s in stock_advice["sell_warning_picks"][:2]:
        print(f" • 🔴 {s['name']} ({s['ticker']}) | 현재가: {s['cur_price']} ➔ 권고 매도가: {s['sell_price']} [{s['type']}]")

    print("=" * 70)
    print("🎉 구글 드라이브 월별 적재, 공식 리포트 PDF 저장, 주간 결산 연동이 완료되었습니다!")


if __name__ == "__main__":
    main()
