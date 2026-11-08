// Luke James demo · three.js scenes (hero chair + menu brush)
import {
  WebGLRenderer, Scene, PerspectiveCamera, PMREMGenerator, Group, Box3, Vector3, Vector2,
  MeshPhysicalMaterial, MeshStandardMaterial, DirectionalLight, PlaneGeometry, Mesh, ShadowMaterial,
  MeshBasicMaterial, CanvasTexture, SRGBColorSpace, ACESFilmicToneMapping, PCFShadowMap, Color, MathUtils,
  CylinderGeometry, Quaternion, Matrix4, EquirectangularReflectionMapping
} from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';

const BASE = (document.currentScript && document.currentScript.src) || import.meta.url;
const asset = p => new URL('../' + p, BASE).href;
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const loader = new GLTFLoader();
let hdrPromise = null;
const loadHDR = () => hdrPromise || (hdrPromise = new HDRLoader().loadAsync(asset('assets/studio.hdr')));

function makeRenderer(canvas) {
  const r = new WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  r.setPixelRatio(Math.min(devicePixelRatio || 1, 1.75));
  r.outputColorSpace = SRGBColorSpace;
  r.toneMapping = ACESFilmicToneMapping;
  r.toneMappingExposure = 1.0;
  return r;
}
async function envFor(r) {
  const t = await loadHDR();
  const pm = new PMREMGenerator(r);
  const env = pm.fromEquirectangular(t).texture;
  pm.dispose();
  return env;
}
function fit(obj, height) {
  const b = new Box3().setFromObject(obj), s = b.getSize(new Vector3()), c = b.getCenter(new Vector3());
  obj.position.sub(c);
  const g = new Group(); g.add(obj);
  g.scale.setScalar(height / s.y);
  return { g, size: s };
}
function radialTex(inner = 'rgba(0,0,0,.55)', outer = 'rgba(0,0,0,0)') {
  const c = document.createElement('canvas'); c.width = c.height = 256;
  const x = c.getContext('2d'), gr = x.createRadialGradient(128, 128, 0, 128, 128, 128);
  gr.addColorStop(0, inner); gr.addColorStop(.55, 'rgba(0,0,0,.18)'); gr.addColorStop(1, outer);
  x.fillStyle = gr; x.fillRect(0, 0, 256, 256);
  const t = new CanvasTexture(c); t.colorSpace = SRGBColorSpace; return t;
}
function sizeTo(r, cam, el) {
  const w = el.clientWidth, h = el.clientHeight;
  if (!w || !h) return;
  r.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix();
}
function visibleLoop(el, tick) {
  let on = false, raf = 0;
  const run = t => { tick(t); raf = on ? requestAnimationFrame(run) : 0; };
  new IntersectionObserver(([e]) => { on = e.isIntersecting; if (on && !raf) raf = requestAnimationFrame(run); }, { rootMargin: '120px' }).observe(el);
}

/* ------------------------------------------------------------------ hexagon LED ceiling (from the salon) */
// flat-top honeycomb of hexagon outlines, each a merged set of 6 thin tubes
function honeycomb(R, rings) {
  const out = [], w = Math.sqrt(3) * R;
  for (let q = -rings; q <= rings; q++) for (let r = Math.max(-rings, -q - rings); r <= Math.min(rings, -q + rings); r++) {
    const x = 1.5 * R * q, z = w * (r + q / 2), pts = [];
    for (let i = 0; i < 6; i++) { const a = Math.PI / 3 * i; pts.push(new Vector3(x + R * Math.cos(a), 0, z + R * Math.sin(a))); }
    out.push({ x, z, pts, d: Math.hypot(x, z) });
  }
  return out;
}
const Y = new Vector3(0, 1, 0);
function hexGeometry(pts, rad, inset = 0) {
  const parts = [];
  for (let i = 0; i < 6; i++) {
    const a = pts[i], b = pts[(i + 1) % 6], len = a.distanceTo(b);
    const g = new CylinderGeometry(rad, rad, len * (1 - inset), 6, 1, true);
    const q = new Quaternion().setFromUnitVectors(Y, b.clone().sub(a).normalize());
    g.applyMatrix4(new Matrix4().compose(a.clone().add(b).multiplyScalar(.5), q, new Vector3(1, 1, 1)));
    parts.push(g);
  }
  return mergeGeometries(parts);
}
function hexCeiling(R = .5, rings = 2, glow = 1) {
  const group = new Group(), cells = [];
  const frame = new MeshStandardMaterial({ color: '#2b2b2b', metalness: .6, roughness: .4 });
  for (const h of honeycomb(R, rings)) {
    const cell = new Group();
    cell.add(new Mesh(hexGeometry(h.pts, .017), frame));
    const strip = new MeshBasicMaterial({ color: new Color(glow, glow, glow), toneMapped: glow <= 1, transparent: glow <= 1, opacity: 1 });
    const s = new Mesh(hexGeometry(h.pts, .019, .02), strip); s.position.y = -.026; cell.add(s);
    cell.userData = { d: h.d, strip }; group.add(cell); cells.push(cell);
  }
  return { group, cells };
}
// studio HDRI plus the hexagon lights, so chrome and leather reflect the ceiling
async function hexEnv(r) {
  const t = await loadHDR(); t.mapping = EquirectangularReflectionMapping;
  const es = new Scene(); es.background = t;
  const { group } = hexCeiling(.55, 2, 9); group.position.y = 3.2; es.add(group);
  const pm = new PMREMGenerator(r); const env = pm.fromScene(es, .012).texture; pm.dispose();
  return env;
}

