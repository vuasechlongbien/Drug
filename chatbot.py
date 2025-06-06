import google.generativeai as genai
import os

# === Cấu hình API KEY của bạn tại đây ===
API_KEY = "AIzaSyDf_uTNt8HzArhKqHBu7rrXb51Robz_QyI"  # ← thay bằng key của bạn

# === Cấu hình Gemini ===
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# === Hàm xử lý Gemini và TTS ===
def process_with_gemini_and_tts(prompt, mp3_filename="response.mp3"):
    full_prompt = ("Bạn hãy đóng vai 1 chuyên gia dược liệu hãy đưa ra lời khuyên ngắn gọn về những loại thuốc nên dùng nếu bị triệu chứng đi kèm với liều lượng và một chút thông tin (tác dụng, khuyến cáo chỉ định,..... , trả lời đúng trọng tâm và không nói gì thêm, không chào hỏi gì cả"
                   ) + prompt

    response = model.generate_content(full_prompt)
    reply_text = response.text.strip()

    print(f"\n: {reply_text}\n")

# === Chạy chatbot CLI ===
def main():
    print("=== Chatbot Gemini trên Terminal ===")
    while True:
        user_input = input("👤 Bạn: ")
        if user_input.lower() in ["exit", "quit"]:
            print("👋 Tạm biệt!")
            break
        process_with_gemini_and_tts(user_input)

if __name__ == "__main__":
    main()
