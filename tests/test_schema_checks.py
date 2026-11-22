from mirrordash_sdk.schema_checks import schema_warnings


def test_a_clean_schema_has_nothing_to_fix():
    assert schema_warnings({
        "source": {"type": "string", "enum": ["a", "b"], "enum_titles": ["A", "B"], "default": "a", "title": "Source"},
        "url": {"type": "string", "format": "lan-url", "default": "", "show_if": {"source": ["b"]}, "group": "B"},
        "volume": {"type": "integer", "format": "slider", "minimum": 0, "maximum": 100, "default": 30},
        "photos": {"format": "files", "accept": "image"},
        "school": {"type": "object", "format": "list"},
        "feeds": {"type": "array", "default": [], "items": {"type": "object", "properties": {"name": {"type": "string"}}}},
    }) == []


def test_each_mistake_is_named():
    warnings = schema_warnings({
        "a": {"type": "string", "default": "", "show_iff": {"b": [1]}},       # a misspelt keyword
        "b": {"type": "string", "default": "", "format": "pasword"},          # a misspelt format
        "c": {"type": "string", "default": "x", "enum": ["x", "y"]},          # no enum_titles
        "d": {"type": "integer", "default": 1, "format": "slider"},           # a slider without its bounds
        "e": {"type": "string"},                                              # no default
        "f": {"type": "string", "default": "", "show_if": {"nope": ["x"]}},   # show_if naming nothing
    })
    for start in ("a:", "b:", "c:", "d:", "e:", "f:"):
        assert any(line.startswith(start) for line in warnings), start
    assert len(warnings) == 6


def test_shared_works_on_a_top_level_single_value_only():
    assert schema_warnings({
        "url": {"type": "string", "format": "lan-url", "default": "", "shared": True},
        "token": {"type": "string", "format": "password", "default": "", "shared": True},
        "unit": {"type": "string", "enum": ["c", "f"], "enum_titles": ["C", "F"], "default": "c", "shared": True},
        "count": {"type": "integer", "default": 1, "shared": True},
        "on": {"type": "boolean", "default": True, "shared": True},
    }) == []
    warnings = schema_warnings({
        "a": {"type": "array", "default": [], "shared": True, "items": {"type": "object", "properties": {
            "inner": {"type": "string", "shared": True}}}},                    # a list, and a row's setting
        "b": {"type": "object", "properties": {"inner": {"type": "string", "default": "", "shared": True}}},  # in an object
        "c": {"format": "files", "accept": "image", "shared": True},          # files
        "d": {"type": "object", "format": "list", "shared": True},            # a choice from the module
        "e": {"type": "string", "default": "", "shared": "yes"},              # not true
        "position": {"type": "string", "default": "", "shared": True},        # the core's own
    })
    assert [line.split(":")[0] for line in warnings if "shared" in line] == ["a", "a[].inner", "b.inner", "c", "d", "e", "position"]
    assert not any("unknown keyword" in line for line in warnings)  # "shared" is a keyword it knows
