/**
 * GOOGLE_DRIVE_APPS_SCRIPT.js
 * 
 * [구글 드라이브 / 스프레드시트 일자별 누적 저장용 웹앱 스크립트]
 * 1. script.google.com 에 접속하여 새 프로젝트를 만듭니다.
 * 2. 아래 코드를 붙여넣고 저장합니다.
 * 3. 오른쪽 상단 [배포] -> [새 배포] -> 유형 선택: [웹 앱]
 *    - 다음 사용자 권한으로 실행: 나 (내 계정)
 *    - 액세스 권한이 있는 사용자: 모든 사용자 (Anyone)
 * 4. 발급된 웹앱 URL을 email_config.txt 파일에 GOOGLE_APPS_SCRIPT_URL=URL 형태로 입력하시면
 *    매일 아침 일자별 데이터가 구글 드라이브 '데일리_브리핑_수집' 폴더에 누적/축적되어 저장됩니다!
 */

function doGet(e) {
  return ContentService.createTextOutput(JSON.stringify({
    status: "online",
    message: "구글 드라이브 동기화 웹앱이 정상 작동 중입니다!"
  })).setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const filename = data.filename || "daily_report.xlsx";
    const base64Data = data.content_base64;
    const folderName = data.folder_name || "데일리_브리핑_수집";
    const subfolderPath = data.subfolder || "";
    const isMaster = data.is_master || false;
    
    // 1. 대상 최상위 폴더 찾기 또는 생성 ('데일리_브리핑_수집')
    let targetFolder;
    const folders = DriveApp.getFoldersByName(folderName);
    if (folders.hasNext()) {
      targetFolder = folders.next();
    } else {
      targetFolder = DriveApp.createFolder(folderName);
    }
    
    // 2. 월별 서브폴더(예: '2026-10' 또는 '2026-10/공식_리서치_PDF') 경로 처리
    if (subfolderPath && !isMaster) {
      const parts = subfolderPath.split("/").map(function(s) { return s.trim(); }).filter(function(s) { return s.length > 0; });
      for (let i = 0; i < parts.length; i++) {
        const partName = parts[i];
        const subFolders = targetFolder.getFoldersByName(partName);
        if (subFolders.hasNext()) {
          targetFolder = subFolders.next();
        } else {
          targetFolder = targetFolder.createFolder(partName);
        }
      }
    }
    
    // 3. 파일 유형별 Content-Type 설정
    let contentType = "application/octet-stream";
    if (filename.endsWith(".xlsx")) {
      contentType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
    } else if (filename.endsWith(".pdf")) {
      contentType = "application/pdf";
    } else if (filename.endsWith(".md") || filename.endsWith(".txt")) {
      contentType = "text/plain; charset=utf-8";
    }

    // 4. Base64 디코딩 및 Blob 생성
    const decodedBytes = Utilities.base64Decode(base64Data);
    const blob = Utilities.newBlob(decodedBytes, contentType, filename);
    
    // 5. 같은 이름의 파일이 이미 있으면 깔끔하게 덮어쓰기(기존 파일 휴지통 이동)
    const existingFiles = targetFolder.getFilesByName(filename);
    while (existingFiles.hasNext()) {
      existingFiles.next().setTrashed(true);
    }
    
    const file = targetFolder.createFile(blob);
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      filename: filename,
      subfolder: subfolderPath,
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
