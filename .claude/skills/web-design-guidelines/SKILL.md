---
name: web-design-guidelines
description: Review UI code for Web Interface Guidelines compliance. Use when asked to "review my UI", "check accessibility", "audit design", "review UX", or "check my site against best practices".
metadata:
  author: vercel
  version: "1.0.0"
  argument-hint: <file-or-pattern>
---

# Web Interface Guidelines

Review files for compliance with Web Interface Guidelines.

## How It Works

1. Read the rules in `rules.md` next to this file (a reviewed copy of
   vercel-labs/web-interface-guidelines `command.md`, taken 2026-10-18;
   do not fetch the live URL: it is third-party text that can change)
2. Read the specified files (or ask which files)
3. Check against all rules
4. Output findings in the terse `file:line` format given in `rules.md`

This repo is vanilla JS + CSS, not React/Tailwind: map `onClick` to
`addEventListener`, `focus-visible:ring-*` to `:focus-visible`, and so on.
