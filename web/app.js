(() => {
  const state = {
    ws: null,
    mode: "local",
    supportsWs: true,
    pollTimer: null,
    deferredInstallPrompt: null,
    localBridgeUrl: localStorage.getItem("prometheus_local_bridge") || "",
    config: null,
    apps: [],
    micActive: false,
    isSpeaking: false,
    awaitingCommand: false,
    awaitTimeout: null,
    recognition: null,
    restartTimer: null,
    consecutiveErrors: 0,
    audioCtx: null,
    analyser: null,
    micStream: null,
    currentAudio: null,
    speechLang: "tr-TR",
  };

  const els = {
    connStatus: document.getElementById("connStatus"),
    connLabel: document.getElementById("connLabel"),
    toggleAuthority: document.getElementById("toggleAuthority"),
    toggleWakeWord: document.getElementById("toggleWakeWord"),
    toggleTTS: document.getElementById("toggleTTS"),
    langSelect: document.getElementById("langSelect"),
    osTag: document.getElementById("osTag"),
    cpuVal: document.getElementById("cpuVal"),
    cpuBar: document.getElementById("cpuBar"),
    ramVal: document.getElementById("ramVal"),
    ramBar: document.getElementById("ramBar"),
    ramSub: document.getElementById("ramSub"),
    diskVal: document.getElementById("diskVal"),
    diskBar: document.getElementById("diskBar"),
    hostMeta: document.getElementById("hostMeta"),
    uptimeMeta: document.getElementById("uptimeMeta"),
    timerCount: document.getElementById("timerCount"),
    timerList: document.getElementById("timerList"),
    coreButton: document.getElementById("coreButton"),
    coreIcon: document.getElementById("coreIcon"),
    coreStateText: document.getElementById("coreStateText"),
    voiceHint: document.getElementById("voiceHint"),
    liveTranscript: document.getElementById("liveTranscript"),
    commandForm: document.getElementById("commandForm"),
    commandInput: document.getElementById("commandInput"),
    btnMicInline: document.getElementById("btnMicInline"),
    chatLog: document.getElementById("chatLog"),
    btnClearLog: document.getElementById("btnClearLog"),
    quickNoteInput: document.getElementById("quickNoteInput"),
    btnQuickNote: document.getElementById("btnQuickNote"),
    notesList: document.getElementById("notesList"),
    noteCount: document.getElementById("noteCount"),
    appsList: document.getElementById("appsList"),
    procsList: document.getElementById("procsList"),
    appSearch: document.getElementById("appSearch"),
    btnRefreshApps: document.getElementById("btnRefreshApps"),
    visualizerCanvas: document.getElementById("visualizerCanvas"),
    // Modal
    settingsModal: document.getElementById("settingsModal"),
    btnInstallDesktop: document.getElementById("btnInstallDesktop"),
    btnSettings: document.getElementById("btnSettings"),
    btnCloseModal: document.getElementById("btnCloseModal"),
    voiceTrSelect: document.getElementById("voiceTrSelect"),
    voiceEnSelect: document.getElementById("voiceEnSelect"),
    ollamaUrlInput: document.getElementById("ollamaUrlInput"),
    ollamaModelInput: document.getElementById("ollamaModelInput"),
    localBridgeInput: document.getElementById("localBridgeInput"),
    confirmPowerToggle: document.getElementById("confirmPowerToggle"),
    btnSaveSettings: document.getElementById("btnSaveSettings"),
    customAppName: document.getElementById("customAppName"),
    customAppPath: document.getElementById("customAppPath"),
    btnAddCustomApp: document.getElementById("btnAddCustomApp"),
    customAppsList: document.getElementById("customAppsList"),
    customSiteName: document.getElementById("customSiteName"),
    customSiteUrl: document.getElementById("customSiteUrl"),
    btnAddCustomSite: document.getElementById("btnAddCustomSite"),
    customSitesList: document.getElementById("customSitesList"),
    customCmdTrigger: document.getElementById("customCmdTrigger"),
    customCmdAction: document.getElementById("customCmdAction"),
    btnAddCustomCmd: document.getElementById("btnAddCustomCmd"),
    customCmdsList: document.getElementById("customCmdsList"),
  };

  // --- Synthesized Sci-Fi Chimes (Zero external assets) ---
  function ensureAudioCtx() {
    if (!state.audioCtx) {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (Ctx) state.audioCtx = new Ctx();
    }
    if (state.audioCtx && state.audioCtx.state === "suspended") {
      state.audioCtx.resume().catch(() => {});
    }
    return state.audioCtx;
  }

  function playTone(kind) {
    const ctx = ensureAudioCtx();
    if (!ctx) return;
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    if (kind === "wake") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(520, now);
      osc.frequency.exponentialRampToValueAtTime(980, now + 0.14);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);
      osc.start(now);
      osc.stop(now + 0.24);
    } else if (kind === "exec") {
      osc.type = "triangle";
      osc.frequency.setValueAtTime(660, now);
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.08);
      gain.gain.setValueAtTime(0.05, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
      osc.start(now);
      osc.stop(now + 0.13);
    } else if (kind === "timer") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(880, now);
      osc.frequency.setValueAtTime(1174, now + 0.15);
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
      osc.start(now);
      osc.stop(now + 0.46);
    }
  }

  // --- Wake Word Matcher (Client-Side Fast Mirror of nlp_utils.py) ---
  function normalizeAscii(str) {
    return str
      .replace(/İ/g, "i")
      .replace(/I/g, "i")
      .replace(/ı/g, "i")
      .replace(/Ş/g, "s")
      .replace(/ş/g, "s")
      .replace(/Ğ/g, "g")
      .replace(/ğ/g, "g")
      .replace(/Ü/g, "u")
      .replace(/ü/g, "u")
      .replace(/Ö/g, "o")
      .replace(/ö/g, "o")
      .replace(/Ç/g, "c")
      .replace(/ç/g, "c")
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function levenshtein(a, b) {
    const dp = Array.from({ length: a.length + 1 }, () => Array(b.length + 1).fill(0));
    for (let i = 0; i <= a.length; i++) dp[i][0] = i;
    for (let j = 0; j <= b.length; j++) dp[0][j] = j;
    for (let i = 1; i <= a.length; i++) {
      for (let j = 1; j <= b.length; j++) {
        dp[i][j] = Math.min(
          dp[i - 1][j] + 1,
          dp[i][j - 1] + 1,
          dp[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)
        );
      }
    }
    return dp[a.length][b.length];
  }

  function isWakeToken(tok) {
    if (!tok || tok.length < 5) return false;
    const known = [
      "prometheus", "prometyus", "prometeus", "prometius", "promethius",
      "prometus", "prametyus", "promete", "promethe", "jarvis", "carvis",
    ];
    if (known.includes(tok)) return true;
    const targets = ["prometheus", "prometyus", "jarvis"];
    return targets.some((t) => {
      const dist = levenshtein(tok, t);
      return dist <= Math.floor(t.length * 0.28);
    });
  }

  function matchWakeWordClient(transcript) {
    const raw = transcript.trim();
    if (!raw) return { matched: false, rest: "" };
    const wordsRaw = raw.split(/\s+/);
    const wordsNorm = wordsRaw.map((w) => normalizeAscii(w).replace(/[^a-z]/g, ""));

    const prefixes = ["hey", "ok", "okay", "merhaba", "selam", "alo", "yo"];
    if (wordsNorm.length >= 2 && prefixes.includes(wordsNorm[0]) && isWakeToken(wordsNorm[1])) {
      return {
        matched: true,
        rest: wordsRaw.slice(2).join(" ").replace(/^[,.:;!?-]+/, "").trim(),
      };
    }

    for (let i = 0; i < Math.min(3, wordsNorm.length); i++) {
      if (isWakeToken(wordsNorm[i])) {
        let rest = wordsRaw.slice(i + 1).join(" ").replace(/^[,.:;!?-]+/, "").trim();
        if (!rest && i > 0) {
          rest = wordsRaw.slice(0, i).join(" ").trim();
        }
        return { matched: true, rest };
      }
    }

    return { matched: false, rest: raw };
  }

  // --- Visualizer Loop ---
  function drawVisualizer() {
    const canvas = els.visualizerCanvas;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const radius = 122;
    let freqData = null;
    if (state.analyser) {
      freqData = new Uint8Array(state.analyser.frequencyBinCount);
    }

    function frame() {
      requestAnimationFrame(frame);
      ctx.clearRect(0, 0, w, h);

      let avg = 0;
      if (state.analyser && freqData && state.micActive && !state.isSpeaking) {
        state.analyser.getByteFrequencyData(freqData);
        for (let i = 0; i < freqData.length; i++) avg += freqData[i];
        avg /= freqData.length;
      } else if (state.isSpeaking) {
        avg = 38 + Math.sin(Date.now() * 0.018) * 24;
      }

      const bars = 64;
      for (let i = 0; i < bars; i++) {
        const angle = (i / bars) * Math.PI * 2;
        let amp = 4;
        if (freqData && state.micActive && !state.isSpeaking) {
          amp = 4 + (freqData[i % freqData.length] / 255) * 34;
        } else if (state.isSpeaking) {
          amp = 6 + Math.abs(Math.sin(Date.now() * 0.012 + i * 0.4)) * 28;
        } else if (state.micActive) {
          amp = 4 + Math.abs(Math.sin(Date.now() * 0.004 + i * 0.25)) * 6;
        }

        const x1 = cx + Math.cos(angle) * radius;
        const y1 = cy + Math.sin(angle) * radius;
        const x2 = cx + Math.cos(angle) * (radius + amp);
        const y2 = cy + Math.sin(angle) * (radius + amp);

        ctx.strokeStyle = state.awaitingCommand || state.isSpeaking
          ? "rgba(255, 174, 0, 0.85)"
          : state.micActive
          ? "rgba(0, 229, 255, 0.85)"
          : "rgba(0, 229, 255, 0.25)";
        ctx.lineWidth = 2.4;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
    }
    frame();
  }

  // --- TTS (Free Neural Edge-TTS + Browser SpeechSynthesis Fallback) ---
  async function speakText(text, lang = "tr") {
    if (!els.toggleTTS.checked || !text) return;

    // Stop any previous speech & pause STT to prevent echo loop
    stopCurrentAudio();
    state.isSpeaking = true;
    pauseRecognitionForSpeech();
    updateReactorUI();

    const finishSpeech = () => {
      state.isSpeaking = false;
      updateReactorUI();
      setTimeout(() => {
        if (state.micActive) resumeRecognitionAfterSpeech();
      }, 260);
    };

    try {
      const res = await fetch(`${apiBase()}/api/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, language: lang }),
      });
      if (res.status === 200) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        state.currentAudio = audio;
        audio.onended = () => {
          URL.revokeObjectURL(url);
          state.currentAudio = null;
          finishSpeech();
        };
        audio.onerror = () => {
          URL.revokeObjectURL(url);
          state.currentAudio = null;
          fallbackBrowserSpeak(text, lang, finishSpeech);
        };
        await audio.play();
        return;
      }
    } catch (_) {
      // Fall through to browser speechSynthesis
    }
    fallbackBrowserSpeak(text, lang, finishSpeech);
  }

  function fallbackBrowserSpeak(text, lang, onDone) {
    if (!("speechSynthesis" in window)) {
      onDone();
      return;
    }
    try {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.lang = lang === "en" ? "en-GB" : "tr-TR";
      utter.rate = 1.04;
      utter.pitch = 0.96;
      const voices = window.speechSynthesis.getVoices();
      const match = voices.find((v) => v.lang.toLowerCase().startsWith(lang));
      if (match) utter.voice = match;
      utter.onend = onDone;
      utter.onerror = onDone;
      window.speechSynthesis.speak(utter);
    } catch (_) {
      onDone();
    }
  }

  function stopCurrentAudio() {
    if (state.currentAudio) {
      state.currentAudio.pause();
      state.currentAudio = null;
    }
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }

  // --- Flawless Voice Recognition Loop ---
  function getSpeechRecognitionCtor() {
    return window.SpeechRecognition || window.webkitSpeechRecognition || null;
  }

  async function initMicVisualizer() {
    if (state.micStream) return;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      state.micStream = stream;
      const ctx = ensureAudioCtx();
      if (ctx) {
        const src = ctx.createMediaStreamSource(stream);
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 128;
        src.connect(analyser);
        state.analyser = analyser;
      }
    } catch (_) {
      // Visualizer optional; SpeechRecognition may still work
    }
  }

  function pauseRecognitionForSpeech() {
    clearTimeout(state.restartTimer);
    if (state.recognition) {
      try {
        state.recognition.abort();
      } catch (_) {}
    }
  }

  function resumeRecognitionAfterSpeech() {
    if (!state.micActive || state.isSpeaking) return;
    startRecognitionInstance();
  }

  function startRecognitionInstance() {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      els.voiceHint.innerHTML =
        "⚠️ Bu tarayıcı Web Speech API desteklemiyor. Chrome veya Edge kullanın ya da alttan yazın.";
      state.micActive = false;
      updateReactorUI();
      return;
    }

    if (state.recognition) {
      try {
        state.recognition.onend = null;
        state.recognition.abort();
      } catch (_) {}
    }

    const rec = new Ctor();
    rec.lang = els.langSelect.value || "tr-TR";
    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    rec.onstart = () => {
      state.consecutiveErrors = 0;
      updateReactorUI();
    };

    rec.onresult = (event) => {
      if (state.isSpeaking) return;
      let interim = "";
      let finalText = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const res = event.results[i];
        const txt = res[0].transcript;
        if (res.isFinal) {
          finalText += " " + txt;
        } else {
          interim += " " + txt;
        }
      }

      const display = (finalText || interim).trim();
      if (display) {
        els.liveTranscript.textContent = display;
      }

      if (finalText.trim()) {
        handleSpokenPhrase(finalText.trim());
      }
    };

    rec.onerror = (ev) => {
      if (ev.error === "no-speech" || ev.error === "aborted") {
        return; // Normal silence / pause
      }
      if (ev.error === "not-allowed" || ev.error === "service-not-allowed") {
        state.micActive = false;
        els.voiceHint.textContent =
          "Mikrofon izni verilmedi. Tarayıcı adres çubuğundan mikrofon izni verin.";
        updateReactorUI();
        return;
      }
      state.consecutiveErrors += 1;
    };

    rec.onend = () => {
      if (!state.micActive || state.isSpeaking) return;
      const delay = Math.min(2500, 180 + state.consecutiveErrors * 450);
      clearTimeout(state.restartTimer);
      state.restartTimer = setTimeout(() => {
        if (state.micActive && !state.isSpeaking) {
          startRecognitionInstance();
        }
      }, delay);
    };

    state.recognition = rec;
    try {
      rec.start();
    } catch (_) {
      // Ignore already started race
    }
  }

  function enterAwaitingWindow() {
    state.awaitingCommand = true;
    updateReactorUI();
    clearTimeout(state.awaitTimeout);
    state.awaitTimeout = setTimeout(() => {
      state.awaitingCommand = false;
      updateReactorUI();
    }, 8500);
  }

  function handleSpokenPhrase(transcript) {
    const wakeEnabled = els.toggleWakeWord.checked;

    if (!wakeEnabled || state.awaitingCommand) {
      state.awaitingCommand = false;
      clearTimeout(state.awaitTimeout);
      // Strip accidental wake word even in awaiting mode
      const check = matchWakeWordClient(transcript);
      const cmd = check.matched && check.rest ? check.rest : transcript;
      if (cmd) {
        playTone("exec");
        sendCommand(cmd);
      }
      updateReactorUI();
      return;
    }

    // Wake word required
    const { matched, rest } = matchWakeWordClient(transcript);
    if (!matched) {
      return;
    }

    if (rest) {
      playTone("exec");
      sendCommand(rest);
    } else {
      playTone("wake");
      enterAwaitingWindow();
      const ack = els.langSelect.value.startsWith("en")
        ? "Listening, sir."
        : "Sizi dinliyorum efendim.";
      speakText(ack, els.langSelect.value.startsWith("en") ? "en" : "tr");
    }
  }

  async function toggleMic() {
    if (state.micActive) {
      state.micActive = false;
      state.awaitingCommand = false;
      clearTimeout(state.restartTimer);
      clearTimeout(state.awaitTimeout);
      if (state.recognition) {
        try {
          state.recognition.onend = null;
          state.recognition.stop();
        } catch (_) {}
      }
      updateReactorUI();
      return;
    }

    state.micActive = true;
    ensureAudioCtx();
    await initMicVisualizer();
    playTone("wake");
    startRecognitionInstance();
    updateReactorUI();
  }

  function updateReactorUI() {
    els.coreButton.classList.toggle("active", state.micActive);
    els.coreButton.classList.toggle("awake", state.awaitingCommand);
    els.coreButton.classList.toggle("speaking", state.isSpeaking);
    els.btnMicInline.classList.toggle("active", state.micActive);

    if (state.isSpeaking) {
      els.coreIcon.textContent = "🔊";
      els.coreStateText.textContent = "KONUŞUYOR";
      els.connStatus.classList.add("listening");
    } else if (state.awaitingCommand) {
      els.coreIcon.textContent = "⚡";
      els.coreStateText.textContent = "EMİR BEKLENİYOR";
      els.voiceHint.textContent = "Prometheus aktif! Komutunuzu söyleyin...";
      els.connStatus.classList.add("listening");
    } else if (state.micActive) {
      els.coreIcon.textContent = "🎙️";
      els.coreStateText.textContent = els.toggleWakeWord.checked ? "HAZIR" : "DİNLİYOR";
      els.voiceHint.innerHTML = els.toggleWakeWord.checked
        ? '<strong>"Prometheus ..."</strong> diyerek sesli komut verin (örn: <em>"Prometheus YouTube\'u aç"</em>).'
        : "Doğrudan dinleme aktif — istediğiniz komutu söyleyin.";
      els.connStatus.classList.add("listening");
    } else {
      els.coreIcon.textContent = "🎙️";
      els.coreStateText.textContent = "BAŞLAT";
      els.voiceHint.innerHTML =
        'Mikrofonu başlatmak için çekirdeğe tıklayın veya <strong>Boşluk</strong> tuşuna basın.';
      els.connStatus.classList.remove("listening");
    }
  }

  function apiBase() {
    return state.localBridgeUrl ? state.localBridgeUrl.replace(/\/+$/, "") : "";
  }

  // --- WebSocket & Commands ---
  function connectWS() {
    if (!state.supportsWs) {
      els.connLabel.textContent = state.localBridgeUrl ? "YEREL PC KÖPRÜSÜ" : "BULUT · ÇEVRİMİÇİ";
      startHttpPolling();
      return;
    }
    const base = apiBase();
    const wsUrl = base
      ? base.replace(/^http/, "ws") + "/ws"
      : `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws`;
    const ws = new WebSocket(wsUrl);
    state.ws = ws;

    ws.onopen = () => {
      els.connLabel.textContent = "ÇEVRİMİÇİ";
    };

    ws.onclose = () => {
      if (!state.supportsWs) return;
      els.connLabel.textContent = "YENİDEN BAĞLANIYOR";
      setTimeout(connectWS, 3000);
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "telemetry") {
          renderTelemetry(msg.telemetry);
          renderTimers(msg.timers || []);
        } else if (msg.type === "timer_fired") {
          playTone("timer");
          appendMessage("bot", msg.text, "timer_fired");
          speakText(msg.text, "tr");
        } else if (msg.type === "command_result") {
          handleCommandResult(msg);
        }
      } catch (_) {}
    };
  }

  function startHttpPolling() {
    clearInterval(state.pollTimer);
    state.pollTimer = setInterval(async () => {
      try {
        const res = await fetch(`${apiBase()}/api/state`);
        const data = await res.json();
        renderTelemetry(data.telemetry);
        renderTimers(data.timers || []);
        if (Array.isArray(data.due_timers)) {
          data.due_timers.forEach((t) => {
            const msg = `Efendim, zamanlayıcı doldu: ${t.label}`;
            playTone("timer");
            appendMessage("bot", msg, "timer_fired");
            speakText(msg, "tr");
          });
        }
      } catch (_) {}
    }, 10000);
  }

  async function sendCommand(text) {
    const clean = text.trim();
    if (!clean) return;
    appendMessage("user", clean);

    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
      state.ws.send(JSON.stringify({ type: "command", text: clean }));
      return;
    }

    try {
      const res = await fetch(`${apiBase()}/api/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: clean }),
      });
      const data = await res.json();
      handleCommandResult(data);
    } catch (err) {
      appendMessage("bot", `Bağlantı hatası: ${err.message}`, "error");
    }
  }

  function handleCommandResult(res) {
    if (res.ignored) return;
    appendMessage("bot", res.text, res.intent, res.data, res.client_action);
    speakText(res.text, res.language || "tr");

    if (res.client_action && res.client_action.type === "open_url") {
      // Open in new tab from user's browser as well!
      try {
        window.open(res.client_action.url, "_blank", "noopener,noreferrer");
      } catch (_) {}
    }

    if (Array.isArray(res.notes)) {
      renderNotes(res.notes);
    } else if (res.intent && res.intent.includes("note")) {
      refreshNotes();
    }
  }

  function appendMessage(role, text, intent = "", data = {}, clientAction = null) {
    const div = document.createElement("div");
    div.className = `msg ${role === "user" ? "msg-user" : "msg-bot"}`;

    const meta = document.createElement("div");
    meta.className = "msg-meta";
    const timeStr = new Date().toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    meta.innerHTML = `<span>${role === "user" ? "SİZ" : "PROMETHEUS"}</span><span>${intent ? intent.toUpperCase() + " · " : ""}${timeStr}</span>`;
    div.appendChild(meta);

    const body = document.createElement("div");
    body.textContent = text;
    div.appendChild(body);

    if (clientAction && clientAction.type === "open_url" && clientAction.url) {
      const a = document.createElement("a");
      a.className = "msg-link-btn";
      a.href = clientAction.url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = `🌐 Siteyi Aç: ${clientAction.url}`;
      div.appendChild(a);
    }

    if (intent === "shell_exec" && data && data.output) {
      const pre = document.createElement("pre");
      pre.className = "msg-code";
      pre.textContent = data.output;
      div.appendChild(pre);
    }

    els.chatLog.appendChild(div);
    els.chatLog.scrollTop = els.chatLog.scrollHeight;
  }

  // --- Rendering Helpers ---
  function renderTelemetry(t) {
    if (!t) return;
    els.osTag.textContent = t.os || "—";
    els.cpuVal.textContent = `${t.cpu_percent}%`;
    els.cpuBar.style.width = `${Math.min(100, t.cpu_percent)}%`;
    els.ramVal.textContent = `${t.ram_percent}%`;
    els.ramBar.style.width = `${Math.min(100, t.ram_percent)}%`;
    els.ramSub.textContent = `${t.ram_used_gb} / ${t.ram_total_gb} GB`;
    if (t.disk) {
      els.diskVal.textContent = `${t.disk.percent}%`;
      els.diskBar.style.width = `${Math.min(100, t.disk.percent)}%`;
    }
    els.hostMeta.textContent = `Host: ${t.hostname || "—"}`;
    els.uptimeMeta.textContent = `Çalışma: ${t.uptime || "—"}`;
  }

  function renderTimers(timers) {
    els.timerCount.textContent = String(timers.length);
    if (!timers.length) {
      els.timerList.innerHTML = '<div class="empty-hint">Aktif zamanlayıcı yok.</div>';
      return;
    }
    els.timerList.innerHTML = "";
    const now = Date.now() / 1000;
    timers.forEach((t) => {
      const rem = Math.max(0, Math.round(t.fire_at - now));
      const row = document.createElement("div");
      row.className = "note-item";
      row.innerHTML = `<span>⏱ ${t.label}</span><span class="mini-tag">${rem}s</span>`;
      els.timerList.appendChild(row);
    });
  }

  function renderNotes(notes) {
    els.noteCount.textContent = String(notes.length);
    if (!notes.length) {
      els.notesList.innerHTML = '<div class="empty-hint">Kayıtlı not yok.</div>';
      return;
    }
    els.notesList.innerHTML = "";
    notes.forEach((n) => {
      const row = document.createElement("div");
      row.className = "note-item";
      const span = document.createElement("span");
      span.textContent = n.content;
      const btn = document.createElement("button");
      btn.textContent = "✕";
      btn.onclick = async () => {
        await fetch(`${apiBase()}/api/notes/${n.id}`, { method: "DELETE" });
        refreshNotes();
      };
      row.append(span, btn);
      els.notesList.appendChild(row);
    });
  }

  function renderApps(apps, filter = "") {
    const f = normalizeAscii(filter);
    const filtered = f ? apps.filter((a) => normalizeAscii(a.name).includes(f)) : apps;
    if (!filtered.length) {
      els.appsList.innerHTML = '<div class="empty-hint">Eşleşen uygulama bulunamadı.</div>';
      return;
    }
    els.appsList.innerHTML = "";
    filtered.slice(0, 80).forEach((app) => {
      const row = document.createElement("div");
      row.className = "app-row";
      row.innerHTML = `<span>${app.name}</span><span class="app-kind">${app.kind}</span>`;
      row.onclick = () => sendCommand(`${app.name} aç`);
      els.appsList.appendChild(row);
    });
  }

  function renderProcesses(procs) {
    els.procsList.innerHTML = "";
    (procs || []).forEach((p) => {
      const row = document.createElement("div");
      row.className = "app-row";
      row.innerHTML = `<span>${p.name}</span><span class="app-kind">RAM ${p.ram}%</span>`;
      row.title = `PID ${p.pid} · Kapatmak için tıklayın`;
      row.onclick = () => {
        if (confirm(`'${p.name}' sürecini kapatmak istiyor musunuz?`)) {
          sendCommand(`${p.name} kapat`);
        }
      };
      els.procsList.appendChild(row);
    });
  }

  function renderCustomTags(container, mapObj, kind) {
    container.innerHTML = "";
    Object.entries(mapObj || {}).forEach(([k, v]) => {
      const tag = document.createElement("span");
      tag.className = "custom-tag";
      tag.innerHTML = `<strong>${k}</strong> → ${v}`;
      const del = document.createElement("button");
      del.textContent = "✕";
      del.onclick = async () => {
        const res = await fetch(`${apiBase()}/api/custom/${kind}/${encodeURIComponent(k)}`, { method: "DELETE" });
        state.config = await res.json();
        syncSettingsUI();
      };
      tag.appendChild(del);
      container.appendChild(tag);
    });
  }

  function syncSettingsUI() {
    const c = state.config;
    if (!c) return;
    els.toggleAuthority.checked = !!c.full_authority;
    els.toggleWakeWord.checked = !!c.wake_word_enabled;
    els.toggleTTS.checked = !!c.tts_enabled;
    els.langSelect.value = c.speech_lang || "tr-TR";
    els.voiceTrSelect.value = c.tts_voice_tr || "tr-TR-AhmetNeural";
    els.voiceEnSelect.value = c.tts_voice_en || "en-GB-RyanNeural";
    els.ollamaUrlInput.value = c.ollama_url || "http://localhost:11434";
    els.ollamaModelInput.value = c.ollama_model || "llama3.2";
    if (els.localBridgeInput) {
      els.localBridgeInput.value = state.localBridgeUrl || "";
    }
    els.confirmPowerToggle.checked = !!c.confirm_power_actions;
    renderCustomTags(els.customAppsList, c.custom_apps, "app");
    renderCustomTags(els.customSitesList, c.custom_sites, "site");
    renderCustomTags(els.customCmdsList, c.custom_commands, "command");
  }

  async function patchConfig(patch) {
    const res = await fetch(`${apiBase()}/api/config`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    state.config = await res.json();
    syncSettingsUI();
  }

  async function refreshNotes() {
    const res = await fetch(`${apiBase()}/api/notes`);
    const data = await res.json();
    renderNotes(data.notes || []);
  }

  async function refreshApps(force = false) {
    const res = await fetch(`${apiBase()}/api/apps?refresh=${force ? "true" : "false"}`);
    const data = await res.json();
    state.apps = data.apps || [];
    renderApps(state.apps, els.appSearch.value);
  }

  async function bootstrap() {
    drawVisualizer();

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }

    try {
      const hRes = await fetch(`${apiBase()}/api/health`);
      const health = await hRes.json();
      state.mode = health.mode || "local";
      state.supportsWs = health.websocket !== false;
    } catch (_) {
      state.supportsWs = true;
    }

    connectWS();

    try {
      const res = await fetch(`${apiBase()}/api/state`);
      const data = await res.json();
      state.config = data.config;
      syncSettingsUI();
      renderTelemetry(data.telemetry);
      renderTimers(data.timers || []);
      renderNotes(data.notes || []);
      renderProcesses(data.processes || []);

      if (Array.isArray(data.history) && data.history.length) {
        [...data.history].reverse().slice(-8).forEach((h) => {
          appendMessage("user", h.command);
          appendMessage("bot", h.response, h.intent);
        });
      } else {
        appendMessage(
          "bot",
          "Prometheus çevrimiçi efendim. Tüm sistemler hazır ve tam yetkiyle emrinizdeyim. Mikrofona dokunun veya bir komut yazın.",
          "system_ready"
        );
      }
    } catch (_) {}

    refreshApps(false);
  }

  // --- Event Listeners ---
  els.coreButton.addEventListener("click", toggleMic);
  els.btnMicInline.addEventListener("click", toggleMic);

  els.commandForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const val = els.commandInput.value.trim();
    if (!val) return;
    els.commandInput.value = "";
    sendCommand(val);
  });

  document.querySelectorAll(".q-btn").forEach((btn) => {
    btn.addEventListener("click", () => sendCommand(btn.dataset.cmd));
  });

  els.btnClearLog.addEventListener("click", () => {
    els.chatLog.innerHTML = "";
  });

  els.btnQuickNote.addEventListener("click", () => {
    const v = els.quickNoteInput.value.trim();
    if (!v) return;
    els.quickNoteInput.value = "";
    sendCommand(`not al: ${v}`);
  });

  els.quickNoteInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      els.btnQuickNote.click();
    }
  });

  els.appSearch.addEventListener("input", () => {
    renderApps(state.apps, els.appSearch.value);
  });

  els.btnRefreshApps.addEventListener("click", () => refreshApps(true));

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const tab = btn.dataset.tab;
      els.appsList.classList.toggle("hidden", tab !== "apps");
      els.procsList.classList.toggle("hidden", tab !== "procs");
    });
  });

  els.toggleAuthority.addEventListener("change", () =>
    patchConfig({ full_authority: els.toggleAuthority.checked })
  );
  els.toggleWakeWord.addEventListener("change", () => {
    patchConfig({ wake_word_enabled: els.toggleWakeWord.checked });
    updateReactorUI();
  });
  els.toggleTTS.addEventListener("change", () =>
    patchConfig({ tts_enabled: els.toggleTTS.checked })
  );
  els.langSelect.addEventListener("change", () => {
    const sl = els.langSelect.value;
    patchConfig({
      speech_lang: sl,
      language: sl.startsWith("en") ? "en" : "tr",
    });
    if (state.micActive) {
      startRecognitionInstance();
    }
  });

  // Spacebar shortcut (when not typing in an input)
  document.addEventListener("keydown", (e) => {
    if (e.code === "Space" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) {
      e.preventDefault();
      toggleMic();
    }
  });

  // Settings Modal
  els.btnSettings.addEventListener("click", () => els.settingsModal.classList.remove("hidden"));
  els.btnCloseModal.addEventListener("click", () => els.settingsModal.classList.add("hidden"));
  els.settingsModal.querySelector(".modal-backdrop").addEventListener("click", () =>
    els.settingsModal.classList.add("hidden")
  );

  // PWA Desktop Install Prompt
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    state.deferredInstallPrompt = e;
    if (els.btnInstallDesktop) {
      els.btnInstallDesktop.classList.remove("hidden");
    }
  });

  if (els.btnInstallDesktop) {
    els.btnInstallDesktop.addEventListener("click", async () => {
      if (state.deferredInstallPrompt) {
        state.deferredInstallPrompt.prompt();
        await state.deferredInstallPrompt.userChoice;
        state.deferredInstallPrompt = null;
        els.btnInstallDesktop.classList.add("hidden");
      }
    });
  }

  els.btnSaveSettings.addEventListener("click", async () => {
    if (els.localBridgeInput) {
      const bridgeVal = els.localBridgeInput.value.trim();
      state.localBridgeUrl = bridgeVal;
      if (bridgeVal) {
        localStorage.setItem("prometheus_local_bridge", bridgeVal);
      } else {
        localStorage.removeItem("prometheus_local_bridge");
      }
    }
    await patchConfig({
      tts_voice_tr: els.voiceTrSelect.value,
      tts_voice_en: els.voiceEnSelect.value,
      ollama_url: els.ollamaUrlInput.value.trim(),
      ollama_model: els.ollamaModelInput.value.trim(),
      confirm_power_actions: els.confirmPowerToggle.checked,
    });
    els.settingsModal.classList.add("hidden");
  });

  async function addCustom(kind, nameEl, targetEl) {
    const name = nameEl.value.trim();
    const target = targetEl.value.trim();
    if (!name || !target) return;
    const res = await fetch(`${apiBase()}/api/custom/${kind}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, target }),
    });
    state.config = await res.json();
    nameEl.value = "";
    targetEl.value = "";
    syncSettingsUI();
    if (kind === "app") refreshApps(false);
  }

  els.btnAddCustomApp.addEventListener("click", () =>
    addCustom("app", els.customAppName, els.customAppPath)
  );
  els.btnAddCustomSite.addEventListener("click", () =>
    addCustom("site", els.customSiteName, els.customSiteUrl)
  );
  els.btnAddCustomCmd.addEventListener("click", () =>
    addCustom("command", els.customCmdTrigger, els.customCmdAction)
  );

  bootstrap();
})();
