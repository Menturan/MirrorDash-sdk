"""What `validate` reports about in a module's config_schema.json settings: the mistakes the admin page passes
over in silence: a misspelt keyword or format, an enum shown without words, a show_if naming no setting,
a setting without a default, "shared" where the core ignores it."""

import re

# Every keyword the admin page reads in a setting (MirrorDash 0.14): JSON Schema's own and ours
KEYWORDS = {"type", "default", "title", "description", "enum", "enum_titles", "enumNames", "format", "items",
            "properties", "required", "minimum", "maximum", "minLength", "maxLength", "pattern", "pattern_message",
            "step", "uniqueItems", "show_if", "group", "accept", "max_files", "shared", "help", "copy_value", "unit", "min_label"}
UNITS = {"s", "min", "h", "%"}  # "unit": the suffix after a number box or slider (value stays a number)
FORMATS = {"password", "lan-url", "icon", "color", "textarea", "time", "slider", "files", "list", "search", "fields"}
# The core adds these to every module's settings form; a module redeclaring them is ignored
CORE_FIELDS = ["instance_name", "enabled", "position", "carousel_group", "carousel_interval", "show_in_privacy",
               "schedule"]
# Core settings a module may declare only to give its own default (a wide module: width_percent 60; radio: no heading)
STANDARD_DEFAULT_KEYS = ["show_header", "heading", "width_percent", "height_percent", "opacity_percent"]
STANDARD_DEFAULT_ALLOWED = {"default", "type", "title", "description"}
# Core settings that no longer exist, and what replaced them
REMOVED_CORE_KEYS = {
    "max_width": "use the core's width_percent (the owner sets it; a module may give a default)",
    "max_height": "use the core's height_percent (the owner sets it; a module may give a default)",
    "z_index": "stacking follows the module order, there is no layer setting",
    "opacity": "use the core's opacity_percent",
}
# "(Seconds)", "(s)", "(%)", "(px)" at the end of a title: the unit belongs in "unit"
TITLE_UNIT = re.compile(r"\(\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?|ms|s|h|%|px|percent)\s*\)", re.IGNORECASE)
# "shared": true (MirrorDash 0.19) works on a single value at the top level, and on none of these
SHAREABLE_TYPES = {"string", "integer", "number", "boolean"}
NOT_SHAREABLE_FORMATS = {"files", "list", "search", "fields"}
NEEDS_NO_DEFAULT = {"files", "list", "search", "fields"}  # files live in the cache folder; a choice or fields arrive as {}


def schema_errors(properties: dict, path: str = "") -> list[str]:
    """One line per thing that breaks the module's settings (the admin page or the core would act on it wrongly)."""
    errors = []
    for key, prop in properties.items():
        name = f"{path}{key}"
        if not isinstance(prop, dict):
            continue
        if not path and key in REMOVED_CORE_KEYS:
            errors.append(f"{name}: the core no longer has this setting; {REMOVED_CORE_KEYS[key]}. Remove it")
        if "unit" in prop and prop["unit"] not in UNITS:
            errors.append(f"{name}: unit must be one of {sorted(UNITS)}, not {prop['unit']!r}")
        if isinstance(prop.get("properties"), dict):
            errors += schema_errors(prop["properties"], f"{name}.")
        items = prop.get("items")
        if isinstance(items, dict) and isinstance(items.get("properties"), dict):
            errors += schema_errors(items["properties"], f"{name}[].")
    return errors


