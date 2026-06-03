"""
The 10 benchmark questions from the Arize article, across 3 tiers.
tier: simple (1-few reads), mid (aggregation), complex (extraction/synthesis)
"""

QUESTIONS = [
    # Simple
    {"id": "q1", "tier": "simple", "question": "What is the path of the document about quickstart for tracing?"},
    {"id": "q2", "tier": "simple", "question": "List all top-level sections available in the documentation."},
    {"id": "q3", "tier": "simple", "question": "How many documents are in the 'concepts' section?"},
    # Mid
    {"id": "q4", "tier": "mid", "question": "How many documents mention 'span' in their content?"},
    {"id": "q5", "tier": "mid", "question": "Which section has the most documents?"},
    {"id": "q6", "tier": "mid", "question": "List all document titles that contain the word 'evaluation'."},
    # Complex
    {"id": "q7", "tier": "complex", "question": "Summarise the key differences between tracing and evaluation in the docs."},
    {"id": "q8", "tier": "complex", "question": "Which documents reference both 'prompt' and 'span' — list their paths."},
    {"id": "q9", "tier": "complex", "question": "What integrations are documented? List each integration name and its section."},
    {"id": "q10", "tier": "complex", "question": "Describe the full onboarding flow for a new user based on the documentation."},
]
