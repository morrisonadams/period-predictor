from __future__ import annotations

import datetime as dt
import os
import sqlite3
import statistics
from dataclasses import dataclass
from typing import List, Optional

from openai import OpenAI

DB_PATH = os.environ.get("PREDICTION_DB", "predictions.db")


@dataclass
class Cycle:
    start: dt.date
    end: dt.date
    notes: Optional[str] = None

    @property
    def length(self) -> int:
        return (self.end - self.start).days


@dataclass
class Prediction:
    text: str
    created_at: dt.datetime
    cycle_length: int
    next_start: dt.date
    pms_start: dt.date
    pms_end: dt.date
    period_length: int


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        (
            "CREATE TABLE IF NOT EXISTS predictions ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "text TEXT, "
            "created_at TEXT, "
            "cycle_length INTEGER, "
            "next_start TEXT, "
            "pms_start TEXT, "
            "pms_end TEXT, "
            "period_length INTEGER"
            ")"
        )
    )
    return conn


def _summarize_history(history: List[Cycle]) -> str:
    if not history:
        return "No cycle history provided."
    lengths = [c.length for c in history]
    avg = statistics.mean(lengths)
    var = statistics.pvariance(lengths) if len(lengths) > 1 else 0.0
    recent_notes = "; ".join(filter(None, (c.notes for c in history[-3:] if c.notes)))
    return (
        f"Average cycle length: {avg:.1f} days\n"
        f"Variance: {var:.2f}\n"
        f"Recent notes: {recent_notes or 'None'}"
    )


def generate_prediction(history: List[Cycle]) -> Prediction:
    # Estimate cycle length
    if history:
        lengths = [c.length for c in history]
        cycle_length = round(statistics.mean(lengths))
        last_start = history[-1].start
    else:
        cycle_length = 28
        last_start = dt.date.today()
    next_start = last_start + dt.timedelta(days=cycle_length)

    # PMS window approximately 7 to 5 days before period
    pms_start = next_start - dt.timedelta(days=7)
    pms_end = next_start - dt.timedelta(days=5)

    # Expected period length (simple default)
    period_length = 5

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    prompt = _summarize_history(history) + "\nPredict the next menstrual cycle."
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content.strip()
    except Exception:
        if history:
            text = (
                f"Based on historical average ({cycle_length} days), next cycle around "
                f"{next_start.isoformat()}."
            )
        else:
            text = "Insufficient data for prediction."

    pred = Prediction(
        text=text,
        created_at=dt.datetime.utcnow(),
        cycle_length=cycle_length,
        next_start=next_start,
        pms_start=pms_start,
        pms_end=pms_end,
        period_length=period_length,
    )

    conn = _get_db()
    conn.execute(
        "INSERT INTO predictions(text, created_at, cycle_length, next_start, pms_start, pms_end, period_length) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            pred.text,
            pred.created_at.isoformat(),
            pred.cycle_length,
            pred.next_start.isoformat(),
            pred.pms_start.isoformat(),
            pred.pms_end.isoformat(),
            pred.period_length,
        ),
    )
    conn.commit()
    conn.close()
    return pred


def get_latest_prediction(stale_hours: int = 24) -> Optional[Prediction]:
    conn = _get_db()
    row = conn.execute(
        "SELECT text, created_at, cycle_length, next_start, pms_start, pms_end, period_length "
        "FROM predictions ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        return None
    text, created_at, cycle_length, next_start, pms_start, pms_end, period_length = row
    created_at_dt = dt.datetime.fromisoformat(created_at)
    if dt.datetime.utcnow() - created_at_dt > dt.timedelta(hours=stale_hours):
        return None
    return Prediction(
        text=text,
        created_at=created_at_dt,
        cycle_length=cycle_length,
        next_start=dt.date.fromisoformat(next_start),
        pms_start=dt.date.fromisoformat(pms_start),
        pms_end=dt.date.fromisoformat(pms_end),
        period_length=period_length,
    )
