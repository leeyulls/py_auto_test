"""
stock_universe.py
국내 및 해외 주요 관심 종목 유니버스 및 키워드 매핑 테이블
"""

# 주요 관심 종목 목록 (종목코드, 한글명, 섹터, 뉴스 매칭 키워드)
STOCK_UNIVERSE = [
    {
        "ticker": "005930.KS",
        "name": "삼성전자",
        "sector": "반도체/IT",
        "keywords": ["삼성전자", "삼성", "반도체", "D램", "파운드리", "HBM"]
    },
    {
        "ticker": "000660.KS",
        "name": "SK하이닉스",
        "sector": "반도체/AI",
        "keywords": ["SK하이닉스", "하이닉스", "HBM3E", "엔비디아 납품"]
    },
    {
        "ticker": "005380.KS",
        "name": "현대차",
        "sector": "자동차/모빌리티",
        "keywords": ["현대차", "현대자동차", "전기차", "아이오닉", "미국 공장"]
    },
    {
        "ticker": "000270.KS",
        "name": "기아",
        "sector": "자동차/모빌리티",
        "keywords": ["기아", "EV3", "기아차", "호실적"]
    },
    {
        "ticker": "035420.KS",
        "name": "NAVER",
        "sector": "인터넷/AI",
        "keywords": ["NAVER", "네이버", "하이퍼클로바", "서치GPT"]
    },
    {
        "ticker": "035720.KS",
        "name": "카카오",
        "sector": "인터넷/플랫폼",
        "keywords": ["카카오", "카카오톡", "카나나", "카카오페이", "카카오뱅크"]
    },
    {
        "ticker": "068270.KS",
        "name": "셀트리온",
        "sector": "바이오/헬스케어",
        "keywords": ["셀트리온", "짐펜트라", "바이오시밀러", "FDA 승인"]
    },
    {
        "ticker": "012450.KS",
        "name": "한화에어로스페이스",
        "sector": "방산/우주",
        "keywords": ["한화에어로스페이스", "한화에어로", "K9 자주포", "방산 수출", "루마니아"]
    },
    {
        "ticker": "373220.KS",
        "name": "LG에너지솔루션",
        "sector": "2차전지/배터리",
        "keywords": ["LG에너지솔루션", "LG엔솔", "배터리", "테슬라 수주", "4680"]
    },
    {
        "ticker": "005490.KS",
        "name": "POSCO홀딩스",
        "sector": "철강/이차전지소재",
        "keywords": ["포스코", "POSCO홀딩스", "리튬", "철강"]
    },
    {
        "ticker": "NVDA",
        "name": "엔비디아 (NVIDIA)",
        "sector": "글로벌 AI/반도체",
        "keywords": ["엔비디아", "NVIDIA", "블랙웰", "AI 가속기"]
    },
    {
        "ticker": "AAPL",
        "name": "애플 (Apple)",
        "sector": "글로벌 빅테크",
        "keywords": ["애플", "Apple", "아이폰", "애플 인텔리전스"]
    },
    {
        "ticker": "TSLA",
        "name": "테슬라 (Tesla)",
        "sector": "전기차/자율주행",
        "keywords": ["테슬라", "Tesla", "로보택시", "FSD", "일론 머스크"]
    }
]


def match_stocks_from_news(news_list: list) -> list:
    """수집된 뉴스 기사에서 관련 종목을 매핑하고 뉴스 모멘텀 결합"""
    matched_results = {}

    for stock in STOCK_UNIVERSE:
        matched_articles = []
        sentiment_score = 0  # +점수: 호재, -점수: 악재

        for news in news_list:
            title = news.get("기사제목", "")
            summary = news.get("요약내용", "")
            combined_text = f"{title} {summary}"

            # 종목 키워드 매칭
            is_matched = any(kw in combined_text for kw in stock["keywords"])
            if is_matched:
                # 감성 및 모멘텀 분석
                if any(w in combined_text for w in ["호조", "상승", "돌파", "사상최대", "수주", "승인", "상향", "매수"]):
                    sentiment_score += 1
                elif any(w in combined_text for w in ["부진", "하락", "급락", "우려", "사이드카", "소송", "하향", "제재"]):
                    sentiment_score -= 1

                matched_articles.append({
                    "title": title,
                    "link": news.get("링크", ""),
                    "source": news.get("언론사", "")
                })

        # 뉴스가 있거나 주요 대표 종목인 경우 분석 대상에 포함
        matched_results[stock["ticker"]] = {
            "stock_info": stock,
            "matched_news": matched_articles[:3],
            "news_count": len(matched_articles),
            "sentiment_score": sentiment_score
        }

    return matched_results
