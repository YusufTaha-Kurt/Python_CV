// Hologram masası: Python'daki goru.hologram.Masa'nın durumunu three.js ile çizer.
// Bu dosya hiçbir karar vermez; tüm etkileşim mantığı Python tarafında, test edilerek çalışır.
// Durum /durum (SSE) üzerinden ~30 Hz gelir, burada 60 Hz çizilir ve aradaki kareler yumuşatılır.

import * as THREE from "three";

const Q = new URLSearchParams(location.search);
let piramit = Q.get("piramit") === "1";
const FOV = 35;
const MAVI = 0x00d8ff;

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.autoClear = false;
document.body.appendChild(renderer.domElement);

const sahne = new THREE.Scene();
sahne.add(new THREE.AmbientLight(0x88ccff, 0.7));
const isik = new THREE.PointLight(0x66e0ff, 3.0, 0, 0);
isik.position.set(0, 200, 900);
sahne.add(isik);
const kamera = new THREE.PerspectiveCamera(FOV, 1, 1, 50000);

let W = 0, H = 0;
function boyutla() {
  W = window.innerWidth;
  H = window.innerHeight;
  renderer.setSize(W, H);
}
window.addEventListener("resize", boyutla);
boyutla();

// --- Durum akışı ---
let durum = { boyut: [1280, 720], nesneler: [], imlecler: [], mesajlar: [], ozellikler: {} };
let sonDurumZamani = 0;
const kaynak = new EventSource("/durum");
kaynak.onmessage = (e) => { durum = JSON.parse(e.data); sonDurumZamani = performance.now(); };
const baglanti = document.getElementById("baglanti");

// Kamera pikseli -> dünya koordinatı: merkez (0,0), y yukarı. 1 dünya birimi = 1 kamera pikseli.
function dunya(x, y) {
  const [vw, vh] = durum.boyut;
  return new THREE.Vector3(x - vw / 2, vh / 2 - y, 0);
}

// --- Yardımcı çizimler ---
function yuvarlakDikdortgen(g, x, y, w, h, r) {
  g.beginPath();
  g.moveTo(x + r, y);
  g.arcTo(x + w, y, x + w, y + h, r);
  g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r);
  g.arcTo(x, y, x + w, y, r);
  g.closePath();
}

function metinSar(g, metin, x, y, genislik, satirYuk, altSinir) {
  for (const paragraf of (metin || "").split("\n")) {
    let satir = "";
    for (const kelime of paragraf.split(" ")) {
      const deneme = satir ? satir + " " + kelime : kelime;
      if (g.measureText(deneme).width > genislik && satir) {
        g.fillText(satir, x, y);
        y += satirYuk;
        satir = kelime;
        if (y > altSinir) return;
      } else satir = deneme;
    }
    g.fillText(satir, x, y);
    y += satirYuk;
    if (y > altSinir) return;
  }
}

function kartTuvali(n) {
  const tuval = document.createElement("canvas");
  tuval.width = 640;
  tuval.height = Math.round(640 * n.h / n.g);
  const g = tuval.getContext("2d");
  yuvarlakDikdortgen(g, 8, 8, tuval.width - 16, tuval.height - 16, 26);
  const dolgu = g.createLinearGradient(0, 0, 0, tuval.height);
  dolgu.addColorStop(0, "rgba(14, 46, 72, 0.78)");
  dolgu.addColorStop(1, "rgba(4, 18, 32, 0.70)");
  g.fillStyle = dolgu;
  g.fill();
  g.shadowColor = "#00e0ff";
  g.shadowBlur = 22;
  g.lineWidth = 4;
  g.strokeStyle = "rgba(0, 224, 255, 0.95)";
  g.stroke();
  g.shadowBlur = 0;
  g.fillStyle = "#c8f8ff";
  g.font = "600 40px 'Segoe UI', sans-serif";
  g.fillText(n.baslik || "", 34, 70, tuval.width - 68);
  g.fillStyle = "rgba(0, 224, 255, 0.55)";
  g.fillRect(34, 90, tuval.width - 68, 3);
  g.fillStyle = "#e8fcff";
  g.font = "28px 'Segoe UI', sans-serif";
  metinSar(g, n.govde, 34, 136, tuval.width - 68, 38, tuval.height - 34);
  if (!n.acik && n.govde) {
    g.fillStyle = "rgba(127, 246, 255, 0.7)";
    g.font = "italic 22px 'Segoe UI', sans-serif";
    g.fillText("kısa çimdik: aç", tuval.width - 200, tuval.height - 26);
  }
  return tuval;
}

const hologramMalzeme = () => new THREE.MeshPhongMaterial({
  color: MAVI, emissive: 0x0a5a7a, transparent: true, opacity: 0.55, shininess: 90, side: THREE.DoubleSide,
});
const kenarMalzeme = () => new THREE.LineBasicMaterial({
  color: 0x9ff8ff, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending,
});