def schema_warnings(properties: dict, path: str = "", in_list: bool = False) -> list[str]:
    """One line per thing to fix in these settings (and the settings in their nested objects and lists).
    in_list: a list item's fields, which start empty in a new item, so they need no default."""
    warnings = []
    for key, prop in properties.items():
        name = f"{path}{key}"
        if not isinstance(prop, dict):
            warnings.append(f"{name}: a setting must be an object")
            continue
        if unknown := sorted(set(prop) - KEYWORDS):
            warnings.append(f"{name}: unknown keyword(s) {unknown}, ignored by the admin page (a typo?)")
        fmt = prop.get("format")
        if fmt is not None and fmt not in FORMATS:
            warnings.append(f"{name}: unknown format {fmt!r}; known: {sorted(FORMATS)}")
        if prop.get("enum") and not (prop.get("enum_titles") or prop.get("enumNames")):
            warnings.append(f"{name}: an enum without enum_titles shows its raw values; add the words people read")
        if fmt == "slider" and not ("minimum" in prop and "maximum" in prop):
            warnings.append(f"{name}: format slider needs a minimum and a maximum")
        if not in_list and "default" not in prop and fmt not in NEEDS_NO_DEFAULT and prop.get("type") not in ("object", None):
            warnings.append(f"{name}: no default, so config may lack it; give it one")
        if "shared" in prop and (problem := _shared_problem(key, prop, path, in_list)):
            warnings.append(f"{name}: \"shared\" is ignored by the mirror: {problem}")
        show_if = prop.get("show_if")
        if show_if is not None and (not isinstance(show_if, dict) or any(other not in properties for other in show_if)):
            warnings.append(f"{name}: show_if must name settings beside it: {{\"source\": [\"immich\"]}}")
        elif isinstance(show_if, dict) and (problem := _show_if_problem(show_if)):
            warnings.append(f"{name}: show_if {problem}")
        if "min_label" in prop and (fmt != "slider" or not isinstance(prop["min_label"], str)):
            warnings.append(f"{name}: min_label is a text for a slider's minimum; it needs \"format\": \"slider\"")
        if not path and key in STANDARD_DEFAULT_KEYS and (extra := sorted(set(prop) - STANDARD_DEFAULT_ALLOWED)):
            warnings.append(f"{name}: a core setting; declare it only to give your default (default, type, title, "
                            f"description). {extra} is ignored")
        if isinstance(prop.get("title"), str) and TITLE_UNIT.search(prop["title"]):
            warnings.append(f"{name}: the title holds a unit in parentheses; drop it and add \"unit\" "
                            f"({', '.join(sorted(UNITS))}), or say it in the description")
        if prop.get("type") == "array" and isinstance(prop.get("items"), dict) and prop["items"].get("properties") \
                and not prop["items"].get("title"):
            warnings.append(f"{name}: add items.title (\"Station\"): the add button would say \"Add Item\"")
        if isinstance(prop.get("properties"), dict):
            warnings += schema_warnings(prop["properties"], f"{name}.")
        items = prop.get("items")
        if isinstance(items, dict) and isinstance(items.get("properties"), dict):
            warnings += schema_warnings(items["properties"], f"{name}[].", in_list=True)
    warnings += _single_field_groups(properties, path)
    return warnings


def _single_field_groups(properties: dict, path: str) -> list[str]:
    """A group holding one field is a section with nothing to fold away: drop the group."""
    groups: dict[str, list[str]] = {}
    for key, prop in properties.items():
        if isinstance(prop, dict) and isinstance(prop.get("group"), str):
            groups.setdefault(prop["group"], []).append(key)
    return [f"{path}{keys[0]}: the group {group!r} holds only this setting; drop \"group\" (it is a section of one)"
            for group, keys in groups.items() if len(keys) == 1]


def _show_if_problem(show_if: dict) -> str | None:
    """Why a show_if value is neither a list of values nor {"not": [values]} (None when fine)."""
    for source, value in show_if.items():
        if isinstance(value, dict) and (set(value) != {"not"} or not isinstance(value["not"], list)):
            return f"on {source!r}: write a list of values, or {{\"not\": [values]}}"
    return None


def _shared_problem(key: str, prop: dict, path: str, in_list: bool) -> str | None:
    """Why "shared": true does nothing on this setting (None when it works): the core takes it only on a
    top-level single value that isn't one of its own fields."""
    if prop["shared"] is not True:
        return "write it as true"
    if path or in_list:
        return "only a top-level setting can be shared, not one in a list or an object"
    if key in CORE_FIELDS or key in STANDARD_DEFAULT_KEYS:
        return "the core's own settings can't be shared"
    if prop.get("format") in NOT_SHAREABLE_FORMATS:
        return f"a {prop['format']} setting can't be shared"
    if prop.get("type") not in SHAREABLE_TYPES:
        return "only a text, a number or a switch (or a dropdown of them) can be shared, not a list or an object"
    return None
