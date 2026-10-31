# RRULE Expander

A `nanoagent.plugin/v0001` plugin.

## Tools

| Tool | Does | Code |
|---|---|---|
| `expand_rrule` | Validates and expands a supported RFC 5545 daily recurrence rule within an inclusive date-time window. | `src/plugin/expand_rrule.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `expand-rrule` | Expands a validated daily recurrence rule into deterministic date-time occurrences. | `tool`, with `expand_rrule` |

## Layout

```text
.
├── nanoagent.yaml
├── contract.py
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env
├── src/plugin/
├── tests/
├── ui/
├── product/
└── verifier/
```

`contract.py` is the one place a value's shape is declared. Its Output classes are the JSON Schemas the server offers and the agent sees, and every input and output is built into its class on the way in and out. A tool that fails raises; NanoAgent sees an MCP error.

## Develop and run

```
uv sync --extra dev
uv run pytest
```

Publishing checks every plugin rule: push the plugin to a public GitHub repository and run:

```
rush publish <server> <github-url>
```