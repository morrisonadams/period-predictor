# Period Predictor Add-on Repository

This repository contains a Home Assistant add-on that lets you record period start dates and predicts the next period using a simple statistical model. Data persists in `/data` inside the add-on (stored as an SQLite database).

The backend now runs on [Express](https://expressjs.com/) with a small Vue-based frontend, listening on port **3002** by default.

## Logging

Logs from the add-on appear in Home Assistant's add-on log panel. Set the verbosity by adjusting the `log_level` option in the add-on configuration (`debug`, `info`, `warning`, or `error`).

## Configuration

In your add-on configuration you can set:

- `log_level`: Controls log verbosity.
- `openai_api_key`: Your OpenAI API key used for generating predictions.

## Events

The add-on emits Home Assistant events that can be used in automations or
flows (e.g. Node-RED):

- `period_predictor_pms_start` – fired on the predicted PMS start date.
- `period_predictor_period_start_predicted` – fired on the predicted period
  start date.
- `period_predictor_period_start` – fired when a period start is recorded via
  the API.

Each event includes the `user` and `date` in its data payload.

## Add this repository to Home Assistant

1. Go to **Settings → Add-ons → Add-on Store**.
2. Click the **three dots ⋮ → Repositories**.
3. Paste your GitHub repo URL (after you upload this folder) and click **Add**.
4. Find **Period Predictor** in the store and install it.
5. Start it, then click **Open Web UI** (Ingress).

> Tip: For quick, local testing without GitHub, copy the `period_predictor` folder into your Home Assistant `addons/` directory and use **Settings → Add-ons → Add-on Store → ⋮ → Reload**.
