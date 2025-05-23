import pyodbc

# 1. Chuỗi kết nối
try:
    conn = pyodbc.connect(
        "DRIVER={SQL Server};"
        "SERVER=DESKTOP-JPU330S\\SQLEXPRESS;"
        "DATABASE=PHARMACY;"
        "Trusted_Connection=yes;"
    )
    cursor = conn.cursor()
except pyodbc.Error as e:
    print(f"Lỗi kết nối: {e}")
    exit()

# 2. Nhập tên thuốc
input_drugs = input("Nhập tên thuốc (phân tách bởi dấu phẩy): ")
drug_names = [name.strip() for name in input_drugs.split(',')]

# 3. Lấy thông tin từng thuốc từ bảng Prescriptions
print("\n🔍 Thông tin thuốc:")
prescription_ids = []
for name in drug_names:
    try:
        query = """
            SELECT prescription_id, name, effects, dosage, side_effects, instructions
            FROM Prescriptions
            WHERE name = ?
        """
        print(f"Thực thi truy vấn: {query.replace('?', f"'{name}'")}")
        cursor.execute(query, name)
        row = cursor.fetchone()
        if row:
            prescription_ids.append(row.prescription_id)
            # Tách effects thành nhiều dòng nếu có ký tự |
            effect_lines = row.effects.split('|') if row.effects else ['']
            print(f"\n💊 Tên thuốc: {row.name}")
            print(f"🌟 Công dụng: {effect_lines[0]}")  # Dòng đầu tiên của effects
            if len(effect_lines) > 1:
                print(f"📋 Chỉ định: {effect_lines[1]}")  # Dòng thứ hai của effects (nếu có)
            print(f"💡 Liều dùng: {row.dosage}")  # Liều dùng
            print(f"⚠️ Tác dụng phụ: {row.side_effects}")  # Tác dụng phụ
            if row.instructions:  # Hiển thị instructions nếu có
                print(f"📜 Hướng dẫn: {row.instructions}")
            print(f"💊 Tên thuốc: {row.name}")  # Lặp lại name ở cuối
        else:
            print(f"\n⚠️ Không tìm thấy thông tin cho thuốc: {name}")
    except pyodbc.Error as e:
        print(f"Lỗi truy vấn thuốc {name}: {e}")

# 4. Kiểm tra tương tác thuốc
print("\n⚠️ Tương tác phát hiện:")
interactions_found = False
if prescription_ids:
    # Lấy drug_id tương ứng từ bảng Drug
    drug_id_map = {}
    for prescription_id in prescription_ids:
        cursor.execute("SELECT drug_id FROM Drug WHERE drug_name = (SELECT name FROM Prescriptions WHERE prescription_id = ?)", prescription_id)
        drug_id_row = cursor.fetchone()
        if drug_id_row:
            drug_id_map[prescription_id] = drug_id_row[0]

    # Kiểm tra tương tác
    for i in range(len(prescription_ids)):
        for j in range(i + 1, len(prescription_ids)):
            drug_id_1 = drug_id_map.get(prescription_ids[i])
            drug_id_2 = drug_id_map.get(prescription_ids[j])
            if drug_id_1 and drug_id_2 and drug_id_1 < drug_id_2:  # Đáp ứng CHECK (drug_id_1 < drug_id_2)
                try:
                    cursor.execute("""
                        SELECT interaction_description, severity
                        FROM Drug_interaction
                        WHERE (drug_id_1 = ? AND drug_id_2 = ?)
                    """, (drug_id_1, drug_id_2))
                    for row in cursor.fetchall():
                        interactions_found = True
                        print(f"- {row.interaction_description} (**{row.severity}**)")
                except pyodbc.Error as e:
                    print(f"Lỗi kiểm tra tương tác giữa {drug_id_1} và {drug_id_2}: {e}")

if not interactions_found:
    print("✅ Không phát hiện tương tác nguy hiểm giữa các thuốc đã nhập.")

# 5. Đóng kết nối
conn.close()