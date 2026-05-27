/**
 * TASS — Tokeniser-Aware Structured Shorthand
 * JavaScript parser and schema compiler
 *
 * White paper : https://doi.org/10.5281/zenodo.20403219
 * License     : MIT
 */

'use strict';

const TOKEN_POOL = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');

class SchemaCompiler {
  constructor(prefixChar = '~') {
    this.prefix = prefixChar;
  }

  /**
   * Compile a schema object into a system prompt + parser map.
   *
   * @param {Object} schema  - { fieldName: 'string'|'integer'|'float'|'boolean' }
   * @returns {{ parserMap: Object, systemPrompt: string }}
   */
  compile(schema) {
    const keys = Object.keys(schema);
    if (keys.length > TOKEN_POOL.length) {
      throw new Error(
        `Schema has ${keys.length} fields but pool only supports ${TOKEN_POOL.length}.`
      );
    }

    const parserMap = {};
    const formatParts = [];
    const dictLines = [];

    keys.forEach((key, i) => {
      const sym = TOKEN_POOL[i];
      parserMap[sym] = { field: key, type: schema[key] };
      formatParts.push(`${this.prefix}${sym}:<value>`);
      dictLines.push(`  ${this.prefix}${sym} = ${key}`);
    });

    const systemPrompt = [
      'You are a data extraction engine.',
      'Output ONLY the TASS format below. No prose. No markdown. No explanation.',
      `Format: ${formatParts.join(' ')}`,
      'Dictionary:',
      ...dictLines,
    ].join('\n');

    return { parserMap, systemPrompt };
  }
}

class TASSParser {
  /**
   * @param {Object} options
   * @param {Object} options.dictionaryMap  - output of SchemaCompiler.compile()
   * @param {string} [options.prefixChar]   - default "~"
   */
  constructor({ dictionaryMap, prefixChar = '~' } = {}) {
    this.prefix = prefixChar;
    // Normalise legacy maps that store only field name strings
    this.dictionary = {};
    for (const [k, v] of Object.entries(dictionaryMap)) {
      this.dictionary[k] = typeof v === 'string'
        ? { field: v, type: 'string' }
        : v;
    }
  }

  /**
   * Parse a TASS string. Throws on failure.
   * @param {string} raw
   * @returns {Object}
   */
  parse(raw) {
    const line = this._stripMarkdown(raw);
    return this._parseLine(line);
  }

  /**
   * Parse with JSON fallback. Returns parsed object or throws.
   * @param {string} raw
   * @returns {Object}
   */
  safeParse(raw) {
    try {
      const result = this.parse(raw);
      this._validate(result);
      return result;
    } catch (_) { /* fall through */ }

    try {
      return JSON.parse(this._stripMarkdown(raw));
    } catch (_) { /* fall through */ }

    throw new Error(`Could not parse output as TASS or JSON: ${raw}`);
  }

  // ── Internal ────────────────────────────────────────────────────

  _parseLine(line) {
    const result = {};
    const pairs = line.trim().split(/\s+/);
    for (const pair of pairs) {
      if (!pair.startsWith(this.prefix) || !pair.includes(':')) continue;
      const rest = pair.slice(this.prefix.length);
      const colonIdx = rest.indexOf(':');
      const key = rest.slice(0, colonIdx);
      const rawVal = rest.slice(colonIdx + 1);
      if (!(key in this.dictionary)) continue;
      const { field, type } = this.dictionary[key];
      result[field] = this._coerce(rawVal, type);
    }
    return result;
  }

  _coerce(value, type) {
    const v = value.trim();
    if (type === 'boolean') return ['true', '1', 'yes'].includes(v.toLowerCase());
    if (type === 'integer') return parseInt(this._expandK(v), 10);
    if (type === 'float')   return parseFloat(this._expandK(v));
    return v; // string
  }

  _expandK(value) {
    if (/^[\d.]+k$/i.test(value)) {
      return String(parseFloat(value) * 1000);
    }
    return value;
  }

  _stripMarkdown(text) {
    const cleaned = text.replace(/```[a-z]*\n?/g, '').replace(/`/g, '').trim();
    const tassLine = cleaned.split('\n').find(l => l.trim().startsWith(this.prefix));
    return tassLine ? tassLine.trim() : cleaned;
  }

  _validate(parsed) {
    const expected = new Set(Object.values(this.dictionary).map(v => v.field));
    const missing = [...expected].filter(f => !(f in parsed));
    if (missing.length > 0) {
      throw new Error(`Missing TASS fields: ${missing.join(', ')}`);
    }
  }
}

module.exports = { SchemaCompiler, TASSParser };
