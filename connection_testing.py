import pyodbc

try:
    conn = pyodbc.connect(
        "DRIVER={SQL Server};"
        "SERVER=DESKTOP-JPU330S\\SQLEXPRESS;"
        "DATABASE=PHARMACY;"
        "Trusted_Connection=yes;"
    )
    print("✅ Kết nối thành công")
except Exception as e:
    print("❌ Lỗi kết nối:", e)
