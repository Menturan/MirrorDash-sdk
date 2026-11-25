from mirrordash_sdk.schema_checks import (
    preferred_width_problem,
    schema_errors,
    schema_warnings,
)


def test_a_clean_schema_has_nothing_to_fix():
    assert schema_warnings({
        "source": {"type": "string", "enum": ["a", "b"], "enum_titles": ["A", "B"], "default": "a", "title": "Source"},
        "url": {"type": "string", "format": "lan-url", "default": "", "show_if": {"source": ["b"]}, "group": "B"},
        "user": {"type": "string", "default": "", "group": "B"},
        "volume": {"type": "integer", "format": "slider", "minimum": 0, "maximum": 100, "default": 30},
        "photos": {"format": "files", "accept": "image"},
        "school": {"type": "object", "format": "list"},
        "feeds": {"type": "array", "default": [], "items": {"type": "object", "title": "Feed", "properties": {"name": {"type": "string"}}}},
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


def test_unit_must_be_one_of_the_known_four():
    assert schema_errors({"a": {"type": "integer", "default": 1, "unit": "s"}}) == []
    for unit in ("s", "min", "h", "%"):
        assert schema_errors({"a": {"type": "integer", "default": 1, "unit": unit}}) == []
    errors = schema_errors({"a": {"type": "integer", "default": 1, "unit": "px"},
                            "b": {"type": "array", "default": [], "items": {"type": "object", "properties": {
                                "c": {"type": "integer", "unit": "seconds"}}}}})
    assert [line.split(":")[0] for line in errors] == ["a", "b[].c"]
    assert not any("unknown keyword" in line for line in schema_warnings({"a": {"type": "integer", "default": 1, "unit": "s"}}))


def test_the_removed_core_settings_are_errors_that_say_what_replaced_them():
    errors = schema_errors({key: {"type": "string", "default": ""} for key in ("max_width", "max_height", "z_index", "opacity")})
    assert len(errors) == 4
    assert "preferred_width" in errors[0] and "height_percent" in errors[1] and "module order" in errors[2] and "opacity_percent" in errors[3]
    assert schema_errors({"row": {"type": "object", "properties": {"opacity": {"type": "integer"}}}}) == []  # only the top level is the core's
    assert not any("provides" in line for line in schema_warnings({"max_width": {"type": "string", "default": ""}}))


def test_a_module_may_declare_a_standard_setting_only_for_its_default():
    assert schema_warnings({"show_header": {"default": False}, "overflow": {"default": "fade"},
                            "heading": {"type": "string", "default": "", "title": "x", "description": "y"}}) == []
    warnings = schema_warnings({"opacity_percent": {"type": "integer", "default": 80, "minimum": 10}})
    assert len(warnings) == 1 and warnings[0].startswith("opacity_percent:") and "default" in warnings[0]


def test_min_label_is_for_sliders_and_show_if_takes_not():
    assert schema_warnings({
        "a": {"type": "integer", "format": "slider", "minimum": 0, "maximum": 9, "default": 0, "min_label": "Auto"},
        "g": {"type": "string", "default": ""},
        "b": {"type": "integer", "default": 5, "show_if": {"g": {"not": [""]}}},
    }) == []
    warnings = schema_warnings({
        "a": {"type": "integer", "default": 0, "min_label": "Auto"},
        "g": {"type": "string", "default": ""},
        "b": {"type": "integer", "default": 5, "show_if": {"g": {"nope": [""]}}},
        "c": {"type": "integer", "default": 5, "show_if": {"g": {"not": "x"}}},
    })
    assert [line.split(":")[0] for line in warnings] == ["a", "b", "c"]


def test_an_array_of_objects_needs_items_title():
    rows = {"properties": {"name": {"type": "string"}}}
    assert schema_warnings({"a": {"type": "array", "default": [], "items": {"type": "object", "title": "Station", **rows}}}) == []
    assert schema_warnings({"a": {"type": "array", "default": [], "items": {"type": "string", "enum": ["x"]}}}) == []
    warnings = schema_warnings({"a": {"type": "array", "default": [], "items": {"type": "object", **rows}}})
    assert len(warnings) == 1 and "Add Item" in warnings[0]


def test_a_unit_in_a_title_is_a_warning():
    for title in ("Update Interval (Seconds)", "Delay (s)", "Size (%)", "Width (px)", "Keep (hours)"):
        warnings = schema_warnings({"a": {"type": "integer", "default": 1, "title": title}})
        assert len(warnings) == 1 and "unit" in warnings[0], title
    assert schema_warnings({"a": {"type": "integer", "default": 1, "title": "Update interval", "unit": "s"},
                            "b": {"type": "string", "default": "", "title": "Name (optional)"}}) == []


def test_a_group_of_one_setting_is_a_warning():
    assert schema_warnings({"a": {"type": "string", "default": "", "group": "Advanced"},
                            "b": {"type": "string", "default": "", "group": "Advanced"}}) == []
    warnings = schema_warnings({"a": {"type": "string", "default": "", "group": "Advanced"},
                                "b": {"type": "string", "default": ""}})
    assert len(warnings) == 1 and warnings[0].startswith("a:")


def test_a_width_or_height_default_is_an_error_that_says_use_preferred_width():
    errors = schema_errors({"width_percent": {"default": 60}, "height_percent": {"default": 40}})
    assert len(errors) == 2 and all("preferred_width" in line for line in errors)
    assert schema_errors({"row": {"type": "object", "properties": {"width_percent": {"type": "integer"}}}}) == []


def test_overflow_is_a_module_default_of_scroll_or_fade():
    assert schema_errors({"overflow": {"default": "fade"}}) == [] and schema_errors({"overflow": {"default": "scroll"}}) == []
    assert len(schema_errors({"overflow": {"default": "hide"}})) == 1
    assert len(schema_errors({"overflow": {}})) == 1
    assert schema_warnings({"overflow": {"default": "fade"}}) == []


def test_preferred_width_is_a_positive_number_of_rem():
    for good in ("28rem", "12.5rem", "0.5rem", ".5rem"):
        assert preferred_width_problem(good) is None
    for bad in ("28", "28px", "0rem", "-3rem", "rem", "28 rem", 28, None, "1/3"):
        assert "preferred_width" in preferred_width_problem(bad)
