import pyodbc
import re

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

# 2. Nhập tên thuốc và liều lượng trên nhiều dòng
print("Nhập danh sách thuốc")
lines = []
while True:
    line = input()
    if line.strip() == "":
        break
    lines.append(line)

# Xử lý các dòng đầu vào
drug_names = []
dosages = []
for line in lines:
    # Loại bỏ dấu đầu dòng (nếu có)
    cleaned_line = re.sub(r'^\s*-\s*', '', line).strip()
    if cleaned_line:
        # Tách tên thuốc và liều lượng với dấu "—"
        match = re.match(r'^\s*([^\—]+?)\s*(?:\—\s*(.+))?$', cleaned_line)
        if match:
            drug_name = match.group(1).strip()
            dosage = match.group(2).strip() if match.group(2) else None
            drug_names.append(drug_name)
            dosages.append(dosage)
        else:
            drug_names.append(cleaned_line.strip())
            dosages.append(None)

# 3. Lấy thông tin từng thuốc từ bảng Prescriptions
print("\n🔍 Thông tin thuốc:")
prescription_ids = []
for name, dosage in zip(drug_names, dosages):
    try:
        query = """
            SELECT prescription_id, name, effects, dosage, side_effects, instructions
            FROM Prescriptions
            WHERE name = ?
        """
        cursor.execute(query, name)
        row = cursor.fetchone()
        if row:
            prescription_ids.append(row.prescription_id)
            effect_lines = row.effects.split('|') if row.effects else ['']
            print(f"\n💊 Tên thuốc: {row.name}")
            print(f"🌟 Công dụng: {effect_lines[0]}")
            if len(effect_lines) > 1:
                print(f"📋 Chỉ định: {effect_lines[1]}")
            print(f"💡 Liều dùng khuyến cáo: {row.dosage}")
            if dosage:
                print(f"💉 Liều nhập vào: {dosage}")
                # Chuẩn hóa liều lượng để so sánh
                input_dosage = dosage.lower().replace(' ', '')
                recommended_dosage = row.dosage.lower().replace(' ', '')
                if input_dosage != recommended_dosage:
                    print(f"⚠️ Cảnh báo: Liều nhập vào ({dosage}) khác với liều khuyến cáo ({row.dosage})")
            print(f"⚠️ Tác dụng phụ: {row.side_effects}")
            if row.instructions:
                print(f"📜 Hướng dẫn: {row.instructions}")
        else:
            print(f"\n⚠️ Không tìm thấy thông tin cho thuốc: {name}")
    except pyodbc.Error as e:
        print(f"Lỗi truy vấn thuốc {name}: {e}")

# 4. Kiểm tra tương tác thuốc
print("\n⚠️ Tương tác phát hiện:")
interactions_found = False
if prescription_ids:
    drug_id_map = {}
    for prescription_id in prescription_ids:
        cursor.execute("SELECT drug_id FROM Drugs WHERE drug_name = (SELECT name FROM Prescriptions WHERE prescription_id = ?)", prescription_id)
        drug_id_row = cursor.fetchone()
        if drug_id_row:
            drug_id_map[prescription_id] = drug_id_row[0]

    for i in range(len(prescription_ids)):
        for j in range(i + 1, len(prescription_ids)):
            drug_id_1 = drug_id_map.get(prescription_ids[i])
            drug_id_2 = drug_id_map.get(prescription_ids[j])
            if drug_id_1 and drug_id_2 and drug_id_1 < drug_id_2:
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