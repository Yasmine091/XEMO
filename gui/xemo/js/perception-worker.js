const CDN = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.1";

const INTERESTING = new Set([ "person", "chair", "couch", "bed", "dining table", "tv", "potted plant", "bottle", "cup", "book", "cell phone", "dog", "cat", "backpack" ]);

let detector = null;

async function getDetector() {
    if (detector) return detector;
    const {pipeline: pipeline, env: env} = await import(CDN);
    env.allowLocalModels = false;
    if (env.backends?.onnx?.wasm) env.backends.onnx.wasm.numThreads = 1;
    detector = await pipeline("object-detection", "Xenova/yolos-tiny", {
        dtype: "q8"
    });
    return detector;
}

self.onmessage = async event => {
    try {
        const {image: image, urgent: urgent, width: width, height: height, generation: generation, requestId: requestId} = event.data || {}, threshold = urgent ? .28 : .4, model = await getDetector();
        const found = await model(image, {
            threshold: threshold,
            percentage: false
        });
        const objects = found.filter((x => INTERESTING.has(x.label) && x.score >= threshold)).slice(0, 8).map((x => ({
            label: x.label,
            score: +x.score.toFixed(2),
            box: {
                xmin: Math.round(x.box.xmin),
                ymin: Math.round(x.box.ymin),
                xmax: Math.round(x.box.xmax),
                ymax: Math.round(x.box.ymax)
            },
            frame: {
                w: width || 1,
                h: height || 1
            }
        })));
        self.postMessage({
            objects: objects,
            generation: generation,
            requestId: requestId
        });
    } catch (error) {
        self.postMessage({
            error: String(error?.message || error),
            generation: event.data?.generation,
            requestId: event.data?.requestId
        });
    }
};