import { useState, useEffect, useRef } from "react";

// ── Mock data ──
const MOCK_NETWORKS = [
  { ssid: "HomeNetwork_5G", bssid: "A4:2B:8C:1D:4E:FF", signal: 92, auth: "WPA3", cipher: "CCMP", channel: "36", band: "802.11ac/5GHz" },
  { ssid: "OfficeWifi", bssid: "BC:97:E1:03:AB:22", signal: 78, auth: "WPA2", cipher: "CCMP", channel: "6", band: "802.11n/2.4GHz" },
  { ssid: "Neighbor_Net", bssid: "D8:07:B6:88:CC:11", signal: 55, auth: "WPA2", cipher: "TKIP", channel: "11", band: "802.11n/2.4GHz" },
  { ssid: "CoffeeShop_Free", bssid: "F0:18:98:3C:7D:44", signal: 41, auth: "Open", cipher: "None", channel: "1", band: "802.11g/2.4GHz" },
  { ssid: "AndroidAP_5544", bssid: "22:FD:AB:11:2C:88", signal: 28, auth: "WPA2", cipher: "CCMP", channel: "44", band: "802.11ac/5GHz" },
  { ssid: "<Скрытая>", bssid: "99:AA:BB:CC:DD:EE", signal: 15, auth: "WPA2", cipher: "CCMP", channel: "13", band: "802.11n/2.4GHz" },
];

const MOCK_PROFILES = [
  { name: "HomeNetwork_5G", auth: "WPA3", connected: true },
  { name: "OfficeWifi", auth: "WPA2", connected: false },
  { name: "CoffeeShop_Free", auth: "Open", connected: false },
  { name: "GrandmaHouse", auth: "WPA2", connected: false },
];

const MOCK_SIGNAL_HISTORY = [60,62,65,70,74,72,68,71,75,78,80,82,85,87,83,80,79,82,85,88,85,82,80,78,75,72,74,77,80,85];

// ── Colors ──
const C = {
  bg: "#0d1117", panel: "#161b22", border: "#30363d",
  accent: "#58a6ff", green: "#3fb950", warn: "#f0883e", danger: "#f85149",
  text: "#e6edf3", sub: "#8b949e", purple: "#bc8cff",
};

// ── Helpers ──
const signalColor = (s) => s >= 60 ? C.green : s >= 30 ? C.warn : C.danger;
const signalBars = (s) => {
  const filled = s >= 80 ? 4 : s >= 60 ? 3 : s >= 40 ? 2 : s >= 20 ? 1 : 0;
  return (
    <span style={{ letterSpacing: 1, fontSize: 14 }}>
      {[1,2,3,4].map(i => (
        <span key={i} style={{ color: i <= filled ? signalColor(s) : C.border, fontWeight: "bold" }}>▌</span>
      ))}
    </span>
  );
};
const authBadge = (auth) => {
  const color = auth === "WPA3" ? C.green : auth === "WPA2" ? C.accent : auth === "Open" ? C.warn : C.sub;
  return (
    <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, background: color + "22", color, border: `1px solid ${color}44`, fontWeight: 600 }}>
      {auth}
    </span>
  );
};

