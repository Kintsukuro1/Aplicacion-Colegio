/**
 * Shared formatting utilities.
 */

/**
 * Format a numeric value for display.
 * Returns '0' for nullish, handles NaN, and trims trailing .0
 *
 * @param {*} value - Value to format
 * @param {string} fallback - Fallback for nullish values (default '0')
 * @returns {string}
 */
export function formatNumber(value, fallback = '0') {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }

  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) {
    return String(value);
  }

  return numericValue.toFixed(1).replace(/\.0$/, '');
}

/**
 * Normalize Chilean grade values for display and comparisons.
 * If a grade arrives as 40 (legacy scale), normalize to 4.0.
 */
export function normalizeGrade(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) {
    return null;
  }

  if (Math.abs(numericValue) > 10) {
    return numericValue / 10;
  }

  return numericValue;
}

/**
 * Format grades using Chilean notation (one decimal, comma separator).
 */
export function formatGrade(value, fallback = '-') {
  const normalized = normalizeGrade(value);
  if (normalized === null) {
    return fallback;
  }

  return normalized.toFixed(1).replace('.', ',');
}

/**
 * Format API dates as day/month without time details.
 */
export function formatShortDate(value, fallback = '-') {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }

  if (typeof value === 'string') {
    const isoDateMatch = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (isoDateMatch) {
      return `${isoDateMatch[3]}/${isoDateMatch[2]}`;
    }
  }

  const parsedDate = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return String(value);
  }

  const day = String(parsedDate.getDate()).padStart(2, '0');
  const month = String(parsedDate.getMonth() + 1).padStart(2, '0');
  return `${day}/${month}`;
}
