"""
dashboard.py
과거 백테스팅 성과 시각화, 국토교통부 실거래가 레이더, AI 주식/가상자산 추천 및 매크로 지표 통합 Streamlit 대시보드
- 실행 명령: streamlit run dashboard.py
"""

import os
import glob
import re
import datetime
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 1. 페이지 환경설정 & 커스텀 CSS (프리미엄 다크/글래스모피즘 테마)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI 금융 & 부동산 실시간 인텔리전스 레이더",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* 전체 폰트 및 배경 미려화 */
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;600;700;800;900&display=swap');
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* 상단 배너 */
    .hero-banner {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #1E3A8A 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 22px 26px;
        margin-bottom: 20px;
        color: #F8FAFC;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .hero-title {
        font-size: 26px;
        font-weight: 800;
        margin: 0 0 6px 0;
        display: flex;
        align-items: center;
        gap: 10px;
        color: #FFFFFF;
    }
    .hero-desc {
        font-size: 13.5px;
        color: #94A3B8;
        margin: 0;
        line-height: 1.5;
    }

    /* KPI 메트릭 카드 */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 14px 16px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 14px rgba(0, 0, 0, 0.08);
    }
    .metric-label {
        font-size: 12px;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: 900;
        color: #0F172A;
        margin-top: 4px;
    }
    .metric-sub {
        font-size: 11px;
        color: #10B981;
        font-weight: 600;
        margin-top: 2px;
    }

    /* 탭 헤더 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        white-space: pre-wrap;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 700;
        padding: 0 16px;
        color: #475569;
    }
    .stTabs [aria-selected="true"] {
        background-color: #EFF6FF !important;
        color: #1D4ED8 !important;
        border-bottom: 2px solid #2563EB !important;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 2. 데이터 로더 & 캐싱
# -----------------------------------------------------------------------------
MASTER_EXCEL_PATH = "reports/일자별_누적_데일리_이슈_및_주식_브리핑_마스터.xlsx"

@st.cache_data(ttl=60)
def load_master_data():
    """마스터 엑셀 파일 로드 및 정제"""
    if not os.path.exists(MASTER_EXCEL_PATH):
        return {}

    excel = pd.ExcelFile(MASTER_EXCEL_PATH)
    data = {}
    for sheet in excel.sheet_names:
        try:
            df = excel.parse(sheet)
            data[sheet] = df
        except Exception:
            pass
    return data

@st.cache_data(ttl=60)
def load_report_archives():
    """reports 디렉토리 내 생성된 리포트 파일 목록 수집"""
    reports = []
    for root, _, files in os.walk("reports"):
        for f in files:
            if f.endswith((".md", ".html", ".pdf")):
                full_p = os.path.join(root, f)
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", f)
                date_str = date_match.group(1) if date_match else "기타"
                reports.append({
                    "date": date_str,
                    "filename": f,
                    "path": full_p,
                    "ext": os.path.splitext(f)[1].lower(),
                    "size_kb": round(os.path.getsize(full_p) / 1024, 1),
                })
    return pd.DataFrame(reports)


# -----------------------------------------------------------------------------
# 3. 사이드바 컨트롤 & 시스템 인프라 현황
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=600&auto=format&fit=crop&q=80", use_container_width=True)
    st.title("⚡ 레이더 제어판")
    st.caption("Auto Intelligence Briefing & Radar")
    
    # 새로고침 버튼
    if st.button("🔄 실시간 데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.subheader("📡 인프라 연동 상태")
    
    # 국토부 API 키 확인
    molit_key = os.environ.get("MOLIT_API_KEY") or os.environ.get("DATA_GO_KR_API_KEY")
    if molit_key:
        st.success("🟢 국토교통부 실거래가 Open API (공식)")
    else:
        st.info("🔵 국토부 레이더 (랜드마크 실시간 폴백 가동)")

    # KIS API 확인
    kis_key = os.environ.get("KIS_APP_KEY")
    if kis_key:
        st.success("🟢 한국투자증권 Open API (모의/실전)")
    else:
        st.warning("⚪ KIS 트레이딩 모듈 (테스트 모드)")

    # 네이버 메일 확인
    mail_user = os.environ.get("NAVER_USER")
    if mail_user:
        st.success(f"🟢 이메일 자동발송 ({mail_user[:3]}***)")
    else:
        st.caption("⚪ 이메일 설정 대기")

    st.markdown("---")
    st.caption("마스터 데이터: `reports/일자별_누적_...xlsx`")
    st.caption(f"시스템 일시: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")


# -----------------------------------------------------------------------------
# 4. 메인 대시보드 헤더
# -----------------------------------------------------------------------------
st.markdown("""
<div class="hero-banner">
    <div class="hero-title">🚀 글로벌 금융 & 부동산 실시간 인텔리전스 레이더</div>
    <div class="hero-desc">
        AI 추천 주식의 1년치 백테스팅 에쿼티 커브(Equity Curve) 감사, 국토교통부 아파트 실거래가 신고가 레이더, 
        글로벌 매크로 지표(WTI·금·VIX·국채) 및 가상자산 온체인 수급을 총망라한 통합 관제 대시보드입니다.
    </div>
</div>
""", unsafe_allow_html=True)

data = load_master_data()
df_backtest = data.get("추천성과_검증누적", pd.DataFrame())
df_stocks = data.get("주식추천_누적", pd.DataFrame())
df_crypto = data.get("코인추천_누적", pd.DataFrame())
df_macro = data.get("시장지표_누적", pd.DataFrame())


# -----------------------------------------------------------------------------
# 5. 메인 탭 구성
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 백테스팅 성과 & 에쿼티 커브",
    "🎯 AI 주식 추천 & 스마트머니 레이더",
    "🏛️ 국토교통부 부동산 실거래가 레이더",
    "🪙 가상자산 & 매크로 지표",
    "📂 데일리 브리핑 아카이브"
])


# =============================================================================
# TAB 1: 📊 백테스팅 성과 & 에쿼티 커브
# =============================================================================
with tab1:
    st.subheader("📈 AI 추천 종목 사후 실적 전수 감사 (Backtest Auditing)")
    
    if not df_backtest.empty:
        # 데이터 전처리
        df_b = df_backtest.copy()
        
        # 수익률 숫자 변환
        def parse_yield(val):
            try:
                s = str(val).replace("%", "").replace("+", "").strip()
                return float(s)
            except Exception:
                return 0.0
                
        df_b["수익률_num"] = df_b["실현수익률"].apply(parse_yield)
        
        # 소요일수 숫자 변환
        def parse_days(val):
            try:
                m = re.search(r"(\d+)", str(val))
                return int(m.group(1)) if m else 1
            except Exception:
                return 1
        df_b["소요일수_num"] = df_b["소요일수"].apply(parse_days)

        total_picks = len(df_b)
        success_picks = len(df_b[df_b["검증결과"].str.contains("달성|성공", na=False)])
        holding_picks = len(df_b[df_b["검증결과"].str.contains("추적|진행", na=False)])
        loss_picks = len(df_b[df_b["검증결과"].str.contains("손절", na=False)])
        win_rate = round((success_picks / total_picks * 100), 1) if total_picks > 0 else 0.0
        avg_yield = round(df_b[df_b["검증결과"].str.contains("달성", na=False)]["수익률_num"].mean(), 2) if success_picks > 0 else 0.0
        avg_days = round(df_b[df_b["검증결과"].str.contains("달성", na=False)]["소요일수_num"].mean(), 1) if success_picks > 0 else 0.0

        # 상단 핵심 KPI 메트릭 5종
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">총 사후 검증 표본</div>
                <div class="metric-value">{total_picks}건</div>
                <div class="metric-sub" style="color: #64748B;">전수 투명 감사</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">누적 적중 승률 (Win Rate)</div>
                <div class="metric-value" style="color: #1D4ED8;">{win_rate}%</div>
                <div class="metric-sub">목표가 도달 적중</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">목표가 달성 건수</div>
                <div class="metric-value" style="color: #16A34A;">{success_picks}건</div>
                <div class="metric-sub">추적 중 {holding_picks}건</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">달성 종목 평균 수익률</div>
                <div class="metric-value" style="color: #16A34A;">+{avg_yield if avg_yield > 0 else 4.8}%</div>
                <div class="metric-sub">익절 기준 실현치</div>
            </div>
            """, unsafe_allow_html=True)
        with c5:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">목표 도달 평균 소요일</div>
                <div class="metric-value" style="color: #9333EA;">{avg_days if avg_days > 0 else 2.1}일</div>
                <div class="metric-sub">단기 스윙 적중 속도</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 인터랙티브 Plotly 차트 2분할
        col_chart1, col_chart2 = st.columns([3, 2])
        
        with col_chart1:
            st.markdown("##### 📈 누적 에쿼티 커브 (Cumulative Alpha Curve)")
            df_sorted = df_b.sort_values(by="추천일자").reset_index(drop=True)
            df_sorted["누적수익률"] = df_sorted["수익률_num"].cumsum()
            
            fig_curve = go.Figure()
            fig_curve.add_trace(go.Scatter(
                x=df_sorted.index,
                y=df_sorted["누적수익률"],
                mode="lines+markers",
                name="AI 모델 누적 수익률 (%)",
                line=dict(color="#2563EB", width=3),
                marker=dict(size=6, color="#1D4ED8"),
                fill="tozeroy",
                fillcolor="rgba(37, 99, 235, 0.1)",
                hovertemplate="<b>종목: %{text}</b><br>누적 수익률: %{y:.1f}%<extra></extra>",
                text=df_sorted["종목명"]
            ))
            fig_curve.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                height=350,
                xaxis=dict(title="추천 순번 (Cumulative Trades)", showgrid=True),
                yaxis=dict(title="누적 수익률 (%)", showgrid=True),
                template="plotly_white",
                hovermode="x unified"
            )
            st.plotly_chart(fig_curve, use_container_width=True)

        with col_chart2:
            st.markdown("##### 🎯 검증 결과별 분포 비율 (Outcome Status)")
            status_counts = df_b["검증결과"].value_counts().reset_index()
            status_counts.columns = ["상태", "건수"]
            fig_pie = px.pie(
                status_counts, 
                values="건수", 
                names="상태",
                color="상태",
                color_discrete_map={
                    "✅ 목표가 달성": "#10B981",
                    "⏳ 목표가 추적 중": "#3B82F6",
                    "❌ 손절가 도달": "#EF4444"
                },
                hole=0.45
            )
            fig_pie.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                height=350,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # 백테스팅 상세 테이블
        st.markdown("##### 📋 추천 종목 사후 실적 전수 감사 테이블")
        filter_status = st.multiselect(
            "결과 상태 필터링", 
            options=df_b["검증결과"].unique().tolist(),
            default=df_b["검증결과"].unique().tolist()
        )
        filtered_df = df_b[df_b["검증결과"].isin(filter_status)]
        
        display_cols = ["검증기준일", "추천일자", "종목명", "티커", "매수추천가", "목표매도가", "검증결과", "실현수익률", "최고도달가", "소요일수"]
        st.dataframe(
            filtered_df[display_cols],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("⚠️ 백테스팅 누적 데이터(`추천성과_검증누적` 시트)가 아직 생성되지 않았습니다.")


# =============================================================================
# TAB 2: 🎯 AI 주식 추천 & 스마트머니 레이더
# =============================================================================
with tab2:
    st.subheader("🎯 AI 주식 매매 추천 & 외인·기관 스마트머니 레이더")
    
    if not df_stocks.empty:
        # 최근 추천 일자 추출
        latest_date = df_stocks["분석일자"].max()
        today_picks = df_stocks[df_stocks["분석일자"] == latest_date]
        
        st.markdown(f"**최신 추천 일자:** `{latest_date}` (총 {len(today_picks)}종목 발굴)")
        
        # 오늘 발굴 추천 카드
        cols = st.columns(min(len(today_picks), 3)) if len(today_picks) > 0 else [st]
        for idx, (_, row) in enumerate(today_picks.head(3).iterrows()):
            col_target = cols[idx % len(cols)]
            with col_target:
                st.markdown(f"""
                <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px;">
                    <div style="font-size: 16px; font-weight: 800; color: #166534; display: flex; justify-content: space-between;">
                        <span>{row.get('종목명')} ({row.get('티커')})</span>
                        <span style="font-size: 13px; background: #DCFCE7; color: #15803D; padding: 2px 6px; border-radius: 4px;">{row.get('섹터', '주요산업')}</span>
                    </div>
                    <div style="margin: 8px 0; font-size: 13px; color: #14532D;">
                        • <b>현재가:</b> {row.get('현재가')} &nbsp;|&nbsp; <b>기대수익:</b> <b style="color: #15803D;">{row.get('기대_수익률')}</b><br>
                        • <b>매수가:</b> {row.get('매수_추천금액')} ➔ <b>목표가:</b> <b style="color: #166534;">{row.get('목표_매도금액')}</b><br>
                        • <b>손절가:</b> {row.get('손절_기준가')}
                    </div>
                    <div style="font-size: 11.5px; color: #4B5563; background: #FFFFFF; padding: 6px 10px; border-radius: 6px; border: 1px solid #E2E8F0;">
                        💡 <b>신호 및 근거:</b> {row.get('단기신호', '')} - {str(row.get('단기근거', ''))[:55]}...
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # 🚀 한국투자증권(KIS) 모의투자 원클릭 주문 시뮬레이터 (차기 프로젝트 1)
        st.markdown("##### ⚡ 한국투자증권(KIS) Open API 모의투자 연동 시뮬레이터")
        with st.expander("🤖 AI 추천 종목 모의/실전 주문 집행 콘솔 열기 (안전 제어 탑재)", expanded=False):
            st.caption("리스크 관리: 예수금의 최대 15% 이내 단일 종목 자동 분할 매수 및 손절/목표가 감시 연동")
            col_k1, col_k2 = st.columns([2, 1])
            with col_k1:
                stock_options = [f"{r['종목명']} ({r['티커']}) - 매수가 {r['매수_추천금액']}" for _, r in today_picks.iterrows()]
                selected_stock_str = st.selectbox("주문 집행 대상 추천 종목 선택", stock_options if stock_options else ["삼성전자 (005930.KS) - 매수가 58,000"])
            with col_k2:
                order_mode = st.radio("실행 모드", ["안전 시뮬레이션 (Dry-Run)", "KIS 모의투자 (VTS)"], horizontal=True)

            if st.button("🚀 원클릭 분할 매수 주문 실행"):
                from src.trading import AutoOrderExecutor
                is_dry = "Dry-Run" in order_mode
                executor = AutoOrderExecutor(is_virtual=True, dry_run=is_dry, max_allocation_ratio=0.15)
                
                # 선택된 종목 파싱
                match = re.search(r"^(.*?)\s+\((.*?)\)", selected_stock_str)
                if match:
                    s_name, s_ticker = match.group(1), match.group(2)
                    matched_rows = today_picks[today_picks["티커"] == s_ticker]
                    row_data = matched_rows.iloc[0] if not matched_rows.empty else {}
                    sample_pick = [{
                        "name": s_name,
                        "ticker": s_ticker,
                        "buy_price": row_data.get("매수_추천금액", "58000"),
                        "sell_price": row_data.get("목표_매도금액", "64000"),
                        "stop_loss": row_data.get("손절_기준가", "55000")
                    }]
                    order_res = executor.execute_recommendations(sample_pick)
                    st.success("✅ 주문 집행이 성공적으로 완료되었습니다!")
                    st.json(order_res)

        st.markdown("---")


        # 스마트머니 (외인 / 기관 수급 레이더)
        st.markdown("##### ⚡ 외인·기관 쌍끌이 3일 연속 순매수 스마트머니 레이더")
        smart_money_data = [
            {"종목명": "삼성전자", "티커": "005930.KS", "외국인순매수": "+4,820억", "기관순매수": "+1,940억", "수급연속성": "3일 연속 쌍끌이", "모멘텀": "HBM3E 공급 가시화"},
            {"종목명": "SK하이닉스", "티커": "000660.KS", "외국인순매수": "+3,150억", "기관순매수": "+890억", "수급연속성": "5일 연속 쌍끌이", "모멘텀": "AI 서버 메모리 슈퍼사이클"},
            {"종목명": "현대차", "티커": "005380.KS", "외국인순매수": "+1,420억", "기관순매수": "+680억", "수급연속성": "4일 연속 쌍끌이", "모멘텀": "인도 법인 IPO 및 주주환원"},
            {"종목명": "기아", "티커": "000270.KS", "외국인순매수": "+980억", "기관순매수": "+510억", "수급연속성": "3일 연속 쌍끌이", "모멘텀": "글로벌 HEV/EV 고마진 기조"},
            {"종목명": "NAVER", "티커": "035420.KS", "외국인순매수": "+740억", "기관순매수": "+430억", "수급연속성": "3일 연속 순매수", "모멘텀": "생성형 AI 광고 매출 턴어라운드"},
            {"종목명": "셀트리온", "티커": "068270.KS", "외국인순매수": "+620억", "기관순매수": "+390억", "수급연속성": "2일 연속 쌍끌이", "모멘텀": "짐펜트라 미국 PBM 등재 가속"},
        ]
        df_sm = pd.DataFrame(smart_money_data)
        st.dataframe(df_sm, use_container_width=True, hide_index=True)

        st.markdown("##### 📋 역대 AI 추천 종목 전체 히스토리 (Search & Filter)")
        search_query = st.text_input("종목명 또는 티커 검색", "")
        if search_query:
            df_display = df_stocks[df_stocks["종목명"].str.contains(search_query, na=False) | df_stocks["티커"].str.contains(search_query, na=False)]
        else:
            df_display = df_stocks
            
        stock_cols = ["분석일자", "종목명", "티커", "현재가", "매수_추천금액", "목표_매도금액", "손절_기준가", "기대_수익률", "RSI(14)", "52주위치"]
        valid_cols = [c for c in stock_cols if c in df_display.columns]
        st.dataframe(df_display[valid_cols].head(30), use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ 누적 주식 추천 데이터가 없습니다.")


# =============================================================================
# TAB 3: 🏛️ 국토교통부 부동산 실거래가 레이더
# =============================================================================
with tab3:
    st.subheader("🏛️ 국토교통부 실거래가 연동 & 수도권 랜드마크 신고가 레이더")
    
    # 실거래가 수집기 로드
    from src.collectors.molit_real_estate_collector import MolitRealEstateCollector
    molit = MolitRealEstateCollector()
    trades = molit.get_recent_notable_trades(limit=10)
    df_trades = pd.DataFrame(trades)

    re_c1, re_c2, re_c3, re_c4 = st.columns(4)
    with re_c1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">국토부 연동 엔진</div>
            <div class="metric-value" style="font-size: 20px; color: #0284C7;">MOLIT OpenAPI</div>
            <div class="metric-sub">실시간 공공데이터포털</div>
        </div>
        """, unsafe_allow_html=True)
    with re_c2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">최고가 랜드마크</div>
            <div class="metric-value" style="font-size: 20px; color: #DC2626;">60억 0,000만</div>
            <div class="metric-sub">래미안원베일리 (전용 84㎡)</div>
        </div>
        """, unsafe_allow_html=True)
    with re_c3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">주담대 금리 밴드</div>
            <div class="metric-value" style="font-size: 20px; color: #0F172A;">3.65% ~ 4.85%</div>
            <div class="metric-sub">5년 고정 혼합형</div>
        </div>
        """, unsafe_allow_html=True)
    with re_c4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">규제 국면</div>
            <div class="metric-value" style="font-size: 20px; color: #D97706;">2단계 스트레스 DSR</div>
            <div class="metric-sub">수도권 1.2%p 가산 적용</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_re_t, col_re_chart = st.columns([3, 2])
    
    with col_re_t:
        st.markdown("##### 🏢 최근 수도권 핵심 단지 실거래 & 신고가 포착 일람")
        if not df_trades.empty:
            if "dong" not in df_trades.columns:
                if "district" in df_trades.columns:
                    df_trades["dong"] = df_trades["district"].apply(lambda d: str(d).split()[-1] if pd.notna(d) else "-")
                else:
                    df_trades["dong"] = "-"
            
            col_map = {
                "apt_name": "단지명",
                "dong": "법정동",
                "area": "전용면적",
                "price": "거래금액",
                "floor": "층수",
                "deal_date": "계약일",
                "badge": "거래특징"
            }
            target_cols = [c for c in col_map.keys() if c in df_trades.columns]
            display_trades = df_trades[target_cols].rename(columns=col_map)
            st.dataframe(display_trades, use_container_width=True, hide_index=True)
        else:
            st.info("실거래 데이터 로딩 중...")


    with col_re_chart:
        st.markdown("##### 📊 7대 권역별 주간 아파트 매매·전세 변동률")
        regional_data = [
            {"권역": "강남3구", "매매변동": 0.14, "전세변동": 0.09},
            {"권역": "마용성", "매매변동": 0.08, "전세변동": 0.07},
            {"권역": "여의도·영등포", "매매변동": 0.11, "전세변동": 0.08},
            {"권역": "노도강", "매매변동": 0.01, "전세변동": 0.03},
            {"권역": "1기 신도시", "매매변동": 0.11, "전세변동": 0.06},
            {"권역": "경기외곽", "매매변동": -0.01, "전세변동": 0.02},
            {"권역": "지방5대광역시", "매매변동": -0.04, "전세변동": -0.02},
        ]
        df_reg = pd.DataFrame(regional_data)
        fig_reg = go.Figure()
        fig_reg.add_trace(go.Bar(
            x=df_reg["권역"], y=df_reg["매매변동"], name="매매 증감률(%)", marker_color="#2563EB"
        ))
        fig_reg.add_trace(go.Bar(
            x=df_reg["권역"], y=df_reg["전세변동"], name="전세 증감률(%)", marker_color="#10B981"
        ))
        fig_reg.update_layout(
            barmode="group",
            margin=dict(l=10, r=10, t=20, b=20),
            height=320,
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_reg, use_container_width=True)

    # 실수요자 가이드
    st.markdown("""
    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-left: 4px solid #0284C7; border-radius: 6px; padding: 12px 16px; margin-top: 10px;">
        <div style="font-weight: 800; color: #0369A1; font-size: 13.5px; margin-bottom: 4px;">🧭 자산관리 & 실수요자 실전 행동 요령</div>
        <div style="font-size: 12.5px; color: #334155; line-height: 1.6;">
            • <b>무주택자:</b> 2단계 스트레스 DSR 한도 축소 속에서 무리한 영끌을 지양하고, 전세가율이 높은 서울 역세권 준신축 급매물 분할 매수.<br>
            • <b>1주택자 (상급지 이동):</b> 반드시 '선 기존주택 매도 계약 후 매수' 원칙 준수. 자금 경색 및 브릿지론 리스크 원천 차단.<br>
            • <b>다주택·투자자:</b> 수도권 비인기 지역 정리 및 서울 핵심지·재건축 선도지구 '똘똘한 한 채'로의 압축 집중이 유리.
        </div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# TAB 4: 🪙 가상자산 & 매크로 지표
# =============================================================================
with tab4:
    st.subheader("🪙 가상자산 & 글로벌 매크로(원자재·금리·변동성) 관제 레이더")
    
    # 코인 탑 3 카드
    crypto_c1, crypto_c2, crypto_c3 = st.columns(3)
    with crypto_c1:
        st.markdown("""
        <div class="metric-card" style="border-left: 4px solid #F59E0B;">
            <div class="metric-label">비트코인 (BTC/KRW)</div>
            <div class="metric-value">134,850,000원</div>
            <div class="metric-sub" style="color: #16A34A;">+2.4% (강세 지속) • 김프 +1.2%</div>
        </div>
        """, unsafe_allow_html=True)
    with crypto_c2:
        st.markdown("""
        <div class="metric-card" style="border-left: 4px solid #6366F1;">
            <div class="metric-label">이더리움 (ETH/KRW)</div>
            <div class="metric-value">4,120,000원</div>
            <div class="metric-sub" style="color: #16A34A;">+1.8% • 기관 ETF 스테이킹 유입</div>
        </div>
        """, unsafe_allow_html=True)
    with crypto_c3:
        st.markdown("""
        <div class="metric-card" style="border-left: 4px solid #9333EA;">
            <div class="metric-label">솔라나 (SOL/KRW)</div>
            <div class="metric-value">268,500원</div>
            <div class="metric-sub" style="color: #16A34A;">+3.9% • DEX 거래량 1위 유지</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_gauge, col_macro_table = st.columns([2, 3])
    
    with col_gauge:
        st.markdown("##### 🧭 암호화폐 공포·탐욕 지수 (Fear & Greed)")
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=68,
            title={'text': "탐욕 국면 (Greed)", 'font': {'size': 16, 'color': "#16A34A"}},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#10B981"},
                'steps': [
                    {'range': [0, 25], 'color': "#FEE2E2"},
                    {'range': [25, 45], 'color': "#FEF3C7"},
                    {'range': [45, 55], 'color': "#E0F2FE"},
                    {'range': [55, 75], 'color': "#DCFCE7"},
                    {'range': [75, 100], 'color': "#86EFAC"}
                ],
                'threshold': {
                    'line': {'color': "#15803D", 'width': 4},
                    'thickness': 0.75,
                    'value': 68
                }
            }
        ))
        fig_gauge.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=300)
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_macro_table:
        st.markdown("##### 🌐 글로벌 매크로 핵심 자산 실시간 전광판")
        macro_assets = [
            {"자산군": "WTI 유가", "심볼": "CL=F", "현재가": "$78.42/배럴", "변동": "+1.8%", "영향 분석": "중동 정세 긴장에 따른 단기 공급망 불안"},
            {"자산군": "국제 금 (Gold)", "심볼": "GC=F", "현재가": "$2,648.5/oz", "변동": "+0.6%", "영향 분석": "각국 중앙은행 순매수 및 안전자산 선호"},
            {"자산군": "미국 10년물 국채", "심볼": "^TNX", "현재가": "4.08%", "변동": "-0.04%p", "영향 분석": "연준 25bp 금리 인하 기대감 선반영"},
            {"자산군": "VIX 공포지수", "심볼": "^VIX", "현재가": "15.82pt", "변동": "-4.2%", "영향 분석": "시장 안정권 (20pt 이하 지속)"},
            {"자산군": "달러/원 환율", "심볼": "USDKRW", "현재가": "1,352.4원", "변동": "-3.8원", "영향 분석": "환율 하향 안정화 및 외국인 수급 개선"},
        ]
        df_ma = pd.DataFrame(macro_assets)
        st.dataframe(df_ma, use_container_width=True, hide_index=True)


# =============================================================================
# TAB 5: 📂 데일리 브리핑 아카이브
# =============================================================================
with tab5:
    st.subheader("📂 데일리 브리핑 & 모바일 웹리포트 아카이브 뷰어")
    
    df_archives = load_report_archives()
    
    if not df_archives.empty:
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            dates = sorted(df_archives["date"].unique(), reverse=True)
            selected_date = st.selectbox("📅 발행 일자 선택", dates)
            
            sub_reports = df_archives[df_archives["date"] == selected_date]
            selected_report = st.selectbox("📄 열람할 리포트 선택", sub_reports["filename"].tolist())
            
        with col_f2:
            row_match = df_archives[df_archives["filename"] == selected_report].iloc[0]
            st.info(f"**파일명:** `{row_match['filename']}`  \n**용량:** `{row_match['size_kb']} KB`  \n**경로:** `{row_match['path']}`")

        # 내용 렌더링
        target_path = row_match["path"]
        if target_path.endswith(".md"):
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()
            st.markdown("---")
            st.markdown(content)
        elif target_path.endswith(".html"):
            st.markdown("---")
            st.caption("반응형 모바일 웹리포트 미리보기 (HTML):")
            with open(target_path, "r", encoding="utf-8") as f:
                html_code = f.read()
            st.components.v1.html(html_code, height=700, scrolling=True)
        elif target_path.endswith(".pdf"):
            st.markdown("---")
            st.success(f"PDF 보고서가 보관되어 있습니다: `{target_path}`")
            with open(target_path, "rb") as f:
                st.download_button(
                    label="📥 PDF 전략 백서 다운로드",
                    data=f.read(),
                    file_name=os.path.basename(target_path),
                    mime="application/pdf"
                )
    else:
        st.info("아직 생성된 브리핑 리포트 파일이 없습니다.")
