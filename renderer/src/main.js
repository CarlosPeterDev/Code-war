import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/examples/jsm/utils/SkeletonUtils.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import robotB64 from '../assets/RobotExpressive.glb';

const qs = new URLSearchParams(location.search);
let quality = qs.get('q') || 'medium';
const Q = {
  low:    { pr: 0.75, shadow: 0,    trees: 0.35, aa: false },
  medium: { pr: 1.25, shadow: 1024, trees: 0.7,  aa: true },
  high:   { pr: 2.0,  shadow: 2048, trees: 1.0,  aa: true },
};
const ROBOT_H = 1.5;
const TEAM = [new THREE.Color('#2ea8ff'), new THREE.Color('#ff5a3c')];
const CLS = {
  scout:    { s: 0.78, acc: '#7be0ff' }, miner:    { s: 0.95, acc: '#ffb020' }, builder:  { s: 0.95, acc: '#ffe14a' },
  defender: { s: 1.22, acc: '#9aa7b5' }, support:  { s: 0.95, acc: '#4be08a' }, transport:{ s: 1.05, acc: '#c9a36a' },
  advanced: { s: 1.3,  acc: '#c78bff' },
};
const rnd = (() => { let a = 12345; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; })();

const renderer = new THREE.WebGLRenderer({ antialias: Q[quality].aa, powerPreference: 'high-performance', preserveDrawingBuffer: qs.has('capture') });
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color('#9cc7e8');
const camera = new THREE.PerspectiveCamera(48, 1, 0.3, 400);
camera.position.set(14, 16, 22);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.dampingFactor = 0.12;
controls.minDistance = 5; controls.maxDistance = 70; controls.maxPolarAngle = 1.32; controls.screenSpacePanning = false;
controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };

const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture; scene.environmentIntensity = 0.55;
const hemi = new THREE.HemisphereLight('#cfe6ff', '#4a4030', 0.85); scene.add(hemi);
const sun = new THREE.DirectionalLight('#fff1d6', 2.1); sun.position.set(30, 50, 20); scene.add(sun); scene.add(sun.target);

