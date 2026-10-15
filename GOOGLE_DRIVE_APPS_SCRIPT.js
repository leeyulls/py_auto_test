/**
 * GOOGLE_DRIVE_APPS_SCRIPT.js
 * 
 * [구글 드라이브 / 스프레드시트 일자별 누적 저장용 웹앱 스크립트 v2.2]
 * 1. script.google.com 에 접속하여 기존 프로젝트를 엽니다.
 * 2. 아래 코드를 전체 붙여넣고 저장합니다.
 * 3. 오른쪽 상단 [배포] -> [배포 관리] -> 연필 아이콘 [수정] 클릭
 *    - 버전: [새 버전] 선택
 *    - [배포] 클릭 (URL은 변경되지 않으며 즉시 최신 코드가 반영됩니다!)
 * 4. 특징:
 *    - 휴지통(Trash) 폴더 철저 배제 및 내 드라이브 루트 기준 '데일리_브리핑_수집' 100% 매칭
 *    - 월별 하위폴더 ('2026-10' 및 '2026-10/공식_리서치_PDF') 완벽 생성 및 분기 안착
 *    - PDF 및 HTML 공식 MIME-Type 보장으로 구글 드라이브 뷰어 깨짐 원천 방지
 *    - ?action=tree 파라미터로 드라이브 폴더/파일 구조 실시간 점검 지원
 */

// 1. 안전한 루트 폴더 탐색 (휴지통 제외 및 내 드라이브 직속 우선)
function getOrCreateRootFolder(folderName) {
  const rootDir = DriveApp.getRootFolder();
  const rootFolders = rootDir.getFoldersByName(folderName);
  while (rootFolders.hasNext()) {
    const f = rootFolders.next();
    if (!f.isTrashed()) {
      return f;
    }
  }
  const globalFolders = DriveApp.getFoldersByName(folderName);
  while (globalFolders.hasNext()) {
    const f = globalFolders.next();
    if (!f.isTrashed()) {
      return f;
    }
  }
  return rootDir.createFolder(folderName);
}

// 2. 안전한 계층형 서브폴더 탐색 및 생성
function getOrCreateSubFolder(parentFolder, subfolderPath) {
  if (!subfolderPath) return parentFolder;
  const parts = subfolderPath.split("/").map(function(s) { return s.trim(); }).filter(function(s) { return s.length > 0; });
  let cur = parentFolder;
  for (let i = 0; i < parts.length; i++) {
    const partName = parts[i];
    const subIter = cur.getFoldersByName(partName);
    let matched = null;
    while (subIter.hasNext()) {
      const sf = subIter.next();
      if (!sf.isTrashed()) {
        matched = sf;
        break;
      }
    }
    if (matched) {
      cur = matched;
    } else {
      cur = cur.createFolder(partName);
    }
  }
  return cur;
}

function doGet(e) {
  const rootFolder = getOrCreateRootFolder("데일리_브리핑_수집");

  // 1. 브라우저 클릭으로 루트 폴더 청소: ?action=cleanup_root
  if (e && e.parameter && e.parameter.action === "cleanup_root") {
    const files = rootFolder.getFiles();
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
      message: "루트 메인폴더 정리 완료! (마스터 엑셀 및 월별 서브폴더 외 파일 삭제)",
      cleaned_count: cleaned.length,
      cleaned_files: cleaned
    })).setMimeType(ContentService.MimeType.JSON);
  }

  // 2. 폴더 트리 및 파일 목록 진단: ?action=tree
  if (e && e.parameter && e.parameter.action === "tree") {
    let tree = {
      root: rootFolder.getName(),
      rootId: rootFolder.getId(),
      files_in_root: [],
      subfolders: []
    };
    const rFiles = rootFolder.getFiles();
    while (rFiles.hasNext()) {
      const rf = rFiles.next();
      if (!rf.isTrashed()) {
        tree.files_in_root.push({ name: rf.getName(), size: rf.getSize(), id: rf.getId() });
      }
    }
    const sFolders = rootFolder.getFolders();
    while (sFolders.hasNext()) {
      const sf = sFolders.next();
      if (!sf.isTrashed()) {
        let subData = { name: sf.getName(), id: sf.getId(), files: [] };
        const sfFiles = sf.getFiles();
        while (sfFiles.hasNext()) {
          const sff = sfFiles.next();
          if (!sff.isTrashed()) {
            subData.files.push({ name: sff.getName(), size: sff.getSize(), id: sff.getId() });
          }
        }
        tree.subfolders.push(subData);
      }
    }
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      tree: tree
    })).setMimeType(ContentService.MimeType.JSON);
  }

  return ContentService.createTextOutput(JSON.stringify({
    status: "online",
    version: "v2.2-robust-subfolder-pdf",
    rootFolderId: rootFolder.getId(),
    message: "구글 드라이브 동기화 웹앱 v2.2 정상 가동 중 (?action=tree 로 폴더구조 확인 가능)"
  })).setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);

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
    
    // 2. 최상위 루트 폴더 찾기 또는 생성 ('데일리_브리핑_수집')
    const mainFolder = getOrCreateRootFolder(folderName);
    
    // 3. 월별 서브폴더(예: '2026-10' 또는 '2026-10/공식_리서치_PDF') 계층별 경로 처리
    let targetFolder = mainFolder;
    if (subfolderPath && !isMaster) {
      targetFolder = getOrCreateSubFolder(mainFolder, subfolderPath);
    }
    
    // 4. 파일 유형별 Content-Type 설정 (구글 드라이브 뷰어 및 다운로드 정상 작동 보장)
    let contentType = "application/octet-stream";
    const lowerName = filename.toLowerCase();
    if (lowerName.endsWith(".pdf")) {
      contentType = "application/pdf";
    } else if (lowerName.endsWith(".html") || lowerName.endsWith(".htm")) {
      contentType = "text/html; charset=utf-8";
    } else if (lowerName.endsWith(".xlsx")) {
      contentType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
    } else if (lowerName.endsWith(".md") || lowerName.endsWith(".txt")) {
      contentType = "text/plain; charset=utf-8";
    }

    // 5. Base64 디코딩 및 Blob 생성
    const decodedBytes = Utilities.base64Decode(base64Data);
    const blob = Utilities.newBlob(decodedBytes, contentType, filename);
    
    // 6. 같은 이름의 파일이 이미 타겟 폴더에 있으면 덮어쓰기(기존 파일 휴지통 이동)
    const existingFiles = targetFolder.getFilesByName(filename);
    while (existingFiles.hasNext()) {
      const oldF = existingFiles.next();
      if (!oldF.isTrashed()) {
        oldF.setTrashed(true);
      }
    }
    
    const file = targetFolder.createFile(blob);
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      filename: filename,
      folder_name: folderName,
      subfolder: subfolderPath,
      target_folder_name: targetFolder.getName(),
      target_folder_id: targetFolder.getId(),
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
