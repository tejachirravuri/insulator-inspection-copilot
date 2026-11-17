"""Turn PDF page texts into retrieval chunks.

Design:
  * Clean each page: re-join words hyphenated across line breaks, drop running headers and
    footers (lines that repeat on many pages, e.g. "TM 5-684"), drop bare page numbers.
  * Split into sentences and remember each sentence's page and the latest heading seen.
  * Greedily pack sentences into chunks of at most `max_words` words, never cutting a
    sentence, and start the next chunk with the last ~`overlap_words` words of the previous
    one. The overlap keeps a fact that straddles a boundary retrievable from both sides.

~180 words is roughly 250-300 tokens: well under the 512-token limit of the E5 embedding
model, and small enough that a chunk is about one topic, which makes citations precise.
"""

import re
from collections import Counter
from dataclasses import dataclass

# Headings in these manuals look like "4-47. Pole line insulator class requirements.",
# "6.1 General", "Section IV. INSULATORS", "Volume 3-19", or ALL-CAPS title lines.
_NUMBERED_HEADING = re.compile(r"^\d+-\d+\.\s+[A-Z][^.]{2,90}\.?$")
_HEADING_PATTERNS = [
    # Keyword + identifier, then no lowercase prose (rejects "section 1.2.1, above, ...").
    re.compile(r"^(?i:chapter|section|appendix|volume)\s+[\w.-]+\b[^a-z,]*$"),
    _NUMBERED_HEADING,
    re.compile(r"^\d+(?:\.\d+)*\.?\s+[A-Z][A-Za-z ,/&()<>-]{2,80}$"),  # "1.1.1 General"
    # ALL-CAPS line of at least two words, no digits (rejects codes like "FAC-009-1").
    re.compile(r"^[A-Z][A-Z,/&()-]+(?: [A-Z,/&()-]+)+$"),
]
_CAPTION = re.compile(r"^(table|figure)\s+[\w-]+", re.IGNORECASE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;:])\s+(?=[A-Z0-9(\"'])")
_PAGE_NUMBER = re.compile(r"^(page\s+)?[-\s]*\d{1,4}[-\s]*$|^[A-Z]?-?\d{1,3}-\d{1,3}$", re.I)
_DOT_LEADER = re.compile(r"(?:\s*\.){3,}")  # ". . . . ." in tables of contents and tables


def _normalise(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


@dataclass(frozen=True)
class ChunkData:
    ordinal: int
    text: str
    section: str | None
    page_start: int
    page_end: int


@dataclass(frozen=True)
class _Sentence:
    text: str
    page: int
    section: str | None


def is_heading(line: str) -> bool:
    line = line.strip()
    if len(line) < 4 or len(line) > 100 or _CAPTION.match(line):
        return False
    if _NUMBERED_HEADING.match(line):  # may end with a period
        return True
    if line.endswith((".", ",", ";")):
        return False
    return any(p.match(line) for p in _HEADING_PATTERNS)


def find_repeated_lines(pages: list[str], min_fraction: float = 0.3) -> set[str]:
    """Lines that occur on at least `min_fraction` of pages: running headers/footers."""
    if len(pages) < 4:
        return set()
    counts = Counter()
    for page in pages:
        counts.update({_normalise(line) for line in page.splitlines() if line.strip()})
    threshold = max(3, int(len(pages) * min_fraction))
    return {line for line, n in counts.items() if n >= threshold}


def clean_page(text: str, drop: set[str]) -> list[str]:
    """Return the meaningful lines of a page."""
    text = re.sub(r"(\w)-\n\s*(\w)", r"\1\2", text)  # "insula-\ntor" -> "insulator"
    lines = []
    for raw in text.splitlines():
        line = _normalise(raw)
        if not line or line in drop or _PAGE_NUMBER.match(line):
            continue
        line = _normalise(_DOT_LEADER.sub(" ", line))
        if line:
            lines.append(line)
    return lines


def _split_paragraph(lines: list[str], page: int, section: str | None) -> list[_Sentence]:
    paragraph = " ".join(lines)
    return [
        _Sentence(s.strip(), page, section) for s in _SENTENCE_SPLIT.split(paragraph) if s.strip()
    ]


def _sentences(pages: list[str]) -> list[_Sentence]:
    drop = find_repeated_lines(pages)
    section: str | None = None
    out: list[_Sentence] = []
    for page_no, page in enumerate(pages, start=1):
        buffer: list[str] = []
        previous_was_heading = False
        for line in clean_page(page, drop):
            if is_heading(line):
                # A heading ends the running paragraph; text after it belongs to the new section.
                out.extend(_split_paragraph(buffer, page_no, section))
                buffer = []
                # Titles printed over several lines ("Volume 3-19" / "CORRECTION FOR ...")
                # are merged into one section name.
                if previous_was_heading and section:
                    section = f"{section} {line}"[:300]
                else:
                    section = line[:300]
                previous_was_heading = True
            else:
                buffer.append(line)
                previous_was_heading = False
        out.extend(_split_paragraph(buffer, page_no, section))
    return out


def _split_long(sentences: list[_Sentence], max_words: int) -> list[_Sentence]:
    """Cut 'sentences' longer than max_words (e.g. tables without punctuation) into pieces."""
    out: list[_Sentence] = []
    for s in sentences:
        words = s.text.split()
        for i in range(0, len(words), max_words):
            out.append(_Sentence(" ".join(words[i : i + max_words]), s.page, s.section))
    return out


def chunk_pages(pages: list[str], max_words: int = 180, overlap_words: int = 40) -> list[ChunkData]:
    """Split a document (list of page texts, page 1 first) into overlapping chunks."""
    if overlap_words >= max_words:
        raise ValueError("overlap_words must be smaller than max_words")
    sentences = _split_long(_sentences(pages), max_words - overlap_words)
    chunks: list[ChunkData] = []
    current: list[_Sentence] = []
    n_words = 0

    def emit() -> None:
        chunks.append(
            ChunkData(
                ordinal=len(chunks),
                text=" ".join(s.text for s in current),
                # Section of the first sentence that has one (a chunk may start mid-section).
                section=next((s.section for s in current if s.section), None),
                page_start=current[0].page,
                page_end=current[-1].page,
            )
        )

    for sentence in sentences:
        words = len(sentence.text.split())
        if current and n_words + words > max_words:
            emit()
            # Carry the tail of the previous chunk as overlap.
            carry: list[_Sentence] = []
            carried = 0
            # Never carry the first sentence: the next chunk must differ from this one.
            for prev in reversed(current[1:]):
                w = len(prev.text.split())
                if carried + w > overlap_words:
                    break
                carry.insert(0, prev)
                carried += w
            current, n_words = carry, carried
        current.append(sentence)
        n_words += words
    if current:
        emit()
    return chunks
