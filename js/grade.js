// Grading typed short answers by keyword, for `type: 'text'` questions
// (i18n/questions.en.js). A question's `keys` is a list of ideas, each a
// list of synonyms; the answer must contain every idea (or `need` of them),
// in order if `ordered`, and none of `forbid`. Words match whole: case,
// accents, punctuation, "the"/"of"/"and"/"or" and plurals don't matter,
// number words count as digits, and longer words forgive a typo. Loaded
// before js/viewer.js, which shares `distance`.
window.GRADE = (function () {
  const STOP = new Set(['the', 'a', 'an', 'of', 'and', 'or', 'to', 'is', 'are']);
  const NUMBERS = Object.fromEntries(['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven',
    'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
    'seventeen', 'eighteen', 'nineteen', 'twenty'].map((w, i) => [w, String(i)]));

  function stem(w) {
    if (NUMBERS[w]) return NUMBERS[w];
    if (w.length > 4 && w.endsWith('ies')) return w.slice(0, -3) + 'y';
    if (w.length > 3 && w.endsWith('s') && !w.endsWith('ss')) return w.slice(0, -1);
    return w;
  }
  function tokens(text) {
    return text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
      .split(/[^a-z0-9]+/).filter((w) => w && !STOP.has(w)).map(stem);
  }

  function distance(a, b) {
    let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
    for (let i = 1; i <= a.length; i++) {
      const row = [i];
      for (let j = 1; j <= b.length; j++) {
        row[j] = Math.min(prev[j] + 1, row[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      }
      prev = row;
    }
    return prev[b.length];
  }
  // One typo from 6 letters, two from 12; short words and numbers exactly.
  // (So "voluntary" is not "involuntary", nor "ileum" "ilium".)
  function same(word, key) {
    if (word === key) return true;
    if (/\d/.test(key)) return false;
    const allowed = key.length >= 12 ? 2 : key.length >= 6 ? 1 : 0;
    return allowed > 0 && distance(word, key) <= allowed;
  }
  // Where a key (one synonym, possibly several words) first occurs at or
  // after `from`: the index just past it, or -1.
  function find(words, key, from = 0) {
    const want = tokens(key);
    if (!want.length) return -1;
    for (let i = from; i + want.length <= words.length; i++) {
      if (want.every((k, j) => same(words[i + j], k))) return i + want.length;
    }
    return -1;
  }

  // → { right, hit: [idea indexes found], missed: [idea indexes], forbidden: [words] }
  function grade(q, text) {
    const words = tokens(text);
    const hit = [], missed = [];
    let at = 0;
    q.keys.forEach((idea, i) => {
      const ends = idea.map((k) => find(words, k, q.ordered ? at : 0)).filter((e) => e >= 0);
      if (ends.length) { hit.push(i); if (q.ordered) at = Math.min(...ends); } else missed.push(i);
    });
    const forbidden = (q.forbid ?? []).filter((k) => find(words, k) >= 0);
    const right = hit.length >= (q.need ?? q.keys.length) && !forbidden.length;
    return { right, hit, missed, forbidden };
  }

  return { grade, tokens, distance };
})();
