// Bundles three.js + game renderer + robot model into ONE offline HTML file for the Android WebView.
import { build } from 'esbuild';
import { writeFileSync, mkdirSync } from 'node:fs';

const out = await build({
  entryPoints: ['src/main.js'], bundle: true, minify: true, write: false, format: 'iife',
  target: ['chrome90'], loader: { '.glb': 'base64' }, legalComments: 'none',
});
const js = out.outputFiles[0].text.replace(/<\/script/gi, '<\\/script');
const html = `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<style>html,body{margin:0;height:100%;overflow:hidden;background:#0b1118;touch-action:none;-webkit-user-select:none;user-select:none}
canvas{display:block;width:100%;height:100%}#msg{position:fixed;left:8px;bottom:8px;color:#9fb3c8;font:12px sans-serif;pointer-events:none}</style>
</head><body><div id="msg"></div><script>${js}</script></body></html>`;
mkdirSync('../assets/renderer', { recursive: true });
writeFileSync('../assets/renderer/index.html', html);
console.log('renderer bundle', (html.length / 1024).toFixed(0) + ' KiB');