// ---------- procedural textures (original, generated at runtime)
function noiseTexture(base, var_, size = 128, speck = 900) {
  const c = document.createElement('canvas'); c.width = c.height = size; const g = c.getContext('2d');
  g.fillStyle = base; g.fillRect(0, 0, size, size);
  for (let i = 0; i < speck; i++) {
    const v = (rnd() - 0.5) * var_; g.fillStyle = v > 0 ? `rgba(255,255,255,${v})` : `rgba(0,0,0,${-v})`;
    const r = 1 + rnd() * 3; g.fillRect(rnd() * size, rnd() * size, r, r);
  }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t;
}
const groundTex = noiseTexture('#cfcfcf', 0.55, 128, 1400);
function panelTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 64; const g = c.getContext('2d');
  g.fillStyle = '#16335c'; g.fillRect(0, 0, 64, 64); g.strokeStyle = '#6fa8ff'; g.lineWidth = 2;
  for (let i = 0; i <= 64; i += 16) { g.beginPath(); g.moveTo(i, 0); g.lineTo(i, 64); g.moveTo(0, i); g.lineTo(64, i); g.stroke(); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
const metalTex = noiseTexture('#b9c0c8', 0.35, 64, 500);
const glowTex = (() => { const c = document.createElement('canvas'); c.width = c.height = 64; const g = c.getContext('2d');
  const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.4, 'rgba(255,255,255,0.4)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 64, 64); return new THREE.CanvasTexture(c); })();

// ---------- state
const S = { size: 0, grid: null, palette: null, hq: [], robots: new Map(), structs: new Map(), ores: new Map(), beacons: [], checkpoints: [], dying: [],
  explored: null, visible: null, exploredVer: 0, terrainMesh: null, water: null, trees: null, rocks: null, treeData: [], rockData: [],
  selected: null, tickMs: 250, lastSnap: null, frames: 0, fps: 0, fpsT: performance.now(), ready: false, hmap: null, ring: null };
let gltf = null; let modelH = 1;
const clock = new THREE.Clock();
const pickables = [];
const post = (o) => { try { (window.CWChannel || window.flutter_inappwebview) && window.CWChannel.postMessage(JSON.stringify(o)); } catch (e) {} window.dispatchEvent(new CustomEvent('cw-msg', { detail: o })); };

// ---------- terrain
const tileH = (t) => (t === 2 ? 0.55 : t === 3 ? -0.28 : 0);
function setupTerrain(world) {
  if (S.terrainMesh) { scene.remove(S.terrainMesh); S.terrainMesh.geometry.dispose(); }
  const n = S.size; const g = S.grid;
  const hv = new Float32Array((n + 1) * (n + 1));
  for (let y = 0; y <= n; y++) for (let x = 0; x <= n; x++) {
    let sum = 0, c = 0;
    for (const [dx, dy] of [[-1, -1], [0, -1], [-1, 0], [0, 0]]) { const tx = x + dx, ty = y + dy; if (tx >= 0 && ty >= 0 && tx < n && ty < n) { sum += tileH(g[ty][tx]); c++; } }
    hv[y * (n + 1) + x] = sum / c + (rnd() - 0.5) * 0.12 * (c > 0 && sum / c > 0.2 ? 3 : 1);
  }
  S.hmap = hv;
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * n * 18), 3));
  geo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(n * n * 18), 3));
  geo.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(n * n * 12), 2));
  const uv = geo.attributes.uv.array; let k = 0;
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) { const u0 = x / 4, v0 = y / 4, u1 = (x + 1) / 4, v1 = (y + 1) / 4; [[u0, v0], [u0, v1], [u1, v0], [u1, v0], [u0, v1], [u1, v1]].forEach(([u, v]) => { uv[k++] = u; uv[k++] = v; }); }
  const mat = new THREE.MeshStandardMaterial({ vertexColors: true, map: groundTex, roughness: 0.95, metalness: 0, flatShading: true });
  S.terrainMesh = new THREE.Mesh(geo, mat); S.terrainMesh.receiveShadow = true; scene.add(S.terrainMesh);
  S.tileJitter = new Float32Array(n * n); for (let i = 0; i < n * n; i++) S.tileJitter[i] = 0.9 + rnd() * 0.2;
  if (S.water) scene.remove(S.water);
  S.water = new THREE.Mesh(new THREE.PlaneGeometry(n, n), new THREE.MeshStandardMaterial({ color: S.palette.water, roughness: 0.15, metalness: 0.2, transparent: true, opacity: 0.82 }));
  S.water.rotation.x = -Math.PI / 2; S.water.position.set(n / 2, -0.12, n / 2); scene.add(S.water);
  if (S.voidPlane) scene.remove(S.voidPlane); S.voidPlane = new THREE.Mesh(new THREE.PlaneGeometry(600, 600), new THREE.MeshBasicMaterial({ color: '#0c1117' })); S.voidPlane.rotation.x = -Math.PI / 2; S.voidPlane.position.set(n / 2, -0.4, n / 2); scene.add(S.voidPlane);
  scene.background = new THREE.Color(S.palette.sky); scene.fog = new THREE.Fog(S.palette.sky, 60, 150);
  const half = n / 2; sun.position.set(half + 30, 50, half + 15); sun.target.position.set(half, 0, half);
  applyShadowQuality();
  rebuildTerrain();
}
function applyShadowQuality() {
  const q = Q[quality]; renderer.shadowMap.enabled = q.shadow > 0; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  sun.castShadow = q.shadow > 0;
  if (q.shadow > 0) { const h = Math.max(24, S.size * 0.62); const c = sun.shadow.camera; c.left = -h; c.right = h; c.top = h; c.bottom = -h; c.near = 1; c.far = 160; c.updateProjectionMatrix();
    sun.shadow.mapSize.set(q.shadow, q.shadow); if (sun.shadow.map) { sun.shadow.map.dispose(); sun.shadow.map = null; } sun.shadow.bias = -0.0005; }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, q.pr));
  if (S.terrainMesh) S.terrainMesh.material.needsUpdate = true;
  resize();
}
const colGround = new THREE.Color(), colSand = new THREE.Color(), colRock = new THREE.Color(), colWater = new THREE.Color();
function rebuildTerrain() {
  if (!S.terrainMesh) return;
  const n = S.size, pos = S.terrainMesh.geometry.attributes.position.array, col = S.terrainMesh.geometry.attributes.color.array;
  colGround.set(S.palette.ground); colSand.set(S.palette.sand); colRock.set(S.palette.rock); colWater.set(S.palette.water).multiplyScalar(0.45);
  const unk = new THREE.Color('#0c1117');
  let p = 0, c = 0;
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
    const i = y * n + x; const ex = !S.explored || S.explored[i]; const vi = !S.visible || S.visible[i];
    const t = S.grid[y][x];
    const base = t === 0 ? colGround : t === 1 ? colSand : t === 2 ? colRock : colWater;
    const f = ex ? (vi ? 1 : 0.5) : 0; const j = S.tileJitter[i];
    const hv = (xx, yy) => ex ? S.hmap[yy * (n + 1) + xx] : 0;
    const corners = [[x, y], [x, y + 1], [x + 1, y], [x + 1, y], [x, y + 1], [x + 1, y + 1]];
    for (const [cx, cy] of corners) {
      pos[p++] = cx; pos[p++] = hv(cx, cy); pos[p++] = cy;
      if (ex) { col[c++] = base.r * f * j; col[c++] = base.g * f * j; col[c++] = base.b * f * j; } else { col[c++] = unk.r; col[c++] = unk.g; col[c++] = unk.b; }
    }
  }
  S.terrainMesh.geometry.attributes.position.needsUpdate = true; S.terrainMesh.geometry.attributes.color.needsUpdate = true;
  S.terrainMesh.geometry.computeVertexNormals(); S.terrainMesh.geometry.computeBoundingSphere();
  updateScenery();
}
function groundY(x, y) { const n = S.size; const xi = Math.max(0, Math.min(n - 1, Math.floor(x))), yi = Math.max(0, Math.min(n - 1, Math.floor(y))); if (!S.hmap) return 0;
  const fx = x - xi, fy = y - yi; const h = (a, b) => S.hmap[b * (n + 1) + a]; const top = h(xi, yi) * (1 - fx) + h(xi + 1, yi) * fx; const bot = h(xi, yi + 1) * (1 - fx) + h(xi + 1, yi + 1) * fx; return Math.max(-0.1, top * (1 - fy) + bot * fy); }

