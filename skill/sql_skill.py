"""
SQL Skill: one round-trip to Postgres, everything else runs locally.

The agent calls run_query(sql) which writes results to a temp file,
then uses real bash (grep, jq, sort, awk, pipes, etc.) over that file.
"""

import json
import os
import tempfile
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor


class SQLSkill:
    def __init__(self, dsn: str, workdir: str | None = None):
        self.conn = psycopg2.connect(dsn)
        self.workdir = workdir or tempfile.mkdtemp(prefix="sqlskill_")
        self._file_counter = 0

    def run_query(self, sql: str, out_format: str = "jsonl") -> str:
        """
        Execute SQL and write results to a local file.
        Returns the file path — agent can then use real bash on it.
        """
        self._file_counter += 1
        out_path = Path(self.workdir) / f"result_{self._file_counter:03d}.{out_format}"

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            rows = [dict(r) for r in cur.fetchall()]

        if out_format == "jsonl":
            out_path.write_text("\n".join(json.dumps(r) for r in rows))
        elif out_format == "tsv":
            if rows:
                headers = list(rows[0].keys())
                lines = ["\t".join(headers)]
                lines += ["\t".join(str(r.get(h, "")) for h in headers) for r in rows]
                out_path.write_text("\n".join(lines))
            else:
                out_path.write_text("")
        else:
            out_path.write_text(json.dumps(rows, indent=2))

        return str(out_path)

    def schema(self, table: str = "docs") -> str:
        """Return column info for a table."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = %s ORDER BY ordinal_position",
                (table,),
            )
            return "\n".join(f"{r[0]} ({r[1]})" for r in cur.fetchall())

    def close(self):
        self.conn.close()
        import shutil
        shutil.rmtree(self.workdir, ignore_errors=True)