/* ------------------------------------------------------------------ hero chair */
export async function heroChair(stage, opts = {}) {
  const canvas = stage.querySelector('canvas');
  const r = makeRenderer(canvas);
  r.shadowMap.enabled = true; r.shadowMap.type = PCFShadowMap;
  const scene = new Scene();
  const cam = new PerspectiveCamera(26, 1, .1, 60);
  const [env, gltf] = await Promise.all([hexEnv(r), loader.loadAsync(asset('assets/chair.glb'))]);
  scene.environment = env; scene.environmentIntensity = 0.8;
  const ceil = hexCeiling(.36, 2, 1); ceil.group.position.set(0, 2.42, -.35); ceil.group.rotation.y = .18; scene.add(ceil.group);
  ceil.cells.forEach(c => { c.userData.on = .2 + c.userData.d * .22 + Math.random() * .15; });

  const leather = new MeshPhysicalMaterial({ color: new Color('#585b5e'), roughness: .5, metalness: 0, clearcoat: .35, clearcoatRoughness: .45, sheen: .35, sheenRoughness: .6, sheenColor: new Color('#cfd1d2') });
  const panel = leather.clone(); panel.color = new Color('#525458');
  const chrome = new MeshStandardMaterial({ color: '#f2f2f2', metalness: 1, roughness: .07 });
  const brushed = new MeshStandardMaterial({ color: '#e9e9e9', metalness: 1, roughness: .2 });
  const parts = { 0: panel, 1: panel, 3: chrome, 5: leather, 6: brushed, 7: leather };
  let i = 0;
  gltf.scene.traverse(m => {
    if (!m.isMesh) return;
    const n = m.geometry.attributes.position.count;
    if (n < 10) m.visible = false;
    m.material = parts[i] || leather; m.castShadow = true; m.receiveShadow = true; i++;
  });
  const { g: chair } = fit(gltf.scene, 2);
  chair.position.y = 1; // sits on y = 0
  const pivot = new Group(); pivot.add(chair); scene.add(pivot);

  // floor: soft contact shadow + light-driven shadow
  const contact = new Mesh(new PlaneGeometry(2.6, 2.6), new MeshBasicMaterial({ map: radialTex(), transparent: true, depthWrite: false }));
  contact.rotation.x = -Math.PI / 2; contact.position.y = .002; scene.add(contact);
  const floor = new Mesh(new PlaneGeometry(14, 14), new ShadowMaterial({ opacity: .16 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);

  const key = new DirectionalLight('#fff6ea', 1.7);
  key.castShadow = true; key.shadow.mapSize.set(2048, 2048); key.shadow.radius = 9; key.shadow.blurSamples = 16; key.shadow.bias = -.0004;
  Object.assign(key.shadow.camera, { left: -3, right: 3, top: 3, bottom: -3, near: .5, far: 20 });
  scene.add(key); scene.add(key.target);
  const rim = new DirectionalLight('#dfe8ff', .6); rim.position.set(-4, 3, -4); scene.add(rim);

  const ro = new ResizeObserver(() => sizeTo(r, cam, stage)); ro.observe(stage); sizeTo(r, cam, stage);

  // interaction state
  const ptr = new Vector2(0, 0), ptrT = new Vector2(.35, -.2);
  let drag = 0, dragV = 0, dragging = false, lastX = 0, scrollK = 0, born = performance.now();
  const hero = opts.track || stage;
  hero.addEventListener('pointermove', e => {
    const b = hero.getBoundingClientRect();
    ptrT.set((e.clientX - b.left) / b.width * 2 - 1, -((e.clientY - b.top) / b.height * 2 - 1));
    if (dragging) { dragV = (e.clientX - lastX) * .006; drag += dragV; lastX = e.clientX; }
  });
  stage.addEventListener('pointerdown', e => { dragging = true; lastX = e.clientX; stage.setPointerCapture(e.pointerId); stage.classList.add('grab'); });
  const up = () => { dragging = false; stage.classList.remove('grab'); };
  stage.addEventListener('pointerup', up); stage.addEventListener('pointercancel', up);
  addEventListener('scroll', () => { const b = hero.getBoundingClientRect(); scrollK = MathUtils.clamp(-b.top / b.height, 0, 1); }, { passive: true });

  // labels projected from 3D points
  const tags = [...stage.querySelectorAll('[data-at]')].map(el => ({ el, p: new Vector3(...el.dataset.at.split(',').map(Number)) }));
  const tmp = new Vector3();

  const tick = t => {
    const age = (t - born) / 1000;
    // the lights come on one by one from the middle, with a little flicker
    for (const c of ceil.cells) {
      const u = RM ? 1 : MathUtils.clamp((age - c.userData.on) / .35, 0, 1);
      const fl = u > 0 && u < 1 ? (Math.sin(age * 90 + c.userData.d * 7) > .2 ? 1 : .35) : 1;
      c.userData.strip.opacity = u * fl;
    }
    const age2 = age - (RM ? 0 : .95);
    if (!matchMedia('(hover:hover)').matches && !RM) ptrT.set(Math.sin(t / 2600) * .6, Math.cos(t / 3400) * .3 - .1);
    ptr.lerp(ptrT, .06);
    if (!dragging) { dragV *= .94; drag += dragV; }
    // entrance: drop in on the hydraulic, settle with a little bounce
    const k = RM ? 1 : MathUtils.clamp(age2 / 1.4, 0, 1);
    const drop = RM ? 0 : (1 - k) * (1 - k) * 1.6 - Math.sin(k * Math.PI * 2.2) * (1 - k) * .08;
    pivot.position.y = age2 < 0 ? 3 : drop;
    pivot.rotation.y = -.55 + ptr.x * .38 + drag + scrollK * 1.4 + (RM ? 0 : (1 - k) * 1.2) + (RM ? 0 : Math.sin(t / 3000) * .03);
    pivot.rotation.x = ptr.y * .04;
    contact.material.opacity = .25 + .75 * k;
    // the key light follows the pointer, so the shadow swings across the floor
    key.position.set(ptr.x * 4.5, 5.2 + ptr.y * 1.5, 3.4 - ptr.y * 1.2);
    // camera eases back as you scroll
    cam.position.set(0, 1.2 + scrollK * .6, 8.4 + scrollK * 1.2);
    cam.lookAt(0, 1.02 - scrollK * .1, 0);
    r.render(scene, cam);
    if (window.__snap) { window.__snapData = canvas.toDataURL('image/png'); window.__snap = 0; }
    for (const tg of tags) {
      tmp.copy(tg.p); chair.localToWorld(tmp); tmp.project(cam);
      tg.el.style.transform = `translate(${(tmp.x * .5 + .5) * stage.clientWidth}px, ${(-tmp.y * .5 + .5) * stage.clientHeight}px)`;
    }
  };
  visibleLoop(stage, tick);
  requestAnimationFrame(() => stage.classList.add('ready'));
  return { renderer: r };
}

/* ------------------------------------------------------------------ menu tools (brush, dryer, scissors) */
const TOOLS = {
  scissors: { file: 'assets/scissors.glb', size: 1.38, rot: [.2, .35, -.65], fix(mt) { mt.metalness = 1; mt.roughness = .16; mt.color = new Color('#e4e4e4'); } },
  dryer:    { file: 'assets/dryer.glb',    size: 1.3,  rot: [.12, .95, .05],  fix(mt) { if (mt.roughness < .1) mt.roughness = .14; } },
  brush:    { file: 'assets/brush.glb',    size: 1.6,  rot: [.35, .5, -.45], fix(mt) {
      if (/Aluminum/i.test(mt.name)) { mt.metalness = 1; mt.roughness = .12; mt.color = new Color('#d9d9d9'); }
      if (/Glossy_Black/i.test(mt.name)) { mt.roughness = .18; mt.color = new Color('#0d0d0d'); }
      if (/Matte/i.test(mt.name)) mt.roughness = .7; } },
};
export async function menuTools(stage, first = 'scissors') {
  const canvas = stage.querySelector('canvas');
  const r = makeRenderer(canvas);
  const scene = new Scene();
  const cam = new PerspectiveCamera(28, 1, .05, 50); cam.position.set(0, 0, 4.2);
  scene.environment = await envFor(r); scene.environmentIntensity = 1.05;
  const key = new DirectionalLight('#fff4e6', 1.2); key.position.set(2, 3, 3); scene.add(key);
  const shadow = new Mesh(new PlaneGeometry(2.4, .9), new MeshBasicMaterial({ map: radialTex('rgba(0,0,0,.32)'), transparent: true, depthWrite: false }));
  shadow.position.set(0, -1.05, -.4); shadow.rotation.x = -Math.PI / 2.4; scene.add(shadow);
  new ResizeObserver(() => sizeTo(r, cam, stage)).observe(stage); sizeTo(r, cam, stage);

  const cache = {};
  const load = name => cache[name] || (cache[name] = loader.loadAsync(asset(TOOLS[name].file)).then(g => {
    const T = TOOLS[name], seen = new Set();
    g.scene.traverse(m => { if (m.isMesh && !seen.has(m.material)) { seen.add(m.material); T.fix(m.material); } });
    const b = new Box3().setFromObject(g.scene), s = b.getSize(new Vector3()), c = b.getCenter(new Vector3());
    g.scene.position.sub(c);
    const inner = new Group(); inner.add(g.scene); inner.scale.setScalar(T.size / Math.max(s.x, s.y, s.z));
    const outer = new Group(); outer.add(inner); outer.visible = false; scene.add(outer);
    return { outer, base: T.rot, k: 0 };
  }));
  // each tool has its own spin target; the active one grows in, the others shrink out
  let active = null, want = first, idx = 0;
  const tgt = { y: 0, z: 0 }, cur = { y: -2, z: 0 };
  const items = {};
  async function show(name) {
    want = name;
    const it = await load(name); items[name] = it;
    if (want !== name) return;
    active = name; it.outer.visible = true;
  }
  const api = {
    set(i, name) { idx = i; tgt.y = ((i % 3) - 1) * .55; tgt.z = i % 2 ? .18 : -.12; if (name && name !== want) show(name); },
    preload() { Object.keys(TOOLS).forEach(load); },
  };
  await show(first);
  let last = 0;
  visibleLoop(stage, t => {
    const dt = Math.min(.1, last ? (t - last) / 1000 : .016); last = t;
    const a = RM ? 1 : 1 - Math.exp(-dt * 4.5);
    for (const k in cur) cur[k] += (tgt[k] - cur[k]) * a;
    for (const [name, it] of Object.entries(items)) {
      const on = name === active;
      it.k += ((on ? 1 : 0) - it.k) * (RM ? 1 : 1 - Math.exp(-dt * (on ? 5 : 11)));
      if (!on && it.k < .02) it.k = 0;
      it.outer.visible = it.k > 0;
      const e = it.k * it.k * (3 - 2 * it.k);
      it.outer.scale.setScalar(Math.max(.001, e));
      it.outer.rotation.set(it.base[0], it.base[1] + cur.y + (1 - e) * 2.2, it.base[2] + cur.z);
      it.outer.position.y = (RM ? 0 : Math.sin(t / 900) * .06) - (1 - e) * .5;
    }
    shadow.material.opacity = .4 + .6 * (items[active] ? items[active].k : 0);
    r.render(scene, cam);
  });
  stage.classList.add('ready');
  setTimeout(() => api.preload(), 1500);
  return api;
}

window.LJ3D = { heroChair, menuTools };
window.dispatchEvent(new Event('lj3d'));
