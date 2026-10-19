"""CampusFlow AI — Streamlit interface."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import streamlit as st

from campusflow.models import (
    records_to_rooms, records_to_sessions, schedule_to_dict, schedule_from_dict,
    Assignment,
)
from campusflow.constraints import occupied_slots, validate_schedule
from campusflow.scheduler import solve_csp
from campusflow.rescheduler import repair_schedule
from campusflow.sample_data import sample_records, SLOTS

st.set_page_config(page_title="CampusFlow AI", page_icon="🏫", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.8rem; padding-bottom: 3rem; max-width: 1450px;}
.hero {padding: 1.5rem 1.8rem; border-radius: 18px; background: linear-gradient(120deg,#102a43,#176b87); color: white; margin-bottom: 1.2rem;}
.hero h1 {color:white; margin:0; font-size:2.3rem;}
.hero p {color:#e3f4fb; margin:.45rem 0 0 0; font-size:1.05rem;}
.metric-card {border:1px solid #dbe4ea; border-radius:12px; padding:1rem;}
.small-muted {color:#64748b; font-size:.9rem;}
</style>
<div class="hero">
  <h1>🏫 CampusFlow AI</h1>
  <p>Conflict-aware classroom and laboratory scheduling · CSP · Backtracking · Minimum-change repair</p>
</div>
""", unsafe_allow_html=True)

def initialize():
    room_rows, session_rows = sample_records()
    st.session_state.setdefault("room_rows", room_rows)
    st.session_state.setdefault("session_rows", session_rows)
    st.session_state.setdefault("slots", list(SLOTS))
    st.session_state.setdefault("schedule", None)
    st.session_state.setdefault("last_generation", None)
    st.session_state.setdefault("outages", [])
    st.session_state.setdefault("repair_result", None)

initialize()

def current_models():
    return records_to_rooms(st.session_state.room_rows), records_to_sessions(st.session_state.session_rows), st.session_state.slots

def schedule_frame(schedule, rooms, sessions, slots):
    if schedule and isinstance(next(iter(schedule.values())), dict):
        schedule = schedule_from_dict(schedule)
    if not schedule:
        return pd.DataFrame(columns=["Session", "Students", "Room / Lab", "Start", "End", "Duration", "Priority"])
    room_by_id = {r.id:r for r in rooms}
    session_by_id = {s.id:s for s in sessions}
    rows = []
    for sid, a in schedule.items():
        s = session_by_id[sid]
        room = room_by_id.get(a.room_id)
        occ = occupied_slots(a.start_slot, s.duration, slots)
        end = slots[slots.index(occ[-1])+1] if occ and slots.index(occ[-1])+1 < len(slots) else ("End of day" if occ else "Invalid")
        rows.append({"Session":s.name, "Students":s.students, "Room / Lab":room.name if room else a.room_id,
                     "Start":a.start_slot, "End":end, "Duration":f"{s.duration} slot(s)", "Priority":s.priority,
                     "_session_id":sid, "_room_id":a.room_id})
    return pd.DataFrame(rows).sort_values(["Start","Room / Lab","Session"]).reset_index(drop=True)

def render_schedule(schedule, rooms, sessions, slots, key):
    frame = schedule_frame(schedule, rooms, sessions, slots)
    visible = frame.drop(columns=["_session_id","_room_id"], errors="ignore")
    st.dataframe(visible, use_container_width=True, hide_index=True, key=key)
    return frame

with st.sidebar:
    st.header("Control panel")
    st.caption("Use the sample dataset for a ready-to-run demonstration, or customize your own rooms and sessions.")
    if st.button("↻ Reset to sample data", use_container_width=True):
        room_rows, session_rows = sample_records()
        st.session_state.room_rows, st.session_state.session_rows = room_rows, session_rows
        st.session_state.slots = list(SLOTS)
        st.session_state.schedule = None
        st.session_state.last_generation = None
        st.session_state.outages = []
        st.session_state.repair_result = None
        st.rerun()
    if st.button("Clear generated timetable", use_container_width=True):
        st.session_state.schedule = None
        st.session_state.last_generation = None
        st.session_state.repair_result = None
    st.divider()
    st.subheader("Time slots")
    slot_text = st.text_input("Ordered slots (comma-separated)", value=", ".join(st.session_state.slots))
    if st.button("Apply time slots"):
        new_slots = [x.strip() for x in slot_text.split(",") if x.strip()]
        if not new_slots or len(new_slots) != len(set(new_slots)):
            st.error("Enter at least one unique time slot.")
        else:
            st.session_state.slots = new_slots
            # Keep only slot names that exist in the new list.
            for room in st.session_state.room_rows:
                room["available_slots"] = [s for s in room.get("available_slots", []) if s in new_slots]
            for session in st.session_state.session_rows:
                session["allowed_start_slots"] = [s for s in session.get("allowed_start_slots", []) if s in new_slots]
            st.session_state.schedule = None
            st.session_state.repair_result = None
            st.success("Slots updated. Generate a new timetable.")
            st.rerun()

