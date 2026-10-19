from campusflow.models import Room, Session
from campusflow.scheduler import solve_csp
from campusflow.constraints import validate_schedule

SLOTS = ["09:00", "10:00", "11:00"]

def test_scheduler_finds_valid_schedule():
    rooms = [Room("R1", "Large", 40, ("projector",), tuple(SLOTS)),
             Room("R2", "Lab", 20, ("computers",), tuple(SLOTS))]
    sessions = [Session("S1", "Lecture", 30, 1, ("projector",), ("09:00", "10:00"), 1),
                Session("S2", "Practical", 18, 2, ("computers",), ("09:00",), 2)]
    result = solve_csp(rooms, sessions, SLOTS)
    assert result.schedule is not None
    assert validate_schedule(rooms, sessions, result.schedule, SLOTS) == []

def test_scheduler_reports_infeasible_problem():
    rooms = [Room("R1", "Small", 10, (), tuple(SLOTS))]
    sessions = [Session("S1", "Large class", 30, 1, (), ("09:00",), 1)]
    result = solve_csp(rooms, sessions, SLOTS)
    assert result.schedule is None
    assert "No feasible" in result.message
