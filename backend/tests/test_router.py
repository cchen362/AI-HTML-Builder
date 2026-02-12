from app.services.router import classify_request


# --- No existing HTML -> always create ---


def test_no_html_returns_create():
    assert classify_request("anything at all", has_existing_html=False) == "create"


def test_no_html_even_with_edit_words():
    assert classify_request("Change the title", has_existing_html=False) == "create"


# --- Edit requests (default with existing HTML) ---


def test_edit_request_with_html():
    assert classify_request("Change the title to X", has_existing_html=True) == "edit"


def test_generic_request_defaults_to_edit():
    assert classify_request("Make it blue", has_existing_html=True) == "edit"


def test_improve_formatting_is_edit():
    assert classify_request("Improve the formatting", has_existing_html=True) == "edit"


def test_empty_input_with_html_defaults_to_edit():
    assert classify_request("", has_existing_html=True) == "edit"


# --- Image requests ---


def test_diagram_is_image():
    assert (
        classify_request(
            "Add a diagram showing the process", has_existing_html=True
        )
        == "image"
    )


def test_infographic_is_image():
    assert (
        classify_request(
            "Add an infographic about costs", has_existing_html=True
        )
        == "image"
    )


def test_chart_is_image():
    assert (
        classify_request("Create a bar chart of revenue", has_existing_html=True)
        == "image"
    )


# --- Create requests (explicit new document) ---


def test_create_a_new_is_create():
    assert (
        classify_request(
            "Create a new impact assessment", has_existing_html=True
        )
        == "create"
    )


def test_start_over_is_create():
    assert classify_request("Start over", has_existing_html=True) == "create"


def test_create_separate_document_is_create():
    assert (
        classify_request(
            "Create a separate summary document", has_existing_html=True
        )
        == "create"
    )


def test_from_scratch_is_create():
    assert (
        classify_request("Build it from scratch", has_existing_html=True)
        == "create"
    )


# --- Priority: new document keywords beat image keywords ---


def test_new_document_takes_priority_over_image():
    """'create a new diagram' should route to create, not image."""
    assert (
        classify_request("Create a new diagram", has_existing_html=True)
        == "create"
    )