rooms, sessions, slots = current_models()
overview = st.tabs(["Overview", "Rooms & labs", "Sessions", "Generate timetable", "Simulate disruption", "About the AI"])

with overview[0]:
    rooms, sessions, slots = current_models()
    a,b,c,d = st.columns(4)
    a.metric("Rooms / labs", len(rooms))
    b.metric("Sessions", len(sessions))
    c.metric("Time slots", len(slots))
    d.metric("Timetable status", "Generated" if st.session_state.schedule else "Not generated")
    st.subheader("Project at a glance")
    left, right = st.columns([1.2,1])
    with left:
        st.markdown("""
        **The problem:** assign every class or practical to a suitable room and start time without violating hard constraints.

        **The USP:** when a room becomes unavailable, repair the schedule while moving as few existing sessions as possible.

        **AI techniques:** Constraint Satisfaction Problem (CSP), backtracking search, minimum-remaining-values (MRV), least-constraining-value (LCV), and weighted repair cost.
        """)
        st.info("This is classical AI search and reasoning. No trained ML model or external AI API is required.")
    with right:
        st.markdown("#### Hard constraints")
        st.markdown("- No room double-booking\n- Sufficient room capacity\n- Required facilities available\n- Room open for every occupied slot\n- Valid duration and allowed start time")
        st.markdown("#### Soft objective")
        st.markdown("- Keep existing assignments where possible\n- Penalize moving higher-priority sessions more")
    st.subheader("Current timetable")
    if st.session_state.schedule:
        rooms, sessions, slots = current_models()
        render_schedule(st.session_state.schedule, rooms, sessions, slots, "overview_schedule")
        issues = validate_schedule(rooms, sessions, schedule_from_dict(st.session_state.schedule), slots, set(st.session_state.outages))
        if issues:
            st.error(f"{len(issues)} validation issue(s) detected.")
        else:
            st.success("All hard constraints are satisfied.")
    else:
        st.warning("No timetable generated yet. Open **Generate timetable** to start.")

with overview[1]:
    st.subheader("Manage rooms and labs")
    st.caption("Facilities are comma-separated labels, e.g. projector, computers, networking, electronics.")
    room_df = pd.DataFrame(st.session_state.room_rows)
    edited = st.data_editor(room_df, num_rows="dynamic", use_container_width=True, key="rooms_editor",
                            column_config={
                                "id": st.column_config.TextColumn("ID", required=True),
                                "name": st.column_config.TextColumn("Room / lab name", required=True),
                                "capacity": st.column_config.NumberColumn("Capacity", min_value=1, step=1, required=True),
                                "facilities": st.column_config.ListColumn("Facilities"),
                                "available_slots": st.column_config.ListColumn("Available slots"),
                            })
    if st.button("Save rooms", type="primary"):
        try:
            rows = edited.fillna("").to_dict("records")
            cleaned=[]
            for row in rows:
                if not str(row.get("id","")).strip() or not str(row.get("name","")).strip():
                    raise ValueError("Every room needs an ID and a name.")
                row["id"], row["name"] = str(row["id"]).strip(), str(row["name"]).strip()
                row["capacity"] = int(row["capacity"])
                if row["capacity"] < 1: raise ValueError("Room capacity must be positive.")
                for field in ("facilities","available_slots"):
                    value = row.get(field, [])
                    if isinstance(value, str): value = [x.strip() for x in value.split(",") if x.strip()]
                    row[field] = list(value or [])
                cleaned.append(row)
            if len({r["id"] for r in cleaned}) != len(cleaned): raise ValueError("Room IDs must be unique.")
            st.session_state.room_rows = cleaned
            st.session_state.schedule = None
            st.session_state.repair_result = None
            st.success("Rooms saved. Generate a fresh timetable to apply the changes.")
        except Exception as exc:
            st.error(str(exc))
    st.caption("Tip: each time slot is one consecutive teaching period. A room must list every slot occupied by a session.")

