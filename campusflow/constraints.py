"""Hard-constraint checks shared by the scheduler and UI."""
from __future__ import annotations
from collections import defaultdict
from .models import Room, Session, Assignment


def slot_index(slots: list[str] | tuple[str, ...], slot: str) -> int:
    try:
        return list(slots).index(slot)
    except ValueError:
        return -1


def occupied_slots(start_slot: str, duration: int, ordered_slots: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    start = slot_index(ordered_slots, start_slot)
    if start < 0 or duration < 1 or start + duration > len(ordered_slots):
        return ()
    return tuple(ordered_slots[start:start + duration])


def candidate_is_valid(
    session: Session, room: Room, start_slot: str,
    rooms: list[Room], sessions: list[Session],
    schedule: dict[str, Assignment], slots: list[str] | tuple[str, ...],
    unavailable_rooms: set[str] | None = None,
) -> bool:
    unavailable_rooms = unavailable_rooms or set()
    occupied = occupied_slots(start_slot, session.duration, slots)
    if not occupied or start_slot not in session.allowed_start_slots:
        return False
    if room.id in unavailable_rooms or room.capacity < session.students:
        return False
    if not set(session.required_facilities).issubset(room.facilities):
        return False
    if not set(occupied).issubset(room.available_slots):
        return False

    sessions_by_id = {item.id: item for item in sessions}
    for other_id, other_assignment in schedule.items():
        if other_id == session.id:
            continue
        other_session = sessions_by_id.get(other_id)
        if other_session is None:
            continue
        other_occupied = set(occupied_slots(other_assignment.start_slot, other_session.duration, slots))
        if not other_occupied:
            return False
        if room.id == other_assignment.room_id and set(occupied).intersection(other_occupied):
            return False
        if set(occupied).intersection(other_occupied):
            # A class/session cannot be scheduled simultaneously with itself; distinct sessions may overlap.
            # This project models separate classes, so distinct sessions may share time if in different rooms.
            pass
    return True


def validate_schedule(
    rooms: list[Room], sessions: list[Session],
    schedule: dict[str, Assignment], slots: list[str] | tuple[str, ...],
    unavailable_rooms: set[str] | None = None,
) -> list[str]:
    """Return every detected hard-constraint violation; an empty list means valid."""
    unavailable_rooms = unavailable_rooms or set()
    issues: list[str] = []
    room_by_id = {room.id: room for room in rooms}
    session_by_id = {session.id: session for session in sessions}

    missing = set(session_by_id) - set(schedule)
    extra = set(schedule) - set(session_by_id)
    for sid in sorted(missing):
        issues.append(f"Session '{session_by_id[sid].name}' has no assignment.")
    for sid in sorted(extra):
        issues.append(f"Unknown session id '{sid}' appears in the schedule.")

    occupied_by_room: dict[tuple[str, str], str] = {}
    for sid, assignment in schedule.items():
        session = session_by_id.get(sid)
        room = room_by_id.get(assignment.room_id)
        if session is None:
            continue
        if room is None:
            issues.append(f"{session.name}: assigned room '{assignment.room_id}' does not exist.")
            continue
        if room.id in unavailable_rooms:
            issues.append(f"{session.name}: room {room.name} is unavailable.")
        if room.capacity < session.students:
            issues.append(f"{session.name}: {room.name} capacity ({room.capacity}) is below {session.students}.")
        missing_facilities = set(session.required_facilities) - set(room.facilities)
        if missing_facilities:
            issues.append(f"{session.name}: {room.name} lacks {', '.join(sorted(missing_facilities))}.")
        occupied = occupied_slots(assignment.start_slot, session.duration, slots)
        if not occupied:
            issues.append(f"{session.name}: invalid start slot or duration.")
            continue
        if assignment.start_slot not in session.allowed_start_slots:
            issues.append(f"{session.name}: start slot {assignment.start_slot} is not allowed.")
        unavailable_slots = set(occupied) - set(room.available_slots)
        if unavailable_slots:
            issues.append(f"{session.name}: {room.name} is unavailable during {', '.join(sorted(unavailable_slots))}.")
        for slot in occupied:
            key = (room.id, slot)
            if key in occupied_by_room:
                other = session_by_id[occupied_by_room[key]]
                issues.append(f"Room clash: {other.name} and {session.name} both use {room.name} at {slot}.")
            else:
                occupied_by_room[key] = sid
    return issues
