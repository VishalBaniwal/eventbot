from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
import logging

app = Flask(__name__, static_folder="static")
CORS(app)

logging.basicConfig(level=logging.INFO)

genai.configure(api_key="AIzaSyAmmMFrrGzfCkgAnJogp5K2sSbIuWFX5JM")
model = genai.GenerativeModel("gemini-2.0-flash")

knowledge_base = {
    "planning": {
        "timeline": {"small": "1-3 months", "large": "6-12 months"},
        "checklist": ["Set a budget", "Choose a venue", "Plan catering", "Send invites", "Hire staff"]
    },
    "staff_ratio": {"low": 15, "high": 10}
}

currency_symbols = {
    "$": "USD", "usd": "USD", "inr": "INR", "₹": "INR", "€": "EUR", "eur": "EUR", "£": "GBP", "gbp": "GBP"
}

def detect_currency(text):
    for symbol, currency in currency_symbols.items():
        if symbol.lower() in text.lower():
            return currency
    return "USD"

def convert_budget(guest_count, currency):
    rates = {"USD": 1, "INR": 83, "EUR": 0.93, "GBP": 0.79}
    base_low = guest_count * 75
    base_high = guest_count * 150
    rate = rates.get(currency.upper(), 1)
    converted_low = int(base_low * rate)
    converted_high = int(base_high * rate)
    return f"{converted_low:,} - {converted_high:,} {currency.upper()}"

def get_response(query):
    query = query.lower().strip()

    if any(greet in query for greet in ["hi", "hello", "how are you", "hey"]):
        return "Hey there! I'm here to help you with event planning. What would you like to know?"

    guest_count = 0
    guest_match = re.search(r"(\d+)\s*(guests|people|attendees)?", query)
    if guest_match:
        guest_count = int(guest_match.group(1))

    currency = detect_currency(query)

    if "budget" in query or "cost" in query:
        if guest_count:
            return f"For {guest_count} guests, your estimated budget is {convert_budget(guest_count, currency)}."
        else:
            return "Please tell me how many guests you’re expecting, and I’ll provide a budget estimate!"

    if "timeline" in query:
        return "For a small event, plan 1-3 months ahead. For a large one, 6-12 months is ideal."

    if "staff" in query:
        if guest_count:
            low = guest_count // knowledge_base["staff_ratio"]["low"]
            high = guest_count // knowledge_base["staff_ratio"]["high"]
            return f"For {guest_count} guests, you'll need approximately {low}-{high} staff members."
        else:
            return "Typically, you need 1 staff member for every 10-15 guests."

    prompt = f"You are an event assistant. Answer concisely: {query}"
    try:
        response = model.generate_content([prompt])
        return response.text.strip()
    except Exception as e:
        logging.error(f"Error generating response: {e}")
        return "I'm sorry, but I couldn't process your request at the moment. Please try again later."

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    history = data.get("history", [])
    query = data.get("query", "")

    # Construct context-aware prompt
    context = ""
    for msg in history:
        role = "User" if msg["sender"] == "user" else "Bot"
        context += f"{role}: {msg['message']}\n"

    prompt = f"{context}User: {query}\nBot:"

    try:
        response = model.generate_content(prompt)
        reply = response.text.strip()
        return jsonify({"response": reply})
    except Exception as e:
        return jsonify({"response": "Sorry, I couldn't process that."})
if __name__ == "__main__":
    app.run(debug=True)