with overview[2]:
    st.subheader("Manage teaching sessions")
    session_df = pd.DataFrame(st.session_state.session_rows)
    edited_sessions = st.data_editor(session_df, num_rows="dynamic", use_container_width=True, key="sessions_editor",
        column_config={
            "id": st.column_config.TextColumn("ID", required=True),
            "name": st.column_config.TextColumn("Session name", required=True),
            "students": st.column_config.NumberColumn("Students", min_value=1, step=1, required=True),
            "duration": st.column_config.NumberColumn("Duration (slots)", min_value=1, step=1, required=True),
            "required_facilities": st.column_config.ListColumn("Required facilities"),
            "allowed_start_slots": st.column_config.ListColumn("Allowed start slots"),
            "priority": st.column_config.NumberColumn("Priority (1–5)", min_value=1, max_value=5, step=1),
        })
    if st.button("Save sessions", type="primary"):
        try:
            rows = edited_sessions.fillna("").to_dict("records")
            cleaned=[]
            for row in rows:
                if not str(row.get("id","")).strip() or not str(row.get("name","")).strip():
                    raise ValueError("Every session needs an ID and a name.")
                row["id"], row["name"] = str(row["id"]).strip(), str(row["name"]).strip()
                for field in ("students","duration","priority"):
                    row[field] = int(row[field])
                if row["students"] < 1 or row["duration"] < 1: raise ValueError("Students and duration must be positive.")
                if not 1 <= row["priority"] <= 5: raise ValueError("Priority must be between 1 and 5.")
                for field in ("required_facilities","allowed_start_slots"):
                    value = row.get(field, [])
                    if isinstance(value, str): value = [x.strip() for x in value.split(",") if x.strip()]
                    row[field] = list(value or [])
                cleaned.append(row)
            if len({s["id"] for s in cleaned}) != len(cleaned): raise ValueError("Session IDs must be unique.")
            st.session_state.session_rows = cleaned
            st.session_state.schedule = None
            st.session_state.repair_result = None
            st.success("Sessions saved. Generate a fresh timetable to apply the changes.")
        except Exception as exc:
            st.error(str(exc))
    st.caption("Priority is a soft preference used only when choosing which sessions to move during repair. Hard constraints are never relaxed.")

with overview[3]:
    st.subheader("Generate a valid timetable")
    st.write("The engine models each session as a CSP variable and each feasible room/start-time pair as a domain value.")
    node_limit = st.number_input("Search node limit", min_value=1000, max_value=2_000_000, value=250_000, step=1000, key="gen_node_limit")
    if st.button("🧠 Generate timetable", type="primary", use_container_width=False):
        rooms, sessions, slots = current_models()
        if not rooms or not sessions:
            st.error("Add at least one room and one session first.")
        else:
            with st.spinner("Searching for a valid allocation..."):
                result = solve_csp(rooms, sessions, slots, set(st.session_state.outages), int(node_limit))
            st.session_state.last_generation = {"nodes":result.nodes, "complete":result.complete, "message":result.message}
            if result.schedule is None:
                st.session_state.schedule = None
                st.error(result.message)
            else:
                st.session_state.schedule = schedule_to_dict(result.schedule)
                st.session_state.repair_result = None
                st.success(f"{result.message} Search nodes explored: {result.nodes:,}.")
                st.rerun()
    if st.session_state.last_generation:
        st.caption(f"Last search: {st.session_state.last_generation['nodes']:,} nodes · {st.session_state.last_generation['message']}")
    if st.session_state.schedule:
        rooms, sessions, slots = current_models()
        schedule = st.session_state.schedule
        issues = validate_schedule(rooms, sessions, schedule_from_dict(schedule), slots, set(st.session_state.outages))
        if issues: st.error("\\n".join(issues))
        else: st.success("Independent validator confirms that all hard constraints are satisfied.")
        frame = render_schedule(schedule, rooms, sessions, slots, "generated_schedule")
        csv = frame.drop(columns=["_session_id","_room_id"], errors="ignore").to_csv(index=False).encode("utf-8")
        st.download_button("⬇ Export timetable as CSV", csv, "campusflow_timetable.csv", "text/csv")
        with st.expander("Show raw assignment data"):
            st.json(schedule)

