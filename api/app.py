from dataclasses import asdict
import datetime as dt
import sqlite3

from fastapi import FastAPI

from .prediction import (
    Cycle,
    DB_PATH,
    generate_prediction,
    get_latest_prediction,
)

app = FastAPI()


def _load_history() -> list[Cycle]:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cycles (start TEXT, end TEXT, notes TEXT)"
    )
    rows = conn.execute("SELECT start, end, notes FROM cycles ORDER BY start").fetchall()
    conn.close()
    history: list[Cycle] = []
    for start, end, notes in rows:
        history.append(
            Cycle(start=dt.date.fromisoformat(start), end=dt.date.fromisoformat(end), notes=notes)
        )
    return history


@app.get("/api/prediction")
def prediction_endpoint():
    pred = get_latest_prediction()
    if pred:
        return asdict(pred)
    history = _load_history()
    pred = generate_prediction(history)
    return asdict(pred)
