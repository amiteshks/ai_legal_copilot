# This file defines a workflow to parse, summarize, extract, and resolve legal document events using a state graph.
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from typing import TypedDict, List, Dict
from datetime import datetime, timedelta
import json
from langsmith import traceable
from dotenv import load_dotenv
import os



# ---- Helpers ----
from dateutil import parser

load_dotenv(dotenv_path="./app/.env", override=True)

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("❌ OPENAI_API_KEY not found in environment.")

# ---- State Definition ----
class DocState(TypedDict):
    text: str
    parsed: List[Dict]
    triggers: Dict[str, str]
    summary: str



# Compute deadline given a trigger date and offset in days
def compute_deadline(trigger_date: str, offset_days: int, court_days: bool = False) -> str:
    """
    Compute deadline given a trigger date and offset in days.
    Positive offset = after, Negative offset = before
    """
    date = parser.parse(trigger_date)   #  flexible parsing
    days_added = 0
    step = 1 if offset_days > 0 else -1

    while days_added != offset_days:
        date += timedelta(days=step)
        if court_days:
            if date.weekday() < 5:  # Mon–Fri only
                days_added += step
        else:
            days_added += step

    return date.strftime("%Y-%m-%d")   # always normalize to ISO


# Resolve relative deadlines into absolute dates when possible
def resolve_relative_dates(parsed_events: list, trigger_dates: dict, court_days: bool = False):
    """
    Resolve relative deadlines into absolute dates when possible.
    Cascade forward: newly resolved events become triggers for others.
    """
    updated = parsed_events.copy()
    changed = True

    while changed:  # loop until no more resolutions
        changed = False
        for ev in updated:
            if (
                ev.get("relative_rule")
                and ev.get("trigger_event")
                and ev.get("offset_days") is not None
            ):
                trigger = ev["trigger_event"]
                if trigger in trigger_dates:
                    try:
                        computed = compute_deadline(
                            trigger_dates[trigger], ev["offset_days"], court_days
                        )
                        if not ev.get("obligation_date"):
                            ev["obligation_date"] = computed
                            changed = True
                        if not ev.get("event_date") and ev.get("event"):
                            ev["event_date"] = computed
                            changed = True
                        # cascade: resolved event becomes new trigger
                        if ev.get("event") and ev["event_date"]:
                            trigger_dates[ev["event"]] = ev["event_date"]
                    except Exception as e:
                        print(f"Error computing date for {ev}: {e}")

    return updated


# ---- Nodes ----

# Each node processes the DocState and returns an updated DocState
@traceable(name="parse_node")
def parse_node(state: DocState):
    return {
        "parsed": [{"text": state["text"]}],
        "triggers": state.get("triggers", {}),
        "summary": state.get("summary", None),
    }

# Summarize legal text to focus on key dates, obligations, and parties
@traceable(name="summarize_node")
def summarize_node(state: DocState):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = f"""
    Summarize the following legal text in 3–5 sentences.
    Focus on key dates, obligations, and parties involved.
    Keep it concise and professional.

    Text:
    {state["parsed"][0]["text"]}
    """

    resp = llm.invoke(prompt)
    summary = resp.content.strip()

    return {
        "summary": summary,
        "parsed": state.get("parsed", []),
        "triggers": state.get("triggers", {}),
    }

