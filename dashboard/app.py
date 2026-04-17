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


@app.route("/api/totals")
@login_required
def api_totals():
    try:
        ss = sheets._connect()
        ws = ss.worksheet(SHEET_DAILY_SUMMARY)
        records = ws.get_all_records()

        def sf(v):
            try: return float(v) if v != "" else 0.0
            except: return 0.0

        total_spend   = sum(sf(r.get("total_ad_spend")) for r in records)
        total_leads   = sum(sf(r.get("total_leads")) for r in records)
        total_sales   = sum(sf(r.get("total_sales")) for r in records)
        total_revenue = sum(sf(r.get("total_revenue")) for r in records)
        blended_cac   = round(total_spend / total_sales, 0) if total_sales else 0

        ltv_ws = ss.worksheet(SHEET_LTV_COHORT)
        ltv_records = ltv_ws.get_all_records()
        avg_ltv = 0.0
        if ltv_records:
            ltvs = [sf(r.get("ltv")) for r in ltv_records if sf(r.get("ltv")) > 0]
            avg_ltv = round(sum(ltvs) / len(ltvs), 0) if ltvs else 0

        overall_roi = round(total_revenue / total_spend, 2) if total_spend else 0

        return jsonify({"ok": True, "data": {
            "total_ad_spend": total_spend,
            "total_leads": total_leads,
            "total_sales": total_sales,
            "total_revenue": total_revenue,
            "blended_cac": blended_cac,
            "avg_ltv": avg_ltv,
            "overall_roi": overall_roi,
            "days_count": len(records),
        }})
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


@app.route("/api/funnel_comparison")
@login_required
def api_funnel_comparison():
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

        def sf(v):
            try: return float(v) if v != "" else 0.0
            except: return 0.0

        def pct(num, den):
            return round(num / den * 100, 1) if den else 0.0

        # VSL
        vsl = [r for r in records if r.get("funnel_type") == "VSL"]
        vsl_spend   = sum(sf(r.get("ad_spend")) for r in vsl)
        vsl_views   = sum(sf(r.get("page_views")) for r in vsl)
        vsl_starts  = sum(sf(r.get("video_start")) for r in vsl)
        vsl_cta     = sum(sf(r.get("cta_clicks")) for r in vsl)
        vsl_revenue = sum(sf(r.get("price")) for r in records if r.get("funnel_source") == "VSL")
        vsl_sales   = sum(sf(r.get("sales_count")) for r in vsl)

        # Lead Magnet
        lm = [r for r in records if r.get("funnel_type") == "Lead_Magnet"]
        lm_spend   = sum(sf(r.get("ad_spend")) for r in lm)
        lm_views   = sum(sf(r.get("lp_views")) for r in lm)
        lm_leads   = sum(sf(r.get("new_leads")) for r in lm)
        lm_contact = sum(sf(r.get("contacted")) for r in lm)
        lm_revenue = sum(sf(r.get("price")) for r in records if r.get("funnel_source") == "Lead_Magnet")
        lm_sales   = sum(sf(r.get("sales_count")) for r in lm)

        # Seminar
        sem = [r for r in records if r.get("funnel_type") == "Seminar"]
        sem_spend  = sum(sf(r.get("ad_spend")) for r in sem)
        sem_reg    = sum(sf(r.get("registrations")) for r in sem)
        sem_show   = sum(sf(r.get("show_up")) for r in sem)
        sem_dep    = sum(sf(r.get("deposits")) for r in sem)
        sem_sales  = sum(sf(r.get("sales_count")) for r in sem)
        sem_full   = sum(sf(r.get("full_payments")) for r in sem)
        sem_revenue= sum(sf(r.get("price")) for r in records if r.get("funnel_source") == "Seminar")

        # Overall ROI
        total_spend   = vsl_spend + lm_spend + sem_spend
        total_revenue = vsl_revenue + lm_revenue + sem_revenue
        overall_roi   = round(total_revenue / total_spend, 2) if total_spend else 0

        result = {
            "overall_roi": overall_roi,
            "total_spend": total_spend,
            "total_revenue": total_revenue,
            "vsl": {
                "ad_spend": vsl_spend, "page_views": vsl_views,
                "video_start": vsl_starts, "cta_clicks": vsl_cta,
                "sales": vsl_sales, "revenue": vsl_revenue,
                "view_to_cta": pct(vsl_cta, vsl_views),
                "roi": round(vsl_revenue / vsl_spend, 2) if vsl_spend else 0,
            },
            "lead_magnet": {
                "ad_spend": lm_spend, "lp_views": lm_views,
                "new_leads": lm_leads, "contacted": lm_contact,
                "sales": lm_sales, "revenue": lm_revenue,
                "lead_conv": pct(lm_leads, lm_views),
                "contact_conv": pct(lm_contact, lm_leads),
                "roi": round(lm_revenue / lm_spend, 2) if lm_spend else 0,
            },
            "seminar": {
                "ad_spend": sem_spend, "registrations": sem_reg,
                "show_up": sem_show, "deposits": sem_dep,
                "sales": sem_sales, "full_payments": sem_full,
                "revenue": sem_revenue,
                "show_rate": pct(sem_show, sem_reg),
                "close_rate": pct(sem_sales, sem_show),
                "roi": round(sem_revenue / sem_spend, 2) if sem_spend else 0,
            },
        }
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/export")
@login_required
def api_export():
    try:
        from services.google_api import RAW_HEADERS
        ss = sheets._connect()
        ws = ss.worksheet(SHEET_RAW_DATA)
        records = ws.get_all_records()
        date_from = request.args.get("from", "")
        date_to = request.args.get("to", "")
        if date_from:
            records = [r for r in records if str(r.get("date", "")) >= date_from]
        if date_to:
            records = [r for r in records if str(r.get("date", "")) <= date_to]
        output = io.StringIO()
        fieldnames = records[0].keys() if records else RAW_HEADERS
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        if records:
            writer.writerows(records)
        filename = f"kpi_export_{date.today().isoformat()}.csv"
        return Response(
            "\ufeff" + output.getvalue(),  # BOM for Excel UTF-8
            mimetype="text/csv; charset=utf-8",
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