// ---------- scenery (instanced trees / rocks, hidden in unexplored tiles)
function setupScenery(world) {
  for (const m of [S.trees, S.rocks, S.trunks]) if (m) scene.remove(m);
  const n = S.size; const keepTrees = world.trees.filter(() => rnd() < Q[quality].trees);
  S.treeData = keepTrees.map(([x, y]) => ({ x, y, s: 0.7 + rnd() * 0.7, r: rnd() * 6.28, ox: 0.2 + rnd() * 0.6, oy: 0.2 + rnd() * 0.6 }));
  S.rockData = []; for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) if (S.grid[y][x] === 2) S.rockData.push({ x, y, s: 0.55 + rnd() * 0.5, r: rnd() * 6.28, ox: 0.5, oy: 0.5 });
  const leaf = new THREE.MeshStandardMaterial({ color: '#2f7d3a', roughness: 0.9, flatShading: true });
  const trunk = new THREE.MeshStandardMaterial({ color: '#5b3f26', roughness: 1 });
  S.trees = new THREE.InstancedMesh(new THREE.ConeGeometry(0.42, 1.25, 6).translate(0, 1.15, 0), leaf, Math.max(1, S.treeData.length));
  S.trunks = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.07, 0.1, 0.55, 5).translate(0, 0.27, 0), trunk, Math.max(1, S.treeData.length));
  const rockMat = new THREE.MeshStandardMaterial({ color: S.palette.rock, roughness: 0.95, flatShading: true, map: metalTex });
  S.rocks = new THREE.InstancedMesh(new THREE.DodecahedronGeometry(0.62, 0).translate(0, 0.25, 0), rockMat, Math.max(1, S.rockData.length));
  for (const m of [S.trees, S.trunks, S.rocks]) { m.castShadow = true; m.receiveShadow = true; scene.add(m); }
}
const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _s = new THREE.Vector3(), _p = new THREE.Vector3(), _e = new THREE.Euler();
function updateScenery() {
  if (!S.trees) return; const n = S.size;
  const place = (mesh, data, wide) => data.forEach((d, i) => {
    const ex = !S.explored || S.explored[d.y * n + d.x];
    const sc = ex ? d.s : 0.0001;
    _p.set(d.x + d.ox, ex ? groundY(d.x + d.ox, d.y + d.oy) : 0, d.y + d.oy); _e.set(0, d.r, 0); _q.setFromEuler(_e); _s.set(sc * (wide ? 1.1 : 1), sc * (wide ? 0.9 + (d.r % 1) * 0.6 : 1), sc * (wide ? 1.1 : 1));
    _m.compose(_p, _q, _s); mesh.setMatrixAt(i, _m);
  });
  place(S.trees, S.treeData, false); place(S.trunks, S.treeData, false); place(S.rocks, S.rockData, true);
  S.trees.instanceMatrix.needsUpdate = S.trunks.instanceMatrix.needsUpdate = S.rocks.instanceMatrix.needsUpdate = true;
  S.trees.count = S.trunks.count = S.treeData.length; S.rocks.count = S.rockData.length;
}

// ---------- materials shared by structures
const M = {
  steel: new THREE.MeshStandardMaterial({ color: '#8d97a3', metalness: 0.55, roughness: 0.45, map: metalTex }),
  dark: new THREE.MeshStandardMaterial({ color: '#39414b', metalness: 0.6, roughness: 0.5 }),
  panel: new THREE.MeshStandardMaterial({ map: panelTexture(), metalness: 0.7, roughness: 0.25 }),
  orange: new THREE.MeshStandardMaterial({ color: '#d98a2b', metalness: 0.3, roughness: 0.6 }),
  crystal: (c) => new THREE.MeshStandardMaterial({ color: c, emissive: c, emissiveIntensity: 0.7, roughness: 0.25, metalness: 0.1, flatShading: true }),
};
const teamMat = (t, e = 0.6) => new THREE.MeshStandardMaterial({ color: TEAM[t], emissive: TEAM[t], emissiveIntensity: e, roughness: 0.4 });
const mk = (geo, mat, x = 0, y = 0, z = 0) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; return m; };

