#!/usr/bin/env python3
"""token_report.py — Reads the token ledger written during a tldr run and
prints a formatted per-phase cost breakdown to stdout.

Usage:
    python token_report.py --ledger <REPO>/.repotour/token-ledger.json

The ledger is written incrementally by Claude during the pipeline run.
All LLM costs are estimates — scripts (Phase 1, 3) use zero tokens and
that is exact, not estimated.
"""

import json
import sys
import argparse
from pathlib import Path

# ── Pricing (USD per 1M tokens, March 2026) ──────────────────────────────────
PRICING = {
    'haiku':  {'input': 0.80,  'output': 4.00},
    'sonnet': {'input': 3.00,  'output': 15.00},
    'opus':   {'input': 15.00, 'output': 75.00},
    'none':   {'input': 0.00,  'output': 0.00},
}

# ANSI colours (disabled if not a TTY)
IS_TTY = sys.stdout.isatty()
R = '\x1b[0m'   if IS_TTY else ''
B = '\x1b[1m'   if IS_TTY else ''
D = '\x1b[2m'   if IS_TTY else ''
C = '\x1b[36m'  if IS_TTY else ''
G = '\x1b[32m'  if IS_TTY else ''
Y = '\x1b[33m'  if IS_TTY else ''
M = '\x1b[35m'  if IS_TTY else ''


def cost_usd(tokens_in, tokens_out, model):
    p = PRICING.get(model.lower(), PRICING['sonnet'])
    return (tokens_in * p['input'] + tokens_out * p['output']) / 1_000_000


def fmt_tokens(n):
    if n == 0:
        return f'{D}0{R}'
    return f'{n:,}'


def fmt_cost(usd):
    if usd == 0:
        return f'{D}$0.000{R}'
    if usd < 0.001:
        return f'${usd:.5f}'
    return f'${usd:.4f}'


def load_ledger(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f'  Error: ledger not found at {path}', file=sys.stderr)
        print('  Was the skill run with token tracking enabled?', file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f'  Error: ledger is not valid JSON: {e}', file=sys.stderr)
        sys.exit(1)


