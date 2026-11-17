from inspection_copilot.chunking import chunk_pages, clean_page, find_repeated_lines, is_heading


def test_headings_are_recognised() -> None:
    assert is_heading("Section IV. INSULATORS")
    assert is_heading("4-12. Insulator cleaning")
    assert is_heading("CHAPTER 7")
    assert not is_heading("Insulators should be inspected for cracks and chips.")
    assert not is_heading("12")


def test_clean_page_rejoins_hyphenation_and_drops_page_numbers() -> None:
    lines = clean_page("Inspect each insula-\ntor carefully.\n  7-3  \n", drop=set())
    assert lines == ["Inspect each insulator carefully."]


def test_running_headers_are_detected() -> None:
    pages = [f"TM 5-684\nBody text {i}." for i in range(10)]
    assert find_repeated_lines(pages) == {"TM 5-684"}


def test_chunks_respect_size_and_track_pages_and_sections() -> None:
    sentence = "Porcelain insulators must be checked for chips and radial cracks."  # 10 words
    pages = [
        "Section IV. INSULATORS\n" + " ".join([sentence] * 12),
        " ".join([sentence] * 12),
    ]
    chunks = chunk_pages(pages, max_words=50, overlap_words=10)

    assert all(len(c.text.split()) <= 50 for c in chunks)
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    assert chunks[0].page_start == 1
    assert chunks[-1].page_end == 2
    assert all(c.section == "Section IV. INSULATORS" for c in chunks)


def test_consecutive_chunks_overlap() -> None:
    pages = [" ".join(f"Sentence number {i} is here." for i in range(60))]
    chunks = chunk_pages(pages, max_words=40, overlap_words=10)
    for previous, nxt in zip(chunks, chunks[1:], strict=False):
        last_sentence = previous.text.split(". ")[-1]
        assert last_sentence in nxt.text


def test_text_without_punctuation_is_still_split() -> None:
    table = " ".join(["cell"] * 500)  # e.g. a table extracted from a PDF
    chunks = chunk_pages([table], max_words=100, overlap_words=20)
    assert len(chunks) > 1
    assert all(len(c.text.split()) <= 100 for c in chunks)


def test_real_manual_heading_styles() -> None:
    assert is_heading("4-47. Pole line insulator class requirements.")
    assert is_heading("Volume 3-19")
    assert not is_heading("Table 4-3. Tie wire requirements")


def test_multi_line_titles_merge_into_one_section() -> None:
    pages = ["Volume 3-19\nCORRECTION FOR FAULTY OPERATION\nOF MERCURY SWITCHES\nBody text here."]
    (chunk,) = chunk_pages(pages)
    assert chunk.section == "Volume 3-19 CORRECTION FOR FAULTY OPERATION OF MERCURY SWITCHES"


def test_dot_leaders_are_removed() -> None:
    assert clean_page("Copper AWG. . . . . . . . . Soft-drawn copper", drop=set()) == [
        "Copper AWG Soft-drawn copper"
    ]


def test_reference_lines_are_not_headings() -> None:
    assert is_heading("6.1 General")
    assert is_heading("SECTION IV-INSULATORS")
    assert not is_heading("FAC-009-1")
    assert not is_heading("NFPA 70B")
    assert not is_heading("section 1.2.1, above, variance from these practices is acceptable")
    assert not is_heading("Volume 16, Electric Power Research Institute")