function buildStructure(kind, team) {
  const g = new THREE.Group(); g.userData.parts = {};
  if (kind === 'hq') {
    g.add(mk(new THREE.BoxGeometry(3.2, 0.25, 3.2), M.dark, 0, 0.12, 0));
    g.add(mk(new THREE.BoxGeometry(2.2, 1.2, 2.2), M.steel, 0, 0.85, 0));
    g.add(mk(new THREE.BoxGeometry(2.4, 0.12, 2.4), teamMat(team, 0.4), 0, 1.5, 0));
    for (const [sx, sz] of [[-1.35, -1.35], [1.35, -1.35], [-1.35, 1.35], [1.35, 1.35]]) { g.add(mk(new THREE.CylinderGeometry(0.2, 0.26, 1.7, 8), M.dark, sx, 0.95, sz)); g.add(mk(new THREE.SphereGeometry(0.2, 10, 8), teamMat(team, 1.2), sx, 1.9, sz)); }
    const core = mk(new THREE.IcosahedronGeometry(0.5, 0), teamMat(team, 1.3), 0, 2.2, 0); g.add(core); g.userData.parts.core = core;
    g.add(mk(new THREE.CylinderGeometry(0.1, 0.1, 0.9, 6), M.dark, 0, 1.95, 0));
  } else if (kind === 'turret') {
    g.add(mk(new THREE.CylinderGeometry(0.42, 0.52, 0.35, 10), M.dark, 0, 0.17, 0));
    g.add(mk(new THREE.CylinderGeometry(0.3, 0.38, 0.3, 10), M.steel, 0, 0.5, 0));
    const head = new THREE.Group(); head.position.y = 0.78; head.add(mk(new THREE.SphereGeometry(0.3, 12, 8, 0, Math.PI * 2, 0, Math.PI / 1.7), teamMat(team, 0.25), 0, 0, 0));
    const barrel = mk(new THREE.CylinderGeometry(0.06, 0.08, 0.85, 8).rotateX(Math.PI / 2).translate(0, 0, 0.55), M.dark, 0, 0.08, 0); head.add(barrel);
    head.add(mk(new THREE.SphereGeometry(0.07, 8, 6), teamMat(team, 1.5), 0, 0.08, 1.0)); g.add(head); g.userData.parts.head = head;
  } else if (kind === 'wall') {
    g.add(mk(new THREE.BoxGeometry(0.96, 0.85, 0.96), M.steel, 0, 0.42, 0)); g.add(mk(new THREE.BoxGeometry(1.0, 0.12, 1.0), M.dark, 0, 0.88, 0));
    g.add(mk(new THREE.BoxGeometry(0.98, 0.08, 0.98), teamMat(team, 0.35), 0, 0.62, 0));
  } else if (kind === 'solar') {
    g.add(mk(new THREE.CylinderGeometry(0.08, 0.1, 0.55, 6), M.dark, 0, 0.27, 0));
    const pan = mk(new THREE.BoxGeometry(1.0, 0.06, 0.78), M.panel, 0, 0.62, 0); pan.rotation.x = -0.45; g.add(pan);
    g.add(mk(new THREE.BoxGeometry(1.04, 0.04, 0.04), teamMat(team, 0.6), 0, 0.5, 0.33));
  } else if (kind === 'refinery') {
    g.add(mk(new THREE.BoxGeometry(1.0, 0.18, 1.0), M.dark, 0, 0.09, 0));
    g.add(mk(new THREE.CylinderGeometry(0.28, 0.28, 0.9, 12), M.steel, -0.2, 0.6, 0.1)); g.add(mk(new THREE.CylinderGeometry(0.22, 0.22, 0.7, 12), M.orange, 0.25, 0.5, -0.15));
    g.add(mk(new THREE.CylinderGeometry(0.07, 0.09, 1.3, 8), M.dark, 0.25, 1.35, 0.25)); g.add(mk(new THREE.SphereGeometry(0.09, 8, 6), new THREE.MeshStandardMaterial({ color: '#ff7a1a', emissive: '#ff5a00', emissiveIntensity: 1.6 }), 0.25, 2.02, 0.25));
    g.add(mk(new THREE.CylinderGeometry(0.04, 0.04, 0.6, 6).rotateZ(Math.PI / 2), M.dark, 0.02, 0.85, 0.0)); g.add(mk(new THREE.BoxGeometry(0.96, 0.06, 0.08), teamMat(team, 0.5), 0, 0.2, 0.46));
  } else if (kind === 'factory') {
    g.add(mk(new THREE.BoxGeometry(1.0, 0.18, 1.0), M.dark, 0, 0.09, 0)); g.add(mk(new THREE.BoxGeometry(0.92, 0.85, 0.92), M.steel, 0, 0.6, 0));
    for (let i = 0; i < 3; i++) { const r = mk(new THREE.BoxGeometry(0.3, 0.3, 0.92), M.dark, -0.3 + i * 0.3, 1.14, 0); r.rotation.z = 0.5; g.add(r); }
    g.add(mk(new THREE.CylinderGeometry(0.1, 0.12, 1.1, 8), M.dark, 0.32, 1.45, -0.28)); g.add(mk(new THREE.BoxGeometry(0.34, 0.5, 0.05), teamMat(team, 0.7), -0.18, 0.4, 0.47));
  }
  return g;
}

// ---------- bars / sprites
const barBgMat = new THREE.SpriteMaterial({ color: 0x0b0f14, depthTest: false, transparent: true, opacity: 0.85 });
function makeBar() { const bg = new THREE.Sprite(barBgMat); bg.scale.set(0.9, 0.11, 1); bg.renderOrder = 10; const fg = new THREE.Sprite(new THREE.SpriteMaterial({ color: 0x38e07b, depthTest: false })); fg.center.set(0, 0.5); fg.renderOrder = 11; const grp = new THREE.Group(); grp.add(bg); grp.add(fg); grp.userData = { bg, fg }; grp.visible = false; return grp; }
function setBar(grp, frac, color) { frac = Math.max(0, Math.min(1, frac)); const { fg } = grp.userData; fg.scale.set(0.84 * frac, 0.07, 1); fg.position.set(-0.42, 0, 0.001); fg.material.color.set(color || (frac > 0.5 ? 0x38e07b : frac > 0.25 ? 0xf2c230 : 0xff4d3d)); }

