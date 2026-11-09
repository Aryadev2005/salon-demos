// Bleach demo · the styling chair in the booking section.
// It answers the booking flow: pumps up a notch at each step, turns to face you once a time is held,
// spins when the booking is made, and turns away if it's cancelled.
import {
  WebGLRenderer, Scene, PerspectiveCamera, PMREMGenerator, Group, Box3, Vector3, MeshPhysicalMaterial,
  MeshStandardMaterial, MeshBasicMaterial, DirectionalLight, PlaneGeometry, Mesh, ShadowMaterial, CanvasTexture,
  SRGBColorSpace, ACESFilmicToneMapping, PCFShadowMap, Color, MathUtils
} from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const BASE = import.meta.url;
const asset = p => new URL('../' + p, BASE).href;

function shadowTex() {
  const c = document.createElement('canvas'); c.width = c.height = 256;
  const x = c.getContext('2d'), g = x.createRadialGradient(128, 128, 0, 128, 128, 128);
  g.addColorStop(0, 'rgba(23,32,63,.5)'); g.addColorStop(.5, 'rgba(23,32,63,.16)'); g.addColorStop(1, 'rgba(23,32,63,0)');
  x.fillStyle = g; x.fillRect(0, 0, 256, 256);
  const t = new CanvasTexture(c); t.colorSpace = SRGBColorSpace; return t;
}