// ── Mini Signal Graph ──
function SignalGraph({ history, height = 80 }) {
  const w = 320, h = height, pad = 8, padLeft = 28;
  const max = 100, min = 0;
  const range = max - min;
  const pts = history.map((v, i) => {
    const x = padLeft + ((w - padLeft - pad) * i) / (history.length - 1);
    const y = h - pad - ((h - 2 * pad) * (v - min)) / range;
    return [x, y];
  });
  const polyArea = `${padLeft},${h - pad} ` + pts.map(([x, y]) => `${x},${y}`).join(" ") + ` ${pts[pts.length - 1][0]},${h - pad}`;
  const polyLine = pts.map(([x, y]) => `${x},${y}`).join(" ");
  const gridLines = [25, 50, 75, 100];

  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} style={{ display: "block" }}>
      <rect width={w} height={h} fill={C.panel} rx={8} />
      {gridLines.map(pct => {
        const y = h - pad - ((h - 2 * pad) * pct) / 100;
        return (
          <g key={pct}>
            <line x1={padLeft} y1={y} x2={w - pad} y2={y} stroke={C.border} strokeDasharray="4 4" />
            <text x={2} y={y + 4} fill={C.sub} fontSize={9} fontFamily="Consolas">{pct}%</text>
          </g>
        );
      })}
      <polygon points={polyArea} fill={`${C.accent}28`} />
      <polyline points={polyLine} fill="none" stroke={C.accent} strokeWidth={2} strokeLinejoin="round" />
      {pts.length > 0 && (
        <>
          <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r={4} fill={C.accent} stroke={C.bg} strokeWidth={2} />
          <text x={pts[pts.length - 1][0] + 6} y={pts[pts.length - 1][1] + 4} fill={C.accent} fontSize={9} fontFamily="Consolas">
            {history[history.length - 1]}%
          </text>
        </>
      )}
    </svg>
  );
}

// ── Tab: Dashboard ──
function Dashboard({ currentNetwork, onPing }) {
  const [animPulse, setAnimPulse] = useState(false);
  const [pingResult, setPingResult] = useState(null);
  const [pinging, setPinging] = useState(false);

  useEffect(() => {
    const t = setInterval(() => setAnimPulse(p => !p), 1500);
    return () => clearInterval(t);
  }, []);

  const handlePing = () => {
    setPinging(true);
    setPingResult(null);
    setTimeout(() => {
      const ms = Math.floor(Math.random() * 20) + 5;
      setPingResult({ ms, ok: true });
      setPinging(false);
    }, 1500);
  };

  const sig = currentNetwork?.signal || 85;
  const sColor = signalColor(sig);

  return (
    <div style={{ padding: "16px 0", display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Connection card */}
      <div style={{ background: C.panel, borderRadius: 16, padding: 20, border: `1px solid ${C.border}`, position: "relative", overflow: "hidden" }}>
        <div style={{ position: "absolute", top: -20, right: -20, width: 100, height: 100, borderRadius: "50%", background: `${sColor}18` }} />
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: C.green,
            boxShadow: animPulse ? `0 0 0 6px ${C.green}44` : "none", transition: "box-shadow 0.6s" }} />
          <span style={{ color: C.sub, fontSize: 12, fontFamily: "Consolas" }}>Подключено</span>
        </div>
        <div style={{ fontSize: 22, fontWeight: 700, color: C.text, fontFamily: "Consolas", marginBottom: 4 }}>
          {currentNetwork?.ssid || "HomeNetwork_5G"}
        </div>
        <div style={{ fontSize: 12, color: C.sub, fontFamily: "Consolas", marginBottom: 16 }}>
          {currentNetwork?.bssid || "A4:2B:8C:1D:4E:FF"}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div>
            <div style={{ fontSize: 36, fontWeight: 800, color: sColor, fontFamily: "Consolas", lineHeight: 1 }}>{sig}%</div>
            <div style={{ fontSize: 11, color: C.sub, fontFamily: "Consolas" }}>сигнал</div>
          </div>
          <div style={{ fontSize: 28 }}>{signalBars(sig)}</div>
        </div>
      </div>

      {/* IP Info row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        {[
          { label: "IPv4", val: "192.168.1.42" },
          { label: "Шлюз", val: "192.168.1.1" },
          { label: "DNS", val: "8.8.8.8" },
          { label: "Канал", val: "36 / 5GHz" },
        ].map(({ label, val }) => (
          <div key={label} style={{ background: C.panel, borderRadius: 12, padding: "12px 14px", border: `1px solid ${C.border}` }}>
            <div style={{ fontSize: 11, color: C.sub, fontFamily: "Consolas", marginBottom: 4 }}>{label}</div>
            <div style={{ fontSize: 13, color: C.text, fontFamily: "Consolas", fontWeight: 600 }}>{val}</div>
          </div>
        ))}
      </div>

      {/* Quick ping */}
      <div style={{ background: C.panel, borderRadius: 16, padding: 16, border: `1px solid ${C.border}` }}>
        <div style={{ fontSize: 13, color: C.sub, fontFamily: "Consolas", marginBottom: 10 }}>⚡ Быстрые действия</div>
        <button onClick={handlePing} disabled={pinging}
          style={{ width: "100%", padding: "12px 0", borderRadius: 10, border: "none",
            background: pinging ? C.border : C.accent, color: C.bg, fontFamily: "Consolas",
            fontSize: 14, fontWeight: 700, cursor: pinging ? "default" : "pointer", marginBottom: 8 }}>
          {pinging ? "⏳ Пинг 8.8.8.8..." : "📶 Пинг шлюза"}
        </button>
        {pingResult && (
          <div style={{ textAlign: "center", fontSize: 13, color: pingResult.ok ? C.green : C.danger, fontFamily: "Consolas" }}>
            ✅ Ответ за {pingResult.ms} мс — отличное соединение
          </div>
        )}
      </div>
    </div>
  );
}