// ---------- robots
function accessories(cls, team, H) {
  const g = new THREE.Group(); const acc = new THREE.Color(CLS[cls].acc); const am = new THREE.MeshStandardMaterial({ color: acc, roughness: 0.5, metalness: 0.3 });
  const add = (m) => { m.castShadow = true; g.add(m); return m; };
  if (cls === 'scout') { add(mk(new THREE.CylinderGeometry(0.015, 0.015, 0.7, 5), M.dark, 0.15, H * 1.05, -0.1)); add(mk(new THREE.SphereGeometry(0.05, 8, 6), teamMat(team, 1.4), 0.15, H * 1.05 + 0.35, -0.1)); }
  if (cls === 'miner') { add(mk(new THREE.BoxGeometry(0.46, 0.5, 0.3), am, 0, H * 0.62, -0.38)); add(mk(new THREE.ConeGeometry(0.1, 0.4, 8).rotateX(Math.PI / 2), M.dark, 0.38, H * 0.5, 0.25)); }
  if (cls === 'builder') { add(mk(new THREE.SphereGeometry(0.27, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2), am, 0, H * 0.99, 0.0)); add(mk(new THREE.BoxGeometry(0.62, 0.04, 0.12), am, 0, H * 0.98, 0.27)); }
  if (cls === 'defender') { for (const sx of [-0.42, 0.42]) add(mk(new THREE.BoxGeometry(0.12, 0.38, 0.5), am, sx, H * 0.78, 0)); add(mk(new THREE.BoxGeometry(0.62, 0.34, 0.1), M.dark, 0, H * 0.58, 0.31)); }
  if (cls === 'support') { add(mk(new THREE.BoxGeometry(0.34, 0.09, 0.05), am, 0, H * 0.62, 0.34)); add(mk(new THREE.BoxGeometry(0.09, 0.34, 0.05), am, 0, H * 0.62, 0.34)); }
  if (cls === 'transport') { add(mk(new THREE.BoxGeometry(0.8, 0.5, 0.55), am, 0, H * 0.58, -0.5)); add(mk(new THREE.BoxGeometry(0.82, 0.06, 0.57), M.dark, 0, H * 0.84, -0.5)); }
  if (cls === 'advanced') { for (const sx of [-0.46, 0.46]) add(mk(new THREE.CylinderGeometry(0.07, 0.09, 0.55, 8).rotateX(Math.PI / 2), M.dark, sx, H * 0.84, 0.15)); const halo = mk(new THREE.TorusGeometry(0.3, 0.025, 6, 20).rotateX(Math.PI / 2), new THREE.MeshBasicMaterial({ color: acc }), 0, H * 1.12, 0); g.add(halo); g.userData.halo = halo; }
  return g;
}
function createRobot(d) {
  const root = new THREE.Group(); const body = SkeletonUtils.clone(gltf.scene); const sc = (ROBOT_H / modelH) * CLS[d.cls].s; body.scale.setScalar(sc);
  body.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; o.frustumCulled = false; const mats = Array.isArray(o.material) ? o.material : [o.material]; const nm = mats.map((m) => { const c = m.clone(); if (c.name === 'Main') { c.color.copy(TEAM[d.team]).lerp(new THREE.Color(CLS[d.cls].acc), 0.08); c.emissive = TEAM[d.team].clone().multiplyScalar(0.05); c.metalness = 0.15; c.roughness = 0.55; } return c; }); o.material = Array.isArray(o.material) ? nm : nm[0]; } });
  root.add(body); const H = CLS[d.cls].s; const acc = accessories(d.cls, d.team, H); acc.scale.setScalar(ROBOT_H); root.add(acc);
  const lod = mk(new THREE.CylinderGeometry(0.26, 0.34, 1.0, 6), teamMat(d.team, 0.12), 0, 0.5 * ROBOT_H * H, 0); lod.scale.set(H, ROBOT_H * H, H); lod.visible = false; root.add(lod);
  const ring = new THREE.Mesh(new THREE.RingGeometry(0.46, 0.56, 28).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.0, depthWrite: false })); ring.position.y = 0.03; root.add(ring);
  const bar = makeBar(); bar.position.y = ROBOT_H * H * 1.12 + 0.3; root.add(bar);
  const mixer = new THREE.AnimationMixer(body); const actions = {}; for (const clip of gltf.animations) { actions[clip.name] = mixer.clipAction(clip); }
  const r = { id: d.id, root, body, acc, lod, mixer, actions, cur: null, bar, ring, cls: d.cls, team: d.team, tx: d.x + 0.5, tz: d.y + 0.5, face: d.facing || 0, H, last: d, dead: 0, isLod: false };
  root.position.set(d.x + 0.5, groundY(d.x + 0.5, d.y + 0.5), d.y + 0.5); root.userData.pick = { kind: 'robot', id: d.id }; root.traverse((o) => { o.userData.pickRoot = root; });
  play(r, 'Idle'); scene.add(root); pickables.push(root); return r;
}
function play(r, name, opts = {}) {
  if (r.cur === name) return; const next = r.actions[name]; if (!next) return; const prev = r.actions[r.cur];
  next.reset(); next.enabled = true; next.setEffectiveTimeScale(opts.speed || 1); next.setEffectiveWeight(1);
  if (name === 'Death') { next.setLoop(THREE.LoopOnce, 1); next.clampWhenFinished = true; } else next.setLoop(THREE.LoopRepeat, Infinity);
  if (prev) prev.crossFadeTo(next, 0.2, false); next.play(); r.cur = name;
}
const ANIM = { move: ['Walking', 1.0], attack: ['Punch', 1.3], mine: ['Punch', 0.6], build: ['Punch', 0.5], repair: ['Wave', 1.0], deposit: ['ThumbsUp', 1.0], share: ['Wave', 1.0], recharge: ['Standing', 1], idle: ['Idle', 1] };
function updateRobot(r, d) {
  r.last = d; r.tx = d.x + 0.5; r.tz = d.y + 0.5; r.face = d.facing;
  const a = ANIM[d.action] || ANIM.idle; const fast = (d.cls === 'scout' || d.cls === 'transport') && d.action === 'move';
  play(r, fast ? 'Running' : a[0], { speed: a[1] });
  const frac = d.hp / d.maxhp; const show = frac < 0.999 || S.selected === d.id; r.bar.visible = show; if (show) setBar(r.bar, frac);
}
function removeRobot(r, instant) { if (instant) { scene.remove(r.root); const i = pickables.indexOf(r.root); if (i >= 0) pickables.splice(i, 1); return; } r.dead = 1.4; r.bar.visible = false; r.ring.material.opacity = 0; play(r, 'Death'); const i = pickables.indexOf(r.root); if (i >= 0) pickables.splice(i, 1); S.dying.push(r); }

