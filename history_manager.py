"""
history_manager.py
전일 및 이전 수집 결과물과의 중복 제거 및 연결 이슈(후속 보도) 판별 모듈
"""

import datetime
import difflib
import json
import os
import re

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "data", "history.json")


class HistoryManager:
    def __init__(self, history_file=HISTORY_FILE):
        self.history_file = history_file
        self.history = self._load_history()

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_history(self):
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        # 최근 14일치 이력만 보관 (파일 용량 최적화)
        cutoff_date = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
        cleaned = {
            date: items for date, items in self.history.items() if date >= cutoff_date
        }
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _normalize_title(title: str) -> str:
        """기사 제목에서 언론사명, 대괄호 태그, 특수문자 제거 후 정규화"""
        # [속보], [단독] 등 말머리 및 언론사 표기 제거
        t = re.sub(r"\[.*?\]|\(.*?\)|<.*?>", " ", title)
        t = re.sub(r" - [^ ]+$", "", t)  # 구글 뉴스의 ' - 언론사명' 제거
        t = re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", t)
        return " ".join(t.split()).strip()

    def check_status(self, title: str, link: str):
        """
        기사의 중복 여부 및 연결 이슈 여부 판별
        반환값:
          ('duplicate', None) : 완전 중복 (제거 대상)
          ('follow_up', prev_title) : 연결되는 내용 / 후속 보도 (수집 허용)
          ('new', None) : 완전히 새로운 기사 (수집 허용)
        """
        norm_title = self._normalize_title(title)
        title_words = set(w for w in norm_title.split() if len(w) >= 2)

        is_connected = False
        connected_title = None

        for date_str, items in self.history.items():
            for item in items:
                # 1. 유효한 링크가 같거나 정규화 제목이 완전히 동일한 경우 -> 완전 중복
                if link and link != "#" and item.get("link") and item.get("link") == link:
                    return "duplicate", None

                prev_norm = item.get("norm_title", "")
                if prev_norm and prev_norm == norm_title:
                    return "duplicate", None

                # 2. 제목 유사도 비교
                similarity = difflib.SequenceMatcher(None, norm_title, prev_norm).ratio()
                if similarity >= 0.85:
                    # 85% 이상 동일하면 단순 중복 기사로 판단
                    return "duplicate", None

                # 3. 핵심 단어 2개 이상 겹치지만 유사도가 85% 미만인 경우 -> 연결/후속 이슈 판별
                prev_words = set(item.get("words", []))
                common_words = title_words.intersection(prev_words)
                if len(common_words) >= 2 and similarity >= 0.35:
                    is_connected = True
                    connected_title = item.get("title")

        if is_connected:
            return "follow_up", connected_title

        return "new", None

    def is_research_collected(self, item_name: str, title: str, research_id: str = None) -> bool:
        """해당 종목/리포트가 당일 또는 최근 이력에 이미 발행되었는지 판별"""
        norm_title = self._normalize_title(title or "")
        clean_item = (item_name or "").strip()

        for date_str, items in self.history.items():
            for item in items:
                if item.get("category") != "증권사리포트":
                    continue
                # 1. research_id 일치
                if research_id and item.get("research_id") and str(item.get("research_id")) == str(research_id):
                    return True
                # 2. 동일 종목 + 제목 유사도 70% 이상
                if clean_item and clean_item == item.get("item_name"):
                    prev_norm = item.get("norm_title", "")
                    if prev_norm == norm_title:
                        return True
                    sim = difflib.SequenceMatcher(None, norm_title, prev_norm).ratio()
                    if sim >= 0.7:
                        return True
        return False

    def record_research(self, reports: list):
        """선별된 증권사 공식 리포트를 이력에 등록"""
        today_str = datetime.date.today().isoformat()
        if today_str not in self.history:
            self.history[today_str] = []

        for rep in reports:
            title = rep.get("title", "")
            norm_title = self._normalize_title(title)
            words = list(set(w for w in norm_title.split() if len(w) >= 2))
            self.history[today_str].append({
                "title": title,
                "norm_title": norm_title,
                "link": rep.get("attach_url") or "",
                "category": "증권사리포트",
                "item_name": rep.get("item_name", ""),
                "broker": rep.get("broker", ""),
                "research_id": str(rep.get("id") or ""),
                "words": words,
            })

        self.save_history()

    def record_collected(self, articles: list):
        """오늘 수집된 기사/공시 목록을 이력에 등록"""
        today_str = datetime.date.today().isoformat()
        if today_str not in self.history:
            self.history[today_str] = []

        for art in articles:
            norm_title = self._normalize_title(art["title"])
            words = list(set(w for w in norm_title.split() if len(w) >= 2))
            self.history[today_str].append({
                "title": art["title"],
                "norm_title": norm_title,
                "link": art.get("link", ""),
                "category": art.get("category", ""),
                "words": words,
            })

        self.save_history()