// ── Tab: Networks ──
function Networks() {
  const [nets, setNets] = useState(MOCK_NETWORKS);
  const [scanning, setScanning] = useState(false);
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("signal");
  const [selected, setSelected] = useState(null);
  const [toast, setToast] = useState(null);

  const showToast = (msg, color = C.green) => {
    setToast({ msg, color });
    setTimeout(() => setToast(null), 2200);
  };

  const scan = () => {
    setScanning(true);
    setTimeout(() => {
      setNets([...MOCK_NETWORKS].sort(() => Math.random() - 0.5).map(n => ({
        ...n, signal: Math.max(10, Math.min(98, n.signal + Math.floor(Math.random() * 10) - 5))
      })));
      setScanning(false);
    }, 1800);
  };

  const filtered = nets
    .filter(n => n.ssid.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => sortBy === "signal" ? b.signal - a.signal : a.ssid.localeCompare(b.ssid));

  return (
    <div style={{ padding: "16px 0", display: "flex", flexDirection: "column", gap: 10 }}>
      {toast && (
        <div style={{ position: "fixed", top: 70, left: "50%", transform: "translateX(-50%)", zIndex: 999,
          background: toast.color, color: C.bg, padding: "10px 20px", borderRadius: 10, fontSize: 13,
          fontFamily: "Consolas", fontWeight: 700, boxShadow: "0 4px 20px #0008" }}>
          {toast.msg}
        </div>
      )}

      {/* Toolbar */}
      <div style={{ display: "flex", gap: 8 }}>
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="🔍 Поиск сети..."
          style={{ flex: 1, padding: "10px 14px", borderRadius: 10, border: `1px solid ${C.border}`,
            background: C.panel, color: C.text, fontFamily: "Consolas", fontSize: 13, outline: "none" }} />
        <button onClick={() => setSortBy(s => s === "signal" ? "name" : "signal")}
          style={{ padding: "10px 14px", borderRadius: 10, border: `1px solid ${C.border}`,
            background: C.panel, color: C.accent, fontFamily: "Consolas", fontSize: 12, cursor: "pointer", whiteSpace: "nowrap" }}>
          {sortBy === "signal" ? "📶 Сигнал" : "🔤 Имя"}
        </button>
      </div>

      <button onClick={scan} disabled={scanning}
        style={{ width: "100%", padding: "12px 0", borderRadius: 10, border: "none",
          background: scanning ? C.border : C.panel, color: scanning ? C.sub : C.accent,
          fontFamily: "Consolas", fontSize: 14, fontWeight: 700, cursor: scanning ? "default" : "pointer",
          border: `1px solid ${scanning ? C.border : C.accent}` }}>
        {scanning ? "⏳ Сканирование..." : "🔄 Обновить сети"}
      </button>

      <div style={{ fontSize: 11, color: C.sub, fontFamily: "Consolas" }}>
        Найдено: {filtered.length} / {nets.length} сетей
      </div>

      {filtered.map((net) => (
        <div key={net.bssid} onClick={() => setSelected(selected?.bssid === net.bssid ? null : net)}
          style={{ background: selected?.bssid === net.bssid ? C.panel + "cc" : C.panel,
            borderRadius: 14, padding: 14, border: `1px solid ${selected?.bssid === net.bssid ? C.accent : C.border}`,
            cursor: "pointer", transition: "all 0.2s" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
            <div style={{ fontFamily: "Consolas", fontSize: 15, fontWeight: 700, color: C.text }}>{net.ssid}</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {signalBars(net.signal)}
              <span style={{ fontSize: 13, fontWeight: 700, color: signalColor(net.signal), fontFamily: "Consolas" }}>{net.signal}%</span>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            {authBadge(net.auth)}
            <span style={{ fontSize: 11, color: C.sub, fontFamily: "Consolas" }}>CH {net.channel}</span>
            <span style={{ fontSize: 11, color: C.sub, fontFamily: "Consolas" }}>{net.band.split("/")[1] || net.band}</span>
          </div>
          {selected?.bssid === net.bssid && (
            <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${C.border}`, display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ fontSize: 11, color: C.sub, fontFamily: "Consolas" }}>BSSID: {net.bssid}</div>
              <div style={{ fontSize: 11, color: C.sub, fontFamily: "Consolas" }}>Шифр: {net.cipher}</div>
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={(e) => { e.stopPropagation(); showToast(`🔗 Подключение к ${net.ssid}...`, C.accent); }}
                  style={{ flex: 1, padding: "10px 0", borderRadius: 8, border: "none",
                    background: C.accent, color: C.bg, fontFamily: "Consolas", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>
                  🔗 Подключиться
                </button>
                <button onClick={(e) => { e.stopPropagation(); navigator.clipboard?.writeText(net.ssid); showToast("📋 SSID скопирован"); }}
                  style={{ flex: 1, padding: "10px 0", borderRadius: 8, border: `1px solid ${C.border}`,
                    background: "transparent", color: C.text, fontFamily: "Consolas", fontSize: 13, cursor: "pointer" }}>
                  📋 Копировать
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Tab: Monitor ──
function Monitor() {
  const [running, setRunning] = useState(false);
  const [history, setHistory] = useState(MOCK_SIGNAL_HISTORY.slice(-15));
  const [log, setLog] = useState([]);
  const intervalRef = useRef(null);
  const avg = history.length ? Math.round(history.reduce((a, b) => a + b) / history.length) : 0;
  const mn = history.length ? Math.min(...history) : 0;
  const mx = history.length ? Math.max(...history) : 0;

  const toggle = () => {
    if (running) {
      clearInterval(intervalRef.current);
      setRunning(false);
    } else {
      setRunning(true);
      intervalRef.current = setInterval(() => {
        const newSig = Math.max(20, Math.min(98, (history[history.length - 1] || 80) + Math.floor(Math.random() * 14) - 7));
        const ts = new Date().toLocaleTimeString("ru-RU");
        setHistory(h => [...h.slice(-29), newSig]);
        setLog(l => [`[${ts}]  SSID: HomeNetwork_5G   Сигнал: ${newSig}%`, ...l.slice(0, 49)]);
      }, 2000);
    }
  };

  useEffect(() => () => clearInterval(intervalRef.current), []);

  return (
    <div style={{ padding: "16px 0", display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
        {[["Avg", avg, C.accent], ["Min", mn, C.warn], ["Max", mx, C.green]].map(([label, val, color]) => (
          <div key={label} style={{ background: C.panel, borderRadius: 12, padding: "12px 0", textAlign: "center", border: `1px solid ${C.border}` }}>
            <div style={{ fontSize: 26, fontWeight: 800, color, fontFamily: "Consolas" }}>{val}%</div>
            <div style={{ fontSize: 11, color: C.sub, fontFamily: "Consolas" }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Graph */}
      <div style={{ background: C.panel, borderRadius: 16, padding: 12, border: `1px solid ${C.border}` }}>
        <div style={{ fontSize: 12, color: C.sub, fontFamily: "Consolas", marginBottom: 8 }}>
          📊 График сигнала ({history.length} точек)
        </div>
        <SignalGraph history={history} height={100} />
      </div>

      {/* Control */}
      <button onClick={toggle}
        style={{ width: "100%", padding: "14px 0", borderRadius: 12, border: "none",
          background: running ? C.danger : C.green, color: C.bg,
          fontFamily: "Consolas", fontSize: 15, fontWeight: 700, cursor: "pointer" }}>
        {running ? "⏹ Остановить мониторинг" : "▶ Запустить мониторинг"}
      </button>

      {/* Log */}
      {log.length > 0 && (
        <div style={{ background: C.panel, borderRadius: 16, padding: 14, border: `1px solid ${C.border}`, maxHeight: 200, overflow: "auto" }}>
          <div style={{ fontSize: 12, color: C.sub, fontFamily: "Consolas", marginBottom: 8 }}>📝 Лог</div>
          {log.map((line, i) => (
            <div key={i} style={{ fontSize: 11, color: i === 0 ? C.accent : C.sub, fontFamily: "Consolas", padding: "2px 0" }}>{line}</div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Tab: Profiles ──
function Profiles() {
  const [selected, setSelected] = useState(null);
  const [showPass, setShowPass] = useState({});
  const [toast, setToast] = useState(null);
  const passwords = { "HomeNetwork_5G": "SuperSecure#2024", "OfficeWifi": "Office@Pass123", "GrandmaHouse": "qwerty12345" };

  const showToast = (msg, color = C.green) => {
    setToast({ msg, color });
    setTimeout(() => setToast(null), 2200);
  };

  return (
    <div style={{ padding: "16px 0", display: "flex", flexDirection: "column", gap: 10 }}>
      {toast && (
        <div style={{ position: "fixed", top: 70, left: "50%", transform: "translateX(-50%)", zIndex: 999,
          background: toast.color, color: C.bg, padding: "10px 20px", borderRadius: 10, fontSize: 13,
          fontFamily: "Consolas", fontWeight: 700, boxShadow: "0 4px 20px #0008" }}>
          {toast.msg}
        </div>
      )}
      <div style={{ fontSize: 11, color: C.sub, fontFamily: "Consolas" }}>
        Сохранено профилей: {MOCK_PROFILES.length}
      </div>
      {MOCK_PROFILES.map(p => (
        <div key={p.name} onClick={() => setSelected(selected === p.name ? null : p.name)}
          style={{ background: C.panel, borderRadius: 14, padding: 14, border: `1px solid ${selected === p.name ? C.accent : C.border}`, cursor: "pointer" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 20 }}>{p.connected ? "📶" : "💾"}</span>
              <div>
                <div style={{ fontFamily: "Consolas", fontSize: 14, fontWeight: 700, color: p.connected ? C.green : C.text }}>{p.name}</div>
                <div style={{ fontSize: 11, color: C.sub, fontFamily: "Consolas" }}>{p.auth}</div>
              </div>
            </div>
            {p.connected && <span style={{ fontSize: 11, color: C.green, background: C.green + "22", padding: "3px 8px", borderRadius: 6, fontFamily: "Consolas" }}>Активно</span>}
          </div>

          {selected === p.name && (
            <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${C.border}`, display: "flex", flexDirection: "column", gap: 8 }}>
              {passwords[p.name] && (
                <div style={{ background: C.bg, borderRadius: 8, padding: "10px 12px", fontFamily: "Consolas" }}>
                  <div style={{ fontSize: 11, color: C.sub, marginBottom: 4 }}>🔑 Пароль</div>
                  <div style={{ fontSize: 14, color: C.purple, letterSpacing: showPass[p.name] ? 0 : 3 }}>
                    {showPass[p.name] ? passwords[p.name] : "●".repeat(passwords[p.name].length)}
                  </div>
                </div>
              )}
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {passwords[p.name] && (
                  <>
                    <button onClick={(e) => { e.stopPropagation(); setShowPass(s => ({ ...s, [p.name]: !s[p.name] })); }}
                      style={{ flex: 1, padding: "9px 0", borderRadius: 8, border: `1px solid ${C.purple}`,
                        background: "transparent", color: C.purple, fontFamily: "Consolas", fontSize: 12, cursor: "pointer" }}>
                      {showPass[p.name] ? "🙈 Скрыть" : "👁 Показать"}
                    </button>
                    <button onClick={(e) => { e.stopPropagation(); navigator.clipboard?.writeText(passwords[p.name]); showToast("📋 Пароль скопирован"); }}
                      style={{ flex: 1, padding: "9px 0", borderRadius: 8, border: `1px solid ${C.border}`,
                        background: "transparent", color: C.text, fontFamily: "Consolas", fontSize: 12, cursor: "pointer" }}>
                      📋 Копировать
                    </button>
                  </>
                )}
                {!p.connected && (
                  <button onClick={(e) => { e.stopPropagation(); showToast(`🔗 Подключение к ${p.name}`, C.accent); }}
                    style={{ width: "100%", padding: "10px 0", borderRadius: 8, border: "none",
                      background: C.accent, color: C.bg, fontFamily: "Consolas", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>
                    🔗 Подключиться
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Tab: Diagnostic ──
function Diagnostic() {
  const [host, setHost] = useState("8.8.8.8");
  const [pinging, setPinging] = useState(false);
  const [pingLog, setPingLog] = useState([]);
  const [ipInfo] = useState({
    IPv4: "192.168.1.42", Маска: "255.255.255.0",
    Шлюз: "192.168.1.1", DNS: "8.8.8.8",
    SSID: "HomeNetwork_5G", Тип: "802.11ac (Wi-Fi 5)",
  });

  const runPing = () => {
    if (pinging) return;
    setPinging(true);
    setPingLog(l => [`\n── Ping ${host} ──`, ...l]);
    let count = 0;
    const t = setInterval(() => {
      const ms = Math.floor(Math.random() * 30) + 4;
      const loss = Math.random() > 0.9;
      setPingLog(l => [loss ? `Запрос превысил время ожидания` : `Ответ от ${host}: время=${ms} мс TTL=57`, ...l]);
      count++;
      if (count >= 4) {
        clearInterval(t);
        setPingLog(l => [`Потерь: ${loss ? 1 : 0}/4 (${loss ? 25 : 0}%)   Время: мин=${ms - 2} макс=${ms + 4} ср=${ms}`, ...l]);
        setPinging(false);
      }
    }, 500);
  };

  return (
    <div style={{ padding: "16px 0", display: "flex", flexDirection: "column", gap: 12 }}>
      {/* IP Info */}
      <div style={{ background: C.panel, borderRadius: 16, padding: 16, border: `1px solid ${C.border}` }}>
        <div style={{ fontSize: 13, color: C.accent, fontFamily: "Consolas", fontWeight: 700, marginBottom: 10 }}>🌐 Сетевая информация</div>
        {Object.entries(ipInfo).map(([k, v]) => (
          <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0",
            borderBottom: `1px solid ${C.border}11`, fontFamily: "Consolas" }}>
            <span style={{ fontSize: 12, color: C.sub }}>{k}</span>
            <span style={{ fontSize: 12, color: C.text, fontWeight: 600 }}>{v}</span>
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
        {[
          { label: "Сброс TCP/IP", color: C.warn, icon: "🔄" },
          { label: "DHCP", color: C.green, icon: "♻️" },
          { label: "DNS кэш", color: C.accent, icon: "🗑" },
        ].map(({ label, color, icon }) => (
          <button key={label}
            style={{ padding: "12px 6px", borderRadius: 10, border: `1px solid ${color}44`,
              background: color + "18", color, fontFamily: "Consolas", fontSize: 11, cursor: "pointer",
              display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
            <span style={{ fontSize: 18 }}>{icon}</span>
            {label}
          </button>
        ))}
      </div>

      {/* Ping tool */}
      <div style={{ background: C.panel, borderRadius: 16, padding: 16, border: `1px solid ${C.border}` }}>
        <div style={{ fontSize: 13, color: C.accent, fontFamily: "Consolas", fontWeight: 700, marginBottom: 10 }}>📶 Ping / Трассировка</div>
        <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
          <input value={host} onChange={e => setHost(e.target.value)}
            style={{ flex: 1, padding: "10px 12px", borderRadius: 8, border: `1px solid ${C.border}`,
              background: C.bg, color: C.text, fontFamily: "Consolas", fontSize: 13, outline: "none" }} />
          <button onClick={runPing} disabled={pinging}
            style={{ padding: "10px 16px", borderRadius: 8, border: "none",
              background: pinging ? C.border : C.accent, color: C.bg,
              fontFamily: "Consolas", fontSize: 13, fontWeight: 700, cursor: pinging ? "default" : "pointer" }}>
            {pinging ? "⏳" : "Ping"}
          </button>
        </div>
        {pingLog.length > 0 && (
          <div style={{ background: C.bg, borderRadius: 10, padding: 12, maxHeight: 150, overflow: "auto" }}>
            {pingLog.map((line, i) => (
              <div key={i} style={{ fontSize: 11, color: line.startsWith("──") ? C.accent : line.includes("Потерь") ? C.warn : C.green,
                fontFamily: "Consolas", padding: "1px 0" }}>{line}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main App ──
export default function WiFiManagerMobile() {
  const [tab, setTab] = useState("dashboard");
  const tabs = [
    { id: "dashboard", icon: "📡", label: "Главная" },
    { id: "networks",  icon: "🔍", label: "Сети" },
    { id: "monitor",   icon: "📊", label: "Монитор" },
    { id: "profiles",  icon: "💾", label: "Профили" },
    { id: "diag",      icon: "🛠", label: "Диагност." },
  ];

  const renderTab = () => {
    switch (tab) {
      case "dashboard": return <Dashboard currentNetwork={MOCK_NETWORKS[0]} />;
      case "networks":  return <Networks />;
      case "monitor":   return <Monitor />;
      case "profiles":  return <Profiles />;
      case "diag":      return <Diagnostic />;
      default:          return null;
    }
  };

  return (
    <div style={{ background: C.bg, minHeight: "100vh", display: "flex", justifyContent: "center", fontFamily: "Consolas, monospace" }}>
      <div style={{ width: "100%", maxWidth: 420, display: "flex", flexDirection: "column", minHeight: "100vh", position: "relative" }}>
        {/* Header */}
        <div style={{ background: C.panel, padding: "14px 20px 10px", borderBottom: `1px solid ${C.border}`,
          display: "flex", alignItems: "center", justifyContent: "space-between", position: "sticky", top: 0, zIndex: 100 }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 800, color: C.text }}>📡 WiFi Manager</div>
            <div style={{ fontSize: 11, color: C.sub }}>Pro  v2.0  •  Mobile</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: C.green, boxShadow: `0 0 8px ${C.green}` }} />
            <span style={{ fontSize: 12, color: C.green }}>HomeNetwork_5G</span>
          </div>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: "auto", padding: "0 16px 80px" }}>
          {renderTab()}
        </div>

        {/* Bottom nav */}
        <div style={{ position: "fixed", bottom: 0, left: "50%", transform: "translateX(-50%)",
          width: "100%", maxWidth: 420, background: C.panel, borderTop: `1px solid ${C.border}`,
          display: "flex", padding: "8px 0 12px", zIndex: 100 }}>
          {tabs.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 3,
                background: "none", border: "none", cursor: "pointer", padding: "4px 0",
                transition: "all 0.15s" }}>
              <div style={{ fontSize: 20, filter: tab === t.id ? "none" : "grayscale(0.4) opacity(0.6)" }}>{t.icon}</div>
              <div style={{ fontSize: 10, color: tab === t.id ? C.accent : C.sub, fontFamily: "Consolas",
                fontWeight: tab === t.id ? 700 : 400, transition: "color 0.15s" }}>
                {t.label}
              </div>
              {tab === t.id && (
                <div style={{ width: 20, height: 2, borderRadius: 1, background: C.accent, marginTop: 1 }} />
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