// ---------- structures / ore / markers
function syncStructures(list) {
  const seen = new Set();
  for (const d of list) {
    seen.add(d.id); let s = S.structs.get(d.id);
    if (!s) { const grp = buildStructure(d.kind, d.team); grp.position.set(d.x + 0.5, groundY(d.x + 0.5, d.y + 0.5), d.y + 0.5); if (d.kind === 'hq') grp.position.set(d.x + 0.5, groundY(d.x + 0.5, d.y + 0.5), d.y + 0.5);
      const bar = makeBar(); bar.position.y = d.kind === 'hq' ? 3.0 : 1.7; grp.add(bar); grp.userData.pick = { kind: 'structure', id: d.id }; grp.traverse((o) => { o.userData.pickRoot = grp; }); scene.add(grp); pickables.push(grp); s = { grp, bar, d, born: performance.now() }; S.structs.set(d.id, s); }
    s.d = d; const frac = d.hp / d.maxhp; const build = d.built ? 1 : Math.max(0.08, frac);
    s.grp.scale.set(1, build, 1); s.bar.scale.set(1, 1 / build, 1); s.bar.visible = !d.built || frac < 0.999; if (s.bar.visible) setBar(s.bar, frac, d.built ? undefined : 0x4aa3ff);
    if (s.grp.userData.parts.head && d.angle !== undefined) s.grp.userData.parts.head.rotation.y = Math.PI / 2 - d.angle;
  }
  for (const [id, s] of S.structs) if (!seen.has(id)) { burst(s.grp.position.x, 0.8, s.grp.position.z, 0xffa040, 26, 3.2); scene.remove(s.grp); const i = pickables.indexOf(s.grp); if (i >= 0) pickables.splice(i, 1); S.structs.delete(id); }
}
function crystalGroup(color) { const g = new THREE.Group(); const m = M.crystal(color); for (let i = 0; i < 4; i++) { const c = mk(new THREE.OctahedronGeometry(0.2 + rnd() * 0.12, 0).scale(0.7, 1.7 + rnd() * 0.8, 0.7), m, (rnd() - 0.5) * 0.45, 0.28, (rnd() - 0.5) * 0.45); c.rotation.y = rnd() * 3; c.rotation.z = (rnd() - 0.5) * 0.4; g.add(c); } return g; }
function syncOre(list) {
  const seen = new Set();
  for (const o of list) { seen.add(o.id); let e = S.ores.get(o.id);
    if (!e) { const grp = crystalGroup('#ffc233'); grp.position.set(o.x + 0.5, groundY(o.x + 0.5, o.y + 0.5), o.y + 0.5); grp.userData.pick = { kind: 'resource', id: o.id }; grp.traverse((x) => { x.userData.pickRoot = grp; }); scene.add(grp); pickables.push(grp); e = { grp }; S.ores.set(o.id, e); }
    const k = 0.45 + 0.75 * Math.min(1, o.amount / Math.max(1, o.max)); e.grp.scale.setScalar(k); e.amount = o.amount; }
  for (const [id, e] of S.ores) if (!seen.has(id)) { scene.remove(e.grp); const i = pickables.indexOf(e.grp); if (i >= 0) pickables.splice(i, 1); S.ores.delete(id); }
}
let markers = [];
function syncMarkers(beacons, cps) {
  for (const m of markers) scene.remove(m); markers = [];
  for (const b of beacons) { const g = new THREE.Group(); const col = b.found ? '#4be08a' : '#ffd24a';
    g.add(mk(new THREE.CylinderGeometry(0.08, 0.14, 2.2, 8), new THREE.MeshStandardMaterial({ color: col, emissive: col, emissiveIntensity: 0.8 }), 0, 1.1, 0)); const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: col, blending: THREE.AdditiveBlending, depthWrite: false })); s.scale.set(1.8, 1.8, 1); s.position.y = 2.3; g.add(s);
    g.position.set(b.x + 0.5, groundY(b.x + 0.5, b.y + 0.5), b.y + 0.5); g.userData.beacon = true; scene.add(g); markers.push(g); }
  cps.forEach((c, i) => { const g = new THREE.Group(); const t = mk(new THREE.TorusGeometry(0.8, 0.07, 8, 28), new THREE.MeshStandardMaterial({ color: '#ffd24a', emissive: '#ffb000', emissiveIntensity: 0.9 }), 0, 0.9, 0); g.add(t);
    const cv = document.createElement('canvas'); cv.width = cv.height = 64; const x = cv.getContext('2d'); x.fillStyle = '#fff'; x.font = 'bold 44px sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(String(i + 1), 32, 34);
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(cv), depthTest: false })); sp.scale.set(0.8, 0.8, 1); sp.position.y = 2.0; g.add(sp);
    g.position.set(c[0] + 0.5, groundY(c[0] + 0.5, c[1] + 0.5), c[1] + 0.5); scene.add(g); markers.push(g); });
}

// ---------- effects (pooled)
const FX = { beams: [], sparks: [] };
for (let i = 0; i < 24; i++) { const geo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3(0, 0, 1)]); const l = new THREE.Line(geo, new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, depthWrite: false })); l.visible = false; l.frustumCulled = false; scene.add(l); FX.beams.push({ l, t: 0 }); }
const sparkMat = (c) => new THREE.SpriteMaterial({ map: glowTex, color: c, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true });
for (let i = 0; i < 120; i++) { const s = new THREE.Sprite(sparkMat(0xffffff)); s.visible = false; scene.add(s); FX.sparks.push({ s, t: 0, v: new THREE.Vector3(), life: 1 }); }
function beam(fx, fy, tx, ty, color, kind) {
  const b = FX.beams.find((x) => x.t <= 0); if (!b) return; const y0 = groundY(fx + 0.5, fy + 0.5) + (kind === 'turret' ? 1.0 : 0.75), y1 = groundY(tx + 0.5, ty + 0.5) + 0.6;
  const p = b.l.geometry.attributes.position; p.setXYZ(0, fx + 0.5, y0, fy + 0.5); p.setXYZ(1, tx + 0.5, y1, ty + 0.5); p.needsUpdate = true; b.l.material.color.set(color); b.l.material.opacity = 1; b.l.visible = true; b.t = 0.16;
  burst(tx + 0.5, y1, ty + 0.5, color, 4, 1.4);
}
function burst(x, y, z, color, n, speed) { for (let i = 0; i < n; i++) { const s = FX.sparks.find((q) => q.t <= 0); if (!s) return; s.s.material.color.set(color); s.s.position.set(x, y, z); s.v.set((rnd() - 0.5) * speed, rnd() * speed * 0.8 + 0.3, (rnd() - 0.5) * speed); s.life = s.t = 0.5 + rnd() * 0.5; s.s.scale.setScalar(0.35 + rnd() * 0.3); s.s.visible = true; } }
function handleEvents(evs) {
  for (const e of evs || []) {
    if (e.t === 'attack') beam(e.fx, e.fy, e.tx, e.ty, e.team === 0 ? 0x66d4ff : 0xff7a4a, e.kind);
    else if (e.t === 'death') burst(e.x + 0.5, groundY(e.x + 0.5, e.y + 0.5) + 0.6, e.y + 0.5, 0xffa040, e.struct ? 30 : 16, 3.0);
    else if (e.t === 'mine') burst(e.x + 0.5, groundY(e.x + 0.5, e.y + 0.5) + 0.6, e.y + 0.5, 0xffc233, 3, 1.2);
    else if (e.t === 'deposit') burst(e.x + 0.5, 1.0, e.y + 0.5, 0xffe27a, 6, 1.6);
    else if (e.t === 'repair') burst(e.x + 0.5, 0.9, e.y + 0.5, 0x4be08a, 5, 1.2);
    else if (e.t === 'built') burst(e.x + 0.5, 0.8, e.y + 0.5, 0xffffff, 10, 2.0);
    else if (e.t === 'spawn') burst(e.x + 0.5, 0.3, e.y + 0.5, 0x9ff, 8, 1.8);
    else if (e.t === 'beacon') burst(e.x + 0.5, 2.0, e.y + 0.5, 0x4be08a, 24, 3.0);
    else if (e.t === 'checkpoint') burst(e.x + 0.5, 1.0, e.y + 0.5, 0xffd24a, 24, 3.0);
  }
}