function parca(geometri, konum, yon) {
  const grup = new THREE.Group();
  grup.add(new THREE.Mesh(geometri, hologramMalzeme()));
  grup.add(new THREE.LineSegments(new THREE.EdgesGeometry(geometri, 25), kenarMalzeme()));
  grup.position.copy(konum);
  grup.userData = { taban: konum.clone(), yon: yon.clone() };
  return grup;
}

// Prosedürel modeller (dosya gerekmez). Her parçanın bir patlama yönü vardır.
function reaktor(r) {
  const grup = new THREE.Group();
  const z = new THREE.Vector3(0, 0, 1);
  grup.add(parca(new THREE.SphereGeometry(r * 0.17, 24, 16), new THREE.Vector3(), z.clone().multiplyScalar(1.2)));
  grup.add(parca(new THREE.TorusGeometry(r * 0.32, r * 0.045, 12, 48), new THREE.Vector3(0, 0, 0), z.clone().multiplyScalar(0.6)));
  for (let i = 0; i < 10; i++) {
    const a = (i / 10) * Math.PI * 2;
    const yon = new THREE.Vector3(Math.cos(a), Math.sin(a), 0.25);
    const kutu = parca(new THREE.BoxGeometry(r * 0.16, r * 0.09, r * 0.09),
      new THREE.Vector3(Math.cos(a), Math.sin(a), 0).multiplyScalar(r * 0.56), yon);
    kutu.rotation.z = a;
    grup.add(kutu);
  }
  grup.add(parca(new THREE.TorusGeometry(r * 0.82, r * 0.05, 12, 64), new THREE.Vector3(), z.clone().multiplyScalar(-0.8)));
  for (let i = 0; i < 3; i++) {
    const a = (i / 3) * Math.PI * 2 + Math.PI / 2;
    const yon = new THREE.Vector3(Math.cos(a), Math.sin(a), -0.4);
    const kol = parca(new THREE.BoxGeometry(r * 0.06, r * 0.36, r * 0.06),
      new THREE.Vector3(Math.cos(a), Math.sin(a), 0).multiplyScalar(r * 0.64), yon);
    kol.rotation.z = a - Math.PI / 2;
    grup.add(kol);
  }
  return grup;
}

function kup(r) {
  const grup = new THREE.Group();
  const a = r * 0.36;
  const geo = new THREE.BoxGeometry(a * 0.9, a * 0.9, a * 0.9);
  for (let x = -1; x <= 1; x++) for (let y = -1; y <= 1; y++) for (let z = -1; z <= 1; z++) {
    const konum = new THREE.Vector3(x, y, z).multiplyScalar(a);
    const yon = (x || y || z) ? new THREE.Vector3(x, y, z).normalize() : new THREE.Vector3();
    grup.add(parca(geo, konum, yon));
  }
  return grup;
}

// --- Nesneler ---
const nesneler = new Map(); // id -> {kok, tur, imza, ...}

function duzlemOlustur(n, doku) {
  const kok = new THREE.Group();
  const parilti = new THREE.Mesh(new THREE.PlaneGeometry(1, 1),
    new THREE.MeshBasicMaterial({ color: MAVI, transparent: true, opacity: 0.12, blending: THREE.AdditiveBlending, depthWrite: false }));
  parilti.scale.set(1.06, 1.08, 1);
  parilti.position.z = -1;
  const yuz = new THREE.Mesh(new THREE.PlaneGeometry(1, 1),
    new THREE.MeshBasicMaterial({ map: doku, transparent: true, depthWrite: false }));
  kok.add(parilti, yuz);
  return { kok, yuz, parilti };
}

function nesneOlustur(n) {
  let kayit;
  if (n.tur === "model") {
    const kok = new THREE.Group();
    const model = n.kaynak === "kup" ? kup(100) : reaktor(100); // 100 birimlik model, sonra ölçeklenir
    kok.add(model);
    kayit = { kok, model, bosta: 0 };
  } else if (n.tur === "gorsel") {
    const doku = new THREE.TextureLoader().load(n.kaynak);
    doku.colorSpace = THREE.SRGBColorSpace;
    kayit = duzlemOlustur(n, doku);
  } else {
    const doku = new THREE.CanvasTexture(kartTuvali(n));
    doku.colorSpace = THREE.SRGBColorSpace;
    kayit = duzlemOlustur(n, doku);
  }
  kayit.tur = n.tur;
  kayit.imza = "";
  kayit.kok.position.copy(dunya(n.x, n.y));
  sahne.add(kayit.kok);
  nesneler.set(n.id, kayit);
  return kayit;
}

