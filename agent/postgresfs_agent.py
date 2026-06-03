"""
Agent using PostgresFS: Bash tool is wired to the PostgresFS adapter.
Every ls/cat/grep/find becomes a Postgres SELECT.
"""

import time
import anthropic
from postgresfs import PostgresFS

SYSTEM_PROMPT = """You are a documentation assistant. You have access to a filesystem interface
over a documentation database. Use shell commands to explore and answer questions.

Command reference:
  ls [path]              — list files/directories at path
  cat <path>             — read a file's content
  grep [-r] [-l] <pattern> <path>  — search for pattern in files
  find <path> [-name <glob>]       — find files by name
  cd <path>              — change current directory

Strategy:
  - Use `find` or `ls` to orient, then `cat` or `grep` to read.
  - Prefer `grep -rl` to locate relevant files before reading them.
  - Keep the number of reads minimal — retrieve what you need, then synthesise.
"""


def run_postgresfs_agent(question: str, dsn: str, model: str = "claude-sonnet-4-6") -> dict:
    client = anthropic.Anthropic()
    fs = PostgresFS(dsn)

    tools = [
        {
            "name": "bash",
            "description": "Run a shell command against the documentation filesystem.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run"}
                },
                "required": ["command"],
            },
        }
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
            if block.type == "tool_use" and block.name == "bash":
                tool_calls += 1
                output = fs.run(block.input["command"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })

        if not tool_results:
            break

        messages.append({"role": "user", "content": tool_results})

    loop_elapsed = time.monotonic() - loop_start
    fs.close()

    final_text = next(
        (b.text for b in response.content if hasattr(b, "text")), ""
    )
    return {
        "answer": final_text,
        "latency_s": round(loop_elapsed, 3),
        "tool_calls": tool_calls,
    }
