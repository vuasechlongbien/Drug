import pyodbc
from fuzzywuzzy import fuzz
import re
import requests
from bs4 import BeautifulSoup

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


# 2. Hàm chuẩn hóa văn bản
def normalize_text(text):
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)  # Xóa dấu cách thừa
    return text


# 3. Từ điển ánh xạ triệu chứng tiếng Việt sang tiếng Anh
symptom_translation = {
    "đau bụng": "abdominal pain",
    "đau đầu": "headache",
    "buồn nôn": "nausea",
    "chóng mặt": "dizziness",
    "đau chim": "penile pain",
    "đau vùng kín": "genital pain",
    "sốt": "fever",
    "ho": "cough",
    "đau ngực": "chest pain",
    "đau ngực khi thở": "chest pain",
    "đau họng": "sore throat"
}


# 4. Hàm tìm triệu chứng gần đúng
def find_closest_disease(symptom, cursor, threshold=80):
    cursor.execute("SELECT name FROM Diseases")
    diseases = [row.name.lower() for row in cursor.fetchall()]
    symptom = normalize_text(symptom)

    best_match = None
    highest_score = 0
    for disease in diseases:
        score = fuzz.ratio(symptom, disease)
        if score > highest_score and score >= threshold:
            highest_score = score
            best_match = disease
    return best_match


# 5. Hàm tìm kiếm trên Drugs.com
def search_drugs_com(symptom_en):
    try:
        url = f"https://www.drugs.com/condition/{symptom_en.replace(' ', '-')}.html"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        drug_elements = soup.select("div.contentBox a[href*='/mtm/']")

        if not drug_elements:
            return []

        drugs = []
        for elem in drug_elements[:3]:
            drug_name = elem.text.strip()
            drug_url = "https://www.drugs.com" + elem['href']
            drug_details = fetch_drug_details(drug_url, source="drugs.com")
            drugs.append({"name": drug_name, **drug_details})
        return drugs
    except requests.RequestException:
        return []


# 6. Hàm tìm kiếm trên MedlinePlus
def search_medlineplus(symptom_en):
    try:
        url = f"https://medlineplus.gov/ency/article/003094.htm"  # Trang chung về chest pain
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()

        drugs = [
            {"name": "Aspirin", "url": "https://medlineplus.gov/druginfo/meds/a682878.html"},
            {"name": "Nitroglycerin", "url": "https://medlineplus.gov/druginfo/meds/a601086.html"}
        ]

        result = []
        for drug in drugs[:3]:
            drug_details = fetch_drug_details(drug["url"], source="medlineplus")
            result.append({"name": drug["name"], **drug_details})
        return result
    except requests.RequestException:
        return []


# 7. Hàm tìm kiếm web tổng hợp
def search_web_for_symptom(symptom):
    symptom = normalize_text(symptom)
    symptom_en = symptom_translation.get(symptom, None)
    if not symptom_en:
        print(
            f"\n📡 Không nhận diện được triệu chứng '{symptom}' trong từ điển. Có thể thuật ngữ chưa chuẩn. Thử nhập lại (ví dụ: 'đau ngực khi thở' thay cho 'đau ngực') hoặc tham khảo bác sĩ.")
        return []

    # Thử Drugs.com trước
    drugs = search_drugs_com(symptom_en)
    source = "Drugs.com"

    # Nếu Drugs.com thất bại, thử MedlinePlus
    if not drugs:
        drugs = search_medlineplus(symptom_en)
        source = "MedlinePlus"

    if not drugs:
        print(
            f"\n📡 Không tìm thấy gợi ý thuốc cho '{symptom}' ({symptom_en}) trên {source}. Triệu chứng này có thể cần chẩn đoán cụ thể. Thử nhập 'đau ngực khi thở' hoặc tham khảo bác sĩ.")
        return []

    print(f"\n📡 Gợi ý từ {source} cho '{symptom}' ({symptom_en}):")
    for drug in drugs:
        print(f"\n💊 Tên thuốc: {drug['name']}")
        if drug.get("uses"):
            print(f"🌟 Công dụng: {drug['uses']}")
        if drug.get("dosage"):
            print(f"💡 Liều dùng: {drug['dosage']}")
        if drug.get("side_effects"):
            print(f"⚠️ Tác dụng phụ: {drug['side_effects']}")
        if drug.get("instructions"):
            print(f"📜 Hướng dẫn: {drug['instructions']}")
        print("(Tham khảo bác sĩ trước khi dùng)")

    # Lưu ý đặc biệt cho đau ngực
    if symptom == "đau ngực":
        print(
            "\n⚠️ Lưu ý: Đau ngực có thể liên quan đến các vấn đề nghiêm trọng như đau tim hoặc viêm phổi. Hãy gọi cấp cứu nếu đau dữ dội, kèm khó thở, hoặc đau lan tỏa.")

    return drugs


