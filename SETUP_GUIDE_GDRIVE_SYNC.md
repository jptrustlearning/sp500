# 📂 Google Drive Sync — Setup Guide
## JP Trust Learning — GitHub CSV → Google Drive (Auto Daily)

---

## สิ่งที่ได้

| รายละเอียด | ค่า |
|-----------|-----|
| **ไฟล์ที่ sync** | `input_sp500_daily.csv` |
| **ต้นทาง** | GitHub raw URL (public repo) |
| **ปลายทาง** | Google Drive โฟลเดอร์ `JP_Trust_SP500` |
| **Sharing** | Anyone with the link (public) |
| **Schedule** | ทุกวัน 08:00 เวลาไทย (หลัง GitHub Actions push เสร็จ) |
| **วิธีทำงาน** | Google Apps Script ดึง CSV จาก GitHub → เขียนทับไฟล์เดิมใน Drive |

---

## 📋 ขั้นตอน Setup (ทำครั้งเดียว)

### ขั้นตอนที่ 1: สร้าง Apps Script Project

1. ไปที่ https://script.google.com
2. กด **New project**
3. ตั้งชื่อโปรเจกต์: `SP500 GitHub to Drive Sync`

### ขั้นตอนที่ 2: วาง Code

ลบโค้ดเดิมทั้งหมดในไฟล์ `Code.gs` แล้ววาง code ด้านล่างนี้ทั้งหมด:

```javascript
// =============================================================================
// 📂 SP500 GitHub → Google Drive Sync
// JP Trust Learning
//
// ดึง CSV จาก GitHub raw URL → เขียนทับไฟล์เดิมใน Google Drive
// ตั้ง trigger รันทุกวัน 08:00 เวลาไทย
// =============================================================================

// ── CONFIG ──────────────────────────────────────────────────────────────────
var CONFIG = {
  // โฟลเดอร์บน Google Drive (สร้างอัตโนมัติถ้ายังไม่มี)
  DRIVE_FOLDER_NAME: "JP_Trust_SP500",

  // ไฟล์ที่ต้อง sync: { ชื่อไฟล์บน Drive: URL ต้นทาง }
  FILES: {
    "input_sp500_daily.csv":
      "https://raw.githubusercontent.com/jptrustlearning/sp500/main/input_sp500_daily.csv"
  }
};

// ── MAIN FUNCTION ───────────────────────────────────────────────────────────
function syncGitHubToDrive() {
  var folder = getOrCreateFolder(CONFIG.DRIVE_FOLDER_NAME);
  var fileNames = Object.keys(CONFIG.FILES);

  for (var i = 0; i < fileNames.length; i++) {
    var fileName = fileNames[i];
    var url = CONFIG.FILES[fileName];

    try {
      // ดึง CSV จาก GitHub
      var response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });

      if (response.getResponseCode() !== 200) {
        Logger.log("❌ FAILED " + fileName + " — HTTP " + response.getResponseCode());
        continue;
      }

      var content = response.getBlob().setName(fileName);
      var contentType = "text/csv";
      content.setContentType(contentType);

      // หาไฟล์เดิมในโฟลเดอร์
      var existingFiles = folder.getFilesByName(fileName);

      if (existingFiles.hasNext()) {
        // เขียนทับไฟล์เดิม (คง file ID เดิม → URL ไม่เปลี่ยน)
        var existingFile = existingFiles.next();
        var fileId = existingFile.getId();

        // ใช้ Drive API v2 เพื่อ update content โดยคง ID เดิม
        Drive.Files.update(
          { title: fileName, mimeType: contentType },
          fileId,
          content
        );

        Logger.log("✅ UPDATED " + fileName + " (ID: " + fileId + ")");
      } else {
        // สร้างไฟล์ใหม่ + ตั้ง public sharing
        var newFile = folder.createFile(content);
        newFile.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

        Logger.log("✅ CREATED " + fileName + " (ID: " + newFile.getId() + ")");
        Logger.log("🔗 Link: https://drive.google.com/file/d/" + newFile.getId() + "/view");
      }

    } catch (e) {
      Logger.log("❌ ERROR " + fileName + ": " + e.message);
    }
  }

  Logger.log("── Sync completed at " + new Date().toISOString() + " ──");
}

// ── HELPER: สร้างหรือหาโฟลเดอร์ ─────────────────────────────────────────
function getOrCreateFolder(folderName) {
  var folders = DriveApp.getFoldersByName(folderName);

  if (folders.hasNext()) {
    var folder = folders.next();
    Logger.log("📂 Found folder: " + folderName + " (ID: " + folder.getId() + ")");
    return folder;
  }

  // สร้างโฟลเดอร์ใหม่ + ตั้ง public
  var newFolder = DriveApp.createFolder(folderName);
  newFolder.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

  Logger.log("📂 Created folder: " + folderName + " (ID: " + newFolder.getId() + ")");
  return newFolder;
}

// ── SETUP TRIGGER (รันครั้งเดียว) ────────────────────────────────────────
function setupDailyTrigger() {
  // ลบ trigger เก่าทั้งหมดก่อน
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    ScriptApp.deleteTrigger(triggers[i]);
  }

  // ตั้ง trigger ใหม่: ทุกวัน 08:00-09:00 เวลาไทย (ICT = UTC+7)
  ScriptApp.newTrigger("syncGitHubToDrive")
    .timeBased()
    .everyDays(1)
    .atHour(8)
    .inTimezone("Asia/Bangkok")
    .create();

  Logger.log("⏰ Trigger set: daily 08:00-09:00 ICT");
}

// ── MANUAL RUN (ทดสอบได้ทุกเมื่อ) ───────────────────────────────────────
function manualSync() {
  syncGitHubToDrive();
}
```

