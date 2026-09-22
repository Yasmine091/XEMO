const DUPLICATE_WINDOW_MS = 9000;

function cleanText(value) {
    return String(value ?? "").replace(/\s+/g, " ").trim();
}

export function createSpeechController({ audio, getSettings, getVoice, getSpanish, getLanguage = () => getSpanish() ? "es-ES" : "en-US", claimLease = () => true, releaseLease = () => {}, log = () => {}, onStart = () => {}, onEnd = () => {} }) {
    let run = 0;
    let active = null;
    let lastText = "";
    let lastAt = 0;

    const stop = () => {
        const hadActive = active !== null;
        run += 1;
        if (hadActive) releaseLease();
        active?.abort();
        active = null;
        try {
            audio.pause();
            audio.currentTime = 0;
            audio.removeAttribute("src");
            audio.load();
        } catch (_) {}
        try {
            window.speechSynthesis?.cancel();
        } catch (_) {}
        if (hadActive) onEnd();
    };

    const speakBrowser = (text, settings, token) => new Promise(resolve => {
        const synthesis = window.speechSynthesis;
        if (!synthesis) return resolve();
        let done = false;
        let timer = 0;
        let startTimer = 0;
        const finish = () => {
            if (done) return;
            done = true;
            clearTimeout(timer);
            clearTimeout(startTimer);
            resolve();
        };
        try {
            synthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = getLanguage(text);
            utterance.pitch = settings.pitch;
            utterance.rate = settings.speed;
            utterance.onstart = () => clearTimeout(startTimer);
            utterance.onend = finish;
            utterance.onerror = finish;
            timer = setTimeout(() => {
                synthesis.cancel();
                finish();
            }, 20000);
            startTimer = setTimeout(() => {
                synthesis.cancel();
                finish();
            }, 3500);
            synthesis.speak(utterance);
        } catch (_) {
            finish();
        }
    });

    const speak = async value => {
        const text = cleanText(value);
        if (!text || /^(?:undefined|null|nan)$/i.test(text)) return;
        if (/\b(?:autonomy priority|relay\s*=|automove\s*=|active_intention)\b/i.test(text)) {
            log("voice", "ignored leaked internal speech");
            return;
        }
        if (/I(?:’|')m here|I heard you, and I(?:’|')m here with you|I heard you, but my thought got stuck/i.test(text)) {
            log("voice", "suppressed stale fallback instead of speaking over the real answer");
            return;
        }
        if (/^Under the full moon, I am keeping this in my memory:\s*nothing new was solid enough to keep this time\.?$/i.test(text)) {
            log("dream", "skipped no-op memory announcement");
            return;
        }
        const now = Date.now();
        const key = text.toLowerCase();
        const settings = getSettings();
        const explicitRepeat = /\b(?:repeat|again|say that again|one more time|otra vez|repite)\b/i.test(text);
        if (!explicitRepeat && key === lastText && now - lastAt < DUPLICATE_WINDOW_MS) {
            log("voice", "duplicate speech suppressed by the single output owner");
            return;
        }
        stop();
        if (!claimLease(text)) {
            log("voice", "another XEMO tab owns audio; suppressed duplicate playback");
            return;
        }
        lastText = key;
        lastAt = now;
        const token = run;
        const controller = new AbortController();
        active = controller;
        onStart(text);
        try {
            if (settings.engine === "kokoro") {
                const response = await fetch("/api/tts", {
                    method: "POST",
                    headers: { "content-type": "application/json" },
                    body: JSON.stringify({ model: "kokoro", voice: getVoice(), input: text, response_format: "wav", speed: settings.speed / settings.pitch }),
                    signal: controller.signal
                });
                if (!response.ok) throw Error(`Kokoro HTTP ${response.status}`);
                const url = URL.createObjectURL(await response.blob());
                if (token !== run) {
                    URL.revokeObjectURL(url);
                    return;
                }
                audio.src = url;
                audio.playbackRate = settings.pitch;
                audio.preservesPitch = false;
                await new Promise((resolve, reject) => {
                    const timer = setTimeout(() => reject(Error("Kokoro playback timed out")), 20000);
                    audio.onended = () => { clearTimeout(timer); resolve(); };
                    audio.onerror = () => { clearTimeout(timer); reject(Error("Kokoro playback failed")); };
                    audio.play().catch(reject);
                });
                URL.revokeObjectURL(url);
                return;
            }
            await speakBrowser(text, settings, token);
        } catch (error) {
            if (controller.signal.aborted || token !== run) return;
            log("voice", String(error?.message || error));
        } finally {
            if (active === controller) active = null;
            audio.onended = null;
            audio.onerror = null;
            if (token === run) {
                try {
                    audio.pause();
                    audio.removeAttribute("src");
                    audio.load();
                } catch (_) {}
            }
            if (token === run) onEnd();
            if (token === run) releaseLease();
        }
    };

    return { speak, stop, isSpeaking: () => active !== null };
}
