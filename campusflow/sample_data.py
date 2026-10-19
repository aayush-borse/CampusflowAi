"""Small, deterministic demonstration dataset."""
from __future__ import annotations
import json
from pathlib import Path
from .models import Room, Session, records_to_rooms, records_to_sessions

SLOTS = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00"]

def sample_records() -> tuple[list[dict], list[dict]]:
    rooms = [
        {"id":"R1","name":"Room 101","capacity":60,"facilities":["projector"],"available_slots":SLOTS},
        {"id":"R2","name":"Room 102","capacity":40,"facilities":["projector","whiteboard"],"available_slots":SLOTS},
        {"id":"R3","name":"Lab A","capacity":30,"facilities":["computers","projector"],"available_slots":SLOTS},
        {"id":"R4","name":"Lab B","capacity":36,"facilities":["computers","networking"],"available_slots":SLOTS},
        {"id":"R5","name":"Seminar Hall","capacity":100,"facilities":["projector","whiteboard"],"available_slots":SLOTS},
        {"id":"R6","name":"Electronics Lab","capacity":24,"facilities":["electronics","computers"],"available_slots":SLOTS},
    ]
    sessions = [
        {"id":"S1","name":"Data Structures Lecture","students":55,"duration":1,"required_facilities":["projector"],"allowed_start_slots":["09:00","10:00","11:00"],"priority":3},
        {"id":"S2","name":"Computer Networks Practical","students":28,"duration":2,"required_facilities":["computers","networking"],"allowed_start_slots":["09:00","10:00","11:00","12:00"],"priority":5},
        {"id":"S3","name":"Database Systems Lecture","students":38,"duration":1,"required_facilities":["projector"],"allowed_start_slots":["09:00","10:00","11:00","12:00"],"priority":2},
        {"id":"S4","name":"AI Practical","students":28,"duration":2,"required_facilities":["computers"],"allowed_start_slots":["10:00","11:00","12:00","13:00"],"priority":4},
        {"id":"S5","name":"Operating Systems Lecture","students":42,"duration":1,"required_facilities":["projector"],"allowed_start_slots":["09:00","10:00","11:00","12:00","13:00"],"priority":2},
        {"id":"S6","name":"Electronics Practical","students":22,"duration":2,"required_facilities":["electronics"],"allowed_start_slots":["09:00","10:00","11:00","12:00"],"priority":5},
        {"id":"S7","name":"Software Engineering Lecture","students":35,"duration":1,"required_facilities":["projector"],"allowed_start_slots":["10:00","11:00","12:00","13:00","14:00"],"priority":2},
        {"id":"S8","name":"Cyber Security Practical","students":26,"duration":2,"required_facilities":["computers"],"allowed_start_slots":["09:00","10:00","11:00","12:00"],"priority":4},
        {"id":"S9","name":"Discrete Mathematics Lecture","students":32,"duration":1,"required_facilities":["whiteboard"],"allowed_start_slots":["09:00","10:00","11:00","12:00","13:00"],"priority":1},
        {"id":"S10","name":"IoT Lab","students":20,"duration":2,"required_facilities":["electronics","computers"],"allowed_start_slots":["10:00","11:00","12:00"],"priority":4},
        {"id":"S11","name":"Communication Skills","students":25,"duration":1,"required_facilities":[],"allowed_start_slots":["11:00","12:00","13:00","14:00"],"priority":1},
        {"id":"S12","name":"Project Review","students":30,"duration":1,"required_facilities":["projector"],"allowed_start_slots":["12:00","13:00","14:00"],"priority":3},
    ]
    return rooms, sessions

def sample_domain() -> tuple[list[Room], list[Session], list[str]]:
    room_rows, session_rows = sample_records()
    return records_to_rooms(room_rows), records_to_sessions(session_rows), list(SLOTS)

def load_sample_json() -> tuple[list[dict], list[dict], list[str]]:
    path = Path(__file__).resolve().parent.parent / "data" / "sample_data.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw["rooms"], raw["sessions"], raw["slots"]