// ---------- fog data
function unpack(b64, n) { const bin = atob(b64); const out = new Uint8Array(n * n); for (let i = 0; i < n * n; i++) out[i] = (bin.charCodeAt(i >> 3) >> (i & 7)) & 1; return out; }

// ---------- public API
const CW = {
  async init(world) {
    S.world = world; S.size = world.size; S.grid = world.grid; S.palette = world.palette; S.hq = world.hq; S.explored = new Uint8Array(S.size * S.size); S.visible = new Uint8Array(S.size * S.size);
    for (const m of [...S.robots.values()]) removeRobot(m, true); S.robots.clear(); for (const s of S.structs.values()) scene.remove(s.grp); S.structs.clear(); for (const o of S.ores.values()) scene.remove(o.grp); S.ores.clear(); pickables.length = 0; S.dying = [];
    setupTerrain(world); setupScenery(world); updateScenery();
    const h = world.hq[0]; controls.target.set(h[0] + 0.5, 0, h[1] + 0.5); camera.position.set(h[0] + 10, 13, h[1] + 14); controls.update();
    if (!S.ring) { S.ring = true; }
    S.ready = true; return true;
  },
  update(snap, tickMs) {
    if (!S.ready || !gltf) return; if (tickMs) S.tickMs = tickMs; S.lastSnap = snap;
    if (snap.visible) { const v = unpack(snap.visible, S.size); S.visible = v; for (let i = 0; i < v.length; i++) if (v[i]) S.explored[i] = 1; }
    if (snap.explored) { const e = unpack(snap.explored, S.size); for (let i = 0; i < e.length; i++) if (e[i]) S.explored[i] = 1; }
    const key = (S.visible ? S.visible.reduce((a, b) => a + b, 0) : 0) * 7 + (S.explored ? S.explored.reduce((a, b) => a + b, 0) : 0); if (key !== S.fogKey) { S.fogKey = key; rebuildTerrain(); }
    const seen = new Set();
    for (const d of snap.robots) { seen.add(d.id); let r = S.robots.get(d.id); if (!r) { r = createRobot(d); S.robots.set(d.id, r); } updateRobot(r, d); }
    for (const [id, r] of S.robots) if (!seen.has(id)) { S.robots.delete(id); removeRobot(r, false); }
    syncStructures(snap.structures); syncOre(snap.ore); if (snap.beacons || snap.checkpoints) syncMarkers(snap.beacons || [], snap.checkpoints || []);
    handleEvents(snap.events);
  },
  focus(x, y, dist) { controls.target.set(x + 0.5, 0, y + 0.5); if (dist) { const dir = camera.position.clone().sub(controls.target).normalize(); camera.position.copy(controls.target).addScaledVector(dir, dist); } },
  focusHome() { const h = S.hq[0]; if (h) CW.focus(h[0], h[1], 20); },
  select(id) { S.selected = id; for (const r of S.robots.values()) r.ring.material.opacity = r.id === id ? 0.95 : 0; },
  setQuality(q) { if (!Q[q]) return; quality = q; applyShadowQuality(); if (S.world) { setupScenery(S.world); updateScenery(); } },
  stats() { return { culled: S.culled || 0, lodRobots: S.lodCount || 0, fps: Math.round(S.fps), drawCalls: renderer.info.render.calls, triangles: renderer.info.render.triangles, geometries: renderer.info.memory.geometries, textures: renderer.info.memory.textures, robots: S.robots.size, structures: S.structs.size, ore: S.ores.size, quality, webgl: renderer.capabilities.isWebGL2 ? 'webgl2' : 'webgl1', pixelRatio: renderer.getPixelRatio(), shadows: renderer.shadowMap.enabled, modelLoaded: !!gltf, animations: gltf ? gltf.animations.length : 0 }; },
  project(id) { const r = S.robots.get(id); if (!r) return null; const v = r.root.position.clone().project(camera); return { x: (v.x + 1) / 2, y: (1 - v.y) / 2 }; },
  ready: () => !!gltf,
};
window.CW = CW;

