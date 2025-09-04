import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import datetime as dt
from fastapi.testclient import TestClient

from api.app import app
from api.prediction import Cycle, generate_prediction, _get_db


def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("PREDICTION_DB", str(db_path))
    return db_path


def _compute_events(periods, prediction):
    events = {}
    for p in periods:
        start = dt.date.fromisoformat(p["start_date"])
        end = dt.date.fromisoformat(p["end_date"]) if p["end_date"] else start
        d = start
        while d <= end:
            events[d.isoformat()] = "start" if d == start else "period"
            d += dt.timedelta(days=1)
    if prediction:
        start = dt.date.fromisoformat(prediction["next_start"])
        for i in range(prediction["period_length"]):
            day = start + dt.timedelta(days=i)
            key = day.isoformat()
            events.setdefault(key, "prediction-start" if i == 0 else "prediction")
        pms_start = dt.date.fromisoformat(prediction["pms_start"])
        pms_end = dt.date.fromisoformat(prediction["pms_end"])
        d = pms_start
        while d <= pms_end:
            key = d.isoformat()
            events.setdefault(key, "pms")
            d += dt.timedelta(days=1)
    return events


def test_generate_prediction_uses_openai(mocker, tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    mock_client = mocker.Mock()
    mock_choice = mocker.Mock()
    mock_choice.message.content = "GPT prediction"
    mock_response = mocker.Mock(choices=[mock_choice])
    mock_client.chat.completions.create.return_value = mock_response
    mocker.patch("api.prediction.OpenAI", return_value=mock_client)

    history = [Cycle(start=dt.date(2024, 1, 1), end=dt.date(2024, 1, 29), notes="ok")]
    pred = generate_prediction(history)
    assert pred.text == "GPT prediction"
    assert pred.cycle_length == 28
    assert pred.next_start == dt.date(2024, 1, 29)
    assert pred.pms_start == dt.date(2024, 1, 22)
    assert pred.pms_end == dt.date(2024, 1, 24)
    assert pred.period_length == 5


def test_generate_prediction_fallback(mocker, tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    mock_client = mocker.Mock()
    mock_client.chat.completions.create.side_effect = Exception("boom")
    mocker.patch("api.prediction.OpenAI", return_value=mock_client)

    history = [Cycle(start=dt.date(2024, 1, 1), end=dt.date(2024, 1, 29))]
    pred = generate_prediction(history)
    assert "Based on historical average" in pred.text
    assert pred.next_start == dt.date(2024, 1, 29)
    assert pred.period_length == 5


def test_prediction_endpoint_uses_cache(tmp_path, monkeypatch):
    db_path = setup_db(tmp_path, monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    conn = _get_db()
    conn.execute(
        "INSERT INTO predictions(text, created_at, cycle_length, next_start, pms_start, pms_end, period_length) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "cached",
            dt.datetime.utcnow().isoformat(),
            28,
            dt.date(2024, 1, 29).isoformat(),
            dt.date(2024, 1, 22).isoformat(),
            dt.date(2024, 1, 24).isoformat(),
            5,
        ),
    )
    conn.commit()
    conn.close()

    client = TestClient(app)
    res = client.get("/api/prediction")
    assert res.status_code == 200
    data = res.json()
    assert data["text"] == "cached"
    assert data["pms_start"] == "2024-01-22"


def test_pms_days_do_not_overlap():
    periods = [{"start_date": "2024-01-01", "end_date": "2024-01-05"}]
    prediction = {
        "next_start": "2024-01-10",
        "period_length": 5,
        "pms_start": "2024-01-02",
        "pms_end": "2024-01-04",
    }
    events = _compute_events(periods, prediction)
    # PMS window overlaps recorded period; existing period days should remain
    assert events["2024-01-02"] == "period"
    assert events["2024-01-03"] == "period"


def test_prediction_events_alignment():
    periods = []
    prediction = {
        "next_start": "2024-02-01",
        "period_length": 5,
        "pms_start": "2024-01-25",
        "pms_end": "2024-01-27",
    }
    events = _compute_events(periods, prediction)
    assert events["2024-02-01"] == "prediction-start"
    assert events["2024-02-03"] == "prediction"
    assert events["2024-01-26"] == "pms"
