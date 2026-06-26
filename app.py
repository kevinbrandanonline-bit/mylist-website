import os

from flask import Flask, request, render_template_string
import google.genai as genai

# ---------------- INVENTORY ---------------- #

inventory = {

    "Paracetamol": {
        "stock": 20,
        "category": "Fever",
        "otc": True
    },

    "Ibuprofen": {
        "stock": 12,
        "category": "Pain",
        "otc": True
    },

    "ORS": {
        "stock": 30,
        "category": "Hydration",
        "otc": True
    },

    "Bandage": {
        "stock": 50,
        "category": "First Aid",
        "otc": False
    }

}

# ---------------- FLASK ---------------- #

app = Flask(__name__)

# Gemini Client

client = genai.Client(
    api_key=os.environ["AQ.Ab8RN6I5rWvsKrqv0Rvxh4PiZraYY9CrHxR-sIyWd1iokKrpkQ"]
)

# ---------------- HTML ---------------- #

HTML = """

<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>MediStock AI</title>

<style>

*{
    margin:0;
    padding:0;
    box-sizing:border-box;
    font-family:Arial, Helvetica, sans-serif;
}

body{

    background:linear-gradient(135deg,#0f172a,#1e293b);

    color:white;

    display:flex;
    justify-content:center;
    align-items:center;

    min-height:100vh;

}

.container{

    width:700px;

    background:#1e293b;

    padding:35px;

    border-radius:20px;

    box-shadow:0 0 30px rgba(0,0,0,.5);

}

h1{

    text-align:center;

    color:#22c55e;

    margin-bottom:10px;

}

.subtitle{

    text-align:center;

    color:#cbd5e1;

    margin-bottom:30px;

}

textarea{

    width:100%;

    height:130px;

    padding:15px;

    border:none;

    border-radius:12px;

    resize:none;

    font-size:17px;

    margin-bottom:20px;

}

button{

    width:100%;

    padding:15px;

    border:none;

    border-radius:12px;

    font-size:18px;

    font-weight:bold;

    cursor:pointer;

    color:white;

    background:linear-gradient(90deg,#22c55e,#eab308);

    transition:.3s;

}

button:hover{

    transform:scale(1.02);

}

.result{

    margin-top:30px;

    background:#334155;

    padding:20px;

    border-radius:15px;

}

.result h2{

    color:#facc15;

    margin-bottom:15px;

}

hr{

    margin:15px 0;

    border:1px solid #475569;

}

.warning{

    margin-top:20px;

    color:#fbbf24;

    font-size:14px;

}

</style>

</head>

<body>

<div class="container">

<h1>🏥 MediStock AI</h1>

<p class="subtitle">

AI Powered Pharmacy Assistant 🚀 Version 1123
</p>
<form action="/analyze" method="POST">

<textarea

name="symptoms"

placeholder="Example: I have headache, fever and sore throat..."

required></textarea>

<button type="submit">

🧠 Analyze Symptoms

</button>

</form>

{% if result %}

<div class="result">

<h2>📋 Your Symptoms</h2>

<p>{{ symptoms }}</p>

<hr>

<h2>🤖 AI Recommendation</h2>

<p>{{ result }}</p>

<p class="warning">

⚠ This AI provides educational information only.
It is not a substitute for professional medical advice.

</p>

</div>

{% endif %}

</div>

</body>

</html>

"""

# ---------------- HOME PAGE ---------------- #

@app.route("/")
def home():

    return render_template_string(
        HTML,
        symptoms="",
        result=None
    )


# ---------------- ANALYZE ---------------- #

@app.route("/analyze", methods=["POST"])
def analyze():

    symptoms = request.form["symptoms"]

    inventory_text = ""

    for medicine, info in inventory.items():

        inventory_text += (
            f"{medicine} | "
            f"Stock: {info['stock']} | "
            f"Category: {info['category']} | "
            f"OTC: {info['otc']}\n"
        )

    print("\n========== INVENTORY ==========")
    print(inventory_text)

    prompt = f"""
You are MediStock AI.

You are NOT a doctor.

You are an AI assistant that helps pharmacists.

Patient Symptoms:
{symptoms}

Current Pharmacy Inventory:

{inventory_text}

Rules:

1. Never diagnose diseases.

2. Only recommend medicines that exist in the inventory.

3. Never recommend medicines whose stock is 0.

4. Mention the available stock.

5. If symptoms indicate an emergency such as:
- Chest pain
- Difficulty breathing
- Severe bleeding
- Loss of consciousness
- Very high fever
- Seizures

Immediately advise visiting the nearest hospital.

Do NOT recommend medicines for emergency cases.
6. Keep the response under 120 words.

7. Finish with:

⚠ This is not a diagnosis.
Please consult a qualified healthcare professional.
"""

    print("\n========== PROMPT ==========")
    print(prompt)
    print("============================")

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        result = response.text

    except Exception as e:

        result = f"❌ Gemini Error:\n{e}"

    return render_template_string(
        HTML,
        symptoms=symptoms,
        result=result
    )
# ---------------- RUN ---------------- #

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port
    )