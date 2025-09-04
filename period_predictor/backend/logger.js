const levels = ['debug', 'info', 'warning', 'error'];
const currentLevel = process.env.LOG_LEVEL ? process.env.LOG_LEVEL.toLowerCase() : 'info';

function shouldLog(level) {
  return levels.indexOf(level) >= levels.indexOf(currentLevel);
}

module.exports = {
  debug: (...args) => {
    if (shouldLog('debug')) console.debug('[DEBUG]', ...args);
  },
  info: (...args) => {
    if (shouldLog('info')) console.log('[INFO]', ...args);
  },
  warn: (...args) => {
    if (shouldLog('warning')) console.warn('[WARN]', ...args);
  },
  error: (...args) => {
    if (shouldLog('error')) console.error('[ERROR]', ...args);
  },
};
