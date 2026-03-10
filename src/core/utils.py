"""Calendar utility functions for the missionary lunch calendar application."""
from datetime import date


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MAX_DISPLAY_WEEKS = 6
MAX_OCCURRENCES = 5
MAX_SLOTS = 2


def get_cell_names(entries, occurrence, day_of_week):
    """Return the first and second slot names for a calendar cell."""
    if not occurrence:
        return {"first": "", "second": ""}

    base_key = f"{occurrence}:{day_of_week}"
    first = entries.get(f"{base_key}:1", "")
    second = entries.get(f"{base_key}:2", "")

    # Backward compatibility for old single-value data.
    if not first and not second:
        first = entries.get(base_key, "")

    return {"first": first, "second": second}


def build_day_lookup(year, month):
    """Build a mapping of (week_number, day_name) to day metadata for a month."""
    day_lookup = {}
    week_number = 1
    day = 1
    occurrence_by_day = {day_name: 0 for day_name in DAYS}

    while True:
        try:
            current = date(year, month, day)
        except ValueError:
            break

        day_name = DAYS[current.weekday()]
        occurrence_by_day[day_name] += 1
        day_lookup[(week_number, day_name)] = {
            "day_number": day,
            "occurrence": occurrence_by_day[day_name],
        }

        if day_name == "Sunday":
            week_number += 1
        day += 1

    return day_lookup


def build_calendar_payload(year, month, entries):
    """Construct the full calendar JSON payload for the given month."""
    day_lookup = build_day_lookup(year, month)
    weeks = []
    for week_number in range(1, MAX_DISPLAY_WEEKS + 1):
        cells = []
        for day_name in DAYS:
            day_data = day_lookup.get((week_number, day_name))
            day_number = day_data["day_number"] if day_data else None
            occurrence = day_data["occurrence"] if day_data else None
            if day_name == "Monday":
                names = {"first": "PDAY", "second": ""}
                editable = False
            else:
                names = get_cell_names(entries, occurrence, day_name)
                editable = True

            cells.append(
                {
                    "week_number": week_number,
                    "day_of_week": day_name,
                    "day_number": day_number,
                    "occurrence": occurrence,
                    "name": names["first"],
                    "names": names,
                    "editable": editable,
                }
            )

        weeks.append({"week_number": week_number, "cells": cells})

    return {
        "status": "ok",
        "month": month,
        "year": year,
        "weeks": weeks,
    }
