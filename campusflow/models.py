"""Typed domain models for CampusFlow AI."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class Room:
    id: str
    name: str
    capacity: int
    facilities: tuple[str, ...]
    available_slots: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Room":
        return cls(
            id=str(data["id"]), name=str(data["name"]),
            capacity=int(data["capacity"]),
            facilities=tuple(data.get("facilities", [])),
            available_slots=tuple(data.get("available_slots", [])),
        )


@dataclass(frozen=True)
class Session:
    id: str
    name: str
    students: int
    duration: int
    required_facilities: tuple[str, ...]
    allowed_start_slots: tuple[str, ...]
    priority: int = 1

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        return cls(
            id=str(data["id"]), name=str(data["name"]),
            students=int(data["students"]), duration=int(data["duration"]),
            required_facilities=tuple(data.get("required_facilities", [])),
            allowed_start_slots=tuple(data.get("allowed_start_slots", [])),
            priority=int(data.get("priority", 1)),
        )


@dataclass(frozen=True)
class Assignment:
    session_id: str
    room_id: str
    start_slot: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def records_to_rooms(records: list[dict[str, Any]]) -> list[Room]:
    return [Room.from_dict(row) for row in records]


def records_to_sessions(records: list[dict[str, Any]]) -> list[Session]:
    return [Session.from_dict(row) for row in records]


def schedule_to_dict(schedule: dict[str, Assignment]) -> dict[str, dict[str, str]]:
    return {sid: assignment.to_dict() for sid, assignment in schedule.items()}


def schedule_from_dict(data: dict[str, dict[str, str]]) -> dict[str, Assignment]:
    return {sid: Assignment(**row) for sid, row in data.items()}