def render_report(ledger):
    col_w = [36, 10, 10, 10, 10, 12]  # Phase | Model | In | Out | Total tok | Cost
    sep = '─'

    def row(phase, model, tok_in, tok_out, note=''):
        total = tok_in + tok_out
        usd = cost_usd(tok_in, tok_out, model)
        model_str = model.capitalize() if model != 'none' else f'{D}—{R}'
        note_str  = f'  {D}{note}{R}' if note else ''
        return (
            f'  {phase:<36} {model_str:<12} '
            f'{fmt_tokens(tok_in):>10}  {fmt_tokens(tok_out):>10}  '
            f'{fmt_tokens(total):>12}  {fmt_cost(usd):>12}'
            f'{note_str}'
        )

    header = (
        f'  {B}{"Phase":<36} {"Model":<12} '
        f'{"Input":>10}  {"Output":>10}  '
        f'{"Total tok":>12}  {"Est. cost":>12}{R}'
    )
    divider = '  ' + sep * (36 + 12 + 10 + 2 + 10 + 2 + 12 + 2 + 12)

    lines = []
    lines.append('')
    lines.append(f'{B}{C}  ╔══ tldr — Token Usage Report ══════════════════════════════╗{R}')
    lines.append(f'{B}{C}  ║  All LLM costs are estimates. Script phases are exact $0.  ║{R}')
    lines.append(f'{B}{C}  ╚════════════════════════════════════════════════════════════╝{R}')
    lines.append('')
    lines.append(header)
    lines.append(divider)

    totals = {'haiku_in': 0, 'haiku_out': 0, 'sonnet_in': 0, 'sonnet_out': 0,
              'opus_in': 0, 'opus_out': 0, 'total_cost': 0.0}

    def add_row(label, model, tin, tout, note=''):
        lines.append(row(label, model, tin, tout, note))
        m = model.lower()
        if m == 'haiku':
            totals['haiku_in']  += tin;  totals['haiku_out']  += tout
        elif m == 'sonnet':
            totals['sonnet_in'] += tin;  totals['sonnet_out'] += tout
        elif m == 'opus':
            totals['opus_in']   += tin;  totals['opus_out']   += tout
        totals['total_cost'] += cost_usd(tin, tout, model)

    # ── Phase 0 ──────────────────────────────────────────────────────────────
    p0 = ledger.get('phase_0', {})
    add_row('Phase 0 · Compatibility check',
            p0.get('model', 'haiku'),
            p0.get('input_tokens', 0),
            p0.get('output_tokens', 0))

    lines.append(divider)

    # ── Phase 1 ──────────────────────────────────────────────────────────────
    add_row('Phase 1 · Scan scripts (Python)', 'none', 0, 0,
            'exact $0 — no LLM')

    p1b = ledger.get('phase_1_bootstrapper', {})
    add_row('Phase 1 · Tier 0 bootstrapper',
            p1b.get('model', 'haiku'),
            p1b.get('input_tokens', 0),
            p1b.get('output_tokens', 0),
            'partition map')

    p1r = ledger.get('phase_1_file_reading', {})
    agents = p1r.get('agent_count', 0)
    add_row(f'Phase 1 · File reading ({agents} Haiku agents)',
            p1r.get('model', 'haiku'),
            p1r.get('input_tokens', 0),
            p1r.get('output_tokens', 0))

    p1t = ledger.get('phase_1_thinking', {})
    if p1t.get('agent_count', 0) > 0:
        t_agents = p1t.get('agent_count', 0)
        add_row(f'Phase 1 · Haiku+thinking ({t_agents} agents)',
                p1t.get('model', 'haiku'),
                p1t.get('input_tokens', 0),
                p1t.get('output_tokens', 0),
                'Tier 1.5 — ambiguous files')

    p1s = ledger.get('phase_1_synthesis', {})
    add_row('Phase 1 · Workflow synthesis (Sonnet)',
            p1s.get('model', 'sonnet'),
            p1s.get('input_tokens', 0),
            p1s.get('output_tokens', 0))

    add_row('Phase 1 · build_graph.py', 'none', 0, 0, 'exact $0 — no LLM')

    lines.append(divider)

    # ── Phase 2 ──────────────────────────────────────────────────────────────
    sections = ledger.get('phase_2_sections', {})
    section_order = [
        'overview', 'architecture', 'cross_cutting', 'tech_stack',
        'entry_points', 'modules', 'workflows', 'directory_guide',
        'glossary_getting_started', 'cookbook',
    ]
    for sec in section_order:
        data = sections.get(sec)
        if not data:
            continue
        label = f'Phase 2 · {sec.replace("_", " ").title()}'
        add_row(label,
                data.get('model', 'sonnet'),
                data.get('input_tokens', 0),
                data.get('output_tokens', 0))

    # Any extra sections not in the standard order
    for sec, data in sections.items():
        if sec not in section_order:
            label = f'Phase 2 · {sec.replace("_", " ").title()}'
            add_row(label,
                    data.get('model', 'sonnet'),
                    data.get('input_tokens', 0),
                    data.get('output_tokens', 0))

    lines.append(divider)

    # ── Phase 3 ──────────────────────────────────────────────────────────────
    add_row('Phase 3 · generate_site.py', 'none', 0, 0, 'exact $0 — no LLM')

    lines.append(divider)

    # ── Totals ────────────────────────────────────────────────────────────────
    haiku_total  = totals['haiku_in']  + totals['haiku_out']
    sonnet_total = totals['sonnet_in'] + totals['sonnet_out']
    opus_total   = totals['opus_in']   + totals['opus_out']
    all_tokens   = haiku_total + sonnet_total + opus_total

    if haiku_total > 0:
        lines.append(row(f'{B}Haiku total{R}', 'haiku',
                         totals['haiku_in'], totals['haiku_out']))
    if sonnet_total > 0:
        lines.append(row(f'{B}Sonnet total{R}', 'sonnet',
                         totals['sonnet_in'], totals['sonnet_out']))
    if opus_total > 0:
        lines.append(row(f'{B}Opus total{R}', 'opus',
                         totals['opus_in'], totals['opus_out']))

    lines.append(divider)
    lines.append(
        f'  {B}{"TOTAL":<36} {"":12} '
        f'{"":>10}  {"":>10}  '
        f'{B}{all_tokens:>12,}{R}  '
        f'{B}{G}${totals["total_cost"]:.4f}{R}'
    )
    lines.append('')
    lines.append(f'  {D}Pricing: Haiku $0.80/$4.00 per 1M · Sonnet $3.00/$15.00 per 1M (input/output){R}')
    lines.append(f'  {D}LLM phase totals are estimates. Script phases (1-scan, 3-generate) are exact $0.{R}')
    lines.append('')

    print('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(description='Print tldr token usage report')
    parser.add_argument('--ledger', required=True, help='Path to token-ledger.json')
    args = parser.parse_args()
    ledger = load_ledger(args.ledger)
    render_report(ledger)


if __name__ == '__main__':
    main()