// ---------- picking
const ray = new THREE.Raycaster(); const ndc = new THREE.Vector2(); let down = null;
renderer.domElement.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY, t: performance.now() }; });
renderer.domElement.addEventListener('pointerup', (e) => {
  if (!down) return; const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y); const dt = performance.now() - down.t; down = null; if (moved > 8 || dt > 600) return;
  const rect = renderer.domElement.getBoundingClientRect(); ndc.set(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1); ray.setFromCamera(ndc, camera);
  const hits = ray.intersectObjects(pickables, true); if (hits.length) { let o = hits[0].object; const root = o.userData.pickRoot; if (root && root.userData.pick) { post({ type: 'select', ...root.userData.pick }); return; } }
  const gh = S.terrainMesh ? ray.intersectObject(S.terrainMesh) : []; if (gh.length) post({ type: 'tile', x: Math.floor(gh[0].point.x), y: Math.floor(gh[0].point.z) });
});

// ---------- loop
function resize() { const w = window.innerWidth, h = window.innerHeight; renderer.setSize(w, h, false); camera.aspect = w / Math.max(1, h); camera.updateProjectionMatrix(); }
window.addEventListener('resize', resize); new ResizeObserver(resize).observe(document.body); resize();
const camDist = new THREE.Vector3(); const frustum = new THREE.Frustum(); const pv = new THREE.Matrix4(); const sph = new THREE.Sphere(new THREE.Vector3(), 2.2);
const LOD_DIST = { low: 17, medium: 28, high: 40 };
function frame() {
  requestAnimationFrame(frame);
  const dt = Math.min(clock.getDelta(), 0.1); const t = clock.elapsedTime;
  S.frames++; const now = performance.now(); if (now - S.fpsT > 1000) { S.fps = (S.frames * 1000) / (now - S.fpsT); S.frames = 0; S.fpsT = now; }
  if (S.ready) {
    const k = 1 - Math.exp(-dt * Math.min(18, 1000 / S.tickMs * 2.2));
    camera.updateMatrixWorld(); pv.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse); frustum.setFromProjectionMatrix(pv);
    S.culled = 0; S.lodCount = 0; const ld = LOD_DIST[quality];
    for (const r of S.robots.values()) {
      const p = r.root.position; p.x += (r.tx - p.x) * k; p.z += (r.tz - p.z) * k; p.y += (groundY(p.x, p.z) - p.y) * 0.4;
      const want = Math.atan2(Math.cos(r.face), Math.sin(r.face)); let diff = want - r.root.rotation.y; diff = Math.atan2(Math.sin(diff), Math.cos(diff)); r.root.rotation.y += diff * Math.min(1, dt * 9);
      camDist.copy(p).sub(camera.position); const d2 = camDist.lengthSq();
      sph.center.copy(p); const inView = frustum.intersectsSphere(sph); r.root.visible = inView; if (!inView) { S.culled++; continue; }
      const wantLod = r.isLod ? d2 > (ld * 0.9) * (ld * 0.9) : d2 > ld * ld;
      if (wantLod !== r.isLod) { r.isLod = wantLod; r.body.visible = !wantLod; r.acc.visible = !wantLod; r.lod.visible = wantLod; }
      if (r.isLod) S.lodCount++; else if (d2 < 60 * 60 || (S.frames & 3) === 0) r.mixer.update(dt);
      if (r.ring.material.opacity > 0) { r.ring.rotation.y += dt; const sc = 1 + Math.sin(t * 5) * 0.05; r.ring.scale.set(sc, 1, sc); }
      const halo = r.acc.userData.halo; if (halo) halo.rotation.z += dt * 2;
    }
    for (let i = S.dying.length - 1; i >= 0; i--) { const r = S.dying[i]; r.mixer.update(dt); r.dead -= dt; if (r.dead < 0.5) r.root.scale.setScalar(Math.max(0.01, r.dead / 0.5)); if (r.dead <= 0) { scene.remove(r.root); S.dying.splice(i, 1); } }
    for (const s of S.structs.values()) { const core = s.grp.userData.parts.core; if (core) { core.rotation.y += dt; core.position.y = 2.2 + Math.sin(t * 2) * 0.06; } }
    for (const o of S.ores.values()) o.grp.rotation.y += dt * 0.25;
    for (const m of markers) if (m.userData.beacon) m.children[1].material.opacity = 0.6 + Math.sin(t * 3) * 0.4;
    for (const b of FX.beams) if (b.t > 0) { b.t -= dt; b.l.material.opacity = Math.max(0, b.t / 0.16); if (b.t <= 0) b.l.visible = false; }
    for (const s of FX.sparks) if (s.t > 0) { s.t -= dt; s.v.y -= dt * 2.2; s.s.position.addScaledVector(s.v, dt); s.s.material.opacity = Math.max(0, s.t / s.life); if (s.t <= 0) s.s.visible = false; }
    if (S.water) S.water.position.y = -0.12 + Math.sin(t * 0.8) * 0.015;
    const n = S.size; controls.target.x = Math.max(0, Math.min(n, controls.target.x)); controls.target.z = Math.max(0, Math.min(n, controls.target.z));
  }
  controls.update(); renderer.render(scene, camera);
}
const loader = new GLTFLoader();
const bin = Uint8Array.from(atob(robotB64), (c) => c.charCodeAt(0));
loader.parse(bin.buffer, '', (g) => { gltf = g; const box = new THREE.Box3().setFromObject(g.scene); modelH = box.max.y - box.min.y || 1; document.getElementById('msg').textContent = ''; window.dispatchEvent(new Event('cw-ready')); post({ type: 'ready' }); },
  (err) => { document.getElementById('msg').textContent = 'model error: ' + err; post({ type: 'error', message: String(err) }); });
frame();
