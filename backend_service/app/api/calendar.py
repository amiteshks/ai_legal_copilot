# This file defines an API endpoint for adding calendar events.
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class CalendarEvent(BaseModel):
    title: str
    description: str | None = None
    start: str  # accept string instead of datetime
    end: str | None = None

# End point to add event to calendar
@router.post("/calendar/add")
async def add_to_calendar(event: CalendarEvent):
    # For demo, just log it
    # Later: integrate Google Calendar / Outlook APIs here
    print(f"Adding event: {event.title} at {event.start}")
    return {"status": "ok", "event": event}
