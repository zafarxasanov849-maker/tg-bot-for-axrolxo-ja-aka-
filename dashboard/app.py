"""
KPI Dashboard — Flask web app.
Runs on port 8080, reads data from Google Sheets.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, render_template
from services.google_api import GoogleSheetsService
from config import SHEET_RAW_DATA, SHEET_DAILY_SUMMARY, SHEET_LTV_COHORT
import asyncio
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
sheets = GoogleSheetsService()


def run_sync(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/summary")
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
def api_ltv():
    try:
        ss = sheets._connect()
        ws = ss.worksheet(SHEET_LTV_COHORT)
        records = ws.get_all_records()
        return jsonify({"ok": True, "data": records})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/raw")
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
