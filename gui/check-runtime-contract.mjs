import fs from "node:fs";

const read = path => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const entry = read("./index.html");
const sw = read("./xemo/sw.js");
const bridge = read("../bot/bridge.py");
const runtimeMatch = entry.match(/\/xemo\/js\/(app-runtime-[^?]+)\?v=(\d+)/);
const app = runtimeMatch ? read(`./xemo/js/${runtimeMatch[1]}`) : "";
const failures = [];

if (!runtimeMatch) failures.push("the GUI does not declare its runtime bundle");
if (!/allow_reuse_address\s*=\s*True/.test(bridge)) failures.push("the bridge cannot reliably rebind after restart");
if (!/const CACHE = "xemo-static-v(\d+)"/.test(sw)) failures.push("the service-worker cache version is missing");
if (!/serviceWorker\.register\("\/xemo\/sw\.js\?v=(\d+)"\)/.test(app)) failures.push("the runtime does not register the service worker");
if (!/const useStreamingBrain\s*=\s*false/.test(app)) failures.push("the stable non-streaming brain path is not selected");
if (!/bm_fable/.test(app)) failures.push("the default Kokoro voice is not B-Fable");
if (!/preservesPitch\s*=\s*false/.test(app)) failures.push("voice pitch is not controlled by the audio path");
if (!/let xemoVoiceFlight\s*=/.test(app) || !/let xemoChatFlight\s*=/.test(app)) failures.push("single-flight guards are missing");
if (/gb-[0-9a-f]+/i.test(entry + app + bridge)) failures.push("a pairing code is embedded in the public files");
if (/\/home\/|Public\/Documents|192\.168\./i.test(entry + app + bridge)) failures.push("a local machine path or LAN address is embedded in the public files");

if (failures.length) {
  console.error(failures.map(value => `- ${value}`).join("\n"));
  process.exit(1);
}

console.log("XEMO runtime contract passed");
