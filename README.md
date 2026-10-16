# 🚀 py_auto_test: 데일리 종합 이슈 & 주식·환율 자동 수집 시스템

대한민국의 주요 분야별 최신 이슈와 주식/환율 특화 정보를 자동으로 수집하고, 중복 필터링을 거쳐 구글 드라이브(Google Drive) 및 엑셀/마크다운 리포트로 자동 정리하는 파이썬 크롤링 프로젝트입니다.

---

## 📌 주요 핵심 기능

### 1. 분야별 종합 이슈 수집 (한국 기준)
- **수집 분야**: 주요 사건사고, 사회, 경제/비즈니스, 세계/국제, 연예/문화, IT/과학/신상품
- **스마트 중복 제거 & 연결 이슈(후속 보도) 판별**:
  - `data/history.json`을 기반으로 전일/이전 수집 결과와 대조
  - 단순 중복 기사(동일 링크, 동일 제목, 85% 이상 유사도)는 **자동 제거**
  - 핵심 키워드가 이어지는 **후속 보도·연결되는 내용**은 `[연결 이슈 (후속 보도)]` 태그를 달아 **수집 허용**

### 2. 주식 / 환율 특화 정보 수집 (별도 시트 분리)
- **실시간 시장 지표**: 코스피(KOSPI), 코스닥(KOSDAQ) 실시간 지수 및 등락률
- **주요 환율**: 미국 달러(USD), 일본 100엔(JPY), 유로(EUR), 중국 위안(CNY)
- **기업 발표 및 주가 변화 예측 뉴스**:
  - 삼성전자, SK하이닉스, 현대차, 카카오 등 주요 기업 실적 발표 및 신제품 모멘텀
  - 증권사 목표주가 상향/하향, 시장 전망 및 변동성 영향 분석 태깅 (`🟢 상승 전망`, `🔴 변동성 주의`, `🔵 신규 발표`)

### 3. 매일 아침 9시 이메일 자동 발송 (네이버 SMTP)
- **카드형 모바일 최적화 HTML 브리핑 발송**:
  - ☕ 오늘의 핵심 주식 매매 추천 (오늘 사면 좋을 주식, 장기 추천주, 팔면 좋은 주식)
  - 📈 실시간 코스피·코스닥 및 환율 요약표
  - 🌐 오늘 아침 주요 사건·사회·경제 헤드라인
  - 📎 당일 생성된 다중 시트 엑셀 리포트(`.xlsx`) 자동 첨부
- **윈도우 작업 스케줄러 (`DailyStockBriefing`)**:
  - 매일 아침 09:00 정각에 PC에서 자동 실행되도록 등록 완료 (`Next Run: 오전 9:00`)

### 4. 구글 드라이브 & 다중 시트 엑셀 자동 정리
- **다중 시트 엑셀 (`.xlsx`)**:
  - 시트 1: `종합이슈_브리핑` (분야, 상태, 기사제목, 요약내용, 언론사, 링크)
  - 시트 2: `주식_환율_경제동향` (증시 지수, 환율 요약, 기업별 주가영향 뉴스)
- **마크다운 브리핑 (`.md`)**: 가독성 높은 일일 요약 보고서 자동 생성
- **구글 드라이브 동기화 모드**:
  1. **Google Drive for Desktop (로컬 연동)**: PC에 구글 드라이브가 설치되어 있으면 `G:\내 드라이브\데일리_브리핑_수집`에 자동 복사
  2. **Google Apps Script Web App**: [GOOGLE_DRIVE_APPS_SCRIPT.js](file:///d:/py_auto_test/GOOGLE_DRIVE_APPS_SCRIPT.js) 웹앱 URL을 환경 변수 `GOOGLE_APPS_SCRIPT_URL`에 등록 시 클라우드 자동 업로드

---

## 📂 프로젝트 폴더 구조

```text
d:\py_auto_test\
├── main.py                          # 메인 실행 엔트리포인트 (CLI/스케줄러/GitHub Actions 호환)
├── run_daily.bat                    # 윈도우 스케줄러 자동 실행 배치 파일
├── requirements.txt                 # 프로젝트 의존 패키지 목록
├── GOOGLE_DRIVE_APPS_SCRIPT.js      # 구글 드라이브 클라우드 연동 웹앱 스크립트
├── data/                            # 수집 이력 캐시 보관소
│   └── history.json                 # 최근 14일간 수집 이력 캐시 (중복 방지)
├── reports/                         # 날짜별 생성된 리포트 아카이브
│   ├── 일자별_누적_데일리_이슈_및_주식_브리핑_마스터.xlsx
│   └── YYYY-MM/                     # 월별 엑셀, 마크다운, PDF 및 리서치 보관 폴더
└── src/                             # 핵심 파이프라인 모듈 패키지
    ├── config/                      # 설정 및 종목 유니버스
    │   ├── crawler_config.py        # RSS 피드, API, 프로젝트 공통 경로 상수
    │   └── stock_universe.py        # 주요 상장 종목 유니버스 및 키워드 매칭
    ├── collectors/                  # 데이터 수집 모듈
    │   ├── news_collector.py        # 7대 분야별 최신 뉴스 수집 및 클러스터링
    │   ├── market_collector.py      # 코스피/코스닥 지표, 환율, 증시 뉴스 수집
    │   ├── disclosure_collector.py  # DART/KIND 특수 공시(자사주, 수주 등) 수집
    │   └── research_manager.py      # 증권사 공식 애널리스트 리포트 Top 10 수집
    ├── advisors/                    # 투자 분석 및 추천 모듈
    │   ├── stock_analyzer.py        # 종목별 기술적 지표(이동평균, RSI) 분석
    │   ├── stock_advisor.py         # 국내/미국 주식 매수가·목표가·손절가 산출
    │   ├── crypto_advisor.py        # BTC/ETH/SOL 3대 가상자산 분석 및 추천가
    │   ├── real_estate_advisor.py   # 권역별 부동산 시장 동향 및 주담대 금리
    │   ├── performance_tracker.py   # 과거 추천 종목 사후 검증(백테스팅) 및 승률 집계
    │   └── weekly_advisor.py        # 일요일 주간 결산 총괄 분석
    ├── intelligence/                # AI 심층 인텔리전스 엔진
    │   ├── gemini_intelligence_client.py  # Google Gemini LLM API 연동 클라이언트
    │   ├── story_dive_engine.py     # 핫이슈 배경·영향·전망 심층 분석 (Story Dive)
    │   └── intelligence_dossier_engine.py # 프리미엄 인텔리전스 도시에 리포트 빌더
    ├── reporting/                   # 보고서 편찬 및 발송 모듈
    │   ├── report_generator.py      # 다중 시트 엑셀(.xlsx) 및 마크다운(.md) 리포트 생성기
    │   ├── pdf_report_generator.py  # Headless 초고해상도 A4 정식 PDF 보고서 편찬기
    │   └── email_sender.py          # 카드형 모바일 반응형 HTML 브리핑 메일 발송기
    ├── sync/                        # 클라우드 동기화 모듈
    │   └── google_drive_sync.py     # Google Drive for Desktop 및 Apps Script 자동 동기화
    └── utils/                       # 공통 유틸리티
        └── history_manager.py       # 기사 중복 필터링 및 후속 보도 연결 판별기
```

---

## 🏃 실행 방법

터미널에서 아래 명령어를 실행하면 즉시 전체 수집 및 리포트가 생성됩니다:

```powershell
python d:\py_auto_test\main.py
```
