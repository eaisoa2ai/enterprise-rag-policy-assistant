"""Single-page Gradio dashboard: pick a role, ask a question, see the
retrieved sources, the answer, its groundedness verdict, and whether it was
flagged for review.

Run with: uv run python ui/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import gradio as gr  # noqa: E402

from policyiq.models import Role  # noqa: E402
from policyiq.query import answer_question  # noqa: E402


def ask(question: str, role: str):
    if not question.strip():
        return "Ask a question first.", "", "", ""

    try:
        result = answer_question(question, Role(role))
    except Exception as exc:
        return f"Query failed: {exc}", "", "", ""

    answer_md = f"**Answer:** {result.final_answer}"

    sources_md = "_No sources retrieved._"
    if result.retrieval and result.retrieval.chunks:
        sources_md = "\n".join(
            f"- {sc.chunk.doc_title} (`{sc.chunk.chunk_id}`) — score {sc.score:.2f}"
            for sc in result.retrieval.chunks
        )

    grounded_md = "_No groundedness check ran (question was refused before generation)._"
    if result.groundedness:
        badge = "✅ Grounded" if result.groundedness.is_grounded else "⚠️ Not grounded"
        grounded_md = f"**{badge}**"
        if result.groundedness.unsupported_claims:
            grounded_md += "\n\n" + "\n".join(f"- {v}" for v in result.groundedness.unsupported_claims)

    review_md = "No human review required."
    if result.requires_review:
        review_md = "**Flagged for review:**\n" + "\n".join(f"- {r}" for r in result.review_reasons)

    return answer_md, sources_md, grounded_md, review_md


with gr.Blocks(title="PolicyIQ") as demo:
    gr.Markdown("# PolicyIQ — Access-Controlled Enterprise Policy Assistant")
    gr.Markdown(
        "Ask a policy question as a given role. Retrieval is filtered to only "
        "documents that role can see *before* ranking — not just before display — "
        "and every answer passes a groundedness check before being trusted."
    )

    with gr.Row():
        role_dropdown = gr.Dropdown(choices=[r.value for r in Role], value="employee", label="Role")
        question_input = gr.Textbox(label="Question", scale=3)
        ask_button = gr.Button("Ask", variant="primary")

    answer_output = gr.Markdown(label="Answer")

    with gr.Row():
        sources_output = gr.Markdown(label="Retrieved Sources")
        grounded_output = gr.Markdown(label="Groundedness")

    review_output = gr.Markdown(label="Review Status")

    ask_button.click(
        ask,
        inputs=[question_input, role_dropdown],
        outputs=[answer_output, sources_output, grounded_output, review_output],
    )

if __name__ == "__main__":
    demo.launch()
