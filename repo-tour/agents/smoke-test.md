---
name: smoke-test
description: Verify subagent dispatch and model routing works
model: haiku
allowed-tools: Bash(echo *)
context: fork
---
Run: echo "haiku-agent-alive"
Output exactly: {"status": "ok"}
Nothing else. Under 20 tokens.
