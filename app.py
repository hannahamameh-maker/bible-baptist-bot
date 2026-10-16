import os, google.generativeai as genai
from flask import Flask, request, jsonify

app = Flask(__name__)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-1.5-flash",
    system_instruction="أنت مساعد كتابي لكنيسة الكتاب المقدس المعمدانية - القدس. جاوب فقط من الكتاب المقدس KJV/فاندايك، عقيدة معمدانية، لا تفتي خارج الكتاب. جاوب بنفس لغة السؤال عربي أو انجليزي."
)

@app.route("/ask", methods=["POST"])
def ask():
    q = request.json.get("question","")
    resp = model.generate_content(q)
    return jsonify({"answer": resp.text})
