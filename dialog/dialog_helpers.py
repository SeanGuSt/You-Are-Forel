import re
def format_time_of_day(line, current_time):
    """Replace {time_of_day} placeholder with time-based greeting."""
    current_hour = current_time.hour
    if 4 <= current_hour < 12:
        return line.replace("{time_of_day}", "morning")
    elif 12 <= current_hour < 22:
        return line.replace("{time_of_day}", "afternoon")
    else:
        return line.replace("{time_of_day}", "evening")



def generate_elevator_text(elevator_config, current_map):
    """Return lines describing available destinations from current map."""
    destinations = elevator_config.get("destinations", {})
    entries = []

    for key, data in destinations.items():
        if data["map"] != current_map:
            entries.append(data["display"])

    if not entries:
        return ["We are already at your only destination."]

    if len(entries) == 1:
        joined = entries[0]
    else:
        *start, last = entries
        joined = ', '.join(start) + f", and {last}"

    return [
        f"And your destination? From here, I can take you to {joined}."
    ]

def get_destination_response(elevator_config, keyword, current_map):
    """Return travel lines and event for destination keyword."""
    dest_data = elevator_config["destinations"].get(keyword)
    if not dest_data:
        return {"text": elevator_config.get("refuse", ["I don't know where that is, kind Faithful."])}

    if dest_data["map"] != current_map:
        return {
            "text": elevator_config.get("confirm", ["Very well. Sit then, and *pray* with me."]),
            "events": {"new_args": {
                                        "target_map": dest_data["map"],
                                        "position": {
                                            "from_any": elevator_config["teleporters"]
                                        }
                                    }}
        }
    else:
        return {
            "text": elevator_config.get("already_here", ["We are already there, kind Faithful."])
        }