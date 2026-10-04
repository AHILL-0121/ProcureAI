// Fails the build if any colour with a hue between 250° and 330° (violet/purple/magenta) or a banned
// "AI template" pattern appears in the frontend. See plan/Design.md §1 and §11.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { extname, join } from 'node:path';

const ROOTS = ['src', 'public'];
const EXT = new Set(['.css', '.ts', '.tsx', '.svg']);
const BANNED = [
  [/backdrop-filter/i, 'glassmorphism (backdrop-filter)'],
  [/background-clip:\s*text/i, 'gradient text'],
  [/-webkit-text-fill-color:\s*transparent/i, 'gradient text'],
  [/[✨🤖]/u, 'sparkle / robot emoji'],
];

function files(dir) {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? files(p) : EXT.has(extname(p)) ? [p] : [];
  });
}

function hsl(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
  const l = (max + min) / 2;
  if (!d) return { h: 0, s: 0, l };
  const s = d / (1 - Math.abs(2 * l - 1));
  let h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  h = (h * 60 + 360) % 360;
  return { h, s, l };
}

const problems = [];
for (const root of ROOTS) {
  for (const f of files(root)) {
    const text = readFileSync(f, 'utf8');
    for (const m of text.matchAll(/#([0-9a-f]{6}|[0-9a-f]{3})\b/gi)) {
      let hex = m[1];
      if (hex.length === 3) hex = hex.split('').map((c) => c + c).join('');
      const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
      const { h, s } = hsl(r, g, b);
      if (s > 0.12 && h >= 250 && h <= 330) problems.push(`${f}: #${m[1]} (hue ${h.toFixed(0)}°) is in the banned violet range`);
    }
    for (const m of text.matchAll(/rgba?\((\d+),\s*(\d+),\s*(\d+)/g)) {
      const { h, s } = hsl(+m[1], +m[2], +m[3]);
      if (s > 0.12 && h >= 250 && h <= 330) problems.push(`${f}: ${m[0]} is in the banned violet range`);
    }
    for (const [re, name] of BANNED) if (re.test(text)) problems.push(`${f}: banned pattern — ${name}`);
  }
}

if (problems.length) {
  console.error(problems.join('\n'));
  process.exit(1);
}
console.log('Colour check passed: no violet, no banned patterns.');
