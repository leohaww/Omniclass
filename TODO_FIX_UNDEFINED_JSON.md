# Fix: TypeError 'Undefined is not JSON serializable' on /lecturer/courses

## What’s happening
Jinja `|tojson` fails when any schedule dict contains a value of type `Undefined` (Jinja “missing” value) rather than a real JSON-serializable value.

## Implemented change (already applied)
- Updated template `templates/lecturer/courses.html` edit-button schedules JSON expression to wrap with `|default([])`.

## Next changes required (codebase)
1. Define a JSON-safe method for Schedule objects in `db.py` (e.g. `Schedule.to_dict()` should return only plain Python types; replace any missing/None/Undefined with a safe fallback like empty string or 0).
2. Ensure schedule dict does not contain Jinja Undefined values.
3. (Optional) add a helper in Flask/Jinja like `safe_primitive(x)` and use it in the dict building.

## How to verify
- Reload: `http://192.168.1.25:5000/lecturer/courses`
- Click Edit on a course that previously broke the page.
- Confirm no server-side TypeError.

