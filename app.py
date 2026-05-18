from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
import logging
import re

app = Flask(__name__, static_folder="static")
CORS(app)

logging.basicConfig(level=logging.INFO)

# Use a stable model name
genai.configure(api_key="AIzaSyCbypqy7FtG-YhgUTNXm7HEs4CR9rIVzy0")
model = genai.GenerativeModel("gemini-1.5-flash")

knowledge_base = {
    "planning": {
        "timeline": {"small": "1-3 months", "large": "6-12 months"},
        "checklist": ["Set a budget", "Choose a venue", "Plan catering", "Send invites", "Hire staff"]
    },
    "staff_ratio": {"low": 15, "high": 10}
}

currency_symbols = {
    "$": "USD", "usd": "USD", "inr": "INR", "₹": "INR",
    "€": "EUR", "eur": "EUR", "£": "GBP", "gbp": "GBP"
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

def get_response(query, history=None):
    query_lower = query.lower().strip()

    # Rule-based overrides
    if any(greet in query_lower for greet in ["hi", "hello", "how are you", "hey"]):
        return "Hey there! I'm here to help you with event planning. What would you like to know?"

    guest_count = 0
    guest_match = re.search(r"(\d+)\s*(guests|people|attendees)?", query_lower)
    if guest_match:
        guest_count = int(guest_match.group(1))

    currency = detect_currency(query_lower)

    if "budget" in query_lower or "cost" in query_lower:
        if guest_count:
            return f"For {guest_count} guests, your estimated budget is {convert_budget(guest_count, currency)}."
        return "Please tell me how many guests you're expecting, and I'll provide a budget estimate!"

    if "timeline" in query_lower:
        return "For a small event, plan 1-3 months ahead. For a large one, 6-12 months is ideal."

    if "staff" in query_lower:
        if guest_count:
            low = guest_count // knowledge_base["staff_ratio"]["low"]
            high = guest_count // knowledge_base["staff_ratio"]["high"]
            return f"For {guest_count} guests, you'll need approximately {low}-{high} staff members."
        return "Typically, you need 1 staff member for every 10-15 guests."

    # Gemini Fallback
    try:
        # Construct chat session
        chat = model.start_chat(history=[])
        if history:
            for msg in history:
                role = "user" if msg["sender"] == "user" else "model"
                chat.history.append({"role": role, "parts": [msg['message']]})
        
        response = chat.send_message(query)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Error generating response: {e}")
        return "I'm having trouble connecting to my planning brain. Please try again in a moment."

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    history = data.get("history", [])
    query = data.get("query", "")

    if not query:
        return jsonify({"response": "Please ask me something!"})

    reply = get_response(query, history)
    return jsonify({"response": reply})

if __name__ == "__main__":
    app.run(debug=True)