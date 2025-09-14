# 🗞 Vendors & Items Index - Baly Food Task

This project was implemented as part of a coding assignment for **Baly** (Food BI Department). It is a data comparison tool designed to help business analysts and procurement teams compare vendor and product information between two companies.

---

## 📌 Objective

Build a user-friendly web dashboard where users can:

- ✅ View vendors that are matched between **Company 1** and **Company 2**
- ✅ See matched products across those vendors
- ✅ Compare product prices (higher/lower/same)
- ✅ Identify vendors offering **discounts**
- ✅ View summary KPIs (e.g., total matched vendors, item count, discount rates)

> 🧠 Additional insights like duplicated pricing and exclusive vendors are also included to improve business visibility.

---

## 🧱 Tech Stack

| Layer        | Technology         |
|--------------|--------------------|
| Frontend     | Streamlit (Python) |
| Backend/Data | pandas, RapidFuzz  |
| Deployment   | Streamlit Cloud    |
| Source Code  | GitHub             |

---

## 📂 Project Structure

```
baly-task/
├── app.py                  # Streamlit UI app
├── help.py                 # Utility functions (normalize, match, deduplicate)
├── company1.csv            # Input file for Company 1
├── company2.csv            # Input file for Company 2
├── requirements.txt        # Dependencies for deployment
├── .gitignore              # Ignore venv, pycache, etc.
└── README.md               # You're here 👋
```

---

## ⚙️ Features Implemented

### 🔍 Vendor Matching
- Vendor names are cleaned and fuzzy matched using `RapidFuzz`
- Matched vendors are indexed and displayed in a dropdown for exploration

### 🛆 Item Comparison
- Products matched by vendor + product name
- Price differences categorized: higher / lower / same

### 📊 KPIs Dashboard
- Total vendors per company
- Matched vendors
- Matched items
- Percent higher/lower/same pricing

### 🏷️ Discount Detector
- Highlights vendors with multiple price listings
- Helps identify where discounts may have been applied

---

## 📈 Problems Encountered & Solutions

### 1️⃣ Fuzzy Matching of Vendors and Products
A major challenge was matching vendor and product names between two companies when the names were slightly different. For example:
- `Bella Pasta Co. Group` vs `Bella Pasta Co.`
- `Basmati Rice 5Kg` vs `Basmati Rice 5000g`

To solve this, I implemented **normalization techniques** and used the **RapidFuzz** library, which is based on optimized fuzzy string matching algorithms like Levenshtein distance and token set ratio. This allowed for intelligent matching of similar but non-identical strings with adjustable thresholds.

### 2️⃣ Multiple Prices for the Same Product
Another challenge was when the same product appeared under the same vendor with multiple prices. I assumed:
- The **maximum price** is the original price
- Lower prices are considered **discounted offers**
- For simplicity, I only considered the minimum price as the discount price — even if more than two prices existed for the same product

I built a dedicated section in the dashboard to identify such items. The user can select any vendor and view:
- Which items were discounted
- What the original price was
- How much the discount was (absolute and percentage)


---

## 📊 Future Improvements

- Add file upload support for new CSVs
- Add user authentication to secure access
- Deploy backend as FastAPI + React (WIP)
- Store matched data to database for history tracking

---

## 🚀 How to Run Locally

1. Clone the repo:
```bash
git clone https://github.com/kjasim98/baly-task.git
cd baly-task
```

2. (Optional) Create a virtual environment:
```bash
python3 -m venv streamlit_env
source streamlit_env/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the app:
```bash
streamlit run app.py
```

---

## 🌐 Live Demo
[View on Streamlit Cloud](https://kjasim98-baly-task-app-srkx9g.streamlit.app/)

---

## 📩 Contact
Feel free to reach out if you have any feedback or suggestions:
- Email: [kjasim98@gmail.com](mailto:kjasim98@gmail.com)
- GitHub: [kjasim98](https://github.com/kjasim98)

---

## 🏑️ Status
✅ Initial version completed and delivered for evaluation by the Baly recruitment team.

---
