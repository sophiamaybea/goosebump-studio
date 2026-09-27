const metersEl = document.getElementById("meters");
const proxies = [
  ["attention", 18],
  ["arousal", 22],
  ["entrainment", 15],
  ["expectation", 40],
  ["anticipation", 28],
  ["tension", 33],
  ["intimacy", 20],
  ["somatic", 16],
];

function drawMeters(extra = {}) {
  metersEl.innerHTML = proxies
    .map(([name, base]) => {
      const v = Math.max(4, Math.min(96, extra[name] ?? base));
      return `<li><span>${name}</span><div class="bar"><i style="width:${v}%"></i></div><span>${v}</span></li>`;
    })
    .join("");
}
drawMeters();

const state = { file: null, url: null, plan: null, takes: [] };

document.getElementById("file").addEventListener("change", (e) => {
  const f = e.target.files[0];
  if (!f) return;
  state.file = f;
  if (state.url) URL.revokeObjectURL(state.url);
  state.url = URL.createObjectURL(f);
  document.getElementById("sourceName").textContent = f.name;
  document.getElementById("sourceHash").textContent = `size ${f.size} · locked as A in session when studio.py inits`;
  document.getElementById("playerA").src = state.url;
});

function draftPlan(text, proxy) {
  const t = text.toLowerCase();
  const plan = {
    name: "take",
    hypothesis: text.trim() || "unspecified edit",
    predicted_proxy: proxy,
  };
  if (/closer|intimate|vocal/.test(t)) {
    plan.eq_hz = 3000;
    plan.eq_gain_db = 1.5;
    plan.gain_db = -1;
  }
  if (/quiet|density|drop|thin/.test(t)) plan.gain_db = -3;
  if (/bass|body|stomach/.test(t)) plan.highpass_hz = 90;
  if (/narrow|width|small/.test(t)) plan.width = 0.65;
  if (/wide|open|expand/.test(t)) plan.width = 1.4;
  if (/compress|glue/.test(t)) plan.compress = true;
  if (/fade/.test(t)) plan.fade_in = 0.2;
  return plan;
}

document.getElementById("planBtn").addEventListener("click", () => {
  const text = document.getElementById("instruction").value;
  const proxy = document.getElementById("proxy").value;
  state.plan = draftPlan(text, proxy);
  document.getElementById("plan").textContent = JSON.stringify(state.plan, null, 2);
});

document.getElementById("renderBtn").addEventListener("click", () => {
  if (!state.file) {
    document.getElementById("plan").textContent = "Load A first.";
    return;
  }
  if (!state.plan) {
    document.getElementById("planBtn").click();
  }
  const n = String(state.takes.length + 1).padStart(3, "0");
  const take = {
    id: `take-${n}`,
    plan: state.plan,
    url: state.url,
    mark: null,
  };
  state.takes.push(take);
  renderTakes();
});

function renderTakes() {
  const root = document.getElementById("takes");
  root.innerHTML = state.takes
    .map(
      (t, i) => `
      <div class="take ${t.mark ? "marked" : ""}">
        <strong>${t.id}</strong>
        <p class="quiet">${t.plan.hypothesis}</p>
        <p class="mono">${t.plan.predicted_proxy} · ${Object.keys(t.plan).filter((k) => !["name","hypothesis","predicted_proxy"].includes(k)).join(", ") || "no audio keys"}</p>
        <audio controls src="${t.url}"></audio>
        <div class="marks">
          <button type="button" data-i="${i}" data-m="nothing">nothing</button>
          <button type="button" data-i="${i}" data-m="closer">closer</button>
          <button type="button" data-i="${i}" data-m="stomach">stomach</button>
          <button type="button" data-i="${i}" data-m="goosebumps">goosebumps</button>
        </div>
        <p class="quiet">${t.mark ? "marked: " + t.mark : "unmarked — not evidence yet"}</p>
      </div>`
    )
    .join("");
  root.querySelectorAll("[data-m]").forEach((btn) => {
    btn.onclick = () => {
      const t = state.takes[+btn.dataset.i];
      t.mark = btn.dataset.m;
      if (t.mark === "goosebumps") drawMeters({ tension: 70, somatic: 74, anticipation: 62, intimacy: 55 });
      if (t.mark === "stomach") drawMeters({ somatic: 80, tension: 58, arousal: 61 });
      if (t.mark === "closer") drawMeters({ intimacy: 72, attention: 48 });
      renderTakes();
    };
  });
}
