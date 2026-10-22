// Shared helpers for every scene. Loaded once in index.html <head>, before the
// sub-compositions mount, so scene scripts can call window.K.* synchronously.
(function () {
  const K = {};

  // Seeded PRNG (mulberry32) — determinism: never Math.random.
  K.rng = function (seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };

  // Scene-relative cue time (seconds) from the generated cue table.
  // Missing keys fall back so a scene never silently collapses to 0.
  K.cue = function (scene, key, fallback) {
    const s = (window.CUES || {})[scene] || {};
    if (key in s) return s[key];
    if (fallback === undefined) console.warn("[cue] missing", scene, key);
    return fallback === undefined ? 0 : fallback;
  };
  K.scene = function (scene) {
    return function (key, fb) {
      return K.cue(scene, key, fb);
    };
  };

  // Stroke-draw prep: every [data-draw] stroke starts fully hidden.
  K.prepDraw = function (root) {
    root.querySelectorAll("[data-draw]").forEach((p) => {
      const len = Math.ceil(p.getTotalLength ? p.getTotalLength() : 1000) + 2;
      p.style.strokeDasharray = len + " " + len;
      p.style.strokeDashoffset = len;
      p.dataset.len = len;
    });
  };
  K.draw = function (tl, targets, at, dur, ease) {
    tl.to(targets, { strokeDashoffset: 0, duration: dur || 0.6, ease: ease || "power2.inOut" }, at);
  };
  K.undraw = function (tl, targets, at, dur) {
    const els = typeof targets === "string" ? document.querySelectorAll(targets) : [].concat(targets);
    els.forEach((el) => {
      if (!el) return;
      tl.to(el, { strokeDashoffset: -(+el.dataset.len || 1000), duration: dur || 0.4, ease: "power2.in" }, at);
    });
  };

  // Typewriter by character count (works for RTL — slices the logical string).
  K.type = function (tl, el, text, at, cps) {
    const o = { n: 0 };
    el.textContent = "";
    tl.to(
      o,
      {
        n: text.length,
        duration: text.length / (cps || 28),
        ease: "none",
        onUpdate: () => {
          el.textContent = text.slice(0, Math.round(o.n));
        },
      },
      at,
    );
  };

  // Seek-safe discrete switch: fn(true) at/after t, fn(false) before.
  // (tl.call is skipped when the renderer seeks — this re-renders both ways.)
  K.at = function (tl, t, fn) {
    const o = { v: 0 };
    tl.fromTo(o, { v: 0 }, { v: 1, duration: 0.001, ease: "none", immediateRender: false, onUpdate: () => fn(o.v >= 0.5), onReverseComplete: () => fn(false) }, t);
    fn(false);
  };
  // Text that changes at given times: steps = [[t, "text"], ...]
  K.textSteps = function (tl, el, steps, initial) {
    const o = { i: -1 };
    el.textContent = initial == null ? "" : initial;
    steps.forEach(([t], idx) => {
      tl.fromTo(o, { i: idx - 1 }, { i: idx, duration: 0.001, ease: "none", immediateRender: false,
        onUpdate: () => { const k = Math.round(o.i); el.textContent = k < 0 ? (initial == null ? "" : initial) : steps[k][1]; } }, t);
    });
  };

  // Count-up with a formatter.
  K.count = function (tl, el, from, to, at, dur, fmt, ease) {
    const o = { v: from };
    fmt = fmt || ((v) => Math.round(v).toLocaleString("en-US"));
    el.textContent = fmt(from);
    tl.to(o, { v: to, duration: dur, ease: ease || "expo.out", onUpdate: () => (el.textContent = fmt(o.v)) }, at);
  };

  // Scramble a number/string through random glyphs, settling left→right.
  K.scramble = function (tl, el, finalText, at, dur, pool, seed) {
    const r = K.rng(seed || 7);
    pool = pool || "0123456789";
    const o = { p: 0 };
    const n = finalText.length;
    const noise = [];
    for (let f = 0; f < 64; f++) {
      let s = "";
      for (let i = 0; i < n; i++) s += pool[Math.floor(r() * pool.length)];
      noise.push(s);
    }
    tl.to(
      o,
      {
        p: 1,
        duration: dur,
        ease: "none",
        onUpdate: () => {
          const settled = Math.floor(o.p * n);
          const frame = noise[Math.floor(o.p * 63)];
          let out = "";
          for (let i = 0; i < n; i++) out += i < settled || !/[0-9A-Za-z]/.test(finalText[i]) ? finalText[i] : frame[i];
          el.textContent = out;
          if (o.p >= 1) el.textContent = finalText;
        },
      },
      at,
    );
  };

  // Drive a canvas/3D render function from the GSAP timeline (seek-safe):
  // the proxy is tweened linearly, onUpdate renders the exact local time.
  K.clock = function (tl, dur, render) {
    const P = { t: 0 };
    tl.to(P, { t: dur, duration: dur, ease: "none", onUpdate: () => render(P.t) }, 0);
    render(0);
    return P;
  };

  // Easing helpers usable inside 3D render(t) functions.
  K.clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  K.seg = (t, a, b) => K.clamp((t - a) / (b - a), 0, 1);
  K.eOut = (x) => 1 - Math.pow(1 - x, 4);
  K.eIO = (x) => (x < 0.5 ? 8 * x * x * x * x : 1 - Math.pow(-2 * x + 2, 4) / 2);
  K.eExpo = (x) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x));
  K.lerp = (a, b, x) => a + (b - a) * x;

  // Chapter title card: a drafting-sheet frame draws, the numeral slams, the
  // Hebrew title rises out of a mask, then the whole sheet flies past camera.
  // Built into `host` (an absolutely-positioned full-frame div in the scene).
  K.chapter = function (host, tl, o) {
    const at = o.at || 0;
    const hold = o.hold || 0.72;
    host.innerHTML = `
      <svg class="full" viewBox="0 0 1080 1920" style="position:absolute;inset:0">
        <path class="ln ch-fr" data-draw d="M1032 48 H48 V1872"/>
        <path class="ln ch-fr" data-draw d="M1032 48 V1872 H48"/>
        <path class="ln thin ch-tk" data-draw d="M48 300 H96 M1032 300 H984 M48 1620 H96 M1032 1620 H984"/>
      </svg>
      <div class="abs lbl ch-l1" style="top:78px;right:90px">${o.sheet || "SHEET " + o.num + " / 06"}</div>
      <div class="abs lbl ch-l2" style="top:78px;left:90px">${o.l2 || "LLM-0 · BUILD LOG"}</div>
      <div class="abs ch-num mono" style="top:560px;left:0;right:0;text-align:center;font-size:360px;font-weight:700;line-height:1;color:var(--signal);letter-spacing:-0.06em">${o.num}</div>
      <div class="abs mask" style="top:960px;left:0;right:0;height:260px"><div class="ch-ttl he" style="text-align:center;font-size:${o.size || 220}px;font-weight:700;line-height:1.1">${o.title}</div></div>
      <div class="abs lbl ch-en" style="top:1250px;left:0;right:0;text-align:center;font-size:30px;letter-spacing:0.5em">${o.en}</div>`;
    K.prepDraw(host);
    const fr = host.querySelectorAll(".ch-fr");
    tl.fromTo(host, { opacity: 1, scale: 1 }, { opacity: 1, scale: 1, duration: 0.01 }, at);
    K.draw(tl, fr, at, 0.34, "power3.out");
    K.draw(tl, host.querySelectorAll(".ch-tk"), at + 0.18, 0.3, "power2.out");
    tl.fromTo(host.querySelector(".ch-num"), { scale: 1.35, opacity: 0, filter: "blur(18px)" }, { scale: 1, opacity: 1, filter: "blur(0px)", duration: 0.32, ease: "expo.out" }, at + 0.02);
    tl.fromTo(host.querySelector(".ch-ttl"), { yPercent: 105 }, { yPercent: 0, duration: 0.42, ease: "expo.out" }, at + 0.1);
    tl.fromTo(host.querySelectorAll(".ch-l1,.ch-l2,.ch-en"), { opacity: 0 }, { opacity: 1, duration: 0.2, stagger: 0.05 }, at + 0.15);
    // fly-through exit
    tl.to(host, { scale: 2.4, opacity: 0, filter: "blur(10px)", duration: 0.36, ease: "power3.in" }, at + hold);
    return at + hold + 0.36;
  };

  // Project a THREE.Vector3 to frame pixels (1080x1920).
  K.proj = function (cam, v) {
    const p = v.clone().project(cam);
    return { x: ((p.x + 1) / 2) * 1080, y: ((1 - p.y) / 2) * 1920, z: p.z };
  };
  // Canvas-texture text sprite for THREE (Almoni / Plex Mono), sized in world units by height.
  K.sprite = function (THREE, txt, o) {
    o = o || {};
    const px = o.px || 72, font = (o.weight || 700) + " " + px + 'px "' + (o.mono ? "Plex Mono" : "Almoni") + '"';
    const c = document.createElement("canvas");
    const x0 = c.getContext("2d"); x0.font = font;
    const w = Math.ceil(x0.measureText(txt).width) + 24, h = Math.ceil(px * 1.4);
    c.width = w; c.height = h;
    const x = c.getContext("2d"); x.font = font; x.textAlign = "center"; x.textBaseline = "middle";
    if (!o.mono) x.direction = "rtl";
    if (o.bg) { x.fillStyle = o.bg; x.fillRect(0, 0, w, h); }
    x.fillStyle = o.color || "#ece6d8"; x.fillText(txt, w / 2, h / 2 + 2);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthWrite: false, depthTest: o.depthTest !== false }));
    const H = o.h || 0.3; sp.scale.set(H * w / h, H, 1);
    return sp;
  };

  window.K = K;
})();
