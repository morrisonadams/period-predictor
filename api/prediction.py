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


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS predictions (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, created_at TEXT)"
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
            avg = statistics.mean(c.length for c in history)
            next_start = history[-1].start + dt.timedelta(days=round(avg))
            text = (
                f"Based on historical average ({avg:.1f} days), next cycle around "
                f"{next_start.isoformat()}."
            )
        else:
            text = "Insufficient data for prediction."
    pred = Prediction(text=text, created_at=dt.datetime.utcnow())
    conn = _get_db()
    conn.execute(
        "INSERT INTO predictions(text, created_at) VALUES (?, ?)",
        (pred.text, pred.created_at.isoformat()),
    )
    conn.commit()
    conn.close()
    return pred


def get_latest_prediction(stale_hours: int = 24) -> Optional[Prediction]:
    conn = _get_db()
    row = conn.execute(
        "SELECT text, created_at FROM predictions ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        return None
    text, created_at = row
    created_at_dt = dt.datetime.fromisoformat(created_at)
    if dt.datetime.utcnow() - created_at_dt > dt.timedelta(hours=stale_hours):
        return None
    return Prediction(text=text, created_at=created_at_dt)
