"""
PostgresFS: a fake filesystem interface over a Postgres docs table.

Each "file" is a row: (path TEXT, content TEXT, updated_at TIMESTAMPTZ).
Shell verbs (ls, cat, grep, find, cd) translate to SQL SELECTs.
Filters (sort, uniq, wc, head, tail, awk, sed, cut, tr, comm) run locally
over bytes already in memory — no extra round-trips.
"""

import re
import subprocess
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor


class PostgresFS:
    def __init__(self, dsn: str, table: str = "docs"):
        self.conn = psycopg2.connect(dsn)
        self.table = table
        self.cwd = "/"

    def _query(self, sql: str, params=()) -> list[dict]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    # ── core verbs ────────────────────────────────────────────────────────────

    def ls(self, path: Optional[str] = None) -> str:
        base = self._resolve(path or self.cwd)
        pattern = base.rstrip("/") + "/%"
        rows = self._query(
            f"SELECT DISTINCT split_part(path, '/', array_length(string_to_array(path,'/'),1)) AS name"
            f" FROM {self.table} WHERE path LIKE %s ORDER BY name",
            (pattern,),
        )
        return "\n".join(r["name"] for r in rows) if rows else ""

    def cat(self, path: str) -> str:
        resolved = self._resolve(path)
        rows = self._query(
            f"SELECT content FROM {self.table} WHERE path = %s", (resolved,)
        )
        if not rows:
            return f"cat: {path}: No such file"
        return rows[0]["content"]

    def grep(self, pattern: str, path: str, recursive: bool = False, files_only: bool = False) -> str:
        resolved = self._resolve(path)
        if recursive:
            like = resolved.rstrip("/") + "%"
            rows = self._query(
                f"SELECT path, content FROM {self.table} WHERE path LIKE %s AND content ~* %s",
                (like, pattern),
            )
        else:
            rows = self._query(
                f"SELECT path, content FROM {self.table} WHERE path = %s AND content ~* %s",
                (resolved, pattern),
            )
        if files_only:
            return "\n".join(r["path"] for r in rows)
        out = []
        for r in rows:
            for line in r["content"].splitlines():
                if re.search(pattern, line, re.IGNORECASE):
                    out.append(f"{r['path']}:{line}")
        return "\n".join(out)

    def find(self, path: str, name: Optional[str] = None, type_: str = "f") -> str:
        resolved = self._resolve(path)
        like = resolved.rstrip("/") + "%"
        if name:
            name_pattern = name.replace("*", "%").replace("?", "_")
            rows = self._query(
                f"SELECT path FROM {self.table} WHERE path LIKE %s AND path LIKE %s ORDER BY path",
                (like, "%" + name_pattern),
            )
        else:
            rows = self._query(
                f"SELECT path FROM {self.table} WHERE path LIKE %s ORDER BY path",
                (like,),
            )
        return "\n".join(r["path"] for r in rows)

    def cd(self, path: str) -> str:
        self.cwd = self._resolve(path)
        return ""

    # ── local filters (run over in-memory bytes, no DB round-trip) ────────────

    def pipe(self, content: str, *commands: str) -> str:
        """Run a pipeline of coreutils commands over content."""
        data = content.encode()
        for cmd in commands:
            result = subprocess.run(
                cmd, shell=True, input=data, capture_output=True
            )
            data = result.stdout
        return data.decode(errors="replace")

    # ── shell dispatch ─────────────────────────────────────────────────────────

    def run(self, command: str) -> str:
        """Dispatch a shell command string to the appropriate method."""
        cmd = command.strip()
        if cmd.startswith("ls"):
            args = cmd[2:].strip()
            return self.ls(args or None)
        if cmd.startswith("cat "):
            return self.cat(cmd[4:].strip())
        if cmd.startswith("grep "):
            return self._dispatch_grep(cmd)
        if cmd.startswith("find "):
            return self._dispatch_find(cmd)
        if cmd.startswith("cd "):
            return self.cd(cmd[3:].strip())
        # fallback: local coreutils only
        return self.pipe("", cmd)

    def _dispatch_grep(self, cmd: str) -> str:
        parts = cmd.split()
        recursive = "-r" in parts or "-rl" in parts
        files_only = "-l" in parts or "-rl" in parts
        clean = [p for p in parts[1:] if not p.startswith("-")]
        if len(clean) >= 2:
            return self.grep(clean[0], clean[1], recursive=recursive, files_only=files_only)
        return ""

    def _dispatch_find(self, cmd: str) -> str:
        parts = cmd.split()
        path = parts[1] if len(parts) > 1 else self.cwd
        name = None
        if "-name" in parts:
            idx = parts.index("-name")
            if idx + 1 < len(parts):
                name = parts[idx + 1]
        return self.find(path, name=name)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _resolve(self, path: str) -> str:
        if path.startswith("/"):
            return path
        return self.cwd.rstrip("/") + "/" + path

    def close(self):
        self.conn.close()
