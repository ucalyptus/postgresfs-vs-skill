"""
Agent using the SQL Skill: one DB round-trip, then real bash.
The agent writes SQL, gets a local file path back, and composes with real shell tools.
"""

import os
import subprocess
import time
import anthropic
from skill import SQLSkill

SYSTEM_PROMPT = """You are a documentation assistant. You have access to a Postgres database
containing documentation, plus a real bash shell.

Workflow:
  1. Call `run_query` with a SQL query → you get a local .jsonl file path.
  2. Use `bash` to compose the answer from that file (grep, jq, sort, awk, pipes, etc.).
  3. For answers reducible to a small set (COUNT, GROUP BY), compute inline in SQL.
     Otherwise, project every candidate row to a file and compose locally.

Database schema (table: docs):
  path     TEXT  — virtual file path, e.g. /tracing/quickstart
  title    TEXT  — document title
  content  TEXT  — full document text
  section  TEXT  — top-level section

SQL tips:
  - Use ILIKE for case-insensitive text search: content ILIKE '%keyword%'
  - Use to_tsvector/to_tsquery for full-text search
  - Do NOT use run_query as a search loop — project broadly and compose locally.
"""


def _bash(cmd: str) -> str:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return (result.stdout + result.stderr).strip()


def run_skill_agent(question: str, dsn: str, model: str = "claude-sonnet-4-6") -> dict:
    client = anthropic.Anthropic()
    skill = SQLSkill(dsn)

    tools = [
        {
            "name": "run_query",
            "description": "Run a SQL query against the docs database. Returns path to a local .jsonl file with results.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL query to execute"},
                    "format": {
                        "type": "string",
                        "enum": ["jsonl", "tsv", "json"],
                        "description": "Output format (default: jsonl)",
                    },
                },
                "required": ["sql"],
            },
        },
        {
            "name": "bash",
            "description": "Run a real bash command (grep, jq, sort, awk, pipes, etc.) over local files.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Bash command to run"}
                },
                "required": ["command"],
            },
        },
    ]

    messages = [{"role": "user", "content": question}]
    loop_start = time.monotonic()
    tool_calls = 0

    while True:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            tool_calls += 1
            if block.name == "run_query":
                fmt = block.input.get("format", "jsonl")
                path = skill.run_query(block.input["sql"], out_format=fmt)
                output = path
            elif block.name == "bash":
                output = _bash(block.input["command"])
            else:
                output = f"unknown tool: {block.name}"

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
            })

        if not tool_results:
            break

        messages.append({"role": "user", "content": tool_results})

    loop_elapsed = time.monotonic() - loop_start
    skill.close()

    final_text = next(
        (b.text for b in response.content if hasattr(b, "text")), ""
    )
    return {
        "answer": final_text,
        "latency_s": round(loop_elapsed, 3),
        "tool_calls": tool_calls,
    }