### ขั้นตอนที่ 3: เปิด Drive API Service

Script ใช้ `Drive.Files.update()` ซึ่งต้องเปิด Advanced Drive Service:

1. ในหน้า Apps Script → คลิก **Services** (ไอคอน + ทางซ้าย)
2. หา **Drive API** → กด **Add**
3. จะเห็น `Drive` ปรากฏในรายการ Services ทางซ้าย

### ขั้นตอนที่ 4: รันครั้งแรก (ทดสอบ + สร้างไฟล์)

1. เลือก function **`manualSync`** จาก dropdown ด้านบน
2. กด **▶ Run**
3. ครั้งแรกจะขอ permission — กด **Review Permissions** → เลือก Google Account → **Allow**
4. ดู **Execution log** ด้านล่าง — ควรเห็น:
   ```
   📂 Created folder: JP_Trust_SP500 (ID: xxx)
   ✅ CREATED input_sp500_daily.csv (ID: yyy)
   🔗 Link: https://drive.google.com/file/d/yyy/view
   ```
5. เปิด Google Drive → จะเห็นโฟลเดอร์ `JP_Trust_SP500` พร้อมไฟล์ CSV ข้างใน

### ขั้นตอนที่ 5: ตั้ง Daily Trigger

1. เลือก function **`setupDailyTrigger`** จาก dropdown
2. กด **▶ Run**
3. ดู log — ควรเห็น:
   ```
   ⏰ Trigger set: daily 08:00-09:00 ICT
   ```

เสร็จแล้ว! จากนี้ทุกวัน 08:00 เวลาไทย script จะดึง CSV จาก GitHub มาเขียนทับอัตโนมัติ

---

## ✅ ตรวจสอบว่าใช้งานได้

### ดู Link สำหรับแชร์

เปิด Google Drive → โฟลเดอร์ `JP_Trust_SP500` → คลิกขวาที่ไฟล์ CSV → **Share** → **Copy link**

Link นี้จะคงที่ตลอด (file ID ไม่เปลี่ยน) ส่งให้ใครก็เข้าถึงได้เลย

### ดู URL สำหรับ download ตรง (ใช้ใน code/dashboard)

```
https://drive.google.com/uc?export=download&id=FILE_ID
```

แทน `FILE_ID` ด้วย ID จริงของไฟล์ (ดูจาก log หรือจาก URL ตอน Share)

### ดู Execution Log

ไปที่ Apps Script → **Executions** (เมนูทางซ้าย) → ดูว่า trigger รันสำเร็จทุกวันหรือไม่

---

## 🔧 เพิ่มไฟล์อื่นในอนาคต

ถ้าต้องการ sync ไฟล์เพิ่ม แค่เพิ่มใน `CONFIG.FILES`:

```javascript
FILES: {
  "input_sp500_daily.csv":
    "https://raw.githubusercontent.com/jptrustlearning/sp500/main/input_sp500_daily.csv",
  "output_combined_score_sp500.csv":
    "https://raw.githubusercontent.com/jptrustlearning/sp500/main/output_combined_score_sp500.csv",
  "all_profiles.csv":
    "https://raw.githubusercontent.com/jptrustlearning/sp500/main/all_profiles.csv"
}
```

แล้วรัน `manualSync` อีกครั้งเพื่อสร้างไฟล์ใหม่บน Drive

---

## 🔧 Troubleshooting

### ปัญหา: "GoogleJsonResponseException: Drive API not enabled"
**วิธีแก้:** ทำขั้นตอนที่ 3 — เปิด Drive API ใน Services

### ปัญหา: "You do not have permission"
**วิธีแก้:** รัน `manualSync` อีกครั้ง → กด Review Permissions → Allow

### ปัญหา: ไฟล์ไม่อัปเดต
**วิธีแก้:** ดู Executions log → ถ้า trigger ไม่รัน ให้รัน `setupDailyTrigger` ใหม่

### ปัญหา: GitHub raw URL ส่ง 404
**วิธีแก้:** ตรวจว่า repo ยัง public อยู่ และชื่อไฟล์ตรง

---

## 📅 VERSION HISTORY

| Version | Date | Changes |
|---------|------|---------|
| **1.0** | **2026-03-18** | Initial: Apps Script sync GitHub CSV to Google Drive with daily trigger |

---

*Created by JP TRUST LEARNING*
*Google Drive Sync — Setup Guide v1.0 — March 2026*
