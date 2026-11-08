"""Check the questions, the names and the model against each other, in the
real page (headless Chrome).

    make check                # errors and warnings; exits 1 on any error
    make check ARGS=--gaps    # also list parts without a clue or aliases

Errors: page errors on load; a question whose answer, `also` or `focus`
names no part or system, or whose `source` or `topic` doesn't exist;
duplicate question ids; a target part with no `part.<id>` name; an i18n key
the page uses but en.js lacks; two parts sharing a typed name or alias (the
typed answer would be ambiguous).
Warnings: anatomy clues about a part already clued, or about a part no
group asks for; i18n part/alias keys for parts that don't exist.
"""

import re
import sys

from browser import app
from paths import INDEX_HTML, ROOT

# Overlay names js/viewer.js knows (its `overlays`).
OVERLAYS = ["quadrants"]

CHECKS = r"""(OVERLAYS) => {
  const D = window.ANATOMY_DEBUG, errors = [], warnings = [], info = [];
  const parts = BODY_DATA.parts;
  const targets = [...new Set(parts.filter((p) => p.kind === 'target').map((p) => p.id))];
  const systems = new Set(parts.map((p) => p.system));
  const bodiesOf = (id) => [...new Set(parts.filter((p) => p.id === id).map((p) => p.sex ?? 'both'))];
  const exists = (id) => targets.includes(id);

  // Questions.
  const seen = new Map(), clued = new Map();
  for (const cat of CATEGORIES) {
    const kinds = cat.groups ? new Set(cat.groups.flatMap((g) => g.kinds)) : null;
    for (const q of cat.questions) {
      const where = `${cat.id}/${q.id}`;
      if (seen.has(q.id)) errors.push(`${where}: id also used in ${seen.get(q.id)}`);
      seen.set(q.id, cat.id);
      const answers = q.answers ?? [q.answer];
      for (const id of [...answers, ...(q.also ?? [])])
        if (!exists(id)) errors.push(`${where}: no target part "${id}"`);
      if (q.answer && q.answers) errors.push(`${where}: has both answer and answers`);
      for (const s of [].concat(q.focus ?? []))
        if (!systems.has(s)) errors.push(`${where}: focus "${s}" is not a system`);
      if (q.overlay && !OVERLAYS.includes(q.overlay)) errors.push(`${where}: unknown overlay "${q.overlay}"`);
      if (!SOURCES[q.source]) errors.push(`${where}: unknown source "${q.source}"`);
      if (!I18N['quiz.topic.' + q.topic]) errors.push(`${where}: no quiz.topic.${q.topic} in en.js`);
      if (!q.prompt || !q.explain) errors.push(`${where}: missing prompt or explain`);
      if (q.url && !/^https:\/\//.test(q.url)) warnings.push(`${where}: url isn't https: ${q.url}`);
      if (kinds) {
        for (const id of answers)
          if (exists(id) && !kinds.has(D.structureKind(id)))
            warnings.push(`${where}: "${id}" is a ${D.structureKind(id)}, which no ${cat.id} group asks for`);
        if (q.answer) {
          if (clued.has(q.answer)) warnings.push(`${where}: "${q.answer}" already has clue ${clued.get(q.answer)}`);
          clued.set(q.answer, q.id);
        }
      }
    }
  }

  // Names and aliases.
  for (const id of targets) if (!I18N['part.' + id]) errors.push(`part "${id}" has no part.${id} in en.js`);
  for (const key of Object.keys(I18N)) {
    const m = key.match(/^(part|alias)\.(.+)$/);
    if (m && !parts.some((p) => p.id === m[2])) warnings.push(`en.js: ${key} names no part`);
  }
  const owner = new Map();
  for (const id of targets) {
    const names = [I18N['part.' + id] ?? id, ...(I18N['alias.' + id]?.split('|') ?? [])];
    for (const name of names) {
      const key = D.nameKey(name);
      if (owner.has(key) && owner.get(key).id !== id)
        errors.push(`"${name}" (${id}) and "${owner.get(key).name}" (${owner.get(key).id}) type the same`);
      owner.set(key, { id, name });
    }
  }

  // Keys the page builds from data.
  const need = [
    ...[...systems].filter((s) => s !== 'integumentary').map((s) => 'system.' + s),
    ...CATEGORIES.flatMap((c) => ['category.' + c.id, 'category.' + c.id + '.tip',
      ...(c.groups ?? []).flatMap((g) => ['group.' + g.id, 'group.' + g.id + '.tip', 'group.' + g.id + '.items'])]),
    ...targets.map((id) => 'quiz.namePrompt.' + D.structureKind(id) + (D.MANY.has(id) ? '.many' : '')),
  ];
  for (const key of new Set(need)) if (!(key in I18N)) errors.push(`no ${key} in en.js`);
  for (const id of D.MANY) if (!exists(id)) warnings.push(`MANY in viewer.js names no part "${id}"`);

  // Coverage, for --gaps.
  for (const cat of CATEGORIES.filter((c) => c.groups)) {
    for (const g of cat.groups) {
      const ids = targets.filter((id) => g.kinds.includes(D.structureKind(id)));
      const bare = ids.filter((id) => !clued.has(id));
      info.push(`${cat.id}/${g.id}: ${ids.length} parts, ${ids.length - bare.length} with a clue`
        + (bare.length ? `; none for: ${bare.join(', ')}` : ''));
    }
  }
  const noAlias = targets.filter((id) => !I18N['alias.' + id]);
  info.push(`${noAlias.length} parts without aliases: ${noAlias.join(', ')}`);
  const oneBody = targets.filter((id) => !bodiesOf(id).includes('both') && bodiesOf(id).length === 1);
  info.push(`one body only: ${oneBody.map((id) => id + ' (' + bodiesOf(id)[0] + ')').join(', ')}`);
  const counts = CATEGORIES.map((c) => `${c.id} ${c.questions.length}`).join(', ');
  const summary = `${targets.length} target parts, ${parts.length} meshes; clues: ${counts}`;
  return { errors, warnings, info, summary };
}"""