# 8. Hàm lấy chi tiết thuốc
def fetch_drug_details(drug_url, source):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(drug_url, headers=headers, timeout=5)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        details = {}

        if source == "drugs.com":
            uses_section = soup.find("h2", id="uses")
            details["uses"] = uses_section.find_next("p").text.strip()[
                              :200] + "..." if uses_section and uses_section.find_next("p") else "Không có thông tin."

            dosage_section = soup.find("h2", id="dosage")
            details["dosage"] = dosage_section.find_next("p").text.strip()[
                                :200] + "..." if dosage_section and dosage_section.find_next(
                "p") else "Không có thông tin."

            side_effects_section = soup.find("h2", id="side-effects")
            details["side_effects"] = side_effects_section.find_next("p").text.strip()[
                                      :200] + "..." if side_effects_section and side_effects.find_next(
                "p") else "Không có thông tin."

            instructions_section = soup.find("h2", id="precautions")
            details["instructions"] = instructions_section.find_next("p").text.strip()[
                                      :200] + "..." if instructions_section and instructions_section.find_next(
                "p") else "Không có thông tin."

        elif source == "medlineplus":
            # Sửa DeprecationWarning: dùng 'string' thay vì 'text'
            uses_section = soup.find("h2", string="Why is this medication prescribed?")
            details["uses"] = uses_section.find_next("p").text.strip()[
                              :200] + "..." if uses_section and uses_section.find_next("p") else "Không có thông tin."

            dosage_section = soup.find("h2", string="How should this medicine be used?")
            details["dosage"] = dosage_section.find_next("p").text.strip()[
                                :200] + "..." if dosage_section and dosage_section.find_next(
                "p") else "Không có thông tin."

            side_effects_section = soup.find("h2", string="What side effects can this medication cause?")
            details["side_effects"] = side_effects_section.find_next("p").text.strip()[
                                      :200] + "..." if side_effects_section and side_effects_section.find_next(
                "p") else "Không có thông tin."

            # Cải thiện trích xuất hướng dẫn
            instructions_section = soup.find("h2",
                                             string="What should I know about storage and disposal of this medication?")
            details["instructions"] = instructions_section.find_next("p").text.strip()[
                                      :200] + "..." if instructions_section and instructions_section.find_next(
                "p") else "Không có thông tin."

        return details
    except requests.RequestException:
        return {"uses": "Không có thông tin.", "dosage": "Không có thông tin.",
                "side_effects": "Không có thông tin.", "instructions": "Không có thông tin."}


# 9. Hàm lấy thuốc khuyến cáo dựa trên triệu chứng
def recommend_medicines(symptom, cursor):
    symptom = normalize_text(symptom)

    # Tìm bệnh lý khớp chính xác
    query = """
        SELECT disease_id, name
        FROM Diseases
        WHERE LOWER(name) = ?
    """
    cursor.execute(query, symptom)
    disease_row = cursor.fetchone()

    if not disease_row:
        # Nếu không khớp chính xác, tìm khớp gần đúng
        closest_disease = find_closest_disease(symptom, cursor)
        if closest_disease:
            print(f"Không tìm thấy chính xác '{symptom}', có phải bạn muốn nói '{closest_disease}'?")
            cursor.execute(query, closest_disease)
            disease_row = cursor.fetchone()
        else:
            print(f"⚠️ Không tìm thấy bệnh lý cho triệu chứng '{symptom}' trong cơ sở dữ liệu.")
            # Tìm kiếm web
            external_drugs = search_web_for_symptom(symptom)
            return [] if not external_drugs else []  # Trả về rỗng vì không kiểm tra tương tác

    disease_id, disease_name = disease_row
    print(f"\n🔍 Triệu chứng: {disease_name}")

    # Lấy danh sách thuốc từ bảng Prescription_Disease
    query = """
        SELECT p.prescription_id, p.name, p.effects, p.dosage, p.side_effects, p.instructions
        FROM Prescriptions p
        JOIN Prescription_Disease pd ON p.prescription_id = pd.prescription_id
        WHERE pd.disease_id = ?
    """
    cursor.execute(query, disease_id)
    medicines = cursor.fetchall()

    if not medicines:
        print("⚠️ Không tìm thấy thuốc khuyến cáo cho triệu chứng này.")
        return []

    print("\n💊 Thuốc khuyến cáo:")
    prescription_ids = []
    for row in medicines:
        prescription_ids.append(row.prescription_id)
        effect_lines = row.effects.split('|') if row.effects else ['']
        print(f"\n💊 Tên thuốc: {row.name}")
        print(f"🌟 Công dụng: {effect_lines[0]}")
        if len(effect_lines) > 1:
            print(f"📋 Chỉ định: {effect_lines[1]}")
        print(f"💡 Liều dùng: {row.dosage}")
        print(f"⚠️ Tác dụng phụ: {row.side_effects}")
        if row.instructions:
            print(f"📜 Hướng dẫn: {row.instructions}")

    return prescription_ids


# 10. Hàm kiểm tra tương tác thuốc
def check_drug_interactions(prescription_ids, cursor):
    print("\n⚠️ Tương tác phát hiện:")
    interactions_found = False
    if len(prescription_ids) < 2:
        print("✅ Chỉ có một thuốc được khuyến cáo, không cần kiểm tra tương tác.")
        return

    # Lấy drug_id tương ứng
    drug_id_map = {}
    for prescription_id in prescription_ids:
        cursor.execute(
            "SELECT drug_id FROM Drug WHERE drug_name = (SELECT name FROM Prescriptions WHERE prescription_id = ?)",
            prescription_id)
        drug_id_row = cursor.fetchone()
        if drug_id_row:
            drug_id_map[prescription_id] = drug_id_row[0]

    # Kiểm tra tương tác
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
        print("✅ Không phát hiện tương tác nguy hiểm giữa các thuốc khuyến cáo.")


# 11. Hàm chính
def main():
    print("Chương trình Hỗ trợ Mua Thuốc")
    symptom = input("\nNhập triệu chứng của bạn: ")
    prescription_ids = recommend_medicines(symptom, cursor)
    if prescription_ids:
        check_drug_interactions(prescription_ids, cursor)


# 12. Chạy chương trình và đóng kết nối
if __name__ == "__main__":
    try:
        main()
    finally:
        conn.close()