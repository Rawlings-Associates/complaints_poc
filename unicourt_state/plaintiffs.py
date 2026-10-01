"""Read plaintiff names out of a civil cover sheet or a complaint PDF.

Two layouts are handled:

* **Cover sheets** label the party: ``PLAINTIFF(S): Jane Doe``, a
  ``PLAINTIFF`` heading with the names on the lines below it, or a case
  name / short title such as ``Jane Doe v. Acme Corp``.
* **Complaints** put the names in the caption, above the word
  ``Plaintiff(s),`` and before ``v.``.

Both are heuristics over extracted text. A scanned PDF has no text layer and
yields nothing (OCR is out of scope); the caller reports that rather than
guessing.
"""

from __future__ import annotations

import re
from pathlib import Path

MAX_PAGES = 3  # captions and cover-sheet party blocks are on the first pages


class NoTextLayer(RuntimeError):
    """The PDF has no extractable text (probably a scan)."""


def extract_text(path: Path, max_pages: int = MAX_PAGES) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover - depends on the environment
        raise SystemExit("pypdf is required to read PDFs: pip install pypdf") from None
    reader = PdfReader(str(path))
    pages = reader.pages[:max_pages]
    text = "\n".join((page.extract_text() or "") for page in pages)
    if not text.strip():
        raise NoTextLayer(f"{path.name} has no text layer (scanned?)")
    return text


# -- shared cleanup -----------------------------------------------------------

_LINE_NUMBER = re.compile(r"^\s*\d{1,2}\s*$")
_LEADING_LINE_NUMBER = re.compile(r"^\s*(?:[1-9]|1\d|2[0-8])\s+(?=[A-Z])")

# Right-hand caption box text that extraction often glues onto a caption line.
_RIGHT_BOX = re.compile(
    r"\s*(?:\)\s*)*(?:case\s+no\b.*|index\s+no\b.*|complaint\s+for\b.*|"
    r"(?:verified\s+)?complaint\b.*|demand\s+for\s+jury.*|jury\s+trial.*|"
    r"dept\b.*|judge\b.*|\(?unlimited\b.*|\(?limited\s+civil.*)$",
    re.I,
)

_DESCRIPTORS = [
    r"\b(?:an?|the)\s+individuals?\b",
    r"\bindividually\b",
    r"\bon\s+behalf\s+of\s+(?:all\s+)?(?:himself|herself|themselves|others)[^;]*",
    r"\bas\s+(?:the\s+)?(?:personal\s+representative|administrat(?:or|rix)|executor|executrix|"
    r"guardian|successor|heir|parent|next\s+friend)\b[^;]*",
    r"\bby\s+and\s+through\b[^;]*",
    r"\ba\s+minor\b",
    r"\bet\s+al\.?",
    r"\b(?:husband|wife|spouses?)\s+and\s+(?:husband|wife)\b",
    r"\b(?:an?\s+)?(?:resident|citizen|domiciliary)\s+of\s+[^;,]*",
    r"\bdeceased\b",
    r"\bpro\s+se\b",
]
_DESCRIPTOR_RE = re.compile("|".join(_DESCRIPTORS), re.I)

_STOP_WORDS = {
    "plaintiff", "plaintiffs", "petitioner", "petitioners", "v", "vs", "versus",
    "and", "the", "of", "in", "a", "an", "individual", "complaint", "case",
    "no", "name", "names", "first", "last", "middle", "defendant", "defendants",
}

_NOT_A_NAME = re.compile(
    r"\b(court|county|state of|division|attorney|telephone|facsimile|email|"
    r"bar no|sbn|suite|street|avenue|jurisdiction|page|form|check|instructions)\b|@|\d{3,}",
    re.I,
)


def clean_lines(text: str) -> list[str]:
    lines = []
    for raw in text.splitlines():
        if _LINE_NUMBER.match(raw):
            continue
        line = _LEADING_LINE_NUMBER.sub("", raw)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return lines


def split_names(block: str, split_commas: bool = True) -> list[str]:
    """Turn a caption fragment into individual names."""
    block = _DESCRIPTOR_RE.sub(" ", block)
    parts = re.split(r";|\n|\band\b|&", block, flags=re.I)
    if split_commas:
        parts = [p for part in parts for p in part.split(",")]
    names = []
    for part in parts:
        name = re.sub(r"\s+", " ", part).strip(" ,.:;-()[]\t")
        if not name or _NOT_A_NAME.search(name):
            continue
        words = [w for w in re.findall(r"[A-Za-z][A-Za-z.'-]*", name)]
        meaningful = [w for w in words if w.lower().strip(".") not in _STOP_WORDS]
        if not meaningful or len(words) > 7:
            continue
        if not any(len(w.strip(".")) > 1 for w in meaningful):
            continue
        names.append(name)
    return _dedupe(names)


