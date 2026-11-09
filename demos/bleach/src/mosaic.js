// Bleach demo · three.js mosaic sign (after the iridescent tile sign in the salon)
import {
  WebGLRenderer, Scene, PerspectiveCamera, PMREMGenerator, InstancedMesh, MeshPhysicalMaterial,
  Object3D, Color, PointLight, DirectionalLight, AmbientLight, SRGBColorSpace, ACESFilmicToneMapping,
  Vector3, Group, Plane, Raycaster, Vector2, InstancedBufferAttribute
} from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;

// seeded random so a given grid always lays the same "hand-laid" tiles
function rng(seed) { let s = seed >>> 0; return () => ((s = Math.imul(s ^ (s >>> 15), 2246822507) ^ Math.imul(s ^ (s >>> 13), 3266489909)) >>> 0) / 4294967296; }

const GOLDS = ['#c99a45', '#b9773b', '#d4a957', '#a8642f', '#d8b468', '#c3874a', '#b58a3c', '#e0bf72', '#9d5a2c', '#c48d55'];
const GLINTS = ['#b06a8a', '#7d6aa8', '#5f8aa0', '#b98a9a'];

async function textMask(cols, rows, word) {
  try { await document.fonts.load('400 120px "Lobster"'); } catch (e) {}
  const S = 10, W = cols * S, H = rows * S;
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const x = c.getContext('2d', { willReadFrequently: true });
  x.fillStyle = '#000'; x.textAlign = 'center'; x.textBaseline = 'middle';
  let size = H * 0.78;
  x.font = `400 ${size}px Lobster, "Brush Script MT", cursive`;
  const maxW = W * (cols / rows > 1.6 ? 0.8 : 0.86);
  const mw = x.measureText(word).width;
  if (mw > maxW) size *= maxW / mw;
  x.font = `400 ${size}px Lobster, "Brush Script MT", cursive`;
  x.fillText(word, W / 2, H * 0.53);
  const d = x.getImageData(0, 0, W, H).data;
  const m = new Uint8Array(cols * rows);
  for (let r = 0; r < rows; r++) for (let q = 0; q < cols; q++) {
    let a = 0, n = 0;
    for (let yy = 2; yy < S; yy += 3) for (let xx = 2; xx < S; xx += 3) { a += d[((r * S + yy) * W + q * S + xx) * 4 + 3]; n++; }
    m[r * cols + q] = a / n > 120 ? 1 : 0;
  }
  return m;
}

