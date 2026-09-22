export function createHearingController({ transcribe, getAbortController, log = () => {} }) {
    let active = null;
    let sequence = 0;

    const stop = () => {
        sequence += 1;
        try {
            getAbortController()?.abort();
        } catch (_) {}
        active = null;
    };

    const hear = blob => {
        if (!blob) return Promise.resolve();
        if (active) {
            log("listen", "duplicate recording ignored while transcription is active");
            return active;
        }
        const token = sequence;
        const flight = Promise.resolve().then(() => transcribe(blob)).finally(() => {
            if (active === flight && token === sequence) active = null;
        });
        active = flight;
        return flight;
    };

    return { transcribe: hear, stop, isTranscribing: () => active !== null };
}
