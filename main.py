"""
main.py
대한민국 종합 이슈(사건·사회·경제·세계·연예·신상품) 및 주식/환율 특화 수집 & 구글 드라이브 동기화 메인 실행기
"""

import datetime
import os
import sys

from history_manager import HistoryManager
from market_collector import MarketCollector
from news_collector import NewsCollector
from report_generator import ReportGenerator
from google_drive_sync import GoogleDriveSync


def main():
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 65)
    print(f"🚀 [데일리 이슈 & 금융/환율 자동 수집 시스템]")
    print(f"⏰ 실행 시각: {now_str}")
    print("=" * 65)

    # 1. 히스토리 매니저 초기화 (중복 및 연결 이슈 필터링)
    print("\n[1/5] 🔍 이전 수집 이력 로드 및 중복 필터 준비...")
    history_mgr = HistoryManager()

    # 2. 주식 및 환율 시장 지표 수집
    print("\n[2/5] 📈 실시간 증시/환율 지표 및 기업 발표/전망 뉴스 수집 중...")
    market_collector = MarketCollector(history_mgr=history_mgr)
    exchange_rates = market_collector.get_exchange_rates()
    stock_indices = market_collector.get_stock_indices()
    market_news = market_collector.get_stock_news(limit_per_topic=10)

    print(f" - 수집된 환율 정보: {len(exchange_rates)}개 통화")
    print(f" - 수집된 증시 지수: {len(stock_indices)}개 지수")
    print(f" - 주식/기업발표/전망 뉴스: {len(market_news)}건")

    # 3. 분야별 종합 이슈(사회, 경제, 세계, 연예, 신상품/IT) 수집
    print("\n[3/5] 🌐 분야별(사건사고, 사회, 경제, 세계, 연예, IT/신상품) 이슈 수집 중...")
    news_collector = NewsCollector(history_mgr=history_mgr)
    general_news = news_collector.collect_all_categories(limit_per_feed=8)
    print(f" - 수집된 종합 이슈 기사: {len(general_news)}건")

    # 신규 수집 건 이력에 등록
    history_mgr.record_collected([
        {"title": n["기사제목"], "link": n["링크"], "category": n["분야"]} for n in general_news
    ] + [
        {"title": m["기사제목"], "link": m["링크"], "category": m["구분"]} for m in market_news
    ])

    # 4. 리포트 생성 (엑셀 다중 시트 & 마크다운 문서)
    print("\n[4/5] 📊 구글 드라이브/스프레드시트용 엑셀 및 마크다운 리포트 생성 중...")
    report_gen = ReportGenerator()
    excel_path = report_gen.generate_excel(
        general_news=general_news,
        market_news=market_news,
        exchange_rates=exchange_rates,
        stock_indices=stock_indices,
        date_str=today_str,
    )
    md_path = report_gen.generate_markdown(
        general_news=general_news,
        market_news=market_news,
        exchange_rates=exchange_rates,
        stock_indices=stock_indices,
        date_str=today_str,
    )
    print(f" - 엑셀 리포트: {excel_path}")
    print(f" - 마크다운 브리핑: {md_path}")

    # 5. 구글 드라이브 동기화 시도
    print("\n[5/5] ☁️ 구글 드라이브 동기화 점검...")
    drive_sync = GoogleDriveSync()
    drive_sync.sync_file(excel_path)
    drive_sync.sync_file(md_path)

    # 6. 최종 요약 출력
    print("\n" + "=" * 65)
    print("✨ [오늘의 주요 금융/환율 요약]")
    for idx in stock_indices:
        print(f" • {idx['지수명']}: {idx['현재지수']} ({idx['전일대비']})")
    for fx in exchange_rates[:2]:
        print(f" • {fx['통화명']}: {fx['환율(원)']}원")

    print("\n✨ [주요 기업 발표 / 주가 전망 헤드라인 (상위 3건)]")
    for m in market_news[:3]:
        print(f" • [{m['관련기업/기관']}] {m['기사제목']} ({m['영향/전망']})")

    print("\n✨ [분야별 주요 이슈 헤드라인 (상위 3건)]")
    for g in general_news[:3]:
        tag = f" [{g['상태']}]" if g['상태'] != "신규 이슈" else ""
        print(f" • [{g['분야']}{tag}] {g['기사제목']} ({g['언론사']})")
    print("=" * 65)
    print("🎉 크롤링 및 리포트 생성이 성공적으로 완료되었습니다!")


if __name__ == "__main__":
    main()
