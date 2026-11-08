// Luke James demo · three.js scenes (hero chair + menu brush)
import {
  WebGLRenderer, Scene, PerspectiveCamera, PMREMGenerator, Group, Box3, Vector3, Vector2,
  MeshPhysicalMaterial, MeshStandardMaterial, DirectionalLight, PlaneGeometry, Mesh, ShadowMaterial,
  MeshBasicMaterial, CanvasTexture, SRGBColorSpace, ACESFilmicToneMapping, PCFShadowMap, Color, MathUtils
} from 'three';
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

/* ------------------------------------------------------------------ hero chair */
export async function heroChair(stage, opts = {}) {
  const canvas = stage.querySelector('canvas');
  const r = makeRenderer(canvas);
  r.shadowMap.enabled = true; r.shadowMap.type = PCFShadowMap;
  const scene = new Scene();
  const cam = new PerspectiveCamera(26, 1, .1, 60);
  const [env, gltf] = await Promise.all([envFor(r), loader.loadAsync(asset('assets/chair.glb'))]);
  scene.environment = env; scene.environmentIntensity = 0.95;

  const leather = new MeshPhysicalMaterial({ color: new Color('#6a6d70'), roughness: .5, metalness: 0, clearcoat: .35, clearcoatRoughness: .45, sheen: .35, sheenRoughness: .6, sheenColor: new Color('#cfd1d2') });
  const panel = leather.clone(); panel.color = new Color('#63666a');
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
    if (!matchMedia('(hover:hover)').matches && !RM) ptrT.set(Math.sin(t / 2600) * .6, Math.cos(t / 3400) * .3 - .1);
    ptr.lerp(ptrT, .06);
    if (!dragging) { dragV *= .94; drag += dragV; }
    // entrance: drop in on the hydraulic, settle with a little bounce
    const k = RM ? 1 : MathUtils.clamp(age / 1.4, 0, 1);
    const drop = RM ? 0 : (1 - k) * (1 - k) * 1.6 - Math.sin(k * Math.PI * 2.2) * (1 - k) * .08;
    pivot.position.y = drop;
    pivot.rotation.y = -.55 + ptr.x * .38 + drag + scrollK * 1.4 + (RM ? 0 : (1 - k) * 1.2) + (RM ? 0 : Math.sin(t / 3000) * .03);
    pivot.rotation.x = ptr.y * .04;
    contact.material.opacity = .25 + .75 * k;
    // the key light follows the pointer, so the shadow swings across the floor
    key.position.set(ptr.x * 4.5, 5.2 + ptr.y * 1.5, 3.4 - ptr.y * 1.2);
    // camera eases back as you scroll
    cam.position.set(0, 1.25 + scrollK * .6, 7.9 + scrollK * 1.2);
    cam.lookAt(0, .92 - scrollK * .1, 0);
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

/* ------------------------------------------------------------------ menu brush */
export async function menuBrush(stage) {
  const canvas = stage.querySelector('canvas');
  const r = makeRenderer(canvas);
  const scene = new Scene();
  const cam = new PerspectiveCamera(28, 1, .05, 50); cam.position.set(0, 0, 4.2);
  const [env, gltf] = await Promise.all([envFor(r), loader.loadAsync(asset('assets/brush.glb'))]);
  scene.environment = env; scene.environmentIntensity = 1.05;
  gltf.scene.traverse(m => {
    if (!m.isMesh) return;
    const mt = m.material;
    if (/Aluminum/i.test(mt.name)) { mt.metalness = 1; mt.roughness = .12; mt.color = new Color('#d9d9d9'); }
    if (/Glossy_Black/i.test(mt.name)) { mt.roughness = .18; mt.color = new Color('#0d0d0d'); }
    if (/Matte/i.test(mt.name)) { mt.roughness = .7; }
  });
  // longest axis -> 2 units
  const b = new Box3().setFromObject(gltf.scene), s = b.getSize(new Vector3()), c = b.getCenter(new Vector3());
  gltf.scene.position.sub(c);
  const g = new Group(); g.add(gltf.scene); g.scale.setScalar(1.75 / Math.max(s.x, s.y, s.z));
  const spin = new Group(); spin.add(g); scene.add(spin);
  const shadow = new Mesh(new PlaneGeometry(2.4, .9), new MeshBasicMaterial({ map: radialTex('rgba(0,0,0,.35)'), transparent: true, depthWrite: false }));
  shadow.position.set(0, -1.05, -.4); shadow.rotation.x = -Math.PI / 2.4; scene.add(shadow);
  const key = new DirectionalLight('#fff4e6', 1.2); key.position.set(2, 3, 3); scene.add(key);

  new ResizeObserver(() => sizeTo(r, cam, stage)).observe(stage); sizeTo(r, cam, stage);
  const tgt = { y: .5, z: -.5, x: .35 }, cur = { y: -2, z: -.5, x: .35 };
  const api = { set(i) { tgt.y = .5 + i * 1.05; tgt.z = (i % 2 ? .35 : -.55); tgt.x = .25 + (i % 3) * .12; } };
  visibleLoop(stage, t => {
    for (const k in cur) cur[k] += (tgt[k] - cur[k]) * (RM ? 1 : .07);
    spin.rotation.set(cur.x, cur.y, cur.z);
    spin.position.y = RM ? 0 : Math.sin(t / 900) * .06;
    r.render(scene, cam);
  });
  stage.classList.add('ready');
  return api;
}

window.LJ3D = { heroChair, menuBrush };
window.dispatchEvent(new Event('lj3d'));
