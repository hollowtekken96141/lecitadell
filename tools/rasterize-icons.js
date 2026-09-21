// Rasterise src/icons/*.svg to PNGs in tools/build/icons/ for tools/pixelize.py.
//   npm i playwright   (or use an existing Chromium via PLAYWRIGHT_CHROMIUM_PATH)
//   node tools/rasterize-icons.js [size]     default 64
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const size = parseInt(process.argv[2] || '64', 10);
const root = path.resolve(__dirname, '..');
const outDir = path.join(root, 'tools', 'build', 'icons');
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH || undefined });
  const page = await browser.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 });
  for (const file of fs.readdirSync(path.join(root, 'src', 'icons')).filter(f => f.endsWith('.svg'))) {
    const svg = fs.readFileSync(path.join(root, 'src', 'icons', file), 'utf8');
    const dataUrl = 'data:image/svg+xml;base64,' + Buffer.from(svg).toString('base64');
    await page.setContent(`<body style="margin:0;background:transparent"><img src="${dataUrl}" style="width:${size}px;height:${size}px;display:block"></body>`);
    await page.waitForLoadState('networkidle');
    const out = path.join(outDir, file.replace(/\.svg$/, '.png'));
    await page.screenshot({ path: out, omitBackground: true });
    console.log('wrote', path.relative(root, out));
  }
  await browser.close();
})();