export async function mountMosaic(host, opts = {}) {
  const canvas = document.createElement('canvas');
  canvas.className = 'mosaic-canvas';
  canvas.setAttribute('aria-hidden', 'true');
  let renderer;
  try {
    renderer = new WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  } catch (e) { return false; }
  host.appendChild(canvas);
  const mobile = matchMedia('(max-width: 700px)').matches;
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, mobile ? 1.5 : 1.75));
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;

  const scene = new Scene();
  const pm = new PMREMGenerator(renderer);
  scene.environment = pm.fromScene(new RoomEnvironment(), 0.03).texture;
  scene.environmentIntensity = 0.7;
  pm.dispose();

  const cam = new PerspectiveCamera(28, 1, 1, 2000);
  const wall = new Group(); scene.add(wall);

  scene.add(new AmbientLight(0xffffff, 0.15));
  const key = new DirectionalLight(0xfff1dc, 1.2); key.position.set(-30, 40, 60); scene.add(key);
  const spark = new PointLight(0xfff4e0, 0, 0, 1.6); scene.add(spark);

  const geo = new RoundedBoxGeometry(0.9, 0.9, 0.28, 2, 0.08);
  const goldMat = new MeshPhysicalMaterial({
    color: 0xffffff, metalness: 0.82, roughness: 0.26, iridescence: 0.95, iridescenceIOR: 1.7,
    iridescenceThicknessRange: [180, 820], clearcoat: 0.7, clearcoatRoughness: 0.12
  });
  const inkMat = new MeshPhysicalMaterial({ color: 0xffffff, metalness: 0.1, roughness: 0.3, clearcoat: 0.5, clearcoatRoughness: 0.2, envMapIntensity: 0.45 });

  let cols = 0, rows = 0, tiles = [], gold = null, ink = null, born = 0;
  const dummy = new Object3D();

  async function build() {
    const w = host.clientWidth, h = host.clientHeight;
    if (!w || !h) return;
    const px = Math.max(mobile ? 5.5 : 7, Math.min(13, w / 112));
    let c = Math.round(w / px), r = Math.round(h / px);
    const cap = mobile ? 4600 : 6400;
    if (c * r > cap) { const k = Math.sqrt(cap / (c * r)); c = Math.round(c * k); r = Math.round(r * k); }
    if (Math.abs(c - cols) < 3 && Math.abs(r - rows) < 3 && gold) { size(); return; }
    cols = c; rows = r;
    const mask = await textMask(cols, rows, opts.word || 'Bleach');
    if (gold) { wall.remove(gold); wall.remove(ink); gold.dispose(); ink.dispose(); }
    const rand = rng(cols * 7919 + rows);
    const nInk = mask.reduce((a, b) => a + b, 0), nGold = cols * rows - nInk;
    gold = new InstancedMesh(geo, goldMat, nGold);
    ink = new InstancedMesh(geo, inkMat, nInk);
    const col = new Color();
    tiles = [];
    let gi = 0, ii = 0;
    for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
      const isInk = mask[y * cols + x] === 1;
      const t = {
        x: x - (cols - 1) / 2, y: (rows - 1) / 2 - y,
        rx: (rand() - 0.5) * 0.16, ry: (rand() - 0.5) * 0.16, rz: (rand() - 0.5) * 0.05,
        delay: (x / cols) * 1.15 + rand() * 0.35 + (isInk ? 0.25 : 0),
        ph: rand() * 6.283, mesh: isInk ? ink : gold, i: isInk ? ii++ : gi++
      };
      if (isInk) col.set('#0c0b0d').offsetHSL(0, 0, rand() * 0.03);
      else if (rand() < 0.02) col.set(GLINTS[(rand() * GLINTS.length) | 0]).offsetHSL(0, -0.15, 0);
      else col.set(GOLDS[(rand() * GOLDS.length) | 0]).offsetHSL((rand() - 0.5) * 0.02, 0, (rand() - 0.5) * 0.06);
      t.mesh.setColorAt(t.i, col);
      tiles.push(t);
    }
    gold.instanceColor.needsUpdate = true; ink.instanceColor.needsUpdate = true;
    wall.add(gold, ink);
    born = performance.now();
    size();
    host.classList.add('is-live');
  }

  function size() {
    const w = host.clientWidth, h = host.clientHeight;
    renderer.setSize(w, h, false);
    cam.aspect = w / h;
    const vFov = cam.fov * Math.PI / 180;
    const dH = (rows * 1.0) / (2 * Math.tan(vFov / 2));
    const dW = (cols * 1.0) / (2 * Math.tan(vFov / 2) * cam.aspect);
    cam.position.set(0, 0, Math.max(dH, dW) * 0.985);
    cam.lookAt(0, 0, 0);
    cam.updateProjectionMatrix();
  }

  // pointer → point on the wall plane
  const ray = new Raycaster(), ndc = new Vector2(), plane = new Plane(new Vector3(0, 0, 1), 0), hit = new Vector3();
  const ptr = { x: 0, y: 0, tx: 0, ty: 0, on: 0, ton: 0, last: 0 };
  host.addEventListener('pointermove', e => {
    const b = host.getBoundingClientRect();
    ndc.set(((e.clientX - b.left) / b.width) * 2 - 1, -((e.clientY - b.top) / b.height) * 2 + 1);
    ray.setFromCamera(ndc, cam);
    if (ray.ray.intersectPlane(plane, hit)) { ptr.tx = hit.x; ptr.ty = hit.y; ptr.ton = 1; ptr.last = performance.now(); }
  }, { passive: true });
  host.addEventListener('pointerleave', () => { ptr.ton = 0; });

  let scrollK = 0;
  const onScroll = () => {
    const b = host.getBoundingClientRect();
    scrollK = Math.max(0, Math.min(1, -b.top / (b.height * 0.9)));
  };
  addEventListener('scroll', onScroll, { passive: true });

  const ease = p => 1 - Math.pow(1 - p, 3);
  function frame(now) {
    if (!gold) return;
    const t = (now - born) / 1000, T = now / 1000;
    // idle: let the light wander across the sign so it glitters like the real one
    const idle = !ptr.ton || now - ptr.last > 2600;
    if (idle) { ptr.tx = Math.sin(T * 0.35) * cols * 0.38; ptr.ty = Math.cos(T * 0.52) * rows * 0.3; }
    ptr.x += (ptr.tx - ptr.x) * 0.08; ptr.y += (ptr.ty - ptr.y) * 0.08;
    ptr.on += ((idle ? 0.55 : 1) - ptr.on) * 0.05;
    spark.position.set(ptr.x, ptr.y, Math.max(cols, rows) * 0.22);
    spark.intensity = (420 * ptr.on + 60) * (cols / 110) * (cols / 110);

    const sig2 = Math.pow(Math.max(cols, rows) * 0.09, 2);
    for (let k = 0; k < tiles.length; k++) {
      const q = tiles[k];
      const p = RM ? 1 : Math.min(1, Math.max(0, (t - q.delay) / 0.95));
      const e = ease(p);
      const dx = q.x - ptr.x, dy = q.y - ptr.y, f = Math.exp(-(dx * dx + dy * dy) / sig2) * ptr.on;
      const wave = RM ? 0 : Math.sin(T * 0.9 + q.x * 0.13 + q.y * 0.09 + q.ph * 0.15) * 0.035;
      const rip = RM ? 0 : Math.sin(scrollK * 9 - (q.y + rows / 2) * 0.22) * scrollK * 0.5;
      dummy.position.set(q.x, q.y, (1 - e) * 9 + f * 0.55);
      dummy.rotation.set(q.rx + wave - dy * f * 0.05 + rip, q.ry + (1 - e) * Math.PI + dx * f * 0.05, q.rz);
      const s = 0.25 + 0.75 * e;
      dummy.scale.set(s, s, s);
      dummy.updateMatrix();
      q.mesh.setMatrixAt(q.i, dummy.matrix);
    }
    gold.instanceMatrix.needsUpdate = true; ink.instanceMatrix.needsUpdate = true;
    wall.rotation.x = -scrollK * 0.32 + (ptr.y / rows) * 0.05 * ptr.on;
    wall.rotation.y = (ptr.x / cols) * 0.07 * ptr.on;
    renderer.render(scene, cam);
  }

  let on = false, raf = 0;
  const run = n => { frame(n); raf = on ? requestAnimationFrame(run) : 0; };
  new IntersectionObserver(([e]) => { on = e.isIntersecting; if (on && !raf) raf = requestAnimationFrame(run); }, { rootMargin: '80px' }).observe(host);

  let rt = 0;
  new ResizeObserver(() => { clearTimeout(rt); rt = setTimeout(build, 200); }).observe(host);
  await build();
  return true;
}

const host = document.querySelector('[data-mosaic]');
if (host) mountMosaic(host, { word: host.dataset.mosaic || 'Bleach' }).then(ok => { if (!ok) host.classList.add('no-webgl'); }).catch(() => host.classList.add('no-webgl'));
