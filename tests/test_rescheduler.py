from campusflow.models import Room, Session, Assignment
from campusflow.rescheduler import repair_schedule
from campusflow.constraints import validate_schedule

SLOTS = ["09:00", "10:00", "11:00"]

def test_repair_moves_only_the_affected_session_when_possible():
    rooms = [Room("R1", "Room 1", 40, ("projector",), tuple(SLOTS)),
             Room("R2", "Room 2", 40, ("projector",), tuple(SLOTS))]
    sessions = [Session("S1", "Lecture A", 30, 1, ("projector",), ("09:00", "10:00"), 1),
                Session("S2", "Lecture B", 30, 1, ("projector",), ("09:00", "10:00"), 1)]
    old = {"S1": Assignment("S1", "R1", "09:00"), "S2": Assignment("S2", "R2", "09:00")}
    result = repair_schedule(rooms, sessions, SLOTS, old, {"R1"})
    assert result.schedule is not None
    assert len(result.moved_sessions) == 1
    assert validate_schedule(rooms, sessions, result.schedule, SLOTS, {"R1"}) == []

def test_repair_reports_infeasibility():
    rooms = [Room("R1", "Only room", 40, (), tuple(SLOTS))]
    sessions = [Session("S1", "Lecture", 30, 1, (), ("09:00",), 1)]
    old = {"S1": Assignment("S1", "R1", "09:00")}
    result = repair_schedule(rooms, sessions, SLOTS, old, {"R1"})
    assert result.schedule is None
    assert "infeasible" in result.message.lower()
