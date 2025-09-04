const path = require('path');
const fs = require('fs');
const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const logger = require('./logger');

const app = express();
const PORT = process.env.PORT || 3002;

process.on('uncaughtException', (err) => {
  logger.error('Uncaught exception:', err);
});

process.on('unhandledRejection', (err) => {
  logger.error('Unhandled promise rejection:', err);
});

// Determine a writable location for the database. In the Home Assistant
// environment the "/data" directory is used for persistence, but in other
// environments (such as local development or tests) that directory may not
// exist. Fall back to a local "data" folder inside the project if needed.
const DATA_DIR = '/data';
let dbPathDir = DATA_DIR;
try {
  fs.mkdirSync(DATA_DIR, { recursive: true });
} catch (e) {
  dbPathDir = path.join(__dirname, '..', 'data');
  fs.mkdirSync(dbPathDir, { recursive: true });
}
const DB_PATH = path.join(dbPathDir, 'periods.db');
logger.info(`Using database at ${DB_PATH}`);

app.use(express.json());
app.use(express.static(path.join(__dirname, '../web/dist')));
app.use((req, _res, next) => {
  logger.debug(`${req.method} ${req.url}`);
  next();
});

// Initialize database and ensure table exists
const db = new sqlite3.Database(DB_PATH, (err) => {
  if (err) {
    logger.error('Failed to open database:', err);
  } else {
    logger.info('Opened database successfully');
  }
});
db.serialize(() => {
  db.run('CREATE TABLE IF NOT EXISTS periods (start_date TEXT)', (err) => {
    if (err) {
      logger.error('Failed to create periods table:', err);
    } else {
      logger.debug('Ensured periods table exists');
    }
  });
});

// List all period start dates or add a new one
app.route('/api/periods')
  .get((req, res) => {
    db.all('SELECT start_date FROM periods ORDER BY start_date', (err, rows) => {
      if (err) {
        logger.error('Failed to fetch periods:', err);
        return res.status(500).json({ error: err.message });
      }
      logger.debug(`Returning ${rows.length} periods`);
      res.json(rows.map(r => r.start_date));
    });
  })
  .post((req, res) => {
    const date = req.body?.date;
    if (!date) {
      logger.error('POST /api/periods missing required "date" field');
      return res.status(400).json({ error: 'date is required' });
    }
    db.run('INSERT INTO periods (start_date) VALUES (?)', [date], function (err) {
      if (err) {
        logger.error('Failed to insert period:', err);
        return res.status(500).json({ error: err.message });
      }
      logger.info(`Recorded period start date ${date}`);
      res.status(201).json({});
    });
  });

// Predict the next period start date
app.get('/api/prediction', (req, res) => {
  db.all('SELECT start_date FROM periods ORDER BY start_date', (err, rows) => {
    if (err) {
      logger.error('Failed to generate prediction:', err);
      return res.status(500).json({ error: err.message });
    }
    if (rows.length < 2) {
      logger.info('Not enough data to generate prediction');
      return res.json({ next: null });
    }
    const dates = rows.map(r => new Date(r.start_date));
    const intervals = [];
    for (let i = 1; i < dates.length; i++) {
      const diffMs = dates[i] - dates[i - 1];
      intervals.push(diffMs / (1000 * 60 * 60 * 24));
    }
    const avg = intervals.reduce((a, b) => a + b, 0) / intervals.length;
    const nextDate = new Date(dates[dates.length - 1].getTime() + avg * 24 * 60 * 60 * 1000);
    logger.info(`Predicted next period start ${nextDate.toISOString().split('T')[0]}`);
    res.json({ next: nextDate.toISOString().split('T')[0] });
  });
});

// Start server
app.listen(PORT, () => {
  logger.info(`Backend server listening on port ${PORT}`);
});

