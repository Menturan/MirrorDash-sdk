"""What `validate` warns about in a module's config_schema.json settings: the mistakes the admin page passes
over in silence (a misspelt keyword or format, an enum shown without words, a show_if naming no setting)
and the places the core doesn't look (a password or home address inside a nested object)."""

# Every keyword the admin page reads in a setting (MirrorDash 0.14): JSON Schema's own and ours
KEYWORDS = {"type", "default", "title", "description", "enum", "enum_titles", "enumNames", "format", "items",
            "properties", "required", "minimum", "maximum", "minLength", "maxLength", "pattern", "pattern_message",
            "step", "uniqueItems", "show_if", "group", "accept", "max_files"}
FORMATS = {"password", "lan-url", "icon", "color", "textarea", "time", "slider", "files", "list", "search"}
NEEDS_NO_DEFAULT = {"files", "list", "search"}  # files live in the cache folder; a choice arrives as {}


def schema_warnings(properties: dict, path: str = "", nested: bool = False, in_list: bool = False) -> list[str]:
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
        if nested and fmt in ("password", "lan-url"):
            warnings.append(f"{name}: a {fmt} inside a nested object is missed by the mirror (backups, home "
                            "network); keep it at the top level (show_if or group to tidy the form)")
        show_if = prop.get("show_if")
        if show_if is not None and (not isinstance(show_if, dict) or any(other not in properties for other in show_if)):
            warnings.append(f"{name}: show_if must name settings beside it: {{\"source\": [\"immich\"]}}")
        if isinstance(prop.get("properties"), dict):
            warnings += schema_warnings(prop["properties"], f"{name}.", nested=True)
        items = prop.get("items")
        if isinstance(items, dict) and isinstance(items.get("properties"), dict):
            warnings += schema_warnings(items["properties"], f"{name}[].", nested=True, in_list=True)
    return warnings
