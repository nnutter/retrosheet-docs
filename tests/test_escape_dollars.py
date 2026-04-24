from retrosheet_docs.update_eventfile import normalize_markdown


def test_normalize_markdown_wraps_dollar_sequences_in_spans() -> None:
    markdown = "This uses $$ as a literal token.\n"
    assert normalize_markdown(markdown) == "This uses <span>$</span><span>$</span> as a literal token.\n"
