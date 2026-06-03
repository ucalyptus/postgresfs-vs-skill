"""
Seed a Postgres database with sample docs for testing.
Creates the `docs` table and inserts synthetic documentation pages.

Usage:
  python scripts/seed_db.py --dsn "postgresql://user:pass@localhost/mydb"
"""

import argparse
import psycopg2

SAMPLE_DOCS = [
    ("/tracing/quickstart", "Tracing", "Quickstart Guide", "concepts",
     "Get started with tracing in 5 minutes. Add the SDK, instrument your first span, and view traces in the dashboard."),
    ("/tracing/concepts", "Tracing Concepts", "What is a span?", "concepts",
     "A span represents a unit of work. Spans have a name, start time, duration, and optional attributes. Traces are trees of spans."),
    ("/evaluation/overview", "Evaluation", "Overview", "evaluation",
     "Evaluation helps you measure LLM quality. Define metrics, run evals on datasets, and track results over time."),
    ("/evaluation/metrics", "Evaluation Metrics", "Built-in Metrics", "evaluation",
     "Built-in metrics include hallucination, relevance, tone, and prompt adherence. Custom metrics use Python functions."),
    ("/evaluation/quickstart", "Evaluation Quickstart", "Run your first evaluation", "evaluation",
     "Create a dataset, define a task, choose metrics, and run. Results appear in the Evals tab with prompt and span details."),
    ("/integrations/openai", "OpenAI Integration", "Integrating with OpenAI", "integrations",
     "Wrap the OpenAI client to auto-instrument calls. Every chat completion becomes a span with prompt, completion, and token counts."),
    ("/integrations/langchain", "LangChain Integration", "Integrating with LangChain", "integrations",
     "Use the ArizeCallbackHandler with any LangChain chain. Chains, tools, and retrievers each emit a span automatically."),
    ("/integrations/llamaindex", "LlamaIndex Integration", "Integrating with LlamaIndex", "integrations",
     "Set the global handler before building your index. Queries, retrievals, and LLM calls are all traced as spans."),
    ("/concepts/datasets", "Datasets", "Working with Datasets", "concepts",
     "Datasets store input/output pairs for evaluation. Upload CSV or JSONL, or generate from production traces via the export button."),
    ("/concepts/prompts", "Prompts", "Prompt Management", "concepts",
     "Store prompt templates with version control. Reference prompts by name in evaluation tasks and compare versions side by side."),
    ("/onboarding/install", "Installation", "Installing the SDK", "onboarding",
     "pip install arize-otel opentelemetry-sdk. Set ARIZE_API_KEY and ARIZE_SPACE_KEY in your environment before importing."),
    ("/onboarding/first-trace", "First Trace", "Sending your first trace", "onboarding",
     "Import register from arize.otel, call register(), then wrap your model call. A trace appears in the UI within seconds."),
    ("/onboarding/first-eval", "First Evaluation", "Running your first evaluation", "onboarding",
     "After tracing, go to Evaluations, pick a dataset, choose a metric, and click Run. Results link back to individual spans."),
]


def seed(dsn: str):
    conn = psycopg2.connect(dsn)
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS docs (
                    path     TEXT PRIMARY KEY,
                    title    TEXT,
                    heading  TEXT,
                    section  TEXT,
                    content  TEXT,
                    updated_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            for path, title, heading, section, content in SAMPLE_DOCS:
                cur.execute("""
                    INSERT INTO docs (path, title, heading, section, content)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (path) DO UPDATE SET
                        title = EXCLUDED.title,
                        heading = EXCLUDED.heading,
                        section = EXCLUDED.section,
                        content = EXCLUDED.content
                """, (path, title, heading, section, content))
    conn.close()
    print(f"Seeded {len(SAMPLE_DOCS)} docs.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", required=True)
    args = parser.parse_args()
    seed(args.dsn)
