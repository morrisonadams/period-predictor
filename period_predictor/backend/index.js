const path = require('path');
const fs = require('fs');
const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const logger = require('./logger');
const { OpenAI } = require('openai');

// Home Assistant supervisor API details
const SUPERVISOR_TOKEN =
  process.env.SUPERVISOR_TOKEN || process.env.HASSIO_TOKEN || '';
const HA_API = 'http://supervisor/homeassistant/api';

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
  db.run(
    'CREATE TABLE IF NOT EXISTS periods (user TEXT, start_date TEXT, end_date TEXT, PRIMARY KEY(user, start_date))',
    (err) => {
      if (err) {
        logger.error('Failed to create periods table:', err);
      } else {
        logger.debug('Ensured periods table exists');
      }
    }
  );
  db.all('PRAGMA table_info(periods)', (err, columns) => {
    if (err) {
      logger.error('Failed to fetch periods table info:', err);
      return;
    }
    const hasUser = columns.some((c) => c.name === 'user');
    if (!hasUser) {
      db.run('ALTER TABLE periods RENAME TO periods_old');
      db.run(
        'CREATE TABLE periods (user TEXT, start_date TEXT, end_date TEXT, PRIMARY KEY(user, start_date))'
      );
      db.run(
        'INSERT INTO periods (user, start_date, end_date) SELECT "default", start_date, end_date FROM periods_old'
      );
      db.run('DROP TABLE periods_old');
      return;
    }
    const hasEndDate = columns.some((c) => c.name === 'end_date');
    if (!hasEndDate) {
      db.run('ALTER TABLE periods ADD COLUMN end_date TEXT', (alterErr) => {
        if (alterErr) {
          logger.error('Failed to add end_date column:', alterErr);
        } else {
          logger.info('Added end_date column to periods table');
        }
      });
    }
  });
});

// Proxy Home Assistant users
app.get('/api/users', async (_req, res) => {
  if (!SUPERVISOR_TOKEN) {
    return res.status(500).json({ error: 'supervisor token not set' });
  }
  try {
    const response = await fetch(`${HA_API}/users`, {
      headers: { Authorization: `Bearer ${SUPERVISOR_TOKEN}` },
    });
    if (!response.ok) {
      throw new Error(`status ${response.status}`);
    }
    const data = await response.json();
    res.json(data);
  } catch (err) {
    logger.error('Failed to fetch users from Home Assistant:', err);
    res.status(500).json({ error: 'failed to fetch users' });
  }
});

// Fetch all period records
app.get('/api/periods', (req, res) => {
  const user = req.query.user;
  if (!user) {
    return res.status(400).json({ error: 'user is required' });
  }
  db.all(
    'SELECT start_date, end_date FROM periods WHERE user = ? ORDER BY start_date',
    [user],
    (err, rows) => {
      if (err) {
        logger.error('Failed to fetch periods:', err);
        return res.status(500).json({ error: err.message });
      }
      logger.debug(`Returning ${rows.length} periods for ${user}`);
      res.json(rows);
    }
  );
});

// Add a period start
app.post('/api/periods/start', (req, res) => {
  const { date, user } = req.body || {};
  if (!date || !user) {
    logger.error('POST /api/periods/start missing required fields');
    return res.status(400).json({ error: 'date and user are required' });
  }
  db.run(
    'INSERT OR IGNORE INTO periods (user, start_date) VALUES (?, ?)',
    [user, date],
    function (err) {
      if (err) {
        logger.error('Failed to insert period start:', err);
        return res.status(500).json({ error: err.message });
      }
      logger.info(`Recorded period start date ${date} for ${user}`);
      res.status(201).json({});
    }
  );
});

// Remove a period start (and associated end if present)
app.delete('/api/periods/start/:date', (req, res) => {
  const { date } = req.params;
  const user = req.query.user;
  if (!user) {
    return res.status(400).json({ error: 'user is required' });
  }
  db.run(
    'DELETE FROM periods WHERE start_date = ? AND user = ?',
    [date, user],
    function (err) {
      if (err) {
        logger.error('Failed to delete period start:', err);
        return res.status(500).json({ error: err.message });
      }
      logger.info(`Removed period start date ${date} for ${user}`);
      res.json({});
    }
  );
});

// Add a period end. Finds the most recent start within 7 days.
app.post('/api/periods/end', (req, res) => {
  const endDate = req.body?.date;
  const user = req.body?.user;
  if (!endDate || !user) {
    logger.error('POST /api/periods/end missing required fields');
    return res.status(400).json({ error: 'date and user are required' });
  }
  db.all(
    'SELECT start_date FROM periods WHERE user = ? AND end_date IS NULL',
    [user],
    (err, rows) => {
      if (err) {
        logger.error('Failed to find open periods:', err);
        return res.status(500).json({ error: err.message });
      }
      const end = new Date(endDate);
      const match = rows.find((r) => {
        const start = new Date(r.start_date);
        const diff = (end - start) / (1000 * 60 * 60 * 24);
        return diff >= 0 && diff <= 7;
      });
      if (!match) {
        logger.info(`No start date within 7 days for end date ${endDate}`);
        return res.status(404).json({ error: 'no start date within 7 days' });
      }
      db.run(
        'UPDATE periods SET end_date = ? WHERE user = ? AND start_date = ?',
        [endDate, user, match.start_date],
        function (updateErr) {
          if (updateErr) {
            logger.error('Failed to add period end:', updateErr);
            return res.status(500).json({ error: updateErr.message });
          }
          logger.info(
            `Recorded period end date ${endDate} for start ${match.start_date} and user ${user}`
          );
          res.status(201).json({});
        }
      );
    }
  );
});

