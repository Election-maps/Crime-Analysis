import os
import sqlite3
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

DB_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "crime_data.db")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = FastAPI(title="Police Crime Review & Analysis Portal", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def build_filter_clause(
    year: Optional[int] = None,
    month: Optional[str] = None,
    ps: Optional[str] = None,
    head: Optional[str] = None,
    sub_div: Optional[str] = None,
    gravity: Optional[str] = None,
    stage: Optional[str] = None,
    q: Optional[str] = None
):
    clauses = ["1=1"]
    params = []
    if year:
        clauses.append("year = ?")
        params.append(year)
    if month and month != "All":
        clauses.append("LOWER(month) = LOWER(?)")
        params.append(month)
    if ps and ps != "All":
        clauses.append("police_station = ?")
        params.append(ps)
    if head and head != "All":
        clauses.append("crime_head = ?")
        params.append(head)
    if sub_div and sub_div != "All":
        clauses.append("sub_division = ?")
        params.append(sub_div)
    if gravity and gravity != "All":
        clauses.append("gravity_type = ?")
        params.append(gravity)
    if stage and stage != "All":
        clauses.append("stage = ?")
        params.append(stage)
    if q and q.strip():
        term = f"%{q.strip()}%"
        clauses.append("(fir_no LIKE ? OR brief LIKE ? OR io_name LIKE ? OR acts_sec LIKE ?)")
        params.extend([term, term, term, term])
    return " AND ".join(clauses), params

@app.get("/api/filters")
def get_filters():
    if not os.path.exists(DB_FILE):
        return {"police_stations": [], "crime_heads": [], "years": [], "sub_divisions": [], "months": []}
    with get_db() as conn:
        cursor = conn.cursor()
        
        ps_list = [r[0] for r in cursor.execute("SELECT DISTINCT police_station FROM crime_records WHERE police_station != '' ORDER BY police_station").fetchall()]
        head_list = [r[0] for r in cursor.execute("SELECT DISTINCT crime_head FROM crime_records WHERE crime_head != '' ORDER BY crime_head").fetchall()]
        years = [r[0] for r in cursor.execute("SELECT DISTINCT year FROM crime_records WHERE year > 1990 ORDER BY year DESC").fetchall()]
        sub_divisions = [r[0] for r in cursor.execute("SELECT DISTINCT sub_division FROM crime_records WHERE sub_division != '' ORDER BY sub_division").fetchall()]
        stages = [r[0] for r in cursor.execute("SELECT DISTINCT stage FROM crime_records WHERE stage != '' ORDER BY stage").fetchall()]
        gravity_types = [r[0] for r in cursor.execute("SELECT DISTINCT gravity_type FROM crime_records WHERE gravity_type != '' ORDER BY gravity_type").fetchall()]
        
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        
        return {
            "police_stations": ps_list,
            "crime_heads": head_list,
            "years": years,
            "sub_divisions": sub_divisions,
            "stages": stages,
            "gravity_types": gravity_types,
            "months": months
        }

@app.get("/api/kpis")
def get_kpis(
    year: Optional[int] = None,
    month: Optional[str] = None,
    ps: Optional[str] = None,
    head: Optional[str] = None,
    sub_div: Optional[str] = None,
    gravity: Optional[str] = None
):
    if not os.path.exists(DB_FILE):
        return {"total": 0, "ui": 0, "chargesheeted": 0, "disposed": 0, "cs_rate": 0, "disp_rate": 0}
        
    where, params = build_filter_clause(year, month, ps, head, sub_div, gravity)
    with get_db() as conn:
        cursor = conn.cursor()
        
        sql = f"""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN LOWER(stage) LIKE '%ui%' OR LOWER(stage) LIKE '%under invest%' THEN 1 ELSE 0 END) as ui_count,
            SUM(CASE WHEN LOWER(stage) LIKE '%charge%' OR LOWER(stage) LIKE '%pt%' OR (date_of_charge != '' AND date_of_charge != '0') THEN 1 ELSE 0 END) as cs_count,
            SUM(CASE WHEN (police_disposal_date != '' AND police_disposal_date != '0') OR (disposal_type != '' AND disposal_type != '0') OR LOWER(stage) LIKE '%dispos%' THEN 1 ELSE 0 END) as police_disp_count,
            SUM(CASE WHEN court_disposal != '' AND court_disposal != '0' THEN 1 ELSE 0 END) as court_disp_count,
            SUM(CASE WHEN LOWER(gravity_type) LIKE '%grave%' AND LOWER(gravity_type) NOT LIKE '%non%' THEN 1 ELSE 0 END) as grave_count,
            SUM(CASE WHEN LOWER(gravity_type) LIKE '%non%' THEN 1 ELSE 0 END) as non_grave_count,
            SUM(CASE WHEN days_pending > 365 THEN 1 ELSE 0 END) as long_pending_count
        FROM crime_records
        WHERE {where}
        """
        row = cursor.execute(sql, params).fetchone()
        
        total = row["total"] or 0
        ui = row["ui_count"] or 0
        cs = row["cs_count"] or 0
        p_disp = row["police_disp_count"] or 0
        c_disp = row["court_disp_count"] or 0
        grave = row["grave_count"] or 0
        non_grave = row["non_grave_count"] or 0
        long_pending = row["long_pending_count"] or 0
        
        cs_rate = round((cs / total * 100), 1) if total > 0 else 0
        disp_rate = round(((p_disp + c_disp) / total * 100), 1) if total > 0 else 0
        
        return {
            "total": total,
            "ui": ui,
            "chargesheeted": cs,
            "police_disposed": p_disp,
            "court_disposed": c_disp,
            "cs_rate": cs_rate,
            "disp_rate": disp_rate,
            "grave": grave,
            "non_grave": non_grave,
            "long_pending": long_pending
        }

@app.get("/api/trends")
def get_trends(
    year: Optional[int] = None,
    ps: Optional[str] = None,
    head: Optional[str] = None,
    sub_div: Optional[str] = None
):
    where, params = build_filter_clause(year, None, ps, head, sub_div)
    with get_db() as conn:
        cursor = conn.cursor()
        
        if year:
            # Monthly trend for the year
            sql = f"""
            SELECT month, COUNT(*) as cnt,
                   SUM(CASE WHEN LOWER(stage) LIKE '%charge%' OR LOWER(stage) LIKE '%pt%' OR (date_of_charge != '' AND date_of_charge != '0') THEN 1 ELSE 0 END) as cs_cnt,
                   SUM(CASE WHEN LOWER(stage) LIKE '%ui%' THEN 1 ELSE 0 END) as ui_cnt
            FROM crime_records
            WHERE {where} AND month != ''
            GROUP BY month
            """
            rows = cursor.execute(sql, params).fetchall()
            month_order = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
            data_map = {r["month"].strip().lower(): r for r in rows}
            
            labels = []
            totals = []
            cs_list = []
            ui_list = []
            for m in month_order:
                m_title = m.capitalize()
                labels.append(m_title)
                if m in data_map:
                    totals.append(data_map[m]["cnt"])
                    cs_list.append(data_map[m]["cs_cnt"])
                    ui_list.append(data_map[m]["ui_cnt"])
                else:
                    totals.append(0)
                    cs_list.append(0)
                    ui_list.append(0)
            return {"type": "monthly", "labels": labels, "totals": totals, "chargesheeted": cs_list, "ui": ui_list}
        else:
            # Yearly trend
            sql = f"""
            SELECT year, COUNT(*) as cnt,
                   SUM(CASE WHEN LOWER(stage) LIKE '%charge%' OR LOWER(stage) LIKE '%pt%' THEN 1 ELSE 0 END) as cs_cnt
            FROM crime_records
            WHERE {where} AND year > 1990
            GROUP BY year
            ORDER BY year ASC
            """
            rows = cursor.execute(sql, params).fetchall()
            return {
                "type": "yearly",
                "labels": [str(r["year"]) for r in rows],
                "totals": [r["cnt"] for r in rows],
                "chargesheeted": [r["cs_cnt"] for r in rows]
            }

@app.get("/api/stations")
def get_station_performance(
    year: Optional[int] = None,
    month: Optional[str] = None,
    head: Optional[str] = None,
    sub_div: Optional[str] = None
):
    where, params = build_filter_clause(year, month, None, head, sub_div)
    with get_db() as conn:
        cursor = conn.cursor()
        sql = f"""
        SELECT 
            police_station,
            sub_division,
            COUNT(*) as total,
            SUM(CASE WHEN LOWER(stage) LIKE '%ui%' THEN 1 ELSE 0 END) as ui,
            SUM(CASE WHEN LOWER(stage) LIKE '%charge%' OR LOWER(stage) LIKE '%pt%' OR (date_of_charge != '' AND date_of_charge != '0') THEN 1 ELSE 0 END) as cs,
            SUM(CASE WHEN (police_disposal_date != '' AND police_disposal_date != '0') OR (disposal_type != '' AND disposal_type != '0') THEN 1 ELSE 0 END) as disp,
            SUM(CASE WHEN days_pending > 365 THEN 1 ELSE 0 END) as long_pending
        FROM crime_records
        WHERE {where} AND police_station != ''
        GROUP BY police_station
        ORDER BY total DESC
        """
        rows = cursor.execute(sql, params).fetchall()
        result = []
        for r in rows:
            tot = r["total"]
            cs = r["cs"]
            cs_rate = round((cs / tot * 100), 1) if tot > 0 else 0
            disp_rate = round((r["disp"] / tot * 100), 1) if tot > 0 else 0
            result.append({
                "station": r["police_station"],
                "sub_division": r["sub_division"],
                "total": tot,
                "ui": r["ui"],
                "chargesheeted": cs,
                "disposed": r["disp"],
                "long_pending": r["long_pending"],
                "cs_rate": cs_rate,
                "disp_rate": disp_rate
            })
        return result

@app.get("/api/crime-heads")
def get_crime_heads(
    year: Optional[int] = None,
    month: Optional[str] = None,
    ps: Optional[str] = None,
    sub_div: Optional[str] = None,
    limit: int = 15
):
    where, params = build_filter_clause(year, month, ps, None, sub_div)
    with get_db() as conn:
        cursor = conn.cursor()
        sql = f"""
        SELECT 
            crime_head,
            COUNT(*) as total,
            SUM(CASE WHEN LOWER(stage) LIKE '%ui%' THEN 1 ELSE 0 END) as ui,
            SUM(CASE WHEN LOWER(stage) LIKE '%charge%' OR LOWER(stage) LIKE '%pt%' THEN 1 ELSE 0 END) as cs
        FROM crime_records
        WHERE {where} AND crime_head != ''
        GROUP BY crime_head
        ORDER BY total DESC
        LIMIT {limit}
        """
        rows = cursor.execute(sql, params).fetchall()
        return [
            {
                "crime_head": r["crime_head"],
                "total": r["total"],
                "ui": r["ui"],
                "chargesheeted": r["cs"],
                "cs_rate": round((r["cs"] / r["total"] * 100), 1) if r["total"] > 0 else 0
            }
            for r in rows
        ]

@app.get("/api/pendency")
def get_pendency_analytics(
    year: Optional[int] = None,
    month: Optional[str] = None,
    ps: Optional[str] = None,
    head: Optional[str] = None
):
    where, params = build_filter_clause(year, month, ps, head)
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Age brackets
        sql_brackets = f"""
        SELECT 
            SUM(CASE WHEN days_pending <= 60 THEN 1 ELSE 0 END) as under_60,
            SUM(CASE WHEN days_pending > 60 AND days_pending <= 90 THEN 1 ELSE 0 END) as b_60_90,
            SUM(CASE WHEN days_pending > 90 AND days_pending <= 180 THEN 1 ELSE 0 END) as b_90_180,
            SUM(CASE WHEN days_pending > 180 AND days_pending <= 365 THEN 1 ELSE 0 END) as b_180_365,
            SUM(CASE WHEN days_pending > 365 THEN 1 ELSE 0 END) as over_365
        FROM crime_records
        WHERE {where} AND (LOWER(stage) LIKE '%ui%' OR LOWER(stage) LIKE '%under%')
        """
        row_b = cursor.execute(sql_brackets, params).fetchone()
        
        # Reasons for UI
        sql_reasons = f"""
        SELECT reason_ui, COUNT(*) as cnt
        FROM crime_records
        WHERE {where} AND reason_ui != '' AND reason_ui != '0'
        GROUP BY reason_ui
        ORDER BY cnt DESC
        LIMIT 8
        """
        reasons = cursor.execute(sql_reasons, params).fetchall()
        
        return {
            "brackets": {
                "< 60 Days": row_b["under_60"] or 0,
                "60 - 90 Days": row_b["b_60_90"] or 0,
                "90 - 180 Days": row_b["b_90_180"] or 0,
                "180 - 365 Days": row_b["b_180_365"] or 0,
                "> 1 Year": row_b["over_365"] or 0
            },
            "reasons": [{"reason": r["reason_ui"], "count": r["cnt"]} for r in reasons]
        }

@app.get("/api/cases")
def get_cases(
    year: Optional[int] = None,
    month: Optional[str] = None,
    ps: Optional[str] = None,
    head: Optional[str] = None,
    sub_div: Optional[str] = None,
    gravity: Optional[str] = None,
    stage: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 25
):
    where, params = build_filter_clause(year, month, ps, head, sub_div, gravity, stage, q)
    offset = (page - 1) * page_size
    with get_db() as conn:
        cursor = conn.cursor()
        
        count_sql = f"SELECT COUNT(*) as total FROM crime_records WHERE {where}"
        total_records = cursor.execute(count_sql, params).fetchone()["total"]
        
        data_sql = f"""
        SELECT id, s_no, sub_division, circle, io_name, police_station, fir_no,
               acts_sec, fir_date, month, year, crime_head, sub_head,
               gravity_type, stage, court_disposal, police_disposal_date,
               disposal_type, reason_ui, brief, days_pending, timeline, motive
        FROM crime_records
        WHERE {where}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """
        rows = cursor.execute(data_sql, params + [page_size, offset]).fetchall()
        
        items = [dict(r) for r in rows]
        return {
            "total": total_records,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_records + page_size - 1) // page_size if page_size > 0 else 1,
            "items": items
        }

# Serve Frontend static assets
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Crime Review API is active. Frontend is loading..."}
