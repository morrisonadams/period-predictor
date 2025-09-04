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


def test_generate_prediction_fallback(mocker, tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    mock_client = mocker.Mock()
    mock_client.chat.completions.create.side_effect = Exception("boom")
    mocker.patch("api.prediction.OpenAI", return_value=mock_client)

    history = [Cycle(start=dt.date(2024, 1, 1), end=dt.date(2024, 1, 29))]
    pred = generate_prediction(history)
    assert "Based on historical average" in pred.text


def test_prediction_endpoint_uses_cache(tmp_path, monkeypatch):
    db_path = setup_db(tmp_path, monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    conn = _get_db()
    conn.execute(
        "INSERT INTO predictions(text, created_at) VALUES (?, ?)",
        ("cached", dt.datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

    client = TestClient(app)
    res = client.get("/api/prediction")
    assert res.status_code == 200
    assert res.json()["text"] == "cached"
