import pymysql
pymysql.install_as_MySQLdb()

# ทำ trick หลอก Django ว่า MySQL เป็นเวอร์ชัน 8.0
pymysql.version_info = (8, 0, 0, "final", 0)