async function mountChair(stage) {
  const canvas = document.createElement('canvas');
  canvas.className = 'chair-canvas'; canvas.setAttribute('aria-hidden', 'true');
  let r;
  try { r = new WebGLRenderer({ canvas, antialias: true, alpha: true }); } catch (e) { stage.classList.add('no-webgl'); return; }
  stage.prepend(canvas);
  r.setPixelRatio(Math.min(devicePixelRatio || 1, 1.75));
  r.outputColorSpace = SRGBColorSpace; r.toneMapping = ACESFilmicToneMapping; r.toneMappingExposure = 1.05;
  r.shadowMap.enabled = true; r.shadowMap.type = PCFShadowMap;

  const scene = new Scene();
  const pm = new PMREMGenerator(r);
  scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture; scene.environmentIntensity = 0.75;
  pm.dispose();
  const cam = new PerspectiveCamera(24, 1, .1, 60);

  const gltf = await new GLTFLoader().loadAsync(asset('assets/chair.glb'));

  // Karl's station chairs: dusty-rose velvet on chrome
  const velvet = new MeshPhysicalMaterial({ color: new Color('#a55f5b'), roughness: .8, metalness: 0, sheen: 1, sheenRoughness: .45, sheenColor: new Color('#f2c6bd') });
  const panel = velvet.clone(); panel.color = new Color('#96524e');
  const chrome = new MeshStandardMaterial({ color: '#f4f4f4', metalness: 1, roughness: .06 });
  const brushed = new MeshStandardMaterial({ color: '#e6e6e6', metalness: 1, roughness: .22 });
  const parts = { 0: panel, 1: panel, 3: chrome, 5: velvet, 6: brushed, 7: velvet };
  let i = 0;
  gltf.scene.traverse(m => {
    if (!m.isMesh) return;
    if (m.geometry.attributes.position.count < 10) m.visible = false;
    m.material = parts[i] || velvet; m.castShadow = true; m.receiveShadow = true; i++;
  });
  const b = new Box3().setFromObject(gltf.scene), s = b.getSize(new Vector3()), c = b.getCenter(new Vector3());
  gltf.scene.position.sub(c);
  const chair = new Group(); chair.add(gltf.scene); chair.scale.setScalar(2 / s.y); chair.position.y = 1;
  const pivot = new Group(); pivot.add(chair); scene.add(pivot);

  const contact = new Mesh(new PlaneGeometry(2.4, 2.4), new MeshBasicMaterial({ map: shadowTex(), transparent: true, depthWrite: false }));
  contact.rotation.x = -Math.PI / 2; contact.position.y = .002; scene.add(contact);
  const floor = new Mesh(new PlaneGeometry(12, 12), new ShadowMaterial({ opacity: .14 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
  const key = new DirectionalLight('#fff4e6', 1.8);
  key.castShadow = true; key.shadow.mapSize.set(1024, 1024); key.shadow.radius = 8; key.shadow.bias = -.0004;
  Object.assign(key.shadow.camera, { left: -3, right: 3, top: 3, bottom: -3, near: .5, far: 20 });
  key.position.set(2.5, 5.5, 3.5); scene.add(key);
  const rim = new DirectionalLight('#cdd6ff', .7); rim.position.set(-4, 3, -3); scene.add(rim);

  const size = () => {
    const w = stage.clientWidth, h = stage.clientHeight; if (!w || !h) return;
    r.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix();
  };
  new ResizeObserver(size).observe(stage); size();

  // booking state → where the chair should be
  const st = { step: 1, lift: 0, liftT: 0, face: -1.05, faceT: -1.05, spin: 0, spinT: 0, bob: 0 };
  const target = n => {
    st.step = n;
    st.liftT = [0, 0, .06, .12, .18, .18][n] || 0;
    st.faceT = [0, -1.05, -.75, -.45, -.12, 0][n] ?? 0;
  };
  addEventListener('bleach:step', e => target(e.detail));
  addEventListener('bleach:booked', () => { st.spinT += Math.PI * 2; st.bob = 1; });
  addEventListener('bleach:cancelled', () => { st.faceT = -2.2; st.liftT = 0; });

  // drag to turn
  let drag = 0, dragV = 0, dragging = false, lastX = 0, px = 0, pxT = 0;
  stage.addEventListener('pointerdown', e => { dragging = true; lastX = e.clientX; stage.setPointerCapture(e.pointerId); stage.classList.add('grab'); });
  stage.addEventListener('pointermove', e => {
    const bb = stage.getBoundingClientRect(); pxT = ((e.clientX - bb.left) / bb.width) * 2 - 1;
    if (dragging) { dragV = (e.clientX - lastX) * .008; drag += dragV; lastX = e.clientX; }
  });
  const up = () => { dragging = false; stage.classList.remove('grab'); };
  stage.addEventListener('pointerup', up); stage.addEventListener('pointercancel', up);
  stage.addEventListener('pointerleave', () => { pxT = 0; });

  const born = performance.now();
  const tick = t => {
    const age = (t - born) / 1000, k = RM ? 1 : MathUtils.clamp(age / 1.3, 0, 1);
    const ease = RM ? 1 : .07;
    st.lift += (st.liftT - st.lift) * ease;
    st.face += (st.faceT - st.face) * ease;
    st.spin += (st.spinT - st.spin) * (RM ? 1 : .035);
    st.bob *= .97;
    if (!dragging) { dragV *= .93; drag += dragV; drag *= .985; }
    px += (pxT - px) * .05;
    const drop = RM ? 0 : (1 - k) * (1 - k) * 1.4;
    pivot.position.y = drop + st.lift + Math.sin(age * 9) * st.bob * .04;
    pivot.rotation.y = st.face + st.spin + drag + px * .25 + (RM ? 0 : Math.sin(t / 2800) * .025);
    contact.material.opacity = (.3 + .7 * k) * (1 - st.lift * 1.5);
    cam.position.set(0, 1.4, 6.6); cam.lookAt(0, 1.08, 0);
    r.render(scene, cam);
  };
  let on = false, raf = 0;
  const run = t => { tick(t); raf = on ? requestAnimationFrame(run) : 0; };
  new IntersectionObserver(([e]) => { on = e.isIntersecting; if (on && !raf) raf = requestAnimationFrame(run); }, { rootMargin: '100px' }).observe(stage);
  stage.classList.add('is-live');
  target(window.__bleachStep || 1);
}

// load the chair only when the booking section is close, so the hero stays fast
const stage = document.querySelector('[data-chair]');
if (stage) {
  const io = new IntersectionObserver(([e]) => {
    if (!e.isIntersecting) return;
    io.disconnect();
    mountChair(stage).catch(() => stage.classList.add('no-webgl'));
  }, { rootMargin: '600px' });
  io.observe(stage);
}
