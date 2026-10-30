# 🎓 Scholarship Intelligence & Verification Engine (Atlas Funding)

An automated data pipeline designed to discover, extract, verify, and monitor authentic Indian higher-education scholarships (spanning Central Government, statutory bodies like AICTE/UGC, and reputable CSR initiatives).

Built with a strict **anti-hallucination sentinel strategy**, a **deterministic 100-point domain authority rubric**, and an **append-only SQLite change detection engine** to track evolving scheme guidelines without destructive overwrites.

---

## 🚀 Key Features

- **Deterministic 100-Point Scoring Engine:** Real-time classification (`VERIFIED` vs `REVIEW REQUIRED` at a 95% threshold) evaluating primary domains (`.gov.in`, `.nic.in`, `.ac.in`, official CSR), guideline citations, and criteria completeness.
- **Anti-Hallucination Guardrails:** Enforced Pydantic v2 schemas defaulting missing attributes strictly to `"Not specified"`, paired with raw circular quote traces (`raw_evidence_trace`).
- **Multi-Run Change Detection:** Dual-table persistence (`scholarships` vs `scholarship_history`) logging granular field mutations across crawler executions.
- **Interactive Streamlit Dashboard:** Live catalog with multi-attribute filtering, evidence inspection cards, and an audit trail viewer.

---

## 🛠️ Tech Stack

- **Language:** Python 3.12+
- **Data Validation & Schemas:** Pydantic v2
- **Persistence & Auditing:** SQLite3
- **Frontend / Visualization:** Streamlit, Pandas

---

## 📂 Project Structure

```text
├── data/
│   └── scholarships.db       # Dual-table SQLite database (current state & audit history)
├── docs/
│   └── technical_note.md     # Architectural writeup & system trade-offs
├── src/
│   ├── app.py                # Streamlit operational dashboard
│   ├── crawler.py            # Ingestion pipeline & multi-run simulation driver
│   ├── database.py           # Pydantic schemas, SQLite setup & change detection engine
│   └── verifier.py           # Domain authority checks & 100-point verification rubric
├── .env                      # Local environment configuration
├── .gitignore                # Files ignored by git
├── README.md                 # Project documentation
└── requirements.txt          # Production dependencies