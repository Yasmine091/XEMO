export function createPerception({onStatus: onStatus = (() => {}), onObjects: onObjects = (() => {}), isUrgent: isUrgent = (() => false), canRun: canRun = (() => true)} = {}) {
    let worker = null, running = false, busy = false, timer = null, videoRef = null, canvas = null, releaseTimer = null, generation = 0, requestSeq = 0, activeRequest = 0, workerFailures = 0;
    const status = (text, state = "") => onStatus({
        text: text,
        state: state
    });
    function ensureWorker() {
        if (worker) return worker;
        worker = new Worker(new URL("./perception-worker.js?v=4", import.meta.url), {
            type: "module"
        });
        worker.onmessage = event => {
            const m = event.data || {};
            if (m.generation !== generation || m.requestId !== activeRequest || !running) return;
            busy = false;
            workerFailures = 0;
            if (m.error) {
                status("local object sense unavailable · Qwen vision still works", "error");
                onStatus({
                    text: m.error,
                    state: "trace"
                });
            } else {
                onObjects(m.objects || []);
                status(m.objects?.length ? m.objects.map((x => `${x.label} ${Math.round(x.score * 100)}%`)).join(" · ") : "no familiar objects", "ready");
            }
            if (running) schedule(isUrgent() ? 1400 : 3e4);
        };
        worker.onerror = event => {
            busy = false;
            workerFailures++;
            status("object worker failed · retrying in background", "error");
            onStatus({
                text: String(event.message || "worker error"),
                state: "trace"
            });
            try {
                worker?.terminate();
            } catch (_) {}
            worker = null;
            if (running) schedule(Math.min(3e4, Math.max(2e3, 1e3 * 2 ** Math.min(workerFailures, 5))));
        };
        status("loading object sense in background…", "loading");
        return worker;
    }
    function tick(video) {
        if (!running || busy || document.hidden || !canRun() || !video?.videoWidth) return schedule(1e3);
        busy = true;
        const requestId = ++requestSeq, requestGeneration = generation;
        try {
            canvas = canvas || document.createElement("canvas");
            const max = isUrgent() ? 176 : 144, scale = Math.min(1, max / Math.max(video.videoWidth, video.videoHeight));
            canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
            canvas.height = Math.max(1, Math.round(video.videoHeight * scale));
            canvas.getContext("2d", {
                alpha: false
            }).drawImage(video, 0, 0, canvas.width, canvas.height);
            activeRequest = requestId;
            ensureWorker().postMessage({
                image: canvas.toDataURL("image/jpeg", .55),
                urgent: isUrgent(),
                width: canvas.width,
                height: canvas.height,
                generation: requestGeneration,
                requestId: requestId
            });
        } catch (error) {
            busy = false;
            status(String(error?.message || error), "trace");
            schedule(4e3);
        }
    }
    function schedule(delay) {
        clearTimeout(timer);
        timer = setTimeout((() => tick(videoRef)), delay);
    }
    function start(video) {
        clearTimeout(releaseTimer);
        generation++;
        activeRequest = 0;
        running = true;
        videoRef = video;
        schedule(isUrgent() ? 500 : 3e4);
    }
    function pulse() {
        if (running && !busy) schedule(0);
    }
    function stop() {
        generation++;
        activeRequest = 0;
        running = false;
        videoRef = null;
        busy = false;
        workerFailures = 0;
        clearTimeout(timer);
        timer = null;
        onObjects([]);
        status("local object sense waits for camera", "idle");
        clearTimeout(releaseTimer);
        releaseTimer = setTimeout((() => {
            if (!running && worker) {
                worker.terminate();
                worker = null;
                canvas = null;
                status("local object sense sleeping", "idle");
            }
        }), 3e4);
    }
    return {
        start: start,
        stop: stop,
        pulse: pulse
    };
}
