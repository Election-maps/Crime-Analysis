import sqlite3
import json
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "data", "crime_data.db")
out_dir = os.path.join(os.path.dirname(__file__), "..", "data_static")
os.makedirs(out_dir, exist_ok=True)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1. Filters
ps_list = [r[0] for r in cur.execute("SELECT DISTINCT police_station FROM crime_records WHERE police_station != '' ORDER BY police_station").fetchall()]
head_list = [r[0] for r in cur.execute("SELECT DISTINCT crime_head FROM crime_records WHERE crime_head != '' ORDER BY crime_head").fetchall()]
years = [r[0] for r in cur.execute("SELECT DISTINCT year FROM crime_records WHERE year > 1990 ORDER BY year DESC").fetchall()]
sub_divisions = [r[0] for r in cur.execute("SELECT DISTINCT sub_division FROM crime_records WHERE sub_division != '' ORDER BY sub_division").fetchall()]
stages = [r[0] for r in cur.execute("SELECT DISTINCT stage FROM crime_records WHERE stage != '' ORDER BY stage").fetchall()]
gravity_types = [r[0] for r in cur.execute("SELECT DISTINCT gravity_type FROM crime_records WHERE gravity_type != '' ORDER BY gravity_type").fetchall()]
months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

filters = {
    'police_stations': ps_list,
    'crime_heads': head_list,
    'years': years,
    'sub_divisions': sub_divisions,
    'stages': stages,
    'gravity_types': gravity_types,
    'months': months
}
with open(os.path.join(out_dir, "filters.json"), "w", encoding="utf-8") as f:
    json.dump(filters, f)

# 2. Overall KPIs
kpi_row = cur.execute("""
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
""").fetchone()

tot = kpi_row['total']
cs = kpi_row['cs_count']
p_disp = kpi_row['police_disp_count']
c_disp = kpi_row['court_disp_count']
kpis = {
    'total': tot,
    'ui': kpi_row['ui_count'],
    'chargesheeted': cs,
    'police_disposed': p_disp,
    'court_disposed': c_disp,
    'cs_rate': round((cs / tot * 100), 1) if tot > 0 else 0,
    'disp_rate': round(((p_disp + c_disp) / tot * 100), 1) if tot > 0 else 0,
    'grave': kpi_row['grave_count'],
    'non_grave': kpi_row['non_grave_count'],
    'long_pending': kpi_row['long_pending_count']
}
with open(os.path.join(out_dir, "kpis.json"), "w", encoding="utf-8") as f:
    json.dump(kpis, f)

# 3. Monthly Trends
rows = cur.execute("""
SELECT month, COUNT(*) as cnt,
       SUM(CASE WHEN LOWER(stage) LIKE '%charge%' OR LOWER(stage) LIKE '%pt%' THEN 1 ELSE 0 END) as cs_cnt,
       SUM(CASE WHEN LOWER(stage) LIKE '%ui%' THEN 1 ELSE 0 END) as ui_cnt
FROM crime_records
WHERE month != ''
GROUP BY month
""").fetchall()
data_map = {r['month'].strip().lower(): r for r in rows}
month_order = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
labels, totals, cs_list, ui_list = [], [], [], []
for m in month_order:
    labels.append(m.capitalize())
    if m in data_map:
        totals.append(data_map[m]['cnt'])
        cs_list.append(data_map[m]['cs_cnt'])
        ui_list.append(data_map[m]['ui_cnt'])
    else:
        totals.append(0); cs_list.append(0); ui_list.append(0)

trends = {'type': 'monthly', 'labels': labels, 'totals': totals, 'chargesheeted': cs_list, 'ui': ui_list}
with open(os.path.join(out_dir, "trends.json"), "w", encoding="utf-8") as f:
    json.dump(trends, f)

