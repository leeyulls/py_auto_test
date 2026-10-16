import os

# 프로젝트 기준 디렉토리 설정
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
MASTER_EXCEL_FILE = os.path.join(REPORTS_DIR, "일자별_누적_데일리_이슈_및_주식_브리핑_마스터.xlsx")

# 7대 핵심 카테고리별 RSS 피드 (구글 뉴스 탑 + 연합뉴스 전문 피드)
NEWS_FEEDS = {
    "정치": [
        "https://news.google.com/rss/headlines/section/topic/POLITICS?hl=ko&gl=KR&ceid=KR:ko",
        "https://www.yna.co.kr/rss/politics.xml",
    ],
    "사회/사건사고": [
        "https://news.google.com/rss/headlines/section/topic/NATION?hl=ko&gl=KR&ceid=KR:ko",
        "https://www.yna.co.kr/rss/society.xml",
    ],
    "거시경제/비즈니스": [
        "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko",
        "https://www.yna.co.kr/rss/economy.xml",
        "https://www.mk.co.kr/rss/30100041/",
    ],
    "세계/국제": [
        "https://news.google.com/rss/headlines/section/topic/WORLD?hl=ko&gl=KR&ceid=KR:ko",
        "https://www.yna.co.kr/rss/international.xml",
    ],
    "IT/과학/신상품": [
        "https://news.google.com/rss/headlines/section/topic/SCITECH?hl=ko&gl=KR&ceid=KR:ko",
        "https://www.yna.co.kr/rss/industry.xml",
    ],
    "연예/대중문화": [
        "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=ko&gl=KR&ceid=KR:ko",
        "https://www.yna.co.kr/rss/entertainment.xml",
    ],
}

# 주식/환율/기업실적/주가전망 특화 검색 피드 (Google News RSS 검색 쿼리)
FINANCE_FEEDS = {
    "주가동향/기업발표": [
        "https://news.google.com/rss/search?q=%EC%A3%BC%EC%8B%9D+%EC%8B%A4%EC%A0%81%EB%B0%9C%ED%91%9C+OR+%EC%A3%BC%EA%B0%80%EC%A0%84%EB%A7%9D+OR+%EB%AA%A9%ED%91%9C%EC%A3%BC%EA%B0%80&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/search?q=%EC%BD%94%EC%8A%A4%ED%94%BC+OR+%EC%BD%94%EC%8A%A4%EB%8B%A5+%EC%8B%9C%ED%99%A9&hl=ko&gl=KR&ceid=KR:ko",
    ],
    "환율/금리/경제정책": [
        "https://news.google.com/rss/search?q=%EC%9B%90%EB%8B%AC%EB%9F%AC+%ED%99%98%EC%9C%A8+OR+%EA%B8%88%EB%A6%AC+%EC%A0%84%EB%A7%9D&hl=ko&gl=KR&ceid=KR:ko",
    ],
}

# 네이버 모바일 증권 애널리스트 리서치 리포트 API (우선순위 3 전문 채널)
NAVER_RESEARCH_API = "https://m.stock.naver.com/api/research/company?page=1&pageSize=15"

# HTTP 요청 헤더
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
