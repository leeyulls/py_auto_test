"""
google_drive_sync.py
구글 드라이브(Google Drive) 및 구글 스프레드시트 일자별 누적 동기화 모듈
"""

import os
import shutil
import base64
import requests


class GoogleDriveSync:
    def __init__(self):
        self.drive_folder = os.environ.get("GOOGLE_DRIVE_FOLDER")
        self.apps_script_url = os.environ.get("GOOGLE_APPS_SCRIPT_URL")

    def find_desktop_drive_path(self):
        """PC에 설치된 Google Drive for Desktop 경로 자동 탐색"""
        if self.drive_folder and os.path.exists(self.drive_folder):
            return self.drive_folder

        candidates = [
            r"G:\내 드라이브",
            r"G:\My Drive",
            r"H:\내 드라이브",
            r"H:\My Drive",
            os.path.expanduser(r"~\Google Drive"),
            os.path.expanduser(r"~\Google 드라이브"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def sync_file(self, file_path: str, is_master: bool = False) -> dict:
        """
        생성된 리포트 파일(당일 리포트 또는 누적 마스터 리포트)을 구글 드라이브로 동기화
        """
        results = {"success": False, "methods_attempted": []}
        if not file_path or not os.path.exists(file_path):
            return results

        filename = os.path.basename(file_path)

        # 1. Google Drive for Desktop 로컬 동기화 폴더 확인
        local_drive = self.find_desktop_drive_path()
        if local_drive:
            try:
                dest_folder = os.path.join(local_drive, "데일리_브리핑_수집")
                os.makedirs(dest_folder, exist_ok=True)
                dest_path = os.path.join(dest_folder, filename)
                shutil.copy2(file_path, dest_path)
                print(f"✅ Google Drive 로컬 동기화 완료: {dest_path}")
                results["success"] = True
                results["local_path"] = dest_path
                results["methods_attempted"].append("Google Drive for Desktop")
            except Exception as e:
                print(f"[경고] 로컬 Google Drive 복사 실패: {e}")

        # 2. Google Apps Script Web App URL이 설정된 경우 클라우드 자동 업로드
        if self.apps_script_url:
            try:
                with open(file_path, "rb") as f:
                    file_b64 = base64.b64encode(f.read()).decode("utf-8")

                payload = {
                    "filename": filename,
                    "content_base64": file_b64,
                    "folder_name": "데일리_브리핑_수집",
                    "is_master": is_master
                }
                res = requests.post(self.apps_script_url, json=payload, timeout=30, allow_redirects=True)
                if res.status_code == 200 or res.status_code == 302:
                    print(f"✅ Google Apps Script 웹앱 클라우드 동기화 완료: {filename}")
                    results["success"] = True
                    results["methods_attempted"].append("Apps Script Web App")
                else:
                    print(f"[경고] Apps Script 웹앱 업로드 응답 코드: {res.status_code}")
            except Exception as e:
                print(f"[경고] Apps Script 웹앱 업로드 실패: {e}")

        if not results["success"]:
            print(f"ℹ️ [{filename}] 구글 드라이브 직접 연동 설정이 없어 로컬 reports/ 폴더에 안전하게 누적 보관 중입니다.")

        return results
