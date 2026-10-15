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
  // 웹 브라우저 링크 클릭 한번으로 루트 폴더 청소 지원: ?action=cleanup_root
  if (e && e.parameter && e.parameter.action === "cleanup_root") {
    const folders = DriveApp.getFoldersByName("데일리_브리핑_수집");
    if (!folders.hasNext()) {
      return ContentService.createTextOutput(JSON.stringify({ status: "error", message: "폴더를 찾을 수 없습니다." })).setMimeType(ContentService.MimeType.JSON);
    }
    const root = folders.next();
    const files = root.getFiles();
    let cleaned = [];
    while (files.hasNext()) {
      const file = files.next();
      const fname = file.getName();
      if (fname !== "일자별_누적_데일리_이슈_및_주식_브리핑_마스터.xlsx") {
        cleaned.push(fname);
        file.setTrashed(true);
      }
    }
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      message: "루트 메인폴더 정리 완료! (마스터 엑셀 및 월별 폴더 제외 파일 삭제)",
      cleaned_count: cleaned.length,
      cleaned_files: cleaned
    })).setMimeType(ContentService.MimeType.JSON);
  }

  return ContentService.createTextOutput(JSON.stringify({
    status: "online",
    version: "v2.1-cleanup-supported",
    message: "구글 드라이브 동기화 웹앱 최신 버전이 정상 작동 중입니다! (?action=cleanup_root 로 메인폴더 청소 가능)"
  })).setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);

    // [특수 명령] 루트 폴더 청소 요청 처리
    if (data.action === "cleanup_root") {
      const folders = DriveApp.getFoldersByName(data.folder_name || "데일리_브리핑_수집");
      if (folders.hasNext()) {
        const root = folders.next();
        const files = root.getFiles();
        let cleaned = [];
        while (files.hasNext()) {
          const file = files.next();
          const fname = file.getName();
          if (fname !== "일자별_누적_데일리_이슈_및_주식_브리핑_마스터.xlsx") {
            cleaned.push(fname);
            file.setTrashed(true);
          }
        }
        return ContentService.createTextOutput(JSON.stringify({
          status: "success",
          cleaned_count: cleaned.length,
          cleaned_files: cleaned
        })).setMimeType(ContentService.MimeType.JSON);
      }
    }
    
    // 1. 파일명 한글 깨짐 원천 방지 (Base64 우선 디코딩)
    let filename = data.filename || "daily_report.xlsx";
    if (data.filename_b64) {
      try {
        const decodedBytes = Utilities.base64Decode(data.filename_b64);
        filename = Utilities.newBlob(decodedBytes).getDataAsString("UTF-8");
      } catch (err) {
        filename = data.filename;
      }
    }
    
    const base64Data = data.content_base64;
    const folderName = data.folder_name || "데일리_브리핑_수집";
    const subfolderPath = data.subfolder || "";
    const isMaster = data.is_master || false;
    
    // 2. 대상 최상위 폴더 찾기 또는 생성 ('데일리_브리핑_수집')
    let targetFolder;
    const folders = DriveApp.getFoldersByName(folderName);
    if (folders.hasNext()) {
      targetFolder = folders.next();
    } else {
      targetFolder = DriveApp.createFolder(folderName);
    }
    
    // 3. 월별 서브폴더(예: '2026-10' 또는 '2026-10/공식_리서치_PDF') 계층별 경로 처리
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
    
    // 4. 파일 유형별 Content-Type 설정 (구글 드라이브 PDF 뷰어 정상 작동 보장)
    let contentType = "application/octet-stream";
    const lowerName = filename.toLowerCase();
    if (lowerName.endsWith(".pdf")) {
      contentType = "application/pdf";
    } else if (lowerName.endsWith(".xlsx")) {
      contentType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
    } else if (lowerName.endsWith(".md") || lowerName.endsWith(".txt")) {
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

/**
 * [유틸 함수] 루트 폴더 청소
 * 이전에 루트 폴더에 잘못 올라간 깨진 파일이나 임시 파일들을 한번에 정리하고 싶을 때
 * 스크립트 편집기 상단에서 'cleanupRootFolder' 함수를 선택하고 [실행]을 누르면
 * 마스터 파일('일자별_누적_데일리_이슈_및_주식_브리핑_마스터.xlsx')을 제외한 루트의 파일들을 안전하게 정리합니다.
 */
function cleanupRootFolder() {
  const folders = DriveApp.getFoldersByName("데일리_브리핑_수집");
  if (!folders.hasNext()) return;
  const root = folders.next();
  const files = root.getFiles();
  while (files.hasNext()) {
    const file = files.next();
    if (file.getName() !== "일자별_누적_데일리_이슈_및_주식_브리핑_마스터.xlsx") {
      file.setTrashed(true);
    }
  }
}