with overview[4]:
    st.subheader("Simulate a room outage and repair the timetable")
    if not st.session_state.schedule:
        st.warning("Generate an initial timetable first.")
    else:
        rooms, sessions, slots = current_models()
        room_options = {r.name:r.id for r in rooms}
        current_outages = set(st.session_state.outages)
        available_choices = [name for name, rid in room_options.items() if rid not in current_outages]
        if available_choices:
            selected_name = st.selectbox("Room that suddenly becomes unavailable", available_choices)
            selected_id = room_options[selected_name]
            repair_limit = st.number_input("Repair search node limit", min_value=1000, max_value=2_000_000, value=250_000, step=1000, key="repair_node_limit")
            st.caption("The outage is treated as a hard constraint. The repair engine never trades validity for a lower change cost.")
            if st.button("⚡ Apply outage and repair timetable", type="primary"):
                outage_set = current_outages | {selected_id}
                old = schedule_from_dict(st.session_state.schedule)
                st.session_state.pre_repair_schedule = dict(st.session_state.schedule)
                with st.spinner("Searching for the lowest-cost valid repair..."):
                    result = repair_schedule(rooms, sessions, slots, old, outage_set, int(repair_limit))
                st.session_state.outages = sorted(outage_set)
                st.session_state.repair_result = {
                    "schedule": schedule_to_dict(result.schedule) if result.schedule else None,
                    "cost": result.cost, "moved_sessions": result.moved_sessions, "nodes": result.nodes,
                    "optimality_proven": result.optimality_proven, "message": result.message,
                    "outage_name": selected_name,
                }
                if result.schedule:
                    st.session_state.schedule = schedule_to_dict(result.schedule)
                st.rerun()
        if st.session_state.outages:
            outage_names = [r.name for r in rooms if r.id in set(st.session_state.outages)]
            st.warning("Currently unavailable: " + ", ".join(outage_names))
            if st.button("Restore all rooms and keep current timetable"):
                st.session_state.outages = []
                st.session_state.repair_result = None
                st.session_state.schedule = None
                st.info("Rooms restored. Generate a fresh timetable.")
                st.rerun()
        rr = st.session_state.repair_result
        if rr:
            st.divider()
            if rr["schedule"]:
                m1,m2,m3 = st.columns(3)
                m1.metric("Sessions moved", len(rr["moved_sessions"]))
                m2.metric("Repair cost", rr["cost"])
                m3.metric("Search nodes", f'{rr["nodes"]:,}')
                st.success(rr["message"])
                st.subheader("Before vs. after")
                before = st.session_state.get("pre_repair_schedule")
                # Reconstruct old schedule for comparison from the last saved snapshot if available.
                if before:
                    st.markdown("**Before**")
                    render_schedule(schedule_from_dict(before), rooms, sessions, slots, "before_repair")
                st.markdown("**Current repaired timetable**")
                render_schedule(schedule_from_dict(rr["schedule"]), rooms, sessions, slots, "after_repair")
                st.markdown("**Change explanation**")
                if rr["moved_sessions"]:
                    for name in rr["moved_sessions"]:
                        by_name = {s.name: s for s in sessions}
                        moved_session = by_name[name]
                        sid = moved_session.id
                        old_map = schedule_from_dict(st.session_state.pre_repair_schedule) if st.session_state.get("pre_repair_schedule") else {}
                        new_map = schedule_from_dict(rr["schedule"])
                        old_a, new_a = old_map.get(sid), new_map.get(sid)
                        room_names = {r.id: r.name for r in rooms}
                        if old_a and new_a:
                            st.markdown(f"- **{name}:** {room_names.get(old_a.room_id, old_a.room_id)} at {old_a.start_slot} → {room_names.get(new_a.room_id, new_a.room_id)} at {new_a.start_slot}. The original allocation conflicted with the outage or a lower-cost valid repair required this move.")
                        else:
                            st.markdown(f"- **{name}** was reassigned to preserve all hard constraints.")
                else:
                    st.markdown("- No session assignment needed to change.")
                st.caption("Repair cost penalizes every moved session, with larger penalties for higher-priority sessions and smaller additional penalties for room/time changes.")
            else:
                st.error(rr["message"])
                st.caption("The system did not replace the timetable with an invalid result.")

with overview[5]:
    st.subheader("How the AI engine works")
    st.markdown("""
    1. **Model the CSP:** every session is a variable; its domain contains room/start-time options that satisfy individual room rules.
    2. **Apply hard constraints:** capacity, facilities, availability, allowed start slots, duration, and room overlap.
    3. **Backtrack:** assign a session, detect conflicts, and undo choices that block the remaining sessions.
    4. **MRV heuristic:** pick the unassigned session with the fewest currently legal options.
    5. **LCV heuristic:** try the option expected to preserve the most choices for other sessions.
    6. **Repair optimization:** after an outage, search for a valid schedule and minimize weighted assignment changes.
    7. **Validate independently:** the final timetable is checked again before it is accepted.
    """)
    st.markdown("#### Objective function")
    st.code("unchanged assignment = 0\\nmoved session = 10 × priority\\n+ 5 if its start time changes\\n+ 2 if its room changes", language="text")
    st.markdown("#### Syllabus connection")
    st.markdown("- **Search techniques:** backtracking and heuristics.\n- **Constraint Satisfaction Problems:** variables, domains, and constraints.\n- **Optimization:** compare valid repairs by their change cost.")
    st.caption("A search limit can stop the optimizer before it proves global optimality. The app reports this distinction explicitly.")
