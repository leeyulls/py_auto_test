/**
 * GOOGLE_DRIVE_APPS_SCRIPT.js
 * 
 * [구글 드라이브 자동 저장용 웹앱 스크립트]
 * 1. script.google.com 에 접속하여 새 프로젝트를 만듭니다.
 * 2. 아래 코드를 붙여넣고 저장합니다.
 * 3. 오른쪽 상단 [배포] -> [새 배포] -> 유형 선택: [웹 앱]
 *    - 다음 사용자 권한으로 실행: 나 (내 계정)
 *    - 액세스 권한이 있는 사용자: 모든 사용자 (Anyone)
 * 4. 발급된 웹앱 URL을 환경 변수 GOOGLE_APPS_SCRIPT_URL 로 지정하거나 python 코드에 입력하면 
 *    크롤링 완료 시 자동으로 구글 드라이브 '데일리_브리핑_수집' 폴더에 파일이 업로드됩니다!
 */

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const filename = data.filename || "daily_report.xlsx";
    const base64Data = data.content_base64;
    const folderName = data.folder_name || "데일리_브리핑_수집";
    
    // 대상 폴더 찾기 또는 생성
    let folder;
    const folders = DriveApp.getFoldersByName(folderName);
    if (folders.hasNext()) {
      folder = folders.next();
    } else {
      folder = DriveApp.createFolder(folderName);
    }
    
    // Base64 디코딩 후 파일 생성
    const decodedBytes = Utilities.base64Decode(base64Data);
    const contentType = filename.endsWith(".xlsx") ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" : "text/plain";
    const blob = Utilities.newBlob(decodedBytes, contentType, filename);
    const file = folder.createFile(blob);
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      fileId: file.getId(),
      fileUrl: file.getUrl()
    })).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}
