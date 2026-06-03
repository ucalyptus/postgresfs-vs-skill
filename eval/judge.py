"""
LLM judge (claude-opus-4-7) for synthesis/extraction questions.
Returns a score 0-10 against a rubric.
"""

import anthropic

JUDGE_SYSTEM = """You are an expert evaluator. You will be given a question, a reference answer,
and a candidate answer. Score the candidate answer from 0 to 10 based on:
- Correctness (does it answer the question accurately?)
- Completeness (does it cover all required points?)
- Conciseness (no hallucination or padding)

Respond with JSON: {"score": <int 0-10>, "reason": "<one sentence>"}"""


def judge(question: str, reference: str, candidate: str, model: str = "claude-opus-4-7") -> dict:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=256,
        system=JUDGE_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Question: {question}\n\nReference: {reference}\n\nCandidate: {candidate}",
            }
        ],
    )
    import json, re
    text = response.content[0].text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {"score": 0, "reason": "parse error"}
