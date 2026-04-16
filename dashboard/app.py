"""
KPI Dashboard — Flask web app.
Runs on port 8080, reads data from Google Sheets.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, render_template, request, session, redirect, url_for, Response
from services.google_api import GoogleSheetsService
from config import SHEET_RAW_DATA, SHEET_DAILY_SUMMARY, SHEET_LTV_COHORT
from datetime import date, datetime
import csv, io, logging

app = Flask(__name__)
app.secret_key = os.getenv("DASHBOARD_SECRET", "kpi-secret-2026")
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASS = os.getenv("DASHBOARD_PASS", "admin123")

logging.basicConfig(level=logging.INFO)
sheets = GoogleSheetsService()


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if (request.form.get("username") == DASHBOARD_USER and
                request.form.get("password") == DASHBOARD_PASS):
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Login yoki parol noto'g'ri"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template("dashboard.html")


@app.route("/api/summary")
@login_required
def api_summary():
    try:
        date_from = request.args.get("from", "")
        date_to = request.args.get("to", "")
        ss = sheets._connect()
        ws = ss.worksheet(SHEET_DAILY_SUMMARY)
        records = ws.get_all_records()
        records = sorted(records, key=lambda r: r.get("date", ""))
        if date_from:
            records = [r for r in records if r.get("date", "") >= date_from]
        if date_to:
            records = [r for r in records if r.get("date", "") <= date_to]
        if not date_from and not date_to:
            records = records[-30:]
        return jsonify({"ok": True, "data": records})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/ltv")
@login_required
def api_ltv():
    try:
        ss = sheets._connect()
        ws = ss.worksheet(SHEET_LTV_COHORT)
        records = ws.get_all_records()
        return jsonify({"ok": True, "data": records})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/miniapp")
def miniapp():
    return render_template("miniapp.html")


@app.route("/api/submit", methods=["POST"])
def api_submit():
    try:
        data = request.get_json(force=True)
        funnel = data.get("funnel_type", "")
        now = datetime.now()
        row = {
            "timestamp": now.isoformat(),
            "date": date.today().isoformat(),
            "reporter_id": data.get("reporter_id", ""),
            "reporter_role": "MINIAPP",
            "funnel_type": funnel,
            "ad_spend": data.get("ad_spend", ""),
            "page_views": data.get("page_views", ""),
            "video_start": data.get("video_start", ""),
            "watch_50": data.get("watch_50", ""),
            "watch_100": data.get("watch_100", ""),
            "cta_clicks": data.get("cta_clicks", ""),
            "lp_views": data.get("lp_views", ""),
            "new_leads": data.get("new_leads", ""),
            "contacted": data.get("contacted", ""),
            "registrations": data.get("registrations", ""),
            "show_up": data.get("show_up", ""),
            "deposits": data.get("deposits", ""),
            "sales_count": data.get("sales_count", ""),
            "full_payments": data.get("full_payments", ""),
            "customer_id": data.get("customer_id", ""),
            "funnel_source": data.get("funnel_source", ""),
            "tariff_type": data.get("tariff_type", ""),
            "price": data.get("price", ""),
            "customer_type": data.get("customer_type", ""),
            "lead_status": data.get("lead_status", ""),
            "screenshot_url": "",
            "anomaly_flag": "",
            "anomaly_explanation": "",
        }
        ss = sheets._connect()
        from services.google_api import RAW_HEADERS
        ws = ss.worksheet(SHEET_RAW_DATA)
        values = [str(row.get(h, "")) for h in RAW_HEADERS]
        ws.append_row(values, value_input_option="USER_ENTERED")

        if funnel == "sales" and data.get("customer_id"):
            sheets._upsert_ltv_sync(row)

        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/export")
@login_required
def api_export():
    try:
        ss = sheets._connect()
        ws = ss.worksheet(SHEET_RAW_DATA)
        records = ws.get_all_records()
        date_from = request.args.get("from", "")
        date_to = request.args.get("to", "")
        if date_from:
            records = [r for r in records if str(r.get("date", "")) >= date_from]
        if date_to:
            records = [r for r in records if str(r.get("date", "")) <= date_to]
        if not records:
            return jsonify({"ok": False, "error": "Ma'lumot yo'q"}), 404
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
        filename = f"kpi_export_{date.today().isoformat()}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/history/<int:user_id>")
def api_history(user_id):
    try:
        ss = sheets._connect()
        ws = ss.worksheet(SHEET_RAW_DATA)
        records = ws.get_all_records()
        user_records = [r for r in records if str(r.get("reporter_id")) == str(user_id)]
        user_records = sorted(user_records, key=lambda r: r.get("date", ""), reverse=True)[:10]
        return jsonify({"ok": True, "data": user_records})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/raw")
@login_required
def api_raw():
    try:
        ss = sheets._connect()
        ws = ss.worksheet(SHEET_RAW_DATA)
        records = ws.get_all_records()
        records = sorted(records, key=lambda r: r.get("date", ""))[-50:]
        return jsonify({"ok": True, "data": records})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
