# 🧾 Vendors & Items Index - Baly Food Task

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

### 📦 Item Comparison
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

## 📈 Future Improvements

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
[View on Streamlit Cloud](https://<your-app-link>.streamlit.app)  ← *(replace with actual link when deployed)*

---

## 👨‍💻 Author
**Kadhim Jasim**  
3rd-Year CS Student @ American University of Baghdad  
US Green Card Holder · Internship Candidate for Baly BI Team

---

## 📩 Contact
Feel free to reach out if you have any feedback or suggestions:
- Email: [kjasim98@gmail.com](mailto:kjasim98@gmail.com)
- GitHub: [kjasim98](https://github.com/kjasim98)

---

## 🏁 Status
✅ Initial version completed and delivered for evaluation by the Baly recruitment team.

---