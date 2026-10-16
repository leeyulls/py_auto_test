"""
google_drive_sync.py
구글 드라이브(Google Drive) 및 구글 스프레드시트 일자별 누적 동기화 모듈
"""

import os
import sys
import shutil
import base64
import requests

# Windows 콘솔 cp949 인코딩 에러 방지
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


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

    def sync_file(self, file_path: str, is_master: bool = False, subfolder: str = "") -> dict:
        """
        생성된 리포트 파일(당일 리포트 또는 누적 마스터 리포트, PDF 리포트)을 구글 드라이브로 동기화
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
                if subfolder and not is_master:
                    parts = [p.strip() for p in subfolder.split("/") if p.strip()]
                    dest_folder = os.path.join(dest_folder, *parts)
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
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    with open(file_path, "rb") as f:
                        file_b64 = base64.b64encode(f.read()).decode("utf-8")

                    filename_b64 = base64.b64encode(filename.encode("utf-8")).decode("utf-8")
                    payload = {
                        "filename": filename,
                        "filename_b64": filename_b64,
                        "content_base64": file_b64,
                        "folder_name": "데일리_브리핑_수집",
                        "subfolder": subfolder,
                        "is_master": is_master
                    }
                    res = requests.post(self.apps_script_url, json=payload, timeout=90, allow_redirects=True)
                    if res.status_code == 200:
                        try:
                            res_data = res.json()
                            if res_data.get("status") == "success":
                                target_f = res_data.get("target_folder_name") or subfolder or "루트"
                                fid = res_data.get("fileId", "")
                                print(f"☁️ [구글드라이브 동기화 성공] {filename} ➔ 폴더: [{target_f}] (FileID: {fid})")
                                results["success"] = True
                                results["methods_attempted"].append("Apps Script Web App")
                                results["file_id"] = fid
                                results["file_url"] = res_data.get("fileUrl", "")
                                break
                            else:
                                err_msg = res_data.get("message", "알 수 없는 오류")
                                print(f"[경고] Apps Script 응답 실패 (시도 {attempt}/{max_retries}): {err_msg}")
                        except Exception:
                            # JSON 파싱 불가 (HTML 리다이렉트 등)
                            print(f"[경고] Apps Script 비정상 응답 (시도 {attempt}/{max_retries}): {res.text[:120]}")
                    else:
                        print(f"[경고] Apps Script HTTP 상태코드 에러 (시도 {attempt}/{max_retries}): {res.status_code}")
                except Exception as e:
                    print(f"[경고] Apps Script 업로드 예외 발생 (시도 {attempt}/{max_retries}): {e}")

                if attempt < max_retries:
                    import time
                    time.sleep(2)

        if not results["success"]:
            print(f"[안내] [{filename}] 구글 드라이브 직접 연동 설정이 없어 로컬 reports/ 폴더에 안전하게 누적 보관 중입니다.")

        return results