# 4. Stations
st_rows = cur.execute("""
SELECT 
    police_station,
    sub_division,
    COUNT(*) as total,
    SUM(CASE WHEN LOWER(stage) LIKE '%ui%' THEN 1 ELSE 0 END) as ui,
    SUM(CASE WHEN LOWER(stage) LIKE '%charge%' OR LOWER(stage) LIKE '%pt%' THEN 1 ELSE 0 END) as cs,
    SUM(CASE WHEN (police_disposal_date != '' AND police_disposal_date != '0') OR (disposal_type != '' AND disposal_type != '0') THEN 1 ELSE 0 END) as disp,
    SUM(CASE WHEN days_pending > 365 THEN 1 ELSE 0 END) as long_pending
FROM crime_records
WHERE police_station != ''
GROUP BY police_station
ORDER BY total DESC
""").fetchall()
stations = []
for r in st_rows:
    t = r['total']
    c = r['cs']
    stations.append({
        'station': r['police_station'],
        'sub_division': r['sub_division'],
        'total': t,
        'ui': r['ui'],
        'chargesheeted': c,
        'disposed': r['disp'],
        'long_pending': r['long_pending'],
        'cs_rate': round((c / t * 100), 1) if t > 0 else 0,
        'disp_rate': round((r['disp'] / t * 100), 1) if t > 0 else 0
    })
with open(os.path.join(out_dir, "stations.json"), "w", encoding="utf-8") as f:
    json.dump(stations, f)

# 5. Crime Heads
ch_rows = cur.execute("""
SELECT 
    crime_head,
    COUNT(*) as total,
    SUM(CASE WHEN LOWER(stage) LIKE '%ui%' THEN 1 ELSE 0 END) as ui,
    SUM(CASE WHEN LOWER(stage) LIKE '%charge%' OR LOWER(stage) LIKE '%pt%' THEN 1 ELSE 0 END) as cs
FROM crime_records
WHERE crime_head != ''
GROUP BY crime_head
ORDER BY total DESC
LIMIT 50
""").fetchall()
crime_heads = [
    {
        'crime_head': r['crime_head'],
        'total': r['total'],
        'ui': r['ui'],
        'chargesheeted': r['cs'],
        'cs_rate': round((r['cs'] / r['total'] * 100), 1) if r['total'] > 0 else 0
    }
    for r in ch_rows
]
with open(os.path.join(out_dir, "crime_heads.json"), "w", encoding="utf-8") as f:
    json.dump(crime_heads, f)

# 6. Pendency
row_b = cur.execute("""
SELECT 
    SUM(CASE WHEN days_pending <= 60 THEN 1 ELSE 0 END) as under_60,
    SUM(CASE WHEN days_pending > 60 AND days_pending <= 90 THEN 1 ELSE 0 END) as b_60_90,
    SUM(CASE WHEN days_pending > 90 AND days_pending <= 180 THEN 1 ELSE 0 END) as b_90_180,
    SUM(CASE WHEN days_pending > 180 AND days_pending <= 365 THEN 1 ELSE 0 END) as b_180_365,
    SUM(CASE WHEN days_pending > 365 THEN 1 ELSE 0 END) as over_365
FROM crime_records
WHERE (LOWER(stage) LIKE '%ui%' OR LOWER(stage) LIKE '%under%')
""").fetchone()

reasons = cur.execute("""
SELECT reason_ui, COUNT(*) as cnt
FROM crime_records
WHERE reason_ui != '' AND reason_ui != '0'
GROUP BY reason_ui
ORDER BY cnt DESC
LIMIT 10
""").fetchall()

pendency = {
    'brackets': {
        '< 60 Days': row_b['under_60'] or 0,
        '60 - 90 Days': row_b['b_60_90'] or 0,
        '90 - 180 Days': row_b['b_90_180'] or 0,
        '180 - 365 Days': row_b['b_180_365'] or 0,
        '> 1 Year': row_b['over_365'] or 0
    },
    'reasons': [{'reason': r['reason_ui'], 'count': r['cnt']} for r in reasons]
}
with open(os.path.join(out_dir, "pendency.json"), "w", encoding="utf-8") as f:
    json.dump(pendency, f)

# 7. Recent Cases (top 200 cases for live offline browsing in GitHub Pages)
case_rows = cur.execute("""
SELECT id, s_no, sub_division, circle, io_name, police_station, fir_no,
       acts_sec, fir_date, month, year, crime_head, sub_head,
       gravity_type, stage, court_disposal, police_disposal_date,
       disposal_type, reason_ui, brief, days_pending, timeline, motive
FROM crime_records
ORDER BY id DESC
LIMIT 200
""").fetchall()
cases = {
    'total': tot,
    'page': 1,
    'page_size': 25,
    'total_pages': 8,
    'items': [dict(r) for r in case_rows]
}
with open(os.path.join(out_dir, "cases.json"), "w", encoding="utf-8") as f:
    json.dump(cases, f)

conn.close()
print("All static analytical datasets generated successfully in data_static/!")