def _dedupe(names: list[str]) -> list[str]:
    seen, out = set(), []
    for n in names:
        key = re.sub(r"[^a-z]", "", n.lower())
        if key and key not in seen:
            seen.add(key)
            out.append(n)
    return out


# -- complaints: the caption --------------------------------------------------

_PLAINTIFF_LABEL = re.compile(
    r"^(?P<before>.*?)\b(?:Plaintiffs?|Petitioners?)(?:\s*\(s\))?\s*[,.;:]?\s*"
    r"(?:(?:v|vs|versus)\.?(?:\s.*)?|-?\s*against\b.*)?$",
    re.I,
)
_CAPTION_STOP = re.compile(
    r"\b(court|county of|state of|in and for|division|district|circuit|parish|"
    r"case no|index no|attorneys?\b|telephone|facsimile|e-?mail|bar no|sbn)\b|@",
    re.I,
)


def plaintiffs_from_caption(text: str, max_lines: int = 12) -> list[str]:
    lines = [_RIGHT_BOX.sub("", l).strip() for l in clean_lines(text)]
    for i, line in enumerate(lines):
        m = _PLAINTIFF_LABEL.match(line)
        if not m or len(line) > 160:
            continue
        # "attorneys for plaintiff" and body text are not the caption label
        if re.search(r"\b(for|of|by|against|the)\s*$", m.group("before"), re.I):
            continue
        block = [m.group("before")] if m.group("before").strip() else []
        j = i - 1
        while j >= 0 and len(block) < max_lines:
            if _CAPTION_STOP.search(lines[j]):
                break
            block.insert(0, lines[j])
            j -= 1
        # Caption lines wrap mid-name ("MARIA" / "GARCIA"); parties are
        # separated by commas, semicolons or "and", not by line breaks.
        names = split_names(" ".join(block))
        if names:
            return names
    return []


# -- cover sheets ---------------------------------------------------------------

_COVER_LABEL = re.compile(
    r"^\W*(?:names?\s+of\s+|first\s+|list\s+)?"
    r"(?:plaintiffs?|petitioners?)(?:\s*\(s\))?"
    r"(?:\s*/\s*(?:plaintiffs?|petitioners?)(?:\s*\(s\))?)?"
    r"\s*[:\-]?\s*(?P<rest>.*)$",
    re.I,
)
_COVER_STOP = re.compile(
    r"^\W*(?:defendants?|respondents?|attorney|vs?\.?$|versus|against|county|case\b|"
    r"court|cause\s+of|nature\s+of|type\s+of)",
    re.I,
)
_FORM_HINT = re.compile(r"\((?:[^)]*\b(?:last|first|middle|if applicable|name)\b[^)]*)\)", re.I)
_CASE_NAME = re.compile(
    r"^\W*(?:short\s+title|case\s+name|case\s+caption|style[d]?|caption)\s*[:\-]?\s*(?P<title>.+)$",
    re.I,
)


def plaintiffs_from_cover_sheet(text: str, max_lines: int = 6) -> list[str]:
    lines = clean_lines(text)
    names: list[str] = []
    for i, line in enumerate(lines):
        m = _COVER_LABEL.match(line)
        if not m or len(line) > 120:
            continue
        if m.group("rest").startswith(","):  # "Plaintiffs," is a caption, not a form label
            continue
        chunk = []
        rest = _FORM_HINT.sub("", m.group("rest")).strip(" :-")
        if rest and not _COVER_STOP.match(rest):
            chunk.append(rest)
        for nxt in lines[i + 1 : i + 1 + max_lines]:
            if _COVER_STOP.match(nxt) or _COVER_LABEL.match(nxt):
                break
            chunk.append(_FORM_HINT.sub("", nxt))
        found = split_names("\n".join(re.split(r"\s+(?:v\.?|vs\.?)\s+", c, flags=re.I)[0] for c in chunk),
                            split_commas=False)
        names.extend(found)
    if names:
        return _dedupe(names)

    for line in lines:
        m = _CASE_NAME.match(line)
        if m:
            title = re.split(r"\s+(?:v\.?|vs\.?|versus)\s+", m.group("title"), flags=re.I)[0]
            found = split_names(title)
            if found:
                return found
    return []


def parse_plaintiffs(text: str, doc_type: str) -> tuple[list[str], str]:
    """Plaintiff names and the method that found them ('' when none)."""
    if doc_type == "civil-cover-sheet":
        names = plaintiffs_from_cover_sheet(text)
        if names:
            return names, "cover-sheet-label"
    names = plaintiffs_from_caption(text)
    return (names, "caption") if names else ([], "")
