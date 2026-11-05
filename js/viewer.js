// Prototype viewer for the BodyParts3D model in data/bodydata.js.
(function () {
  // t('quiz.wrong', { part: 'Liver' }) fills {part} placeholders.
  const t = (key, vars = {}) => (I18N[key] ?? key).replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '');
  document.querySelectorAll('[data-t]').forEach((el) => { el.textContent = t(el.dataset.t); });
  document.querySelectorAll('[data-t-title]').forEach((el) => { el.title = t(el.dataset.tTitle); });
  document.querySelectorAll('[data-t-placeholder]').forEach((el) => { el.placeholder = t(el.dataset.tPlaceholder); });
  document.querySelectorAll('[data-t-aria-label]').forEach((el) => { el.setAttribute('aria-label', t(el.dataset.tAriaLabel)); });

  const SYSTEM_COLORS = {
    nervous: 0xe8c39e, cardiovascular: 0xc0392b, respiratory: 0xe59aa6,
    digestive: 0xc77d4f, muscular: 0x9e3b3b, urinary: 0xd9b25a,
    endocrine: 0x8e6bbf, reproductive: 0x6b8fbf, skeletal: 0xeee8d5,
    integumentary: 0xd8a98a,
  };
  // Veins (ids ending in _vein or _veins, and the venae cavae) are blue.
  const VEIN_COLOR = 0x2e5aa8;
  const isVein = (pid) => /_veins?$/.test(pid) || pid === 'vena_cava';
  const HIGHLIGHT = 0x36c2ff, RIGHT = 0x3fcf7f, WRONG = 0xff5555, MISSED = 0xffb340;

  const stage = document.getElementById('stage');
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  stage.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x14161a);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x404050, 0.8));
  const sun = new THREE.DirectionalLight(0xffffff, 0.7);
  sun.position.set(1, 2, 3);
  scene.add(sun);

  const camera = new THREE.PerspectiveCamera(35, 1, 0.01, 20);
  camera.position.set(0, 1.0, 3.6);
  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0.9, 0);
  controls.enableDamping = true;
  controls.update();

  function decode(b64, Type) {
    const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    return new Type(bytes.buffer);
  }

  // Dequantise uint16 positions back into body-space metres.
  const { min, scale } = BODY_DATA;
  const allMeshes = [];
  for (const part of BODY_DATA.parts) {
    const q = decode(part.positions, Uint16Array);
    const pos = new Float32Array(q.length);
    for (let i = 0; i < q.length; i++) pos[i] = min[i % 3] + q[i] * scale[i % 3];

    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geom.setIndex(new THREE.BufferAttribute(decode(part.indices, part.index32 ? Uint32Array : Uint16Array), 1));
    geom.computeVertexNormals();

    const skin = part.system === 'integumentary';
    const mat = new THREE.MeshStandardMaterial({
      color: isVein(part.id) ? VEIN_COLOR : SYSTEM_COLORS[part.system], roughness: 0.6, metalness: 0,
      transparent: skin, opacity: skin ? 0.12 : 1, depthWrite: !skin,
      side: skin ? THREE.FrontSide : THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(geom, mat);
    mesh.userData = { part, baseColor: mat.color.getHex() };
    mesh.renderOrder = skin ? 1 : 0;
    scene.add(mesh);
    allMeshes.push(mesh);
  }

  // Male or female body: the shared parts plus the chosen body's own (parts
  // with part.sex). The female one swaps in its own pelvis, so some ids
  // (hip_bone, sacrum) exist once per body. Everything below works on
  // `meshes`, the active body only.
  let meshes = [], meshById = {};
  function setBody(sex) {
    meshes = allMeshes.filter((m) => !m.userData.part.sex || m.userData.part.sex === sex);
    meshById = Object.fromEntries(meshes.map((m) => [m.userData.part.id, m]));
    for (const m of allMeshes) {
      m.userData.hidden = false;
      m.visible = meshes.includes(m);
    }
  }
  setBody('male');

  // Hiding. Right click hides the structure under the cursor; the Hide
  // button and Delete hide the selected one. Every hide is one undoable action holding the meshes it hid:
  // a single structure (hide tool / right click) or a whole system
  // (unticking it in the side panel). A system's box is ticked while any of
  // its structures shows, and half-ticked when only some of them do.
  const hideBtn = document.getElementById('hide-selected');
  const undoBtn = document.getElementById('undo');
  const unhideAllBtn = document.getElementById('unhide-all');
  const submitBtn = document.getElementById('quiz-submit');
  const actions = [];
  const boxes = {};
  hideBtn.addEventListener('click', () => hide(selection));

  function sync() {
    for (const m of meshes) m.visible = !m.userData.hidden;
    for (const [sys, box] of Object.entries(boxes)) {
      const own = meshes.filter((m) => m.userData.part.system === sys);
      const shown = own.filter((m) => m.visible).length;
      box.parentElement.hidden = !own.length;  // a system the chosen body lacks
      box.checked = shown > 0;
      box.indeterminate = shown > 0 && shown < own.length;
    }
    if (selection.some((m) => !m.visible)) setSelection(selection.filter((m) => m.visible));
    undoBtn.disabled = unhideAllBtn.disabled = actions.length === 0;
  }
  function hide(list) {
    const fresh = list.filter((m) => !m.userData.hidden);
    if (!fresh.length) return;
    fresh.forEach((m) => { m.userData.hidden = true; });
    actions.push(fresh);
    sync();
  }
  function unhide(list) {
    list.forEach((m) => { m.userData.hidden = false; });
    // Forget them in past actions so undo doesn't replay a stale hide.
    for (let i = actions.length - 1; i >= 0; i--) {
      actions[i] = actions[i].filter((m) => m.userData.hidden);
      if (!actions[i].length) actions.splice(i, 1);
    }
    sync();
  }
  function undo() {
    if (actions.length) unhide(actions.pop());
  }
  function unhideAll() {
    unhide(meshes);
  }

  const systems = [...new Set(BODY_DATA.parts.map((p) => p.system))];
  const panel = document.getElementById('systems');
  // Each row: the checkbox shows or hides the system; clicking its name
  // shows only that system (one undoable hide of everything else).
  for (const sys of systems) {
    const own = () => meshes.filter((m) => m.userData.part.system === sys);
    const label = sys === 'integumentary' ? t('viewer.skin') : t('system.' + sys);
    const row = document.createElement('div');
    row.className = 'system';
    const box = document.createElement('input');
    box.type = 'checkbox';
    box.checked = true;
    box.setAttribute('aria-label', t('systems.toggle', { system: label }));
    box.addEventListener('change', () => { if (box.checked) unhide(own()); else hide(own()); });
    boxes[sys] = box;
    const solo = document.createElement('button');
    solo.type = 'button';
    solo.title = t('systems.solo', { system: label });
    const swatch = document.createElement('span');
    swatch.className = 'swatch';
    swatch.style.background = '#' + SYSTEM_COLORS[sys].toString(16).padStart(6, '0');
    const name = document.createElement('span');
    name.textContent = label;
    solo.append(swatch, name);
    solo.addEventListener('click', () => {
      unhide(own().filter((m) => m.userData.hidden));
      hide(meshes.filter((m) => m.userData.part.system !== sys));
    });
    row.append(box, solo);
    panel.append(row);
  }

  undoBtn.addEventListener('click', undo);
  unhideAllBtn.addEventListener('click', unhideAll);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !controlsEl.hidden) { closeControls(); return; }
    if (e.target.matches('input, select, textarea') || !startEl.hidden || !doneEl.hidden
      || !controlsEl.hidden) return;
    if ((e.metaKey || e.ctrlKey) && !e.shiftKey && e.key.toLowerCase() === 'z') {
      e.preventDefault();
      undo();
    } else if (e.key === 'Enter' && quizOn && !answered && selection.length) {
      e.preventDefault();
      submit();
    } else if ((e.key === 'Delete' || e.key === 'Backspace') && selection.length) {
      // Mac keyboards send Backspace for the key labelled "delete".
      e.preventDefault();
      hide(selection);
    }
  });

  // Click to pick (skin is ignored so you can click through it).
  const ray = new THREE.Raycaster();
  const picked = document.getElementById('picked');
  const partName = (mesh) => t('part.' + mesh.userData.part.id);
  let selection = [], downAt = null;

  function setSelection(list) {
    selection.forEach((m) => m.material.color.setHex(m.userData.baseColor));
    selection = list;
    selection.forEach((m) => m.material.color.setHex(HIGHLIGHT));
    picked.textContent = selection.length ? selection.map(partName).join(', ')
      : quizOn ? t('quiz.title', { category: t('category.' + settings.category) }) : t('viewer.none');
    hideBtn.hidden = !selection.length;
    submitBtn.disabled = !selection.length;
  }
  function select(mesh) {
    setSelection(mesh ? [mesh] : []);
  }
  function toggle(mesh) {
    if (!mesh) return;
    setSelection(selection.includes(mesh) ? selection.filter((m) => m !== mesh) : [...selection, mesh]);
  }

  function meshAt(e, accept) {
    const r = renderer.domElement.getBoundingClientRect();
    ray.setFromCamera({ x: ((e.clientX - r.left) / r.width) * 2 - 1,
                        y: -((e.clientY - r.top) / r.height) * 2 + 1 }, camera);
    const hit = ray.intersectObjects(meshes.filter((m) => m.visible && accept(m.userData.part)))[0];
    return hit ? hit.object : null;
  }

  renderer.domElement.addEventListener('pointerdown', (e) => { downAt = [e.clientX, e.clientY]; });
  renderer.domElement.addEventListener('pointerup', (e) => {
    // Ignore drags: they rotate (left) or pan (right) the camera.
    if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 4) return;
    if (e.button === 2) {
      const mesh = meshAt(e, (p) => p.system !== 'integumentary');
      if (mesh) hide([mesh]);
    } else if (e.button === 0 && run) {
      pickInRun(meshAt(e, (p) => run.ids.includes(p.id)));
    } else if (e.button === 0) {
      const mesh = meshAt(e, (p) => p.kind === 'target');
      // Once an answer is in, the marks stay put until Next; and a name
      // question can't be picked at all, since picking shows the name.
      if (quizOn && (answered || question.type === 'name')) return;
      if (quizOn && question.answers) toggle(mesh); else select(mesh);
    }
  });
  renderer.domElement.addEventListener('contextmenu', (e) => e.preventDefault());

  // Quiz: show a clue, the player selects the structure(s) it describes and
  // submits. Questions live in i18n/questions.en.js.
  const quizEl = document.getElementById('quiz');
  const q$ = (id) => document.getElementById('quiz-' + id);
  let quizOn = false, deck = [], question = null, answered = false, asked = 0;
  // Chosen on the start screen: category id and number of questions (0 = all).
  // mode: 'quiz', or the timed 'name' (name all) and 'find' (find all).
  // group: which of the category's `groups` (bones, muscles, organs), if it has them.
  const settings = { category: CATEGORIES[0].id, count: 10, body: 'male', mode: 'quiz', group: null };
  const category = () => CATEGORIES.find((c) => c.id === settings.category);
  const group = () => category().groups?.find((g) => g.id === settings.group);
  // One entry per answered question, for the overview at the end.
  let history = [], marked = [];

  function mark(mesh, color) {
    mesh.material.color.setHex(color);
    marked.push(mesh);
  }
  function clearMarks() {
    marked.forEach((m) => m.material.color.setHex(m.userData.baseColor));
    marked = [];
    xray(false);
    Object.values(overlays).forEach((o) => { o.visible = false; });
  }

  // Answer-phase overlays, named by a question's `overlay` field.
  const overlays = { quadrants: buildQuadrants() };
  overlays.quadrants.visible = false;
  scene.add(overlays.quadrants);

  // Abdominal quadrants: a midline and a horizontal line crossing at the
  // navel, drawn on the front of the skin and always on top. The navel sits
  // at roughly the L3/L4 level, 40% of the way up the lumbar spine.
  function buildQuadrants() {
    const spine = new THREE.Box3().setFromObject(meshById.lumbar_vertebrae);
    const y = spine.min.y + 0.4 * (spine.max.y - spine.min.y);
    const probe = new THREE.Raycaster(new THREE.Vector3(0, y, 2), new THREE.Vector3(0, 0, -1));
    const hit = probe.intersectObject(meshById.skin)[0];
    const z = (hit ? hit.point.z : spine.max.z + 0.15) + 0.01;
    const group = new THREE.Group();
    const dashed = new THREE.LineDashedMaterial({ color: 0xffffff, dashSize: 0.02, gapSize: 0.012,
      depthTest: false, transparent: true, opacity: 0.9 });
    const line = (x1, y1, x2, y2) => {
      const l = new THREE.Line(new THREE.BufferGeometry().setFromPoints(
        [new THREE.Vector3(x1, y1, z), new THREE.Vector3(x2, y2, z)]), dashed);
      l.computeLineDistances();
      l.renderOrder = 10;
      return l;
    };
    group.add(line(-0.17, y, 0.17, y), line(0, y - 0.2, 0, y + 0.2));
    // Patient's right is -x (the viewer's left when facing the body).
    for (const [key, sx, sy] of [['ruq', -1, 1], ['luq', 1, 1], ['rlq', -1, -1], ['llq', 1, -1]]) {
      const label = textSprite(t('quadrant.' + key));
      label.position.set(sx * 0.1, y + sy * 0.1, z);
      group.add(label);
    }
    return group;
  }
  function textSprite(text) {
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    ctx.font = 'bold 40px system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineWidth = 6;
    ctx.strokeStyle = 'rgba(0, 0, 0, .7)';
    ctx.strokeText(text, 64, 32);
    ctx.fillStyle = '#fff';
    ctx.fillText(text, 64, 32);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
      map: new THREE.CanvasTexture(canvas), depthTest: false, transparent: true }));
    sprite.scale.set(0.09, 0.045, 1);
    sprite.renderOrder = 11;
    return sprite;
  }
  // While an answer shows, fade everything else so a buried answer is visible.
  function xray(on) {
    for (const m of meshes) {
      if (m.userData.part.system === 'integumentary') continue;
      setOpacity(m, on && !marked.includes(m) ? 0.12 : 1);
    }
  }
  function setOpacity(mesh, opacity) {
    mesh.material.transparent = opacity < 1;
    mesh.material.opacity = opacity;
    mesh.material.depthWrite = opacity === 1;
    mesh.material.needsUpdate = true;
  }
  function shuffled(list) {
    const a = list.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  // Two kinds of question, half and half: clues from i18n/questions.en.js
  // ("find it": pick the part), and "name it" questions made here for every
  // target part, where the part is highlighted and the player types its name.
  const guessInput = q$('guess');
  function questionPool() {
    const clues = shuffled(category().questions.filter((q) =>
      answerIds(q).every((id) => meshById[id] && inCategory(id))));
    // Vessels are too thin to spot through the x-rayed body, so their
    // questions show the cardiovascular system alone.
    const named = shuffled(categoryMeshes().map((m) => m.userData.part.id).map((id) => ({
      id: 'name-' + id, type: 'name', answer: id, topic: 'name',
      ...(structureKind(id) === 'vessel' && { focus: 'cardiovascular' }) })));
    // Alternate the two kinds, so any length is half and half.
    const mixed = [];
    for (let i = 0; i < Math.min(clues.length, named.length); i++) mixed.push(clues[i], named[i]);
    return mixed;
  }
  function buildDeck() {
    const pool = questionPool();
    return shuffled(settings.count ? pool.slice(0, settings.count) : pool);
  }

  // Each question starts from the full body: anything hidden (structures or
  // whole systems) comes back, as with Unhide all.
  // What to call the part in a "name it" prompt: bone, muscle or vessel by
  // system, else organ, with a few exceptions.
  const KIND_OVERRIDES = { costal_cartilage: 'cartilage', heart: 'organ' };
  // (Looked up in either body, so it works for parts the other body has.)
  const systemOf = Object.fromEntries(BODY_DATA.parts.map((p) => [p.id, p.system]));
  const structureKind = (pid) => KIND_OVERRIDES[pid]
    ?? { skeletal: 'bone', muscular: 'muscle', cardiovascular: 'vessel' }[systemOf[pid]] ?? 'organ';
  // Parts made of several structures get "(s)" in the prompt.
  const MANY = new Set(['lungs', 'vena_cava', 'cervical_vertebrae', 'thoracic_vertebrae',
    'lumbar_vertebrae', 'ribs', 'costal_cartilage', 'carpals', 'metacarpals', 'finger_phalanges',
    'tarsals', 'metatarsals', 'toe_phalanges', 'rhomboids', 'forearm_flexors', 'forearm_extensors',
    'erector_spinae', 'iliopsoas', 'adductors', 'fibularis', 'ovary', 'fallopian_tube', 'breast',
    'pulmonary_trunk', 'palmar_arches']);
  // The target parts a category asks about: all of them, or those of the chosen group's `kinds`.
  const inCategory = (pid) => !group() || group().kinds.includes(structureKind(pid));
  const categoryMeshes = () =>
    meshes.filter((m) => m.userData.part.kind === 'target' && inCategory(m.userData.part.id));
  const namePrompt = (pid) =>
    t('quiz.namePrompt.' + structureKind(pid) + (MANY.has(pid) ? '.many' : ''));

  function nextQuestion() {
    clearMarks();
    unhideAll();
    question = deck.pop();
    asked++;
    answered = false;
    q$('progress').textContent = t('quiz.progress', { n: asked, total: asked + deck.length });
    const naming = question.type === 'name';
    // One undoable hide, so Undo or Unhide all brings the rest back.
    const focus = [].concat(question.focus ?? []);
    if (focus.length) hide(meshes.filter((m) => !focus.includes(m.userData.part.system)));
    if (naming) {
      mark(meshById[question.answer], HIGHLIGHT);
      xray(true);
    }
    q$('topic').textContent = t('quiz.topic.' + question.topic);
    q$('prompt').textContent = naming ? namePrompt(question.answer) : question.prompt;
    q$('hint').hidden = !question.answers;
    q$('guess-form').hidden = !naming;
    guessInput.value = '';
    guessInput.disabled = false;
    submitBtn.disabled = true;
    q$('result').hidden = true;
    q$('reveal').hidden = false;
    submitBtn.hidden = false;
    q$('next').hidden = true;
    if (naming) guessInput.focus();
  }

  // A question has one `answer`, or several `answers` (all must be picked)
  // plus `also`: parts that are fine to pick but not required.
  const answerIds = (q) => q.answers ?? [q.answer];
  const names = (list) => list.map(partName).join(', ');

  // chosen: the meshes the player picked, or null when they gave up.
  function finish(chosen) {
    answered = true;
    const required = answerIds(question).map((id) => meshById[id]);
    const allowed = new Set([...required, ...(question.also ?? []).map((id) => meshById[id])]);
    const picks = chosen ?? [];
    const wrong = picks.filter((m) => !allowed.has(m));
    const missed = required.filter((m) => !picks.includes(m));
    const right = picks.length > 0 && !wrong.length && !missed.length;
    history.push({ question, right, given: chosen && names(picks), answer: names(required) });

    unhide(required.filter((m) => m.userData.hidden));
    picks.filter((m) => allowed.has(m)).forEach((m) => mark(m, RIGHT));
    missed.forEach((m) => mark(m, chosen ? MISSED : RIGHT));
    wrong.forEach((m) => mark(m, WRONG));
    xray(true);
    if (question.overlay) overlays[question.overlay].visible = true;

    const verdict = q$('verdict');
    verdict.className = 'quiz-verdict ' + (right ? 'right' : 'wrong');
    if (!question.answers) {
      const target = required[0];
      verdict.textContent = right ? t('quiz.correct', { part: partName(target) })
        : chosen ? t('quiz.wrong', { clicked: partName(picks[0]), part: partName(target) })
        : t('quiz.revealed', { part: partName(target) });
    } else if (right) {
      verdict.textContent = t('quiz.allCorrect', { parts: names(required) });
    } else if (!chosen) {
      verdict.textContent = t('quiz.revealedMany', { parts: names(required) });
    } else {
      verdict.textContent = [
        missed.length ? t('quiz.missed', { parts: names(missed) }) : '',
        wrong.length ? t('quiz.notAnswer', { parts: names(wrong) }) : '',
      ].join(' ').trim();
    }
    showResult(question);
  }

  // Explanation, source and buttons once an answer is in. `about` is the
  // question whose explanation to show, or null for none. Explanations follow
  // on from their clue, so a borrowed one (`withClue`) shows the clue first.
  function showResult(about, withClue = false) {
    q$('clue').textContent = withClue && about ? about.prompt : '';
    q$('clue').hidden = !(withClue && about);
    q$('explain').textContent = about ? about.explain : '';
    q$('explain').hidden = !about;
    q$('source').hidden = !about;
    if (about) {
      const src = SOURCES[about.source];
      q$('source').textContent = t('quiz.source', { title: src.title });
      q$('source').href = about.url ?? src.url;
    }
    q$('result').hidden = false;
    q$('reveal').hidden = true;
    submitBtn.hidden = true;
    guessInput.disabled = true;
    q$('next').textContent = t(deck.length ? 'quiz.next' : 'quiz.finish');
    q$('next').hidden = false;
    q$('next').focus();
  }

  // Name questions: guess is the typed text, or null when they gave up. The
  // explanation borrows a single-answer clue about the same part, if there is one.
  function finishName(guess) {
    answered = true;
    const target = meshById[question.answer];
    const right = guess !== null && nameMatches(guess, question.answer);
    history.push({ question, right, given: guess && guess.trim(), answer: partName(target) });
    clearMarks();
    mark(target, right || guess === null ? RIGHT : WRONG);
    xray(true);
    const verdict = q$('verdict');
    verdict.className = 'quiz-verdict ' + (right ? 'right' : 'wrong');
    verdict.textContent = right ? t('quiz.correct', { part: partName(target) })
      : guess !== null ? t('quiz.nameWrong', { guess: guess.trim(), part: partName(target) })
      : t('quiz.revealed', { part: partName(target) });
    // Single-answer clues only: a "Select the organs of…" prompt reads oddly here.
    const related = shuffled(category().questions.filter((q) => q.answer === question.answer))[0];
    showResult(related ?? null, true);
  }

  // Typed answers: case, accents, punctuation, word order, "the"/"of" and
  // plural -s don't matter, and the display name or any `alias.<id>` counts.
  // Small typos pass only when no other part is as close a match.
  const STOP = new Set(['the', 'of', 'a', 'an', 'and', 'left', 'right']);
  function nameKey(text) {
    return text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
      .split(/[^a-z0-9]+/).filter((w) => w && !STOP.has(w))
      .map((w) => (w.length > 3 ? w.replace(/s$/, '') : w))
      .sort().join(' ');
  }
  const nameKeys = Object.fromEntries(allMeshes.map((m) => {
    const id = m.userData.part.id;
    const aliases = I18N['alias.' + id] ? I18N['alias.' + id].split('|') : [];
    return [id, [t('part.' + id), ...aliases].map(nameKey)];
  }));
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
  function nameMatches(guess, id) {
    const key = nameKey(guess);
    if (!key) return false;
    if (nameKeys[id].includes(key)) return true;
    const best = (pid) => Math.min(...nameKeys[pid].map((k) => distance(key, k)));
    const own = best(id);
    const allowed = key.length >= 10 ? 2 : key.length >= 5 ? 1 : 0;
    return own <= allowed && Object.keys(nameKeys).every((pid) => pid === id || best(pid) > own);
  }

  function submit() {
    if (run) { runGuess(true); return; }
    if (!quizOn || answered) return;
    if (question.type === 'name') {
      if (guessInput.value.trim()) finishName(guessInput.value);
      return;
    }
    if (!selection.length) return;
    const choice = selection;
    setSelection([]);
    finish(choice);
  }

  function setQuiz(on) {
    stopRun();
    quizOn = on;
    quizEl.hidden = !on;
    newQuizBtn.hidden = on;
    select(null);
    clearMarks();
    unhideAll();
    q$('timer').hidden = true;
    lockBody(on && settings.mode !== 'name');
    q$('reveal').textContent = t('quiz.reveal');
    guessInput.placeholder = t('quiz.guessPlaceholder');
    if (on && settings.mode !== 'quiz') {
      startRun();
    } else if (on) {
      history = [];
      deck = buildDeck();
      asked = 0;
      nextQuestion();
    }
  }

  // Start screen: pick a category, mode and length. Explore
  // closes it with the quiz off; "New quiz" brings it back.
  const startEl = document.getElementById('start');
  const startForm = document.getElementById('start-form');
  const doneEl = document.getElementById('done');
  const newQuizBtn = document.getElementById('new-quiz');
  const COUNTS = [5, 10, 20, 0], GROUP_COUNT = 10;
  const choice = (name, value, text, checked, tip) => {
    const label = document.createElement('label');
    label.className = 'choice';
    if (tip) label.title = tip;
    const input = Object.assign(document.createElement('input'), { type: 'radio', name, value, checked });
    const span = document.createElement('span');
    span.textContent = text;
    label.append(input, span);
    return label;
  };
  document.getElementById('start-categories').append(...CATEGORIES.map((c) =>
    choice('category', c.id, t('category.' + c.id), c.id === settings.category, t('category.' + c.id + '.tip'))));
  // Categories with `groups` (Anatomy) ask which one, and offer name all /
  // find all. Their quiz is always GROUP_COUNT questions; only the other
  // categories ask how many.
  const MODES = ['quiz', 'name', 'find'];
  function renderModes() {
    const groups = category().groups;
    if (groups && !group()) settings.group = groups[0].id;
    document.getElementById('start-group-set').hidden = !groups;
    document.getElementById('start-groups').replaceChildren(...(groups ?? []).map((g) =>
      choice('group', g.id, t('group.' + g.id), g.id === settings.group, t('group.' + g.id + '.tip'))));
    const timed = !!groups;
    if (!timed) settings.mode = 'quiz';
    document.getElementById('start-mode-set').hidden = !timed;
    document.getElementById('start-modes').replaceChildren(...MODES.map((m) =>
      choice('mode', m, t('start.mode.' + m), m === settings.mode, t('start.mode.' + m + '.tip'))));
    document.getElementById('start-count-set').hidden = timed;
  }
  // Count options depend on how many questions the category has.
  function renderCounts() {
    const available = questionPool().length;
    const chosen = Number(startForm.elements.count?.value ?? settings.count);
    const counts = COUNTS.filter((n) => n < available);
    const box = document.getElementById('start-counts');
    box.replaceChildren(...counts.map((n) =>
      choice('count', n, n ? String(n) : t('start.countAll', { n: available }), false)));
    const pick = counts.includes(chosen) ? chosen : 0;
    box.querySelector(`input[value="${pick}"]`).checked = true;
  }
  // Male/female toggle, bottom right of the stage. It stays usable over the
  // start screen (the body switches behind it) and in name all, which asks
  // for both bodies' parts, but not in the quiz or find all, where the
  // questions and the parts in play were drawn from the current body.
  const bodyToggle = document.getElementById('body-toggle');
  bodyToggle.append(...['male', 'female'].map((sex) =>
    choice('body', sex, t('body.' + sex), sex === settings.body)));
  bodyToggle.addEventListener('change', (e) => {
    showBody(e.target.value);
    if (!startEl.hidden) renderCounts();
  });
  function showBody(sex) {
    settings.body = sex;
    bodyToggle.querySelector(`input[value="${sex}"]`).checked = true;
    select(null);
    setBody(sex);
    unhideAll();
    if (run) showRunBody();
  }
  function lockBody(locked) {
    bodyToggle.querySelectorAll('input').forEach((input) => { input.disabled = locked; });
    bodyToggle.title = locked ? t('body.locked') : '';
  }
  startForm.addEventListener('change', (e) => {
    if (e.target.name === 'category') settings.category = e.target.value;
    if (e.target.name === 'mode') settings.mode = e.target.value;
    if (e.target.name === 'group') settings.group = e.target.value;
    if (e.target.name === 'category' || e.target.name === 'mode') renderModes();
    if (e.target.name !== 'count') renderCounts();
  });
  function showStart() {
    setQuiz(false);
    doneEl.hidden = true;
    newQuizBtn.hidden = true;
    renderModes();
    renderCounts();
    startEl.hidden = false;
    document.getElementById('start-go').focus();
  }
  startForm.addEventListener('submit', (e) => {
    e.preventDefault();
    Object.assign(settings, {
      category: startForm.elements.category.value,
      count: category().groups ? GROUP_COUNT : Number(startForm.elements.count.value),
      mode: startForm.elements.mode.value,
    });
    startEl.hidden = true;
    setQuiz(true);
  });
  function explore() {
    startEl.hidden = doneEl.hidden = true;
    setQuiz(false);
  }
  document.getElementById('start-explore').addEventListener('click', explore);
  document.getElementById('done-explore').addEventListener('click', explore);
  document.getElementById('done-again').addEventListener('click', showStart);
  newQuizBtn.addEventListener('click', showStart);
  q$('quit').addEventListener('click', explore);

  // Controls popup: opened from the header, closed by its button, Escape or
  // a click on the backdrop. Focus goes back to where it was.
  const controlsEl = document.getElementById('controls');
  let controlsReturn = null;
  function closeControls() {
    controlsEl.hidden = true;
    controlsReturn?.focus();
  }
  document.getElementById('controls-open').addEventListener('click', () => {
    controlsReturn = document.activeElement;
    controlsEl.hidden = false;
    document.getElementById('controls-close').focus();
  });
  document.getElementById('controls-close').addEventListener('click', closeControls);
  controlsEl.addEventListener('click', (e) => { if (e.target === controlsEl) closeControls(); });

  function finishQuiz() {
    const right = history.filter((h) => h.right).length, total = history.length;
    const pct = total ? Math.round((100 * right) / total) : 0;
    document.getElementById('done-title').textContent = t('done.title');
    document.getElementById('done-score').textContent = t('done.score', { right, total, pct });
    // Per-topic tally, then every question with the player's answer.
    const topics = [...new Set(history.map((h) => h.question.topic))];
    document.getElementById('done-topics').replaceChildren(...topics.map((topic) => {
      const of = history.filter((h) => h.question.topic === topic);
      const li = document.createElement('li');
      li.textContent = t('done.topic', {
        topic: t('quiz.topic.' + topic), right: of.filter((h) => h.right).length, total: of.length });
      return li;
    }));
    document.getElementById('done-list').replaceChildren(...history.map((h, i) => {
      const li = document.createElement('li');
      li.className = h.right ? 'right' : 'wrong';
      const prompt = document.createElement('p');
      prompt.className = 'done-prompt';
      prompt.textContent = t('done.number', { n: i + 1 }) + ' ' + (h.question.type === 'name'
        ? namePrompt(h.question.answer) : h.question.prompt);
      const detail = document.createElement('p');
      detail.className = 'done-detail';
      detail.textContent = h.right ? t('done.right', { answer: h.answer })
        : h.given ? t('done.wrong', { given: h.given, answer: h.answer })
        : t('done.revealed', { answer: h.answer });
      li.append(prompt, detail);
      return li;
    }));
    setQuiz(false);
    newQuizBtn.hidden = true;
    doneEl.hidden = false;
    document.getElementById('done-again').focus();
  }

  q$('reveal').addEventListener('click', () => {
    if (run) { endRun('gaveUp'); return; }
    if (answered) return;
    select(null);
    if (question.type === 'name') finishName(null); else finish(null);
  });
  submitBtn.addEventListener('click', submit);
  q$('guess-form').addEventListener('submit', (e) => { e.preventDefault(); submit(); });
  guessInput.addEventListener('input', () => {
    submitBtn.disabled = !guessInput.value.trim();
    if (run) runGuess(false);
  });
  q$('next').addEventListener('click', () => (deck.length ? nextQuestion() : finishQuiz()));

  // Name all / find all: a timed run over every part in the category. The
  // rest of the body is hidden; the category's parts start as faint ghosts
  // and turn solid once named. Name all takes any of them as typed; find all
  // only the one the player clicked (as CountryGuesser's list all / find all).
  // Name all asks for the parts of both bodies (so the organs include the
  // prostate and the uterus alike), and once everything the body on show has
  // is named it switches to the other body for the rest. Find all keeps to
  // the body on show, since every part has to be clicked.
  const RUN_SECONDS = { name: 5 * 60, find: 10 * 60 }, LOW_SECONDS = 60;
  // Unnamed parts are grey, front faces only, so layers don't stack up into
  // a solid body and each named part stands out in its own colour.
  const GHOST = 0.2, GHOST_COLOR = 0xa0a6ae;
  // { mode, ids: part ids in play, found: Set of named part ids,
  //   target: the mesh clicked in find all, ends: ms timestamp, tick }
  let run = null;

  const clock = (s) => Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
  const secondsLeft = () => Math.max(0, Math.ceil((run.ends - Date.now()) / 1000));
  const items = () => t('group.' + settings.group + '.items');
  const pidOf = (m) => m.userData.part.id;
  // Meshes of the run's parts, in the body on show or in both.
  const shownRunMeshes = () => meshes.filter((m) => run.ids.includes(pidOf(m)));
  const allRunMeshes = () => allMeshes.filter((m) => run.ids.includes(pidOf(m)));

  function ghost(mesh) {
    mesh.material.color.setHex(GHOST_COLOR);
    mesh.material.side = THREE.FrontSide;
    setOpacity(mesh, GHOST);
  }
  function solid(mesh) {
    mesh.material.color.setHex(mesh.userData.baseColor);
    mesh.material.side = THREE.DoubleSide;
    setOpacity(mesh, 1);
  }

  function startRun() {
    const pool = settings.mode === 'name'
      ? allMeshes.filter((m) => m.userData.part.kind === 'target' && inCategory(pidOf(m)))
      : categoryMeshes();
    run = { mode: settings.mode, ids: [...new Set(pool.map(pidOf))], found: new Set(), target: null,
      ends: Date.now() + RUN_SECONDS[settings.mode] * 1000, tick: null };
    showRunBody();
    q$('topic').textContent = t('run.' + run.mode + '.title');
    q$('prompt').textContent = t('run.' + run.mode + '.prompt', { total: run.ids.length, items: items() });
    q$('hint').hidden = true;
    q$('guess-form').hidden = false;
    guessInput.value = '';
    guessInput.disabled = false;
    guessInput.placeholder = t('run.' + run.mode + '.placeholder');
    q$('result').hidden = true;
    q$('clue').hidden = q$('explain').hidden = q$('source').hidden = true;
    q$('reveal').textContent = t('run.giveUp');
    q$('reveal').hidden = false;
    submitBtn.hidden = true;
    q$('next').hidden = true;
    q$('timer').hidden = false;
    updateRun();
    run.tick = setInterval(updateRun, 250);
    guessInput.focus();
  }
  // Hide all but the run's parts in the body on show (one undoable hide, so
  // Undo or Unhide all brings the rest back), each ghosted or solid.
  function showRunBody() {
    hide(meshes.filter((m) => !run.ids.includes(pidOf(m))));
    shownRunMeshes().forEach((m) => (run.found.has(pidOf(m)) ? solid(m) : ghost(m)));
  }
  // Name all: when the body on show has nothing left to name but the other
  // body does, show the other one.
  function switchBodyIfDone() {
    if (run.mode !== 'name' || !shownRunMeshes().every((m) => run.found.has(pidOf(m)))) return false;
    const other = settings.body === 'male' ? 'female' : 'male';
    if (allRunMeshes().every((m) => m.userData.part.sex !== other || run.found.has(pidOf(m)))) return false;
    showBody(other);
    return true;
  }
  function stopRun() {
    if (!run) return;
    clearInterval(run.tick);
    allRunMeshes().forEach(solid);
    run = null;
  }
  function updateRun() {
    const left = secondsLeft();
    q$('progress').textContent = t('run.progress', { found: run.found.size, total: run.ids.length });
    q$('timer').textContent = clock(left);
    q$('timer').classList.toggle('low', left <= LOW_SECONDS);
    if (!left) endRun('time');
  }
  function feedback(text, good) {
    const verdict = q$('verdict');
    verdict.className = 'quiz-verdict ' + (good ? 'right' : 'wrong');
    verdict.textContent = text;
    q$('result').hidden = !text;
  }
  function shake(text) {
    guessInput.classList.remove('wrong');
    void guessInput.offsetWidth;  // restart the animation
    guessInput.classList.add('wrong');
    feedback(text, false);
  }

  // Find all: clicking a faded part makes it the one to name; clicking a
  // named one just shows its name, as outside the quiz.
  function pickInRun(mesh) {
    if (run.target) {
      ghost(run.target);
      run.target = null;
    }
    const named = mesh && run.found.has(pidOf(mesh));
    if (!named) select(null);
    if (!mesh) return;
    if (named) { select(mesh); return; }
    if (run.mode !== 'find') return;  // name all: a click would give the name away
    run.target = mesh;
    mesh.material.color.setHex(HIGHLIGHT);
    setOpacity(mesh, 1);
    feedback(t('run.nameIt'), true);
    guessInput.focus();
  }

  function accept(pid) {
    if (run.target && pidOf(run.target) === pid) run.target = null;
    run.found.add(pid);
    shownRunMeshes().filter((m) => pidOf(m) === pid).forEach(solid);
    guessInput.value = '';
    // A part only the other body has: show that body, so the player sees it.
    const elsewhere = !meshById[pid];
    if (elsewhere) showBody(settings.body === 'male' ? 'female' : 'male');
    const switched = !elsewhere && switchBodyIfDone();
    feedback(t(elsewhere ? 'run.shown.' + settings.body : switched ? 'run.switched.' + settings.body : 'run.got',
      { part: t('part.' + pid) }), true);
    updateRun();
    if (run.found.size === run.ids.length) endRun('won');
  }

  // Runs on every keystroke; `force` is Enter. Both modes wait for Enter and
  // take only an exact name or alias (case, accents, punctuation, word order
  // and a plural -s still don't matter; see nameKey). Find all scores only
  // the part the player clicked.
  function runGuess(force) {
    guessInput.classList.remove('wrong');
    if (!force) return;
    const text = guessInput.value;
    const key = nameKey(text);
    if (!key) return;
    const named = (ids) => ids.find((id) => nameKeys[id].includes(key));
    // Without a part clicked, keep the text so it can go in after the click.
    const target = run.target && pidOf(run.target);
    if (run.mode === 'find' && !target) { shake(t('run.clickFirst')); return; }
    guessInput.value = '';

    if (run.mode === 'find') {
      if (nameKeys[target].includes(key)) { accept(target); return; }
      const other = named(Object.keys(nameKeys));
      shake(t(other ? 'run.wrongPart' : 'run.notIt', { guess: text.trim() }));
      return;
    }

    const pid = named(run.ids);
    if (!pid) shake(t('run.notOnList', { guess: text.trim() }));
    else if (run.found.has(pid)) feedback(t('run.already', { part: t('part.' + pid) }), false);
    else accept(pid);
  }

  // why: 'won', 'time' or 'gaveUp'. The overview lists what was missed, then
  // what was named.
  function endRun(why) {
    if (!run) return;
    const { ids, found } = run;
    const left = secondsLeft();
    clearInterval(run.tick);
    const total = ids.length, pct = Math.round((100 * found.size) / total);
    document.getElementById('done-title').textContent = t('done.run.' + why);
    document.getElementById('done-score').textContent =
      t('done.run.score', { found: found.size, total, items: items(), pct })
      + (why === 'won' ? ' ' + t('done.run.left', { time: clock(left) }) : '');
    document.getElementById('done-topics').replaceChildren();
    const name = (pid) => t('part.' + pid);
    const byName = (a, b) => name(a).localeCompare(name(b));
    const missed = ids.filter((pid) => !found.has(pid)).sort(byName);
    document.getElementById('done-list').replaceChildren(...[...missed, ...[...found].sort(byName)].map((pid) => {
      const li = document.createElement('li');
      const got = found.has(pid);
      li.className = got ? 'right' : 'wrong';
      const detail = document.createElement('p');
      detail.className = 'done-detail';
      detail.textContent = t(got ? 'done.right' : 'done.run.missed', { answer: name(pid) });
      li.append(detail);
      return li;
    }));
    setQuiz(false);
    newQuizBtn.hidden = true;
    doneEl.hidden = false;
    document.getElementById('done-again').focus();
  }

  function resize() {
    const { clientWidth: w, clientHeight: h } = stage;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);
  resize();

  renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
  showStart();
})();
