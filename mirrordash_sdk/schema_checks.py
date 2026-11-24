"""What `validate` warns about in a module's config_schema.json settings: the mistakes the admin page passes
over in silence: a misspelt keyword or format, an enum shown without words, a show_if naming no setting,
a setting without a default, "shared" where the core ignores it."""

# Every keyword the admin page reads in a setting (MirrorDash 0.14): JSON Schema's own and ours
KEYWORDS = {"type", "default", "title", "description", "enum", "enum_titles", "enumNames", "format", "items",
            "properties", "required", "minimum", "maximum", "minLength", "maxLength", "pattern", "pattern_message",
            "step", "uniqueItems", "show_if", "group", "accept", "max_files", "shared", "help"}
FORMATS = {"password", "lan-url", "icon", "color", "textarea", "time", "slider", "files", "list", "search", "fields"}
# The core adds these to every module's settings form; a module redeclaring them is ignored
CORE_FIELDS = ["instance_name", "enabled", "position", "carousel_group", "carousel_interval", "max_width", "max_height",
               "z_index", "opacity", "show_in_privacy", "schedule"]
# "shared": true (MirrorDash 0.19) works on a single value at the top level, and on none of these
SHAREABLE_TYPES = {"string", "integer", "number", "boolean"}
NOT_SHAREABLE_FORMATS = {"files", "list", "search", "fields"}
NEEDS_NO_DEFAULT = {"files", "list", "search", "fields"}  # files live in the cache folder; a choice or fields arrive as {}


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
        if isinstance(prop.get("properties"), dict):
            warnings += schema_warnings(prop["properties"], f"{name}.")
        items = prop.get("items")
        if isinstance(items, dict) and isinstance(items.get("properties"), dict):
            warnings += schema_warnings(items["properties"], f"{name}[].", in_list=True)
    return warnings


def _shared_problem(key: str, prop: dict, path: str, in_list: bool) -> str | None:
    """Why "shared": true does nothing on this setting (None when it works): the core takes it only on a
    top-level single value that isn't one of its own fields."""
    if prop["shared"] is not True:
        return "write it as true"
    if path or in_list:
        return "only a top-level setting can be shared, not one in a list or an object"
    if key in CORE_FIELDS:
        return "the core's own settings can't be shared"
    if prop.get("format") in NOT_SHAREABLE_FORMATS:
        return f"a {prop['format']} setting can't be shared"
    if prop.get("type") not in SHAREABLE_TYPES:
        return "only a text, a number or a switch (or a dropdown of them) can be shared, not a list or an object"
    return None
