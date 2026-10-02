# workflows-backup

สำเนาไฟล์ workflow ก่อนแก้ (`<ชื่อ>-backup-vN.yml`) — เก็บไว้นอก `.github/workflows/` โดยตั้งใจ
เพื่อไม่ให้ GitHub Actions หยิบไปรันซ้ำ · ห้ามย้ายกลับเข้า workflows/ ตรงๆ

- v1 (2 ต.ค. 2026): ก่อนใส่ push retry ในขั้น Commit and push (เหตุ: Commodities ชนกับ USDJPY ตอน push)
