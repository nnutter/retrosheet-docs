from retrosheet_docs.update_eventfile import generate_markdown
from retrosheet_docs.update_eventfile import insert_sentence_newlines
from retrosheet_docs.update_eventfile import is_plain_paragraph
from retrosheet_docs.update_eventfile import normalize_list_item_block


def test_inserts_newlines_between_sentences() -> None:
    paragraph = "This is one sentence. This is another."
    assert insert_sentence_newlines(paragraph) == "This is one sentence.\nThis is another."


def test_preserves_common_abbreviations() -> None:
    paragraph = "Examples include e.g. bunts and steals. Dr. Smith agreed."
    assert insert_sentence_newlines(paragraph) == "Examples include e.g. bunts and steals.\nDr. Smith agreed."


def test_preserves_acronym_abbreviations() -> None:
    paragraph = "The U.S. record changed. Another sentence follows."
    assert insert_sentence_newlines(paragraph) == "The U.S. record changed.\nAnother sentence follows."


def test_preserves_decimals() -> None:
    paragraph = "The value was 3.14 in one sample. Another sentence follows."
    assert insert_sentence_newlines(paragraph) == "The value was 3.14 in one sample.\nAnother sentence follows."


def test_preserves_urls() -> None:
    paragraph = "See https://www.retrosheet.org/eventfile.htm for details. Another sentence follows."
    assert insert_sentence_newlines(paragraph) == "See https://www.retrosheet.org/eventfile.htm for details.\nAnother sentence follows."


def test_list_items_are_not_plain_paragraphs() -> None:
    assert not is_plain_paragraph("- first item\n- second item")


def test_normalizes_wrapped_ordered_list_items() -> None:
    block = (
        "3. The next field is either 0 (for visiting team),\n"
        "or 1 (for home team). In some games, typically due to scheduling conflicts, the home team"
    )
    assert normalize_list_item_block(block) == (
        "3. The next field is either 0 (for visiting team), or 1 (for home team).\n"
        "   In some games, typically due to scheduling conflicts, the home team"
    )


def test_generate_markdown_joins_inline_text_and_removes_nbsp() -> None:
    html = """
    <html><body>
      <h2><center>The Event File</center></h2>
      <p><font size="+1">The first field is the </font><a href="#2"><font size="+1">Retrosheet
      player id</font></a><font size="+1">, which is unique for each player.&nbsp;</font></p>
    </body></html>
    """
    markdown = generate_markdown(html)
    assert "[Retrosheet player id](#2), which is unique for each player." in markdown
    assert "\xa0" not in markdown


def test_generate_markdown_promotes_inline_label_to_heading() -> None:
    html = """
    <html><body>
      <h2><center>The Event File</center></h2>
      <p><font size="+1"><span style="font-weight: bold;"><i>badj </i> \"Batter adjustment\"</span>. This record is used to mark a plate appearance.</font></p>
    </body></html>
    """
    markdown = generate_markdown(html)
    assert "#### badj \"Batter adjustment\"" in markdown
    assert "This record is used to mark a plate appearance." in markdown


def test_generate_markdown_promotes_standalone_inline_label_to_heading() -> None:
    html = """
    <html><body>
      <h2><center>The Event File</center></h2>
      <p><font size="+1"><span style="font-weight: bold;"><i>info</i></span> There may be from 30 to 40 info records.</font></p>
    </body></html>
    """
    markdown = generate_markdown(html)
    assert "#### info" in markdown
    assert "There may be from 30 to 40 info records." in markdown


def test_generate_markdown_keeps_unquoted_inline_labels_inline() -> None:
    html = """
    <html><body>
      <h2><center>The Event File</center></h2>
      <p><font size="+1"><span style="font-weight: bold;"><i>start</i></span> and <span style="font-weight: bold;"><i>sub</i></span> There are 18 start records.</font></p>
    </body></html>
    """
    markdown = generate_markdown(html)
    assert "#### start and sub" in markdown
    assert "There are 18 start records." in markdown


def test_generate_markdown_promotes_play_label_to_heading() -> None:
    html = """
    <html><body>
      <h2><center>The Event File</center></h2>
      <p><font size="+1"><span style="font-weight: bold;"><i>play</i></span> The play records contain the events of the game.</font></p>
    </body></html>
    """
    markdown = generate_markdown(html)
    assert "#### play" in markdown
    assert "The play records contain the events of the game." in markdown


def test_generate_markdown_unwraps_blockquote_with_h3() -> None:
    html = """
    <html><body>
      <h2><center>The Event File</center></h2>
      <blockquote>
        <h3>Info record types</h3>
        <p>Complete records are shown.</p>
      </blockquote>
    </body></html>
    """
    markdown = generate_markdown(html)
    assert "> ### Info record types" not in markdown
    assert "### Info record types" in markdown
    assert "> Complete records are shown." not in markdown
    assert "Complete records are shown." in markdown
