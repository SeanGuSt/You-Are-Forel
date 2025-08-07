import json
from typing import Dict, List, Optional, Tuple, Any
from constants import Direction
from dataclasses import dataclass
from datetime import datetime, timedelta
import math

@dataclass
class ScheduleEvent:
    """Represents a single scheduled event for an NPC"""
    time_minutes: int  # Time in minutes from start of schedule cycle
    action: str
    target: Optional[str] = None
    patrol_node_template: Optional[str] = None
    start_node: Optional[str] = None
    max_node: Optional[int] = None
    repeat_interval: Optional[int] = None  # Minutes between repetitions (for repeating actions)
    repeat_count_current: Optional[int] = 0
    repeat_count: Optional[int] = None  # How many times to repeat (None = infinite)
    direction: Optional[Direction] = None
    is_dynamic: bool = False
    
class ScheduleManager:
    """
    Manages NPC schedules for a turn-based tile game with variable turn durations.
    
    Features:
    - Daily or multi-day schedule cycles
    - Variable turn durations
    - Schedule overrides for special events
    - Calculate NPC positions based on elapsed time and movement speed
    """
    
    def __init__(self, engine):
        self.schedules: Dict[str, List[ScheduleEvent]] = {}
        self.engine = engine
        self.schedule_cycles: Dict[str, int] = {}  # How many days each NPC's schedule spans
        self.overrides: Dict[str, Dict[str, List[ScheduleEvent]]] = {}  # date -> npc -> events
        self.game_start_time: datetime = datetime(1574, 1, 1, 0, 0, 0)
        self.last_game_time: datetime = self.game_start_time
        self.current_game_time: datetime = self.game_start_time
        self.turn_history: List[int] = []  # List of turn durations in minutes
        self.load_schedules_from_json()
        
    def load_schedules_from_json(self):
        """
        Load NPC schedules from JSON format.
        
        Time format supports:
        - "HH:MM" for daily schedules (e.g., "07:00")
        - "DD:HH:MM" for multi-day schedules (e.g., "31:00" = day 2, hour 7)
        """
        try:
            with open("schedule.json", 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"Warning: {"schedule.json"} not found. Using empty schedules.")
            return {}
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {"schedule.json"}. Using empty schedules.")
            return {}
        
        for npc_name, schedule_data in data.items():
            events = []
            max_time = 0
            
            for time_str, event_data in schedule_data.items():
                time_minutes = self._parse_time_string(time_str)
                max_time = max(max_time, time_minutes)
                
                event = ScheduleEvent(
                    time_minutes=time_minutes,
                    action=event_data.get("action"),
                    target=event_data.get("target"),
                    patrol_node_template=event_data.get("patrol_node_template"),
                    start_node=event_data.get("start_node"),
                    max_node=event_data.get("max_node"),
                    repeat_interval=event_data.get("repeat_interval"),
                    repeat_count=event_data.get("repeat_count"),
                    direction=self.engine.get_direction(event_data.get("direction"))
                )
                events.append(event)
            
            # Sort events by time
            events.sort(key=lambda x: x.time_minutes)
            self.schedules[npc_name] = events
            
            # Determine schedule cycle length (in days)
            if max_time >= 1440:  # More than 24 hours
                self.schedule_cycles[npc_name] = math.ceil(max_time / 1440)
            else:
                self.schedule_cycles[npc_name] = 1

    def _parse_time_string(self, time_str: str) -> int:
        """Parse time string to minutes from schedule start."""
        parts = time_str.split(":")
        
        if len(parts) == 2:  # "HH:MM" format (daily)
            hours, minutes = map(int, parts)
            return hours * 60 + minutes
        elif len(parts) == 3:  # Assume "DD:HH:MM" format (multi-day)
            days, hours, minutes = map(int, parts)
            return (days * 24 + hours) * 60 + minutes
        else:
            # Handle cases like "31:00" as "day:hour"
            if int(parts[0]) >= 24:
                days = int(parts[0]) // 24
                hours = int(parts[0]) % 24
                minutes = int(parts[1])
                return (days * 24 + hours) * 60 + minutes
            else:
                hours, minutes = map(int, parts)
                return hours * 60 + minutes
    
    def add_schedule_override(self, date: str, npc_name: str, schedule_data: Dict):
        """
        Add a schedule override for a specific date.
        
        Args:
            date: Date string in "YYYY-MM-DD" format
            npc_name: Name of the NPC
            schedule_data: Schedule data in the same format as JSON schedules
        """
        if date not in self.overrides:
            self.overrides[date] = {}
        
        events = []
        for time_str, event_data in schedule_data.items():
            time_minutes = self._parse_time_string(time_str)
            event = ScheduleEvent(
                    time_minutes=time_minutes,
                    action=event_data.get("action"),
                    target=event_data.get("target"),
                    patrol_node_template=event_data.get("patrol_node_template"),
                    start_node=event_data.get("start_node"),
                    max_node=event_data.get("max_node"),
                    repeat_interval=event_data.get("repeat_interval"),
                    repeat_count=event_data.get("repeat_count"),
                    direction=Direction(event_data.get("direction"))
                )
            events.append(event)
        
        events.sort(key=lambda x: x.time_minutes)
        self.overrides[date][npc_name] = events

    def add_dynamic_schedule_event(self, npc_name: str, minutes_from_now: int, event_data: Dict):
        """
        Add a schedule event that triggers X minutes from the current game time.
        
        Args:
            npc_name: Name of the NPC
            minutes_from_now: How many minutes from now the event should trigger
            event_data: Event data (action, target, etc.)
        """
        # Calculate the target time within the current schedule cycle
        total_minutes = int((self.current_game_time - self.game_start_time).total_seconds() / 60)
        cycle_length = self.schedule_cycles.get(npc_name, 1) * 1440  # days to minutes
        
        target_time = (total_minutes + minutes_from_now) % cycle_length
        
        # Create the new event
        new_event = ScheduleEvent(
            time_minutes=target_time,
            action=event_data.get("action", "go_to"),
            target=event_data.get("target"),
            patrol_node_template=event_data.get("patrol_node_template"),
            start_node=event_data.get("start_node"),
            max_node=event_data.get("max_node"),
            repeat_interval=event_data.get("repeat_interval"),
            repeat_count=event_data.get("repeat_count"),
            direction=event_data.get("direction"),
            is_dynamic = True
        )
        
        # Add to the NPC's schedule and re-sort
        if npc_name not in self.schedules:
            self.schedules[npc_name] = []
            self.schedule_cycles[npc_name] = 1
            
        self.schedules[npc_name].append(new_event)
        self.schedules[npc_name].sort(key=lambda x: x.time_minutes)
    
    def advance_time(self, turn_duration_minutes: int):
        """Advance the game time by the specified number of minutes."""
        self.turn_history.append(turn_duration_minutes)
        self.current_game_time += timedelta(minutes=turn_duration_minutes)

    
    def get_current_schedule_time(self, npc_name: str) -> int:
        """Get the current time within the NPC's schedule cycle in minutes."""
        if npc_name not in self.schedules:
            return 0
        
        cycle_length_minutes = self.schedule_cycles[npc_name] * 1440  # days to minutes
        total_minutes = int((self.current_game_time - self.game_start_time).total_seconds() / 60)
        return total_minutes % cycle_length_minutes
    
    def get_active_schedule_events(self, npc_name: str) -> List[ScheduleEvent]:
        """Get the schedule events for the current day, including overrides."""
        current_date = self.current_game_time.strftime("%Y-%m-%d")
        
        # Check for overrides first
        if current_date in self.overrides and npc_name in self.overrides[current_date]:
            return self.overrides[current_date][npc_name]
        
        # Return regular schedule
        return self.schedules.get(npc_name, [])
    
    def get_current_event(self, npc_name: str) -> Optional[ScheduleEvent]:
        """Get the currently active event for an NPC."""
        events = self.get_active_schedule_events(npc_name)
        if not events:
            return None
        
        current_time = self.get_current_schedule_time(npc_name)
        # Find the most recent event that should have started
        active_event = None
        for event in events:
            if event.time_minutes <= current_time:
                active_event = event
            else:
                break
        
        return active_event
    
    def get_turns_since_event_start(self, npc_name: str, event: ScheduleEvent) -> int:
        """
        Calculate how many turns have passed since the given event started.
        
        Returns:
            Number of turns that have passed since the event began
        """
        current_time = self.get_current_schedule_time(npc_name)
        
        if current_time < event.time_minutes:
            return 0
        
        minutes_since_event = current_time - event.time_minutes
        
        # Convert minutes to turns by working backwards through turn history
        turns_passed = 0
        minutes_accounted = 0
        
        # Start from the most recent turn and work backwards
        for turn_duration in reversed(self.turn_history):
            if minutes_accounted + turn_duration <= minutes_since_event:
                minutes_accounted += turn_duration
                turns_passed += 1
            else:
                # This turn would exceed the time since event, so we're done
                break
        
        return turns_passed
    
    def calculate_npc_movement_turns(self, npc_name: str, move_interval_minutes: float) -> int:
        """
        Calculate how many movement turns an NPC should have taken based on their current event.
        
        Args:
            npc_name: Name of the NPC
            move_interval_minutes: Minutes required for NPC to move one tile
            
        Returns:
            Number of tiles the NPC should have moved since their current event started
        """
        current_event = self.get_current_event(npc_name)
        if not current_event or move_interval_minutes <= 0:
            return 0
        
        turns_since_start = self.get_turns_since_event_start(npc_name, current_event)
        
        # Calculate total minutes that have passed in those turns
        total_minutes = 0
        turn_count = 0
        
        for turn_duration in reversed(self.turn_history):
            if turn_count >= turns_since_start:
                break
            total_minutes += turn_duration
            turn_count += 1
        
        # Calculate how many movement intervals have completed
        movement_turns = total_minutes // move_interval_minutes
        return movement_turns
    
    def should_execute_repeating_action(self, npc_name: str, event: ScheduleEvent) -> bool:
        """
        Check if a repeating action should be executed this turn.
        
        Returns True if enough time has passed since the last execution
        of this repeating action.
        """
        if not event.repeat_interval:
            return False  # Not a repeating action
        
        current_time = self.get_current_schedule_time(npc_name)
        
        # Calculate how much time has passed since the event started
        if current_time < event.time_minutes:
            return False
        
        time_since_start = current_time - event.time_minutes

        next_execute_time = event.repeat_interval * (event.repeat_count_current + 1)
        return time_since_start >= next_execute_time
    
    def get_repeat_execution_count(self, npc_name: str, event: ScheduleEvent) -> int:
        """
        Get how many times a repeating action should have been executed by now.
        """
        if not event.repeat_interval:
            return 0
        
        current_time = self.get_current_schedule_time(npc_name)
        
        if current_time < event.time_minutes:
            return 0
        
        time_since_start = current_time - event.time_minutes
        times_executed = (time_since_start // event.repeat_interval) + 1  # +1 for initial execution
        
        # Respect repeat_count limit if set
        if event.repeat_count is not None:
            times_executed = min(times_executed, event.repeat_count)
        
        return times_executed
    
    def get_npc_schedule_status(self, npc_name: str, move_interval_minutes: float) -> Dict[str, Any]:
        """
        Get comprehensive status information for an NPC's schedule.
        
        Returns a dictionary with:
        - current_event: The active schedule event
        - turns_since_event: Turns passed since event started  
        - movement_turns: Number of tiles NPC should have moved
        - schedule_time: Current time within schedule cycle
        """
        current_event = self.get_current_event(npc_name)
        
        current_event = self.get_current_event(npc_name)
        
        if not current_event:
            return {
                "current_event": None,
                "turns_since_event": 0,
                "movement_turns": 0,
                "schedule_time": self.get_current_schedule_time(npc_name),
                "should_repeat": False,
                "repeat_count": 0
            }
        
        turns_since_event = self.get_turns_since_event_start(npc_name, current_event)
        movement_turns = self.calculate_npc_movement_turns(npc_name, move_interval_minutes)
        should_repeat = self.should_execute_repeating_action(npc_name, current_event)
        repeat_count = self.get_repeat_execution_count(npc_name, current_event)
        
        return {
            "current_event": current_event,
            "turns_since_event": turns_since_event,
            "movement_turns": movement_turns,
            "schedule_time": self.get_current_schedule_time(npc_name),
            "should_repeat": should_repeat,
            "repeat_count": repeat_count
        }
    
    def process_map_load(self, npc_data: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
        """
        Process all NPCs when loading a map to determine their current schedule status.
        
        Args:
            npc_data: Dictionary mapping NPC names to their move_interval_minutes
            
        Returns:
            Dictionary mapping NPC names to their schedule status
        """
        results = {}
        
        for npc_name, move_interval in npc_data.items():
            results[npc_name] = self.get_npc_schedule_status(npc_name, move_interval)
        
        return results