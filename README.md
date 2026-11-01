# 🛡️ Police Crime Analysis & Investigation Review Portal

A high-performance Crime Analysis, Charge-Sheet Monitoring, and Investigation Review Web Application built with **FastAPI**, **SQLite**, and modern frontend visualization tools (**Tailwind CSS**, **Chart.js**).

---

## 🚀 Key Features

- **Executive Command Dashboard**: Real-time KPI metrics across 68,000+ cases (Reported, Under Investigation, Charge-Sheeted, Police & Court Disposals, CS rates).
- **Interactive Trends**: Monthly and yearly crime volume trajectories comparing reported vs. charge-sheeted cases.
- **Police Station Performance Matrix**: League table and analytics across 37 Police Stations with efficiency scoring.
- **Crime Head Analytics**: Deep dive into 50+ crime heads (BNS/IPC sections, Grave vs. Non-Grave, SC/ST, Property, Bodily crimes).
- **Pendency & UI Aging Monitor**: Investigation aging brackets (<60d, 60–90d, 90–180d, >1yr) and documented pendency reasons.
- **Live Case Explorer**: Real-time multi-filter case search with full case brief and investigation milestone modal.
- **One-Click Export**: Export station performance and case review summaries to CSV/Excel.

---

## 🛠️ Project Structure

```
Crime-Review/
├── 1. Total Reported Cases.xlsx   # Source Crime dataset (68k+ records)
├── run_server.py                  # Server launcher with auto-ingestion
├── start.bat                      # 1-click batch launcher for Windows
├── start.ps1                      # PowerShell launcher
├── requirements.txt               # Python package dependencies
├── .gitignore
├── README.md
├── backend/
│   ├── api.py                     # FastAPI REST API endpoints
│   └── ingest.py                  # Excel to SQLite high-speed ingestion engine
├── frontend/
│   ├── index.html                 # Main dashboard UI
│   └── app.js                     # Dynamic data binding & charts
└── data/
    └── crime_data.db              # High-speed indexed SQLite database (auto-created)
```

---

## ⚡ Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Server
* **PowerShell**:
  ```powershell
  .\start.ps1
  ```
* **Command Prompt / Windows**:
  ```cmd
  start.bat
  ```
* **Python Direct**:
  ```bash
  python run_server.py
  ```

### 3. Open in Browser
Navigate to:
```
http://localhost:8000
```
