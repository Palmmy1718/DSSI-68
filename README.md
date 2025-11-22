# DSSI-68-
pip install django
python manage.py migrate

# คำสั่งสร้างแอดมิน
python manage.py createsuperuser 

# โมเดลที่ใช้แชท
google-genai==1.39.1 
model="models/gemini-2.0-flash-lite

# ไฟล์ data.json ที่ได้จะเก็บข้อมูลทุกตารางในฐานข้อมูล
python manage.py dumpdata > data.json

# ฟอแมทจัดหน้า
shift+alt+F 

# ทดสอบว่าใช้ MySQL จริง
python manage.py dbshell

# MySQL Root Password
RootPass123!

# คำสั่งสร้างอีเมล รหัสแอดมิน
python manage.py createsuperuser