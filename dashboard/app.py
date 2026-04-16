"""
KPI Dashboard — Flask web app.
Runs on port 8080, reads data from Google Sheets.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from services.google_api import GoogleSheetsService
from config import SHEET_RAW_DATA, SHEET_DAILY_SUMMARY, SHEET_LTV_COHORT
import logging

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
        ss = sheets._connect()
        ws = ss.worksheet(SHEET_DAILY_SUMMARY)
        records = ws.get_all_records()
        records = sorted(records, key=lambda r: r.get("date", ""))[-30:]
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
