# DSSI-68 — ระบบจองคิวนวดแผนไทย
ระบบนี้รองรับการจองคิว, จัดการข้อมูลผ่าน Admin, ใช้ฐานข้อมูล MySQL และรองรับ Chat AI ผ่าน Google Generative AI (Gemini) คู่มือนี้อธิบายวิธี Clone → Setup → Run → Demo Phase 1 + Phase 2 ทำตามได้ภายใน 5–8 นาที

---

## 🔽 1. Clone โปรเจกต์
git clone https://github.com/Palmmy1718/DSSI-68.git
cd DSSI-68

---

## 🔧 2. สร้างและเปิดใช้งาน Virtual Environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

---

## 📦 3. ติดตั้งไลบรารีหลัก & ไลบรารีเพิ่มเติมที่จำเป็น
pip install -r requirements.txt

---

## 4. ตั้งค่า MySQL + สร้างฐานข้อมูล + นำเข้าข้อมูล
4.1 ตั้งค่าไฟล์ .env
DB_NAME=dssi68_db
DB_USER=dssi68_user
DB_PASSWORD=NewPass123!
DB_HOST=localhost
DB_PORT=3307

GEMINI_API_KEY=YOUR_KEY
GEMINI_MODEL_NAME=gemini-2.0-flash-lite-latest
# optional
GOOGLE_API_KEY=YOUR_KEY

4.2 เปิด MySQL
mysql -u dssi68_user -p -h localhost -P 3307

4.3 สร้าง Database + User (ทำครั้งแรกครั้งเดียว)
CREATE DATABASE dssi68_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'dssi68_user'@'%' IDENTIFIED BY 'NewPass123!';
GRANT ALL PRIVILEGES ON dssi68_db.* TO 'dssi68_user'@'%';
FLUSH PRIVILEGES;

4.4 Migrate + Import ข้อมูล
python manage.py migrate
python manage.py loaddata data.json


## 5. รันเซิร์ฟเวอร์
python manage.py runserver

## 6. สร้างผู้ดูแลระบบ (Admin)
python manage.py createsuperuser