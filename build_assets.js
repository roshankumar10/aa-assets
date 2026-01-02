#!/usr/bin/env node

const { execFileSync } = require('child_process');
const path = require('path');

const baseDir = __dirname;
const python = process.env.PYTHON || 'python3';
const node = process.env.NODE || 'node';

function run(command, args) {
  execFileSync(command, args, { stdio: 'inherit', cwd: baseDir });
}

run(python, [path.join(baseDir, 'optimize_images.py')]);
run(node, [path.join(baseDir, 'display.js')]);
