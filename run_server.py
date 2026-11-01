import os
import sys
import webbrowser
import uvicorn

if __name__ == "__main__":
    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"

    db_path = os.path.join(os.path.dirname(__file__), "data", "crime_data.db")
    excel_path = os.path.join(os.path.dirname(__file__), "1. Total Reported Cases.xlsx")
    if not os.path.exists(db_path) and os.path.exists(excel_path):
        print("Database not found. Ingesting records from Excel file...")
        from backend.ingest import ingest
        ingest()
    print(f"\n=======================================================")
    print(f"  POLICE CRIME ANALYSIS & INVESTIGATION REVIEW SYSTEM  ")
    print(f"=======================================================")
    print(f"  [+] Starting Web Server at: {url}")
    print(f"  [+] Serving 68,206 Cases across 37 Police Stations")
    print(f"  [+] Press Ctrl+C in terminal to stop server")
    print(f"=======================================================\n")
    
    # Open browser automatically after a short moment
    try:
        webbrowser.open(url)
    except Exception:
        pass
        
    uvicorn.run("backend.api:app", host=host, port=port, reload=False, log_level="info")
