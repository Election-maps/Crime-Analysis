import os
import sys
import sqlite3
import time
from datetime import datetime
import openpyxl

EXCEL_FILE = os.path.join(os.path.dirname(__file__), "..", "1. Total Reported Cases.xlsx")
DB_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "crime_data.db")

def init_db(conn):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS crime_records")
    cursor.execute("""
    CREATE TABLE crime_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        s_no INTEGER,
        sub_division TEXT,
        circle TEXT,
        io_name TEXT,
        police_station TEXT,
        fir_no TEXT,
        acts_sec TEXT,
        fir_date TEXT,
        month TEXT,
        year INTEGER,
        crime_head TEXT,
        sub_head TEXT,
        crime_classification TEXT,
        act_type TEXT,
        gravity_type TEXT,
        date_of_charge TEXT,
        stage TEXT,
        court_disposal TEXT,
        police_disposal_date TEXT,
        disposal_type TEXT,
        reason_ui TEXT,
        brief TEXT,
        days_pending INTEGER,
        timeline TEXT,
        motive TEXT,
        cctns_head TEXT,
        finalized_year TEXT,
        finalized_month TEXT,
        cc_awaited TEXT
    )
    """)
    conn.commit()

def create_indexes(conn):
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX idx_ps ON crime_records(police_station)")
    cursor.execute("CREATE INDEX idx_year ON crime_records(year)")
    cursor.execute("CREATE INDEX idx_month ON crime_records(month)")
    cursor.execute("CREATE INDEX idx_head ON crime_records(crime_head)")
    cursor.execute("CREATE INDEX idx_stage ON crime_records(stage)")
    cursor.execute("CREATE INDEX idx_gravity ON crime_records(gravity_type)")
    cursor.execute("CREATE INDEX idx_sub_division ON crime_records(sub_division)")
    conn.commit()

def clean_val(v):
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v).strip()
    if s.lower() in ("none", "null", "n/a", "#n/a", "#ref!", "#value!", "0"):
        if s == "0":
            return s
        return ""
    return s

def clean_int(v, default=0):
    if v is None:
        return default
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return default

def ingest():
    print(f"Opening Excel file: {EXCEL_FILE}")
    start_time = time.time()
    
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    init_db(conn)
    cursor = conn.cursor()
    
    wb = openpyxl.load_workbook(EXCEL_FILE, read_only=True, data_only=True)
    sheet_name = "Total"
    if sheet_name not in wb.sheetnames:
        sheet_name = wb.sheetnames[0]
    ws = wb[sheet_name]
    print(f"Reading from sheet: {sheet_name}")

    rows_iter = ws.iter_rows(values_only=True)
    header = next(rows_iter, None)
    if not header:
        print("Error: Empty sheet")
        return

    # Map headers
    col_map = {}
    for idx, col in enumerate(header):
        if col:
            col_name = str(col).strip().lower()
            col_map[col_name] = idx

    print(f"Header fields count: {len(col_map)}")
    
    def get_c(row, *aliases):
        for a in aliases:
            a_lower = a.lower()
            if a_lower in col_map:
                idx = col_map[a_lower]
                if idx < len(row):
                    return row[idx]
        return None

    batch = []
    count = 0
    batch_size = 2000

    sql = """
    INSERT INTO crime_records (
        s_no, sub_division, circle, io_name, police_station, fir_no, acts_sec,
        fir_date, month, year, crime_head, sub_head, crime_classification,
        act_type, gravity_type, date_of_charge, stage, court_disposal,
        police_disposal_date, disposal_type, reason_ui, brief, days_pending,
        timeline, motive, cctns_head, finalized_year, finalized_month, cc_awaited
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    for row in rows_iter:
        fir_no = clean_val(get_c(row, "fir no", "fir_no", "firno"))
        ps = clean_val(get_c(row, "police station", "ps", "police_station", "merge ps names"))
        if not fir_no and not ps:
            continue

        s_no = clean_int(get_c(row, "s.no.", "s.no", "sno"))
        sub_div = clean_val(get_c(row, "sub-division", "sub division"))
        circle = clean_val(get_c(row, "cirlce", "circle"))
        io_name = clean_val(get_c(row, "i.o name", "io name", "io"))
        acts_sec = clean_val(get_c(row, "acts & sec", "acts and sec", "acts"))
        fir_dt = clean_val(get_c(row, "fir dt", "fir date", "fir_dt"))
        month = clean_val(get_c(row, "month"))
        year = clean_int(get_c(row, "year"), 0)
        crime_head = clean_val(get_c(row, "crime head", "head"))
        sub_head = clean_val(get_c(row, "sub-head", "sub head"))
        crime_class = clean_val(get_c(row, "crime classfication", "crime classification"))
        act_type = clean_val(get_c(row, "act type"))
        gravity_type = clean_val(get_c(row, "gravity type", "gravity"))
        date_charge = clean_val(get_c(row, "date of charge", "chargedate"))
        stage = clean_val(get_c(row, "stage"))
        court_disp = clean_val(get_c(row, "court disposal"))
        pol_disp_dt = clean_val(get_c(row, "date of police disposal"))
        disp_type = clean_val(get_c(row, "type of disposal", "disposal type"))
        reason_ui = clean_val(get_c(row, "reason for ui", "reason_ui"))
        brief = clean_val(get_c(row, "brief"))
        days_pending = clean_int(get_c(row, "no. of days", "number pending no of days", "days"), 0)
        timeline = clean_val(get_c(row, "time line", "timeline"))
        motive = clean_val(get_c(row, "motive"))
        cctns_head = clean_val(get_c(row, "cctns head"))
        fin_year = clean_val(get_c(row, "finalized year"))
        fin_month = clean_val(get_c(row, "finalized month"))
        cc_awaited = clean_val(get_c(row, "cc awaited"))

        batch.append((
            s_no, sub_div, circle, io_name, ps, fir_no, acts_sec,
            fir_dt, month, year, crime_head, sub_head, crime_class,
            act_type, gravity_type, date_charge, stage, court_disp,
            pol_disp_dt, disp_type, reason_ui, brief, days_pending,
            timeline, motive, cctns_head, fin_year, fin_month, cc_awaited
        ))

        count += 1
        if len(batch) >= batch_size:
            cursor.executemany(sql, batch)
            conn.commit()
            batch = []
            if count % 10000 == 0:
                print(f"Processed {count} records...")

    if batch:
        cursor.executemany(sql, batch)
        conn.commit()

    wb.close()
    print(f"Creating database indexes...")
    create_indexes(conn)
    conn.close()

    elapsed = time.time() - start_time
    print(f"Ingestion complete! Successfully imported {count} records in {elapsed:.2f} seconds.")

if __name__ == "__main__":
    ingest()
