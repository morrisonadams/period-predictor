from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="/web", static_url_path="")
DB_PATH = Path("/data/periods.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS periods (start_date TEXT)")
    conn.commit()
    conn.close()


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/periods", methods=["GET", "POST"])
def periods():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if request.method == "POST":
        data = request.get_json() or {}
        date_str = data.get("date")
        if not date_str:
            return {"error": "date is required"}, 400
        cur.execute("INSERT INTO periods (start_date) VALUES (?)", (date_str,))
        conn.commit()
        conn.close()
        return {}, 201
    cur.execute("SELECT start_date FROM periods ORDER BY start_date")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route("/api/prediction")
def prediction():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT start_date FROM periods ORDER BY start_date")
    dates = [datetime.fromisoformat(r[0]) for r in cur.fetchall()]
    conn.close()
    if len(dates) < 2:
        return jsonify({"next": None})
    intervals = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
    avg = sum(intervals) / len(intervals)
    next_date = dates[-1] + timedelta(days=avg)
    return jsonify({"next": next_date.date().isoformat()})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=80)
