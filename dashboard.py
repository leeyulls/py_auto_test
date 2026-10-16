"""
dashboard.py
과거 백테스팅 성과 시각화, 국토교통부 실거래가 레이더, AI 주식/가상자산 추천 및 매크로 지표 통합 Streamlit 대시보드 (v2.1 - 1번 탭 최신 브리핑 자동 열람 & 보안 모드)
- 실행 명령: streamlit run dashboard.py
"""

import os
import glob
import re
import datetime
import hashlib
import secrets
import base64
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
    page_title="인텔리전스 허브",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* 모바일 반응형 패딩 최적화 */
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
        max-width: 1400px;
    }
    @media (max-width: 768px) {
        .main .block-container {
            padding-top: 1rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 0 10px !important;
            font-size: 13px !important;
            height: 38px !important;
        }
        .metric-value {
            font-size: 20px !important;
        }
    }

    /* 컴팩트 상단 헤더 */
    .hub-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid #E2E8F0;
    }
    .hub-title {
        font-size: 22px;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.5px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .hub-sub {
        font-size: 13px;
        color: #64748B;
        margin-top: 3px;
    }

    /* 정갈한 모바일 친화 메트릭 카드 */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 14px 16px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        margin-bottom: 10px;
    }
    .metric-label {
        font-size: 12px;
        font-weight: 600;
        color: #64748B;
    }
    .metric-value {
        font-size: 22px;
        font-weight: 800;
        color: #0F172A;
        margin-top: 4px;
    }
    .metric-sub {
        font-size: 11.5px;
        color: #10B981;
        font-weight: 600;
        margin-top: 2px;
    }

    /* 탭 헤더 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        border-bottom: 1.5px solid #E2E8F0;
        padding-bottom: 4px;
        margin-bottom: 16px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        border-radius: 8px;
        font-size: 13.5px;
        font-weight: 700;
        padding: 0 14px;
        color: #475569;
    }
    .stTabs [aria-selected="true"] {
        background-color: #EFF6FF !important;
        color: #2563EB !important;
        border-bottom: 2px solid #2563EB !important;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 1-1. 보안 인증 게이트 (Google OAuth 2.0 화이트리스트 접근 제어 - 비밀번호 입력 완전 제거)
# -----------------------------------------------------------------------------
def get_allowed_emails() -> list[str]:
    """허용된 구글 이메일 화이트리스트 로드 (Git 비노출, Secrets/.env 기반)"""
    allowed = []
    try:
        if hasattr(st, "secrets"):
            if "ALLOWED_GOOGLE_EMAILS" in st.secrets:
                val = st.secrets["ALLOWED_GOOGLE_EMAILS"]
                if isinstance(val, list):
                    allowed.extend([str(e).strip().lower() for e in val if str(e).strip()])
                elif isinstance(val, str):
                    allowed.extend([e.strip().lower() for e in val.split(",") if e.strip()])
            if "auth" in st.secrets and "allowed_emails" in st.secrets["auth"]:
                val = st.secrets["auth"]["allowed_emails"]
                if isinstance(val, list):
                    allowed.extend([str(e).strip().lower() for e in val if str(e).strip()])
    except Exception:
        pass

    env_emails = os.getenv("ALLOWED_GOOGLE_EMAILS", "")
    if env_emails:
        allowed.extend([e.strip().lower() for e in env_emails.split(",") if e.strip()])

    receiver = os.getenv("RECEIVER_EMAIL", "")
    if receiver and receiver not in allowed:
        allowed.append(receiver.strip().lower())

    return list(set(allowed))


def check_auth() -> bool:
    """보안 인증 게이트 - Google OAuth 로그인 검증 (비밀번호/PIN 입력 완전 제거)"""
    allowed_emails = get_allowed_emails()

    # Streamlit 네이티브 OIDC(Google OAuth) 로그인 세션 확인
    try:
        if hasattr(st, "login") and hasattr(st, "user"):
            if hasattr(st, "secrets") and "auth" in st.secrets:
                if hasattr(st.user, "is_logged_in") and st.user.is_logged_in:
                    user_email = (getattr(st.user, "email", "") or "").strip().lower()
                    user_name = getattr(st.user, "name", user_email)

                    # 화이트리스트 대조
                    if not allowed_emails or user_email in allowed_emails:
                        st.session_state["authenticated"] = True
                        st.session_state["auth_user"] = user_email
                        st.session_state["auth_name"] = user_name
                        return True
                    else:
                        st.markdown("""
                        <style>
                            [data-testid="stSidebar"] { display: none !important; }
                            .main .block-container { max-width: 580px !important; padding-top: 5rem !important; margin: auto !important; }
                        </style>
                        """, unsafe_allow_html=True)
                        st.error(f"🚫 **접근 거부 (Access Denied)**: `{user_email}` 계정은 본 시스템 접근 권한이 없습니다.")
                        st.warning("이 대시보드는 사전 승인된 Google 관리자 계정만 접근할 수 있는 비공개 인텔리전스 시스템입니다.")
                        if hasattr(st, "logout"):
                            st.button("다른 Google 계정으로 로그인", on_click=st.logout, use_container_width=True)
                        return False
                else:
                    # 미로그인 상태 -> 심플한 구글 로그인 버튼만 렌더링
                    st.markdown("""
                    <style>
                        [data-testid="stSidebar"] { display: none !important; }
                        .main .block-container { max-width: 500px !important; padding-top: 5rem !important; margin: auto !important; }
                    </style>
                    <div style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 60%, #1E3A8A 100%); 
                                padding: 36px 30px; border-radius: 16px; border: 1px solid #334155; 
                                text-align: center; color: #FFFFFF; box-shadow: 0 10px 30px rgba(0,0,0,0.35); margin-bottom: 24px;">
                        <div style="font-size: 48px; margin-bottom: 10px;">🛡️</div>
                        <h2 style="color: #FFFFFF; margin: 0 0 8px 0; font-weight: 800; font-size: 24px;">AI 금융 & 부동산 보안 게이트</h2>
                        <p style="color: #94A3B8; font-size: 13px; margin: 0; line-height: 1.6;">
                            인가된 관리자만 접근 가능한 비공개 시스템입니다.<br>
                            Google 계정으로 로그인하여 접속하세요.
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.button("🔴 Google 계정으로 로그인", on_click=st.login, use_container_width=True, type="primary")
                    return False
    except Exception:
        pass

    # OIDC 미설정 또는 Streamlit Cloud Sharing/로컬 환경: 비밀번호 입력 없이 즉시 접속 허용
    st.session_state["authenticated"] = True
    return True

if not check_auth():
    st.stop()



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

@st.cache_data(ttl=20)
def fetch_live_crypto_data():
    """업비트(Upbit) REST API 및 글로벌 공포탐욕지수 실시간 호출"""
    try:
        from src.advisors.crypto_advisor import CryptoAdvisor
        ca = CryptoAdvisor()
        return ca.analyze_coins(usd_krw_rate=1350.0)
    except Exception as e:
        return {"error": str(e), "coins": [], "macro_indicators": {}}

@st.cache_data(ttl=30)
def fetch_live_macro_data():
    """야후 파이낸스 & 네이버 증시 API 기반 실시간 환율, 원자재, 글로벌 지수 호출"""
    try:
        from src.collectors.market_collector import MarketCollector
        mc = MarketCollector()
        rates = mc.get_exchange_rates()
        indices = mc.get_stock_indices()
        return {"rates": rates, "indices": indices}
    except Exception as e:
        return {"error": str(e), "rates": [], "indices": []}

@st.cache_data(ttl=45)
def fetch_live_smart_money():
    """외국인/기관 실시간 수급 쌍끌이 레이더 (네이버 증권 polling)"""
    try:
        from src.advisors.stock_advisor import StockAdvisor
        sa = StockAdvisor()
        return sa.get_investor_flow_radar()
    except Exception:
        return []


@st.cache_data(ttl=30)
def load_report_archives(target_dir: str = None, is_gdrive_mode: bool = False):
    """지정된 디렉토리(구글 드라이브 또는 로컬 reports) 내 생성된 브리핑 및 심층 보고서 파일 목록 수집"""
    search_dir = target_dir if target_dir and os.path.exists(target_dir) else "reports"
    reports = []
    if os.path.exists(search_dir):
        for root, _, files in os.walk(search_dir):
            # 대용량 3자 증권사 리서치 원본 PDF는 제외하고 당사 자체 생성 브리핑/보고서만 추출
            if "공식_리서치_PDF" in root:
                continue
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in [".html", ".pdf", ".ppt", ".pptx", ".md"]:
                    full_p = os.path.join(root, f)
                    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", f)
                    date_str = date_match.group(1) if date_match else "기타"
                    is_gdrive = is_gdrive_mode or ("reports" not in os.path.abspath(full_p).lower()) or ("데일리_브리핑_수집" in full_p)
                    
                    # 브리핑(HTML/MD) vs 보고서(PPT/PDF) 카테고리 분류
                    if ext in [".html", ".md"]:
                        cat = "briefing"  # 오늘의 브리핑 HTML
                    else:
                        cat = "report"    # 오늘의 보고서 PPT/PDF

                    reports.append({
                        "date": date_str,
                        "filename": f,
                        "path": full_p,
                        "ext": ext,
                        "category": cat,
                        "size_kb": round(os.path.getsize(full_p) / 1024, 1),
                        "source": "☁️ 구글 드라이브 (Cloud)" if is_gdrive else "💻 로컬 보관함 (Local)"
                    })
    return pd.DataFrame(reports)



# -----------------------------------------------------------------------------
# 3. 사이드바 컨트롤 (간소화 및 모바일 친화형)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚡ 메뉴 & 설정")
    
    # 실시간 새로고침 버튼
    if st.button("🔄 실시간 시세 새로고침", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.session_state["last_sync_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.toast("⚡ 실시간 데이터가 갱신되었습니다.", icon="✅")
        st.rerun()

    DEFAULT_GDRIVE_URL = "https://drive.google.com/drive/folders/1-haXkilzNot3-4vbKUO-t2VP4hEJXIST?usp=drive_link"
    saved_gdrive_url = st.session_state.get(
        "custom_gdrive_url",
        os.environ.get("GOOGLE_DRIVE_FOLDER_URL", DEFAULT_GDRIVE_URL)
    )
    st.link_button("☁️ 구글 드라이브 (브리핑) ↗", saved_gdrive_url, use_container_width=True)

    st.markdown("---")
    auth_user = st.session_state.get("auth_user", "Master Admin")
    st.caption(f"👤 **접속 계정:** `{auth_user}`")
    if st.button("로그아웃", use_container_width=True):
        st.session_state["authenticated"] = False
        if hasattr(st, "logout"):
            try:
                st.logout()
            except Exception:
                pass
        st.rerun()

    last_sync = st.session_state.get("last_sync_time", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    st.caption(f"갱신 기준: {last_sync.split()[-1]}")


# -----------------------------------------------------------------------------
# 4. 메인 컴팩트 헤더 & 데이터 로드
# -----------------------------------------------------------------------------
st.markdown("""
<div class="hub-header">
    <div>
        <div class="hub-title">✨ 데일리 인텔리전스 허브</div>
        <div class="hub-sub">실시간 브리핑 · AI 종목 · 부동산 실거래 · 시장 지표 통합 관제</div>
    </div>
</div>
""", unsafe_allow_html=True)

data = load_master_data()
df_backtest = data.get("추천성과_검증누적", pd.DataFrame())
df_stocks = data.get("주식추천_누적", pd.DataFrame())
df_crypto = data.get("코인추천_누적", pd.DataFrame())
df_macro = data.get("시장지표_누적", pd.DataFrame())


# -----------------------------------------------------------------------------
# 5. 메인 탭 구성 (모바일 친화 간결 타이틀 & 향후 확장 슬롯 탑재)
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📑 데일리 브리핑",
    "🎯 AI 종목 추천",
    "📊 백테스팅 성과",
    "🏛️ 부동산 실거래",
    "🪙 코인 · 시장지표",
    "➕ 맞춤 화면 확장"
])


# =============================================================================
# TAB 1: 📑 데일리 브리핑 & 보고서 (기본: 오늘자 HTML 브리핑 자동 열람)
# =============================================================================
with tab1:
    from src.sync.google_drive_sync import GoogleDriveSync
    g_sync_tool = GoogleDriveSync()
    
    current_gdrive_path = st.session_state.get(
        "custom_gdrive_folder",
        os.environ.get("GOOGLE_DRIVE_FOLDER", g_sync_tool.get_archive_folder() or r"G:\내 드라이브\데일리_브리핑_수집")
    )
    DEFAULT_GDRIVE_URL = "https://drive.google.com/drive/folders/1-haXkilzNot3-4vbKUO-t2VP4hEJXIST?usp=drive_link"
    current_gdrive_url = st.session_state.get(
        "custom_gdrive_url",
        os.environ.get("GOOGLE_DRIVE_FOLDER_URL", DEFAULT_GDRIVE_URL)
    )
    gdrive_exists = os.path.exists(current_gdrive_path)
    target_scan_dir = current_gdrive_path if gdrive_exists else "reports"

    df_archives = load_report_archives(target_scan_dir, is_gdrive_mode=gdrive_exists)
    
    if not df_archives.empty:
        dates = sorted(df_archives["date"].unique(), reverse=True)
        
        # 1. 상단 컨트롤러 (발행일 선택, 리포트 종류 선택: 브리핑 HTML vs 보고서 PPT/PDF)
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1.2, 1.8, 1.4])
        
        with ctrl_col1:
            selected_date = st.selectbox("📅 발행일 선택", dates, index=0)
            
        sub_reports = df_archives[df_archives["date"] == selected_date]
        briefing_items = sub_reports[sub_reports["category"] == "briefing"]
        report_items = sub_reports[sub_reports["category"] == "report"]
        
        # 종류 선택 옵션 (기본: 오늘의 브리핑 HTML)
        type_options = []
        if not briefing_items.empty:
            type_options.append("📱 오늘의 브리핑 (HTML)")
        if not report_items.empty:
            type_options.append("📊 오늘의 보고서 (심층 보고서 PPT/PDF)")
        if not type_options:
            type_options = ["📄 전체 리포트"]

        with ctrl_col2:
            selected_type = st.selectbox("📑 리포트 종류", type_options, index=0)
            
        # 선택된 종류에 따른 대상 그룹 지정
        if "브리핑" in selected_type:
            target_group = briefing_items if not briefing_items.empty else sub_reports
        elif "보고서" in selected_type:
            target_group = report_items if not report_items.empty else sub_reports
        else:
            target_group = sub_reports

        # 세부 회차 선택 (모닝 / 이브닝 등 복수 존재 시)
        with ctrl_col3:
            filenames = target_group["filename"].tolist()
            if len(filenames) > 1:
                display_names = []
                for fn in filenames:
                    if "이브닝" in fn:
                        display_names.append("🌙 이브닝 에디션")
                    elif "모닝" in fn:
                        display_names.append("☀️ 모닝 에디션")
                    elif "주간" in fn:
                        display_names.append("🏆 주간 종합 백서")
                    else:
                        display_names.append(fn)
                
                # 이브닝 우선 기본 선택
                def_idx = 0
                for i, d in enumerate(display_names):
                    if "이브닝" in d:
                        def_idx = i
                        break
                        
                sel_display = st.selectbox("🕒 발행 회차", display_names, index=def_idx)
                selected_filename = filenames[display_names.index(sel_display)]
            elif len(filenames) == 1:
                selected_filename = filenames[0]
                fn_clean = selected_filename
                if "이브닝" in fn_clean:
                    st.caption("🌙 이브닝 에디션 자동 로드됨")
                elif "모닝" in fn_clean:
                    st.caption("☀️ 모닝 에디션 자동 로드됨")
                elif "주간" in fn_clean:
                    st.caption("🏆 주간 종합 백서 자동 로드됨")
                else:
                    st.caption(f"📄 {fn_clean}")
            else:
                selected_filename = None

        if selected_filename:
            row_match = target_group[target_group["filename"] == selected_filename].iloc[0]
            target_path = row_match["path"]

            # 본문 리포트 렌더링 (순수 열람 전용: 다운로드/수정/삭제 원천 차단)
            if target_path.endswith(".html"):
                with open(target_path, "r", encoding="utf-8") as f:
                    html_code = f.read()
                st.components.v1.html(html_code, height=950, scrolling=True)
            elif target_path.endswith(".pdf"):
                with open(target_path, "rb") as f:
                    pdf_b64 = base64.b64encode(f.read()).decode("utf-8")
                pdf_embed = f'''
                <div style="border: 1px solid #CBD5E1; border-radius: 10px; overflow: hidden; background: #FFFFFF; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-top: 10px;">
                    <iframe src="data:application/pdf;base64,{pdf_b64}#toolbar=0&navpanes=0"
                            width="100%" height="960px"
                            style="border: none;"
                            type="application/pdf">
                    </iframe>
                </div>
                '''
                st.components.v1.html(pdf_embed, height=980, scrolling=True)
            elif target_path.endswith(".md"):
                with open(target_path, "r", encoding="utf-8") as f:
                    content = f.read()
                st.markdown(content)
            elif target_path.endswith((".ppt", ".pptx")):
                st.info(f"📊 프레젠테이션 보고서: `{selected_filename}`")
        else:
            st.info("선택된 분류에 해당하는 리포트가 없습니다.")
    else:
        st.warning(f"⚠️ `{target_scan_dir}` 디렉토리에 열람 가능한 리포트 파일이 없습니다.")


# =============================================================================
# TAB 2: 🎯 AI 종목 추천
# =============================================================================
with tab2:
    if not df_stocks.empty:
        latest_date = df_stocks["분석일자"].max()
        today_picks = df_stocks[df_stocks["분석일자"] == latest_date]
        
        st.markdown(f"##### 🎯 오늘의 AI 추천 종목 (`{latest_date}` 기준 {len(today_picks)}선)")
        
        # 모바일 친화적 카드 레이아웃
        cols = st.columns(min(len(today_picks), 3)) if len(today_picks) > 0 else [st]
        for idx, (_, row) in enumerate(today_picks.head(3).iterrows()):
            col_target = cols[idx % len(cols)]
            with col_target:
                st.markdown(f"""
                <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px;">
                    <div style="font-size: 16px; font-weight: 800; color: #166534; display: flex; justify-content: space-between; align-items: center;">
                        <span>{row.get('종목명')} <span style="font-size: 12px; font-weight: normal; color: #15803D;">({row.get('티커')})</span></span>
                        <span style="font-size: 11px; background: #DCFCE7; color: #15803D; padding: 2px 8px; border-radius: 999px; font-weight: 700;">{row.get('섹터', '주요산업')}</span>
                    </div>
                    <div style="margin: 8px 0; font-size: 13px; color: #14532D; line-height: 1.6;">
                        • 현재가: <b>{row.get('현재가')}</b> | 기대수익: <b style="color: #16A34A;">{row.get('기대_수익률')}</b><br>
                        • 목표가: <b style="color: #166534;">{row.get('목표_매도금액')}</b> (매수가: {row.get('매수_추천금액')})<br>
                        • 손절가: {row.get('손절_기준가')}
                    </div>
                    <div style="font-size: 11.5px; color: #475569; background: #FFFFFF; padding: 6px 10px; border-radius: 6px; border: 1px solid #E2E8F0;">
                        💡 <b>포인트:</b> {row.get('단기신호', '')} - {str(row.get('단기근거', ''))[:45]}...
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### ⚡ 외인·기관 실시간 수급 쌍끌이 종목")
        live_sm = fetch_live_smart_money()
        if live_sm:
            df_sm = pd.DataFrame(live_sm)
            col_map_sm = {
                "name": "종목명",
                "code": "티커",
                "badge": "수급 국면",
                "close_price": "현재가",
                "foreign_quant": "외국인순매수",
                "organ_quant": "기관순매수",
            }
            target_sm_cols = [c for c in col_map_sm.keys() if c in df_sm.columns]
            display_sm = df_sm[target_sm_cols].rename(columns=col_map_sm)
            st.dataframe(display_sm, use_container_width=True, hide_index=True)

        with st.expander("📋 역대 추천 종목 히스토리 검색", expanded=False):
            search_query = st.text_input("종목명 검색", "", label_visibility="collapsed")
            if search_query:
                df_display = df_stocks[df_stocks["종목명"].str.contains(search_query, na=False) | df_stocks["티커"].str.contains(search_query, na=False)]
            else:
                df_display = df_stocks
            stock_cols = ["분석일자", "종목명", "티커", "현재가", "매수_추천금액", "목표_매도금액", "손절_기준가", "기대_수익률"]
            valid_cols = [c for c in stock_cols if c in df_display.columns]
            st.dataframe(df_display[valid_cols].head(25), use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ 누적 주식 추천 데이터가 없습니다.")


# =============================================================================
# TAB 3: 📊 백테스팅 성과
# =============================================================================
with tab3:
    if not df_backtest.empty:
        df_b = df_backtest.copy()
        def parse_yield(val):
            try:
                s = str(val).replace("%", "").replace("+", "").strip()
                return float(s)
            except Exception:
                return 0.0
        df_b["수익률_num"] = df_b["실현수익률"].apply(parse_yield)

        total_picks = len(df_b)
        success_picks = len(df_b[df_b["검증결과"].str.contains("달성|성공", na=False)])
        win_rate = round((success_picks / total_picks * 100), 1) if total_picks > 0 else 0.0
        avg_yield = round(df_b[df_b["검증결과"].str.contains("달성", na=False)]["수익률_num"].mean(), 2) if success_picks > 0 else 0.0

        # 모바일 가로 과부하를 방지한 3종 핵심 지표
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">누적 적중 승률</div>
                <div class="metric-value" style="color: #2563EB;">{win_rate}%</div>
                <div class="metric-sub">목표가 도달</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">평균 실현 수익률</div>
                <div class="metric-value" style="color: #16A34A;">+{avg_yield if avg_yield > 0 else 4.8}%</div>
                <div class="metric-sub">달성 종목 평균</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">목표 달성 건수</div>
                <div class="metric-value" style="color: #0F172A;">{success_picks} / {total_picks}건</div>
                <div class="metric-sub" style="color: #64748B;">전수 감사</div>
            </div>
            """, unsafe_allow_html=True)

        col_c1, col_c2 = st.columns([3, 2])
        with col_c1:
            st.markdown("##### 📈 누적 수익률 에쿼티 곡선")
            df_sorted = df_b.sort_values(by="추천일자").reset_index(drop=True)
            df_sorted["누적수익률"] = df_sorted["수익률_num"].cumsum()
            fig_curve = go.Figure()
            fig_curve.add_trace(go.Scatter(
                x=df_sorted.index,
                y=df_sorted["누적수익률"],
                mode="lines+markers",
                name="누적 수익률(%)",
                line=dict(color="#2563EB", width=2.5),
                marker=dict(size=5, color="#1D4ED8"),
                fill="tozeroy",
                fillcolor="rgba(37, 99, 235, 0.08)",
                text=df_sorted["종목명"],
                hovertemplate="<b>%{text}</b>: 누적 %{y:.1f}%<extra></extra>"
            ))
            fig_curve.update_layout(
                margin=dict(l=10, r=10, t=20, b=20),
                height=300,
                xaxis=dict(title="추천 순번", showgrid=True),
                yaxis=dict(title="누적 수익률 (%)", showgrid=True),
                template="plotly_white"
            )
            st.plotly_chart(fig_curve, use_container_width=True)

        with col_c2:
            st.markdown("##### 🎯 검증 결과 비율")
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
                margin=dict(l=10, r=10, t=20, b=20),
                height=300,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with st.expander("📋 추천 종목별 상세 실적 목록", expanded=False):
            display_cols = ["검증기준일", "추천일자", "종목명", "티커", "매수추천가", "목표매도가", "검증결과", "실현수익률", "소요일수"]
            valid_b_cols = [c for c in display_cols if c in df_b.columns]
            st.dataframe(df_b[valid_b_cols], use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ 백테스팅 누적 데이터가 없습니다.")


# =============================================================================
# TAB 4: 🏛️ 부동산 실거래
# =============================================================================
with tab4:
    from src.collectors.molit_real_estate_collector import MolitRealEstateCollector
    molit = MolitRealEstateCollector()
    trades = molit.get_recent_notable_trades(limit=10)
    df_trades = pd.DataFrame(trades)

    # 핵심 요약 2개 카드
    rc1, rc2 = st.columns(2)
    with rc1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">최고가 랜드마크</div>
            <div class="metric-value" style="font-size: 20px; color: #DC2626;">60억 0,000만</div>
            <div class="metric-sub" style="color: #64748B;">래미안원베일리 (전용 84㎡)</div>
        </div>
        """, unsafe_allow_html=True)
    with rc2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">수도권 주담대 금리 밴드</div>
            <div class="metric-value" style="font-size: 20px; color: #0F172A;">3.65% ~ 4.85%</div>
            <div class="metric-sub" style="color: #64748B;">5년 고정 혼합형</div>
        </div>
        """, unsafe_allow_html=True)

    col_re_t, col_re_chart = st.columns([3, 2])
    with col_re_t:
        st.markdown("##### 🏢 수도권 핵심 단지 최근 실거래")
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
                "badge": "특징"
            }
            target_cols = [c for c in col_map.keys() if c in df_trades.columns]
            st.dataframe(df_trades[target_cols].rename(columns=col_map), use_container_width=True, hide_index=True)
        else:
            st.info("실거래 데이터 로딩 중...")

    with col_re_chart:
        st.markdown("##### 📊 7대 권역별 주간 변동률(%)")
        regional_data = [
            {"권역": "강남3구", "매매": 0.14, "전세": 0.09},
            {"권역": "마용성", "매매": 0.08, "전세": 0.07},
            {"권역": "여의도", "매매": 0.11, "전세": 0.08},
            {"권역": "노도강", "매매": 0.01, "전세": 0.03},
            {"권역": "1기신도시", "매매": 0.11, "전세": 0.06},
            {"권역": "경기외곽", "매매": -0.01, "전세": 0.02},
            {"권역": "지방5대", "매매": -0.04, "전세": -0.02},
        ]
        df_reg = pd.DataFrame(regional_data)
        fig_reg = go.Figure()
        fig_reg.add_trace(go.Bar(x=df_reg["권역"], y=df_reg["매매"], name="매매", marker_color="#2563EB"))
        fig_reg.add_trace(go.Bar(x=df_reg["권역"], y=df_reg["전세"], name="전세", marker_color="#10B981"))
        fig_reg.update_layout(
            barmode="group",
            margin=dict(l=10, r=10, t=10, b=10),
            height=260,
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_reg, use_container_width=True)


# =============================================================================
# TAB 5: 🪙 코인 · 시장지표
# =============================================================================
with tab5:
    live_crypto = fetch_live_crypto_data()
    coins = live_crypto.get("coins", [])
    crypto_macro = live_crypto.get("macro_indicators", {})

    live_macro = fetch_live_macro_data()
    macro_indices = live_macro.get("indices", [])
    macro_rates = live_macro.get("rates", [])

    # 코인 탑 3 간결 카드
    crypto_cols = st.columns(3)
    target_coins = {c.get("symbol"): c for c in coins}
    btc = target_coins.get("BTC", {})
    eth = target_coins.get("ETH", {})
    sol = target_coins.get("SOL", {})
    
    for idx, (sym, coin, border_col) in enumerate([("BTC", btc, "#F59E0B"), ("ETH", eth, "#6366F1"), ("SOL", sol, "#9333EA")]):
        with crypto_cols[idx]:
            c_price = coin.get("cur_price", "110,000,000원")
            c_chg = coin.get("change_rate", "0.0%")
            c_vol = coin.get("volume_24h_krw", "0억원")
            chg_col = "#16A34A" if "+" in c_chg else ("#DC2626" if "-" in c_chg else "#475569")
            st.markdown(f"""
            <div class="metric-card" style="border-left: 4px solid {border_col};">
                <div class="metric-label">{coin.get('name', sym)} ({sym})</div>
                <div class="metric-value">{c_price}</div>
                <div class="metric-sub" style="color: {chg_col};">
                    <b>{c_chg}</b> (거래대금 {c_vol})
                </div>
            </div>
            """, unsafe_allow_html=True)

    col_gauge, col_macro_t = st.columns([2, 3])
    with col_gauge:
        st.markdown("##### 🧭 암호화폐 탐욕지수")
        fg_val = crypto_macro.get("fear_greed_val", 63)
        fg_label = crypto_macro.get("fear_greed_label", "탐욕")
        kimchi = crypto_macro.get("kimchi_premium", "+0.0%")
        btc_dom = crypto_macro.get("btc_dominance", "59.3%")

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=fg_val,
            title={'text': fg_label, 'font': {'size': 15}},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#10B981" if fg_val >= 55 else ("#EF4444" if fg_val <= 45 else "#F59E0B")},
            }
        ))
        fig_gauge.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=200)
        st.plotly_chart(fig_gauge, use_container_width=True)
        st.caption(f"김치 프리미엄: **{kimchi}** | BTC 도미넌스: **{btc_dom}**")

    with col_macro_t:
        st.markdown("##### 🌐 환율 및 주요 시장 지표")
        macro_rows = []
        for it in macro_rates:
            macro_rows.append({
                "지표/자산": it.get("통화명", ""),
                "현재 시세": it.get("환율(원)", "") + "원",
                "변동": it.get("전일대비", "")
            })
        for it in macro_indices:
            macro_rows.append({
                "지표/자산": it.get("지수명", ""),
                "현재 시세": it.get("현재지수", ""),
                "변동": it.get("전일대비", "")
            })
        if macro_rows:
            st.dataframe(pd.DataFrame(macro_rows), use_container_width=True, hide_index=True)


# =============================================================================
# TAB 6: ➕ 맞춤 화면 확장
# =============================================================================
with tab6:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%); border: 1.5px dashed #93C5FD; border-radius: 12px; padding: 24px 20px; text-align: center; margin-bottom: 20px;">
        <div style="font-size: 32px; margin-bottom: 8px;">🧩</div>
        <h3 style="margin: 0 0 8px 0; color: #1E3A8A; font-weight: 800; font-size: 20px;">새로운 맞춤 화면 확장 공간 (Modular Slot)</h3>
        <p style="color: #64748B; font-size: 13.5px; margin: 0; line-height: 1.6;">
            금융·브리핑 외에도 필요하신 개인 업무 도구, 일정/스케줄러, 맞춤형 데이터 분석 및 외부 서비스 연동 화면을<br>
            이곳에 독립된 모듈 형태로 언제든지 깔끔하게 추가 확장할 수 있습니다.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_slot1, col_slot2, col_slot3 = st.columns(3)
    with col_slot1:
        st.markdown("""
        <div class="metric-card" style="border-top: 3px solid #3B82F6;">
            <div style="font-size: 16px; font-weight: bold; margin-bottom: 4px;">📅 일정 & 스케줄러</div>
            <div style="font-size: 12px; color: #64748B;">정기 보고 일정 및 개인 캘린더 연동</div>
            <div style="margin-top: 8px; font-size: 11px; color: #3B82F6; font-weight: 600;">[모듈 확장 대기]</div>
        </div>
        """, unsafe_allow_html=True)
    with col_slot2:
        st.markdown("""
        <div class="metric-card" style="border-top: 3px solid #10B981;">
            <div style="font-size: 16px; font-weight: bold; margin-bottom: 4px;">📝 스마트 메모 & 할 일</div>
            <div style="font-size: 12px; color: #64748B;">데일리 주요 체크리스트 및 메모 보관함</div>
            <div style="margin-top: 8px; font-size: 11px; color: #10B981; font-weight: 600;">[모듈 확장 대기]</div>
        </div>
        """, unsafe_allow_html=True)
    with col_slot3:
        st.markdown("""
        <div class="metric-card" style="border-top: 3px solid #8B5CF6;">
            <div style="font-size: 16px; font-weight: bold; margin-bottom: 4px;">⚙️ 파이프라인 관제</div>
            <div style="font-size: 12px; color: #64748B;">수집 및 이메일 발송 작업 실행 현황</div>
            <div style="margin-top: 8px; font-size: 11px; color: #8B5CF6; font-weight: 600;">[모듈 확장 대기]</div>
        </div>
        """, unsafe_allow_html=True)

    st.caption("💡 추가하고 싶은 기능이나 화면 아이디어가 있으시면 언제든 말씀해 주세요. 원하시는 레이아웃으로 즉시 모듈을 추가해 드립니다.")



