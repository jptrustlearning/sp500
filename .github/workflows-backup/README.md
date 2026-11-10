# workflows-backup

สำเนาไฟล์ workflow ก่อนแก้ (`<ชื่อ>-backup-vN.yml`) — เก็บไว้นอก `.github/workflows/` โดยตั้งใจ
เพื่อไม่ให้ GitHub Actions หยิบไปรันซ้ำ · ห้ามย้ายกลับเข้า workflows/ ตรงๆ

- v1 (2 ต.ค. 2026): ก่อนใส่ push retry ในขั้น Commit and push (เหตุ: Commodities ชนกับ USDJPY ตอน push)
- v2 (5 ต.ค. 2026): `create_mini_sp500_last14days` ก่อนเพิ่ม trigger ให้รันซ้ำหลัง Benchmark + Commodities (SPY/GOLD/WTI ใน mini_sp500_rotation.csv ช้า 1 วันเสมอ)
- kick_daily_updates v1 (11 พ.ย. 2026): ก่อนเปลี่ยน GH_TOKEN เป็น SP500_PAT (run ที่สั่งด้วย github.token ไม่ปลุก Mini/Sync)
- kick_daily_updates v2 (11 พ.ย. 2026): ก่อนเพิ่ม path ops/kicks/** (task สร้างไฟล์ใหม่วันละไฟล์)
