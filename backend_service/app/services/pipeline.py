# This file defines the end-to-end workflow for processing uploaded PDF files.
import tempfile
from app.core.parser import parse_pdf
from app.core.workflow import build_graph
import tempfile
from app.core.parser import parse_pdf
from app.core.workflow import build_graph
from datetime import datetime, timedelta
from dateutil import parser

# End-to-end workflow to process uploaded PDF file
async def pdf_processor_workflow(file):
    # Save uploaded file to a temporary path
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    # Parse all pages
    pages = parse_pdf(tmp_path)

    # Join all pages into a single document text
    full_text = "\n\n".join([text for _, text in pages])

    # Run the LangGraph pipeline once on the entire doc
    graph = build_graph()
    state = {"text": full_text, "parsed": []}
    final_state = graph.invoke(state)

    # Collect structured results
    results = []
    for item in final_state["parsed"]:
        results.append({
            "event": item.get("event"),
            "event_date": item.get("event_date"),
            "obligation": item.get("obligation"),
            "obligation_date": item.get("obligation_date"),
            "confidence": item.get("confidence"),
        })

    results = prioritize_items(results)

    return {
        "summary": final_state.get("summary"),
        "results": results,
        "triggers": final_state.get("triggers", {})
    }


# Prioritize items based on due dates
def prioritize_items(results):
    today = datetime.today()
    for item in results:
        due = item.get("obligation_date") or item.get("event_date")
        if not due:
            item["priority"] = "Low"
            continue
        try:
            due_date = parser.parse(str(due)).date()
            if due_date < today.date():
                item["priority"] = "overdue"
            elif due_date <= today.date() + timedelta(days=7):
                item["priority"] = "High"
            else:
                item["priority"] = "Medium"
        except Exception:
            item["priority"] = "Low"
    return results