# Extract events and obligations from legal text
@traceable(name="extract_node")
def extract_node(state: DocState):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = f"""
    You are a legal docketing assistant.
    Extract ALL events and obligations from the following legal text.

    For each item, return an object with:
    - event
    - event_date
    - obligation
    - obligation_date
    - relative_rule
    - trigger_event
    - offset_days
    - rule_type
    - business_days
    - evidence_text
    - why

    Text:
    {state["parsed"][0]["text"]}

    Return ONLY a valid JSON array (no markdown).
    """

    resp = llm.invoke(prompt)
    raw = resp.content.strip()

    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

    try:
        parsed = json.loads(raw)
    except Exception as e:
        print("Error parsing JSON:", e)
        parsed = []

    # Auto-populate triggers from explicit event dates
    triggers = state.get("triggers", {}).copy()
    for item in parsed:
        if item.get("event") and item.get("event_date"):
            triggers[item["event"]] = item["event_date"]

    # Compute offsets for evidence text
    doc_text = state["parsed"][0]["text"]
    for item in parsed:
        ev = (item.get("evidence_text") or "").strip()
        start = doc_text.find(ev) if ev else -1
        item["evidence_start"] = start if start >= 0 else None
        item["evidence_end"] = (start + len(ev)) if start >= 0 else None

    return {
        "parsed": parsed,
        "triggers": triggers,
        "summary": state.get("summary"),  # ✅ preserve summary
    }
from datetime import datetime

def is_iso_date(val: str) -> bool:
    """Check if a string is a valid ISO YYYY-MM-DD date."""
    try:
        datetime.fromisoformat(val)
        return True
    except Exception:
        return False


@traceable(name="resolve_node")
def resolve_node(state: DocState):
    trigger_dates = state.get("triggers", {}).copy()
    resolved = state["parsed"].copy()
    today = datetime.today().strftime("%Y-%m-%d")
    last_known_date = None

    for ev in resolved:
        trigger = ev.get("trigger_event")

        # Service of Order → today
        if trigger and "service of this order" in trigger.lower():
            trigger_dates[trigger] = today

        # Unknown trigger → fall back to last known date or today
        if trigger and trigger not in trigger_dates:
            trigger_dates[trigger] = last_known_date or today

        # Resolve relative rules
        if ev.get("relative_rule") and trigger and ev.get("offset_days") is not None:
            base = trigger_dates.get(trigger)
            if base:
                computed = compute_deadline(base, ev["offset_days"])

                # Overwrite if missing or not ISO
                if not ev.get("obligation_date") or not is_iso_date(ev["obligation_date"]):
                    ev["obligation_date"] = computed

                if (not ev.get("event_date") or not is_iso_date(ev["event_date"])) and ev.get("event"):
                    ev["event_date"] = computed

                # Cascade: resolved event becomes a trigger
                if ev.get("event") and ev.get("event_date"):
                    trigger_dates[ev["event"]] = ev["event_date"]

                last_known_date = computed

        # Explicit ISO date → add to triggers
        date_str = ev.get("event_date") or ev.get("obligation_date")
        if date_str and is_iso_date(date_str):
            trigger_dates[ev["event"]] = date_str
            last_known_date = date_str

    # Pass 2: assign status
    for ev in resolved:
        date_str = ev.get("event_date") or ev.get("obligation_date")
        ev["status"] = "resolved" if (date_str and is_iso_date(date_str)) else "pending"

    # Pass 3: assign priority based on chronological order
    dated_events = [ev for ev in resolved if (ev.get("event_date") or ev.get("obligation_date")) and is_iso_date(ev.get("event_date") or ev.get("obligation_date"))]
    dated_events.sort(key=lambda x: x.get("obligation_date") or x.get("event_date"))

    for i, ev in enumerate(dated_events):
        ev["priority"] = "High" if i == 0 else "Medium" if i == 1 else "Low"

    for ev in resolved:
        if "priority" not in ev:
            ev["priority"] = "Low"

    # Pass 4: final sort
    def get_sort_date(ev):
        d = ev.get("obligation_date") or ev.get("event_date")
        return d if (d and is_iso_date(d)) else "9999-12-31"

    resolved.sort(key=get_sort_date)

    return {
        "parsed": resolved,
        "triggers": trigger_dates,
        "summary": state.get("summary"),
    }

# ---- Graph Builder ----
def build_graph():
    graph = StateGraph(DocState)
    graph.add_node("parse", parse_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("extract", extract_node)
    graph.add_node("resolve", resolve_node)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "summarize")
    graph.add_edge("summarize", "extract")
    graph.add_edge("extract", "resolve")
    graph.add_edge("resolve", END)

    return graph.compile()