// Remove a period end
app.delete('/api/periods/end/:date', (req, res) => {
  const { date } = req.params;
  const user = req.query.user;
  if (!user) {
    return res.status(400).json({ error: 'user is required' });
  }
  db.run(
    'UPDATE periods SET end_date = NULL WHERE end_date = ? AND user = ?',
    [date, user],
    function (err) {
      if (err) {
        logger.error('Failed to remove period end:', err);
        return res.status(500).json({ error: err.message });
      }
      logger.info(`Removed period end date ${date} for ${user}`);
      res.json({});
    }
  );
});

// Delete all period records
app.delete('/api/periods', (req, res) => {
  const user = req.query.user;
  const sql = user ? 'DELETE FROM periods WHERE user = ?' : 'DELETE FROM periods';
  const params = user ? [user] : [];
  db.run(sql, params, (err) => {
    if (err) {
      logger.error('Failed to clear periods table:', err);
      return res.status(500).json({ error: err.message });
    }
    if (user) {
      logger.warn(`All period records deleted for ${user}`);
    } else {
      logger.warn('All period records deleted');
    }
    res.json({});
  });
});

// Predict the next period start date using GPT with a fallback heuristic
app.get('/api/prediction', (req, res) => {
  const user = req.query.user;
  if (!user) {
    return res.status(400).json({ error: 'user is required' });
  }
  db.all(
    'SELECT start_date FROM periods WHERE user = ? ORDER BY start_date',
    [user],
    async (err, rows) => {
      if (err) {
        logger.error('Failed to generate prediction:', err);
        return res.status(500).json({ error: err.message });
      }

    let nextDate;
    let message = '';

    const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
    try {
      const dates = rows.map((r) => r.start_date).join(', ');
      const prompt =
        rows.length > 0
          ? `Given the recorded menstrual cycle start dates: ${dates}. Predict the next start date and provide a short encouraging message. Respond with JSON {"next_start":"YYYY-MM-DD","message":"text"}.`
          : `No prior period data is available. Assume a 28 day cycle starting today ${new Date()
              .toISOString()
              .split('T')[0]}. Respond with JSON {"next_start":"YYYY-MM-DD","message":"text"}.`;
      const response = await client.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: [{ role: 'user', content: prompt }],
      });
      const content = response.choices[0].message.content;
      const parsed = JSON.parse(content);
      nextDate = new Date(parsed.next_start);
      message = parsed.message;
      logger.info(`Predicted next period start ${parsed.next_start} using GPT`);
    } catch (gptErr) {
      logger.error('GPT prediction failed, falling back:', gptErr);
      let cycleLength = 28; // default cycle length
      if (rows.length >= 2) {
        const dates = rows.map((r) => new Date(r.start_date));
        const intervals = [];
        for (let i = 1; i < dates.length; i++) {
          const diffMs = dates[i] - dates[i - 1];
          intervals.push(diffMs / (1000 * 60 * 60 * 24));
        }
        cycleLength = intervals.reduce((a, b) => a + b, 0) / intervals.length;
        nextDate = new Date(
          dates[dates.length - 1].getTime() + cycleLength * 24 * 60 * 60 * 1000
        );
        logger.info(
          `Predicted next period start ${nextDate.toISOString().split('T')[0]} based on history`
        );
      } else if (rows.length === 1) {
        const lastStart = new Date(rows[0].start_date);
        nextDate = new Date(
          lastStart.getTime() + cycleLength * 24 * 60 * 60 * 1000
        );
        logger.info('Only one period record; using default 28 day cycle');
      } else {
        nextDate = new Date();
        nextDate.setDate(nextDate.getDate() + cycleLength);
        logger.info('No period data; using today + 28 days for prediction');
      }
      message = `Based on historical average, next period around ${nextDate
        .toISOString()
        .split('T')[0]}.`;
    }

    const pmsStart = new Date(nextDate.getTime() - 7 * 24 * 60 * 60 * 1000);
    const pmsEnd = new Date(nextDate.getTime() - 5 * 24 * 60 * 60 * 1000);

    res.json({
      next_start: nextDate.toISOString().split('T')[0],
      period_length: 5,
      pms_start: pmsStart.toISOString().split('T')[0],
      pms_end: pmsEnd.toISOString().split('T')[0],
      text: message,
    });
  });
});

// Start server
app.listen(PORT, () => {
  logger.info(`Backend server listening on port ${PORT}`);
});

