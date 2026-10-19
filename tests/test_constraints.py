from campusflow.models import Room, Session, Assignment
from campusflow.constraints import validate_schedule

SLOTS = ["09:00", "10:00", "11:00"]

def fixtures():
    rooms = [Room("R1", "Room 1", 40, ("projector",), tuple(SLOTS)),
             Room("R2", "Lab", 20, ("computers",), tuple(SLOTS))]
    sessions = [Session("S1", "Lecture", 30, 1, ("projector",), ("09:00", "10:00"), 1),
                Session("S2", "Lab", 18, 2, ("computers",), ("09:00", "11:00"), 1)]
    return rooms, sessions

def test_valid_schedule_has_no_issues():
    rooms, sessions = fixtures()
    schedule = {"S1": Assignment("S1", "R1", "09:00"), "S2": Assignment("S2", "R2", "09:00")}
    assert validate_schedule(rooms, sessions, schedule, SLOTS) == []

def test_room_double_booking_is_detected():
    rooms, sessions = fixtures()
    schedule = {"S1": Assignment("S1", "R1", "09:00"), "S2": Assignment("S2", "R1", "09:00")}
    assert any("Room clash" in x for x in validate_schedule(rooms, sessions, schedule, SLOTS))

def test_capacity_and_facilities_are_hard_constraints():
    rooms, sessions = fixtures()
    schedule = {"S1": Assignment("S1", "R2", "09:00"), "S2": Assignment("S2", "R2", "09:00")}
    issues = validate_schedule(rooms, sessions, schedule, SLOTS)
    assert any("capacity" in x.lower() for x in issues)
    assert any("lacks" in x.lower() for x in issues)

def test_duration_must_fit_in_day():
    rooms, sessions = fixtures()
    schedule = {"S1": Assignment("S1", "R1", "11:00"), "S2": Assignment("S2", "R2", "11:00")}
    assert any("invalid start slot or duration" in x for x in validate_schedule(rooms, sessions, schedule, SLOTS))