function nesneGuncelle(kayit, n, sure) {
  const hedef = dunya(n.x, n.y);
  if (n.titreme > 0) {
    const genlik = 4 + n.titreme * 40;
    hedef.x += (Math.random() - 0.5) * genlik;
    hedef.y += (Math.random() - 0.5) * genlik;
  }
  kayit.kok.position.lerp(hedef, 0.35);
  kayit.kok.renderOrder = n.sira;
  kayit.kok.position.z = n.sira * 2 + (n.tutuluyor ? 40 : 0);
  const vurgulu = n.tutuluyor || n.mod === "elde" || n.mod === "cekiliyor";

  if (kayit.tur === "model") {
    const s = n.g / 200;
    kayit.kok.scale.setScalar(THREE.MathUtils.lerp(kayit.kok.scale.x, s * (vurgulu ? 1.05 : 1), 0.3));
    if (n.mod === "serbest") kayit.bosta += sure * 0.35;
    kayit.model.rotation.x = THREE.MathUtils.lerp(kayit.model.rotation.x, n.don_x + 0.35, 0.3);
    kayit.model.rotation.y = THREE.MathUtils.lerp(kayit.model.rotation.y, n.don_y + kayit.bosta, 0.3);
    for (const p of kayit.model.children) {
      p.position.copy(p.userData.taban).addScaledVector(p.userData.yon, n.patlama * 85);
      p.children[0].material.emissiveIntensity = 1 + n.titreme * 3 + (vurgulu ? 0.6 : 0);
    }
    return;
  }
  // Kart ve görsel: içerik değiştiyse kartı yeniden çiz
  const imza = `${n.baslik}|${n.govde}|${n.acik}|${Math.round(n.h / n.g * 100)}`;
  if (kayit.tur === "kart" && imza !== kayit.imza) {
    kayit.yuz.material.map.dispose();
    kayit.yuz.material.map = new THREE.CanvasTexture(kartTuvali(n));
    kayit.yuz.material.map.colorSpace = THREE.SRGBColorSpace;
    kayit.yuz.material.needsUpdate = true;
    kayit.imza = imza;
  }
  kayit.kok.scale.x = THREE.MathUtils.lerp(kayit.kok.scale.x, n.g, 0.3);
  kayit.kok.scale.y = THREE.MathUtils.lerp(kayit.kok.scale.y, n.h, 0.3);
  kayit.parilti.material.opacity = vurgulu ? 0.45 : 0.12 + n.titreme * 0.4;
}

// --- El imleçleri ---
const imlecler = new Map();

function imlecOlustur() {
  const kok = new THREE.Group();
  const halka = new THREE.Mesh(new THREE.RingGeometry(16, 21, 48),
    new THREE.MeshBasicMaterial({ color: MAVI, transparent: true, opacity: 0.9, depthTest: false }));
  const dolgu = new THREE.Mesh(new THREE.CircleGeometry(12, 32),
    new THREE.MeshBasicMaterial({ color: 0x66ff99, transparent: true, opacity: 0.0, depthTest: false }));
  const nisan = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3(1, 0, 0)]),
    new THREE.LineDashedMaterial({ color: 0xff5544, dashSize: 14, gapSize: 10, transparent: true, opacity: 0.0, depthTest: false }));
  nisan.computeLineDistances();
  kok.add(halka, dolgu, nisan);
  kok.renderOrder = 1000;
  sahne.add(kok);
  return { kok, halka, dolgu, nisan };
}

function imlecGuncelle(kayit, i) {
  const hedef = dunya(i.x, i.y);
  hedef.z = 400;
  kayit.kok.position.lerp(hedef, 0.5);
  const renk = i.pence ? 0xff5544 : i.hayalet ? 0xffaa33 : i.kavrayabilir ? 0x66ff99 : MAVI;
  kayit.halka.material.color.setHex(renk);
  kayit.dolgu.material.opacity = i.cimdik ? 0.75 : Math.max(0, 0.5 - i.oran * 0.5);
  const s = i.pence ? 1.6 + i.pence.gerilim * 0.8 : 1;
  kayit.halka.scale.setScalar(s);
  if (i.pence) {
    const [dx, dy] = i.pence.yon;
    kayit.nisan.scale.setScalar(900);
    kayit.nisan.rotation.z = Math.atan2(-dy, dx);
    kayit.nisan.material.opacity = 0.8;
  } else kayit.nisan.material.opacity = 0;
}

// --- Çizim döngüsü ---
const mesajKutusu = document.getElementById("mesajlar");
const sayac = document.getElementById("sayac");
let sonCizim = performance.now(), cizimFps = 0, sonMesajlar = "";

