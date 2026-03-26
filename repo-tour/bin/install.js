#!/usr/bin/env node
'use strict';

const fs   = require('fs');
const path = require('path');
const os   = require('os');

// ─── Config ────────────────────────────────────────────────────────────────
const SKILL_NAME  = 'tldr';
const PKG_ROOT    = path.join(__dirname, '..');
const SKILLS_DIR  = path.join(os.homedir(), '.claude', 'skills');
const DEST        = path.join(SKILLS_DIR, SKILL_NAME);
const SKILL_ITEMS = ['SKILL.md', 'agents', 'references', 'scripts', 'templates', 'LICENSE.txt'];

// ─── Args ──────────────────────────────────────────────────────────────────
const args      = process.argv.slice(2);
const UNINSTALL = args.includes('--uninstall') || args.includes('-u');
const HELP      = args.includes('--help') || args.includes('-h');

// ─── Colours (no deps) ─────────────────────────────────────────────────────
const isTTY = process.stdout.isTTY;
const c = {
  reset:  isTTY ? '\x1b[0m'  : '',
  bold:   isTTY ? '\x1b[1m'  : '',
  dim:    isTTY ? '\x1b[2m'  : '',
  cyan:   isTTY ? '\x1b[36m' : '',
  green:  isTTY ? '\x1b[32m' : '',
  yellow: isTTY ? '\x1b[33m' : '',
  red:    isTTY ? '\x1b[31m' : '',
};
const fmt = (col, str) => `${col}${str}${c.reset}`;

// ─── Helpers ───────────────────────────────────────────────────────────────
function copyRecursive(src, dest) {
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    fs.mkdirSync(dest, { recursive: true });
    for (const item of fs.readdirSync(src)) {
      copyRecursive(path.join(src, item), path.join(dest, item));
    }
  } else {
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(src, dest);
  }
}

function countFiles(dir) {
  let n = 0;
  if (!fs.existsSync(dir)) return n;
  for (const item of fs.readdirSync(dir)) {
    const p = path.join(dir, item);
    if (fs.statSync(p).isDirectory()) n += countFiles(p);
    else n++;
  }
  return n;
}

function rmRecursive(dir) {
  if (!fs.existsSync(dir)) return;
  // Node 14 safe removal
  if (fs.rmSync) {
    fs.rmSync(dir, { recursive: true, force: true });
  } else {
    const entries = fs.readdirSync(dir);
    for (const entry of entries) {
      const p = path.join(dir, entry);
      if (fs.lstatSync(p).isDirectory()) rmRecursive(p);
      else fs.unlinkSync(p);
    }
    fs.rmdirSync(dir);
  }
}

// ─── Help ──────────────────────────────────────────────────────────────────
if (HELP) {
  console.log(`
${fmt(c.bold + c.cyan, 'TLDR Skill — Claude Code Installer')}

${fmt(c.bold, 'Usage:')}
  npx tldr-skill              Install the skill
  npx tldr-skill --uninstall  Remove the skill
  npx tldr-skill --help       Show this help

${fmt(c.bold, 'What it does:')}
  Copies the TLDR skill into ~/.claude/skills/tldr/
  so Claude Code discovers it automatically.

${fmt(c.bold, 'After install, in Claude Code type:')}
  ${fmt(c.cyan, '/tldr')}
  or just say: ${fmt(c.dim, '"explain this repo"')}
`);
  process.exit(0);
}

// ─── Uninstall ─────────────────────────────────────────────────────────────
if (UNINSTALL) {
  console.log(`\n${fmt(c.yellow, '⚠')}  Uninstalling TLDR skill...`);
  if (!fs.existsSync(DEST)) {
    console.log(`${fmt(c.dim, '   Not installed — nothing to remove.')}\n`);
    process.exit(0);
  }
  try {
    rmRecursive(DEST);
    console.log(`${fmt(c.green, '✓')}  Removed ${fmt(c.dim, DEST)}\n`);
  } catch (err) {
    console.error(`${fmt(c.red, '✗')}  Failed to remove: ${err.message}\n`);
    process.exit(1);
  }
  process.exit(0);
}

// ─── Install ───────────────────────────────────────────────────────────────
const isUpdate = fs.existsSync(DEST);

console.log(`
${fmt(c.bold + c.cyan, 'TLDR')} ${fmt(c.dim, '— Too Long, Didn\'t Read')}
${fmt(c.dim, 'Claude Code Skill Installer')}
`);

console.log(`${fmt(c.dim, isUpdate ? '↻  Updating' : '→  Installing')} to ${fmt(c.dim, DEST)}\n`);

// Ensure ~/.claude/skills/ exists
try {
  fs.mkdirSync(SKILLS_DIR, { recursive: true });
} catch (err) {
  console.error(`${fmt(c.red, '✗')}  Could not create skills directory: ${err.message}`);
  process.exit(1);
}

// Copy each skill component
let copied = 0;
const errors = [];

for (const item of SKILL_ITEMS) {
  const src  = path.join(PKG_ROOT, item);
  const dest = path.join(DEST, item);
  if (!fs.existsSync(src)) continue;
  try {
    copyRecursive(src, dest);
    copied++;
    console.log(`  ${fmt(c.green, '✓')} ${item}`);
  } catch (err) {
    errors.push(item);
    console.log(`  ${fmt(c.red, '✗')} ${item} — ${err.message}`);
  }
}

if (errors.length) {
  console.log(`\n${fmt(c.red, '✗')}  Install failed for: ${errors.join(', ')}`);
  process.exit(1);
}

const total = countFiles(DEST);

console.log(`
${fmt(c.green + c.bold, '✓  Done!')} ${fmt(c.dim, `${total} files installed`)}

${fmt(c.bold, 'Open Claude Code and type:')}

  ${fmt(c.cyan + c.bold, '/tldr')}

${fmt(c.dim, 'Or just say "explain this repo" — Claude will use it automatically.')}
${fmt(c.dim, `Skill location: ${DEST}`)}
`);
