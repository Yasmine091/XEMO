import fs from "node:fs";
import path from "node:path";

const root = new URL(".", import.meta.url).pathname;
const indexPath = path.join(root, "index.html");
const partsDir = path.join(root, "xemo", "html");
const source = fs.readFileSync(indexPath, "utf8");
const styleMatch = source.match(/<style>\s*([\s\S]*?)\s*<\/style>/);
const sourceWithoutStyle = styleMatch ? source.replace(styleMatch[0], "") : source;
const cssPath = path.join(root, "xemo", "css", "app.css");
if (styleMatch) {
    const css = fs.readFileSync(cssPath, "utf8");
    if (!css.includes("#birthChoice{")) {
        fs.appendFileSync(cssPath, `\n\n${styleMatch[1].trim()}\n`);
    }
}

function between(text, start, end) {
    const a = text.indexOf(start);
    const b = text.indexOf(end, a + start.length);
    if (a < 0 || b < 0) throw new Error(`GUI boundary missing: ${start} → ${end}`);
    return text.slice(a + start.length, b).trim();
}

function writePart(name, content) {
    fs.mkdirSync(partsDir, { recursive: true });
    fs.writeFileSync(path.join(partsDir, name), content.trim() + "\n");
}

const bodyClass = sourceWithoutStyle.match(/<body[^>]*>/)?.[0] || '<body class="face-home">';
const head = sourceWithoutStyle.includes("<head>") ?
    between(sourceWithoutStyle, "<head>", "</head>") :
    between(sourceWithoutStyle, '<html lang="en">', bodyClass);
const spriteMarkup = sourceWithoutStyle.match(/<svg class="icon-sprite"[\s\S]*?<\/svg>/)?.[0];
const mainMarkup = sourceWithoutStyle.match(/<main class="app">[\s\S]*?<\/main>/)?.[0];
const birthStart = sourceWithoutStyle.indexOf('<div id="birthChoice"');
const navStart = sourceWithoutStyle.indexOf('<nav class="nav"');
const scriptStart = sourceWithoutStyle.indexOf('<script type="module"', navStart);
const birthMarkup = birthStart >= 0 && navStart > birthStart ? sourceWithoutStyle.slice(birthStart, navStart).trim() : "";
const navMarkup = navStart >= 0 && scriptStart > navStart ? sourceWithoutStyle.slice(navStart, scriptStart).trim() : "";
if (!spriteMarkup || !mainMarkup || !birthMarkup || !navMarkup) {
    throw new Error("GUI markup boundary missing while assembling partials");
}

writePart("head.html", head);
writePart("icons.html", spriteMarkup);
writePart("views.html", mainMarkup);
writePart("overlays.html", birthMarkup);
writePart("navigation.html", navMarkup);

const assembled = `<!doctype html>
<html lang="en">
<head>
${fs.readFileSync(path.join(partsDir, "head.html"), "utf8")}
</head>
${bodyClass}
${fs.readFileSync(path.join(partsDir, "icons.html"), "utf8")}
${fs.readFileSync(path.join(partsDir, "views.html"), "utf8")}
${fs.readFileSync(path.join(partsDir, "overlays.html"), "utf8")}
${fs.readFileSync(path.join(partsDir, "navigation.html"), "utf8")}
<script type="module" src="/xemo/js/app-runtime-947.js?v=1116"></script>
</body>
</html>
`;

fs.writeFileSync(indexPath, assembled);
console.log("GUI assembled from xemo/html partials");