function senkronla(sure) {
  const gorulen = new Set();
  durum.nesneler.forEach((n, sira) => {
    n.sira = sira;
    gorulen.add(n.id);
    nesneGuncelle(nesneler.get(n.id) || nesneOlustur(n), n, sure);
  });
  for (const [id, kayit] of nesneler) if (!gorulen.has(id)) { sahne.remove(kayit.kok); nesneler.delete(id); }

  const eller = new Set();
  for (const i of durum.imlecler) {
    eller.add(i.el);
    if (!imlecler.has(i.el)) imlecler.set(i.el, imlecOlustur());
    imlecGuncelle(imlecler.get(i.el), i);
  }
  for (const [el, kayit] of imlecler) if (!eller.has(el)) { sahne.remove(kayit.kok); imlecler.delete(el); }

  const yeni = durum.mesajlar.join("\n");
  if (yeni !== sonMesajlar) {
    sonMesajlar = yeni;
    // Mesajlar dışarıdan eklenen kart başlıklarını içerebilir: HTML olarak değil düz metin olarak yaz
    mesajKutusu.replaceChildren(...durum.mesajlar.map((m) => {
      const satir = document.createElement("div");
      satir.textContent = m;
      return satir;
    }));
  }
}

function kameraKur(alanW, alanH, gorunenYukseklik, yuvarlanma) {
  kamera.aspect = alanW / alanH;
  kamera.position.set(0, 0, (gorunenYukseklik / 2) / Math.tan(THREE.MathUtils.degToRad(FOV / 2)));
  kamera.rotation.set(0, 0, yuvarlanma);
  kamera.updateProjectionMatrix();
}

function ciz() {
  const [vw, vh] = durum.boyut;
  renderer.setScissorTest(false);
  renderer.setViewport(0, 0, W, H);
  renderer.setClearColor(0x000000, piramit ? 1 : 0);
  renderer.clear();
  if (!piramit) {
    // object-fit: cover ile aynı ölçek: görünen kamera yüksekliği = H / s
    const s = Math.max(W / vw, H / vh);
    kameraKur(W, H, H / s, 0);
    renderer.render(sahne, kamera);
    return;
  }
  // Pepper's ghost piramidi: dört görüntü ortadaki karenin etrafında, alt kenarları merkeze bakar.
  // Ters çevrilmiş plastik piramit ekranın ortasına konunca her yüzü bir görüntüyü yansıtır.
  const S = Math.floor(Math.min(W, H) / 3);
  const x0 = Math.floor(W / 2 - S / 2), y0 = Math.floor(H / 2 - S / 2);
  const gorunumler = [
    [x0, y0 + S, 0],              // üst: dik
    [x0, y0 - S, Math.PI],        // alt: ters
    [x0 - S, y0, -Math.PI / 2],   // sol: alt kenarı sağa (merkeze) bakar
    [x0 + S, y0, Math.PI / 2],    // sağ: alt kenarı sola bakar
  ];
  renderer.setScissorTest(true);
  for (const [x, y, yuvarlanma] of gorunumler) {
    renderer.setViewport(x, y, S, S);
    renderer.setScissor(x, y, S, S);
    kameraKur(S, S, Math.max(vw, vh) * 0.95, yuvarlanma);
    renderer.render(sahne, kamera);
  }
}

function dongu(simdi) {
  const sure = Math.min((simdi - sonCizim) / 1000, 0.1);
  sonCizim = simdi;
  cizimFps = cizimFps * 0.9 + (sure > 0 ? 1 / sure : 0) * 0.1;
  senkronla(sure);
  ciz();
  const canli = simdi - sonDurumZamani < 1500;
  baglanti.textContent = canli ? "" : "bağlanıyor...";
  sayac.textContent = `çizim ${cizimFps.toFixed(0)} FPS · takip ${durum.fps ?? "-"} FPS · ${durum.nesneler.length} nesne`;
  requestAnimationFrame(dongu);
}
requestAnimationFrame(dongu);

// --- Tuşlar ---
document.body.classList.toggle("piramit", piramit);
window.addEventListener("keydown", (e) => {
  if (e.key === "p") { piramit = !piramit; document.body.classList.toggle("piramit", piramit); }
  else if (e.key === "f") { document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen(); }
  else if (e.key === "h") { document.getElementById("bilgi").classList.toggle("gizli"); }
  else if (e.key === "t") { fetch("/komut", { method: "POST", body: JSON.stringify({ a: "toparla" }) }); }
});
const ders7 = document.getElementById("ders7");
setInterval(() => {
  const acik = Boolean(durum.ozellikler && durum.ozellikler.pence);
  ders7.textContent = acik ? "pençe: avucu aç, pençe yap, nişan al, 2 sn bekle, kapat · alkış: toparla" : "";
  ders7.style.display = acik ? "block" : "none";
}, 1000);