def static_keys():
    """i18n keys named literally in index.html and js/viewer.js."""
    html = INDEX_HTML.read_text()
    js = (ROOT / "js" / "viewer.js").read_text()
    keys = set(re.findall(r'data-t(?:-[a-z-]+)?="([^"]+)"', html))
    keys |= set(re.findall(r"\bt\('([^'{}+]+)'[,)]", js))
    return keys


def choose(page, name, value):
    page.click(f"input[name={name}][value={value}] + span")


def play(page):
    """Smoke test through the UI: a few quiz questions in every category,
    group and body, then a name all and a find all run. Page errors land
    in page.errors; returns problems the UI shows."""
    problems = []
    # Stop drawing: Playwright waits for animation frames before each click,
    # and every frame is a slow software render.
    page.evaluate("ANATOMY_DEBUG.renderer.setAnimationLoop(null)")
    cats = page.evaluate("CATEGORIES.map((c) => [c.id, (c.groups ?? []).map((g) => g.id)])")
    for body in ("male", "female"):
        for cat, groups in cats:
            for group in groups or [None]:
                choose(page, "body", body)
                choose(page, "category", cat)
                if group:
                    choose(page, "group", group)
                    choose(page, "mode", "quiz")
                page.click("#start-go")
                for _ in range(2):
                    prompt = page.inner_text("#quiz-prompt")
                    page.click("#quiz-reveal")
                    if not prompt or not page.inner_text("#quiz-verdict"):
                        problems.append(f"{body}/{cat}/{group}: empty prompt or verdict")
                    page.click("#quiz-next")
                page.click("#quiz-quit")
                page.click("#new-quiz")
    for mode in ("name", "find"):
        choose(page, "category", "anatomy")
        choose(page, "group", "bones")
        choose(page, "mode", mode)
        page.click("#start-go")
        page.fill("#quiz-guess", "femur")
        page.press("#quiz-guess", "Enter")
        verdict = page.inner_text("#quiz-verdict")
        want = "✓" if mode == "name" else "Click"
        if want not in verdict:
            problems.append(f"{mode} all: typing femur gave {verdict!r}")
        page.click("#quiz-reveal")
        page.click("#done-again")
    return problems


def main(gaps):
    # Small, since headless Chrome renders every frame in software.
    with app(800, 600) as page:
        page.wait_for_timeout(500)
        result = page.evaluate(CHECKS, OVERLAYS)
        en = page.evaluate("Object.keys(I18N)")
        problems = play(page)
        errors = page.errors + result["errors"] + problems
    errors += [f"no {key} in en.js (used in index.html or viewer.js)"
               for key in sorted(static_keys() - set(en))]
    for label, rows in (("ERROR", errors), ("warning", result["warnings"])):
        for row in rows:
            print(f"{label}: {row}")
    if gaps:
        print("\n".join(result["info"]))
    print(f"{result['summary']}. {len(errors)} errors, {len(result['warnings'])} warnings.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main("--gaps" in sys.argv[1:]))
