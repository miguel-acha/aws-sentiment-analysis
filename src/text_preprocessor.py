"""
text_preprocessor.py
--------------------
Normaliza letras antes de enviarlas a Amazon Comprehend.

Objetivos:
- Quitar ruido (headers, markup, adlibs, lineas vacias)
- Reducir repeticion excesiva de coros
- Expandir slang y contracciones comunes en espanol e ingles
- Reinterpretar jerga urbana como conceptos mas semanticos
- Preservar contexto realmente negativo (violencia, ruptura, odio)
- Mantener el texto dentro de limites razonables para Comprehend
"""

import html
import re
import unicodedata
from collections import Counter

MAX_ANALYSIS_CHARS = 5000
MAX_LINE_OCCURRENCES = 2
MIN_ANALYSIS_CHARS = 24

SECTION_HEADER_RE = re.compile(
    r"^\s*[\[(]?\s*"
    r"(verse|chorus|hook|bridge|intro|outro|pre-chorus|post-chorus|refrain|"
    r"coro|verso|puente|interludio|estribillo)"
    r"[^)\]]*[\])]?\s*$",
    re.IGNORECASE,
)
PURE_PUNCT_RE = re.compile(r"^[\W_]+$")
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
MULTISPACE_RE = re.compile(r"\s+")
REPEATED_CHAR_RE = re.compile(r"([A-Za-z])\1{2,}")
REPEATED_WORD_RE = re.compile(
    r"\b([A-Za-z][A-Za-z']{1,})(?:\s+\1){2,}\b",
    re.IGNORECASE,
)
BRACKETED_META_RE = re.compile(
    r"[\[(]\s*(?:verse|chorus|hook|bridge|intro|outro|pre-chorus|post-chorus|"
    r"refrain|coro|verso|puente|interludio|estribillo)[^)\]]*[\])]",
    re.IGNORECASE,
)

ADLIB_TOKENS = {
    "ah", "ay", "ayy", "brr", "eh", "ey", "ha", "haha", "hey", "hm", "hmm",
    "la", "lalala", "mmm", "mm", "nah", "oh", "ooh", "prr", "rr", "skrrt",
    "skrt", "tra", "uh", "uhh", "uhm", "woo", "woah", "wuh", "yah", "yeah",
    "yeh", "yo",
}

CONTRACTION_REPLACEMENTS = [
    (r"\bain['\u2019]?t\b", "is not"),
    (r"\bi['\u2019]m\b", "i am"),
    (r"\byou['\u2019]re\b", "you are"),
    (r"\bwe['\u2019]re\b", "we are"),
    (r"\bthey['\u2019]re\b", "they are"),
    (r"\bit['\u2019]s\b", "it is"),
    (r"\bthat['\u2019]s\b", "that is"),
    (r"\bthere['\u2019]s\b", "there is"),
    (r"\bimma\b", "i am going to"),
    (r"\bfinna\b", "about to"),
    (r"\btryna\b", "trying to"),
    (r"\bgonna\b", "going to"),
    (r"\bwanna\b", "want to"),
    (r"\bgotta\b", "have to"),
    (r"\bcuz\b", "because"),
    (r"\bcoz\b", "because"),
    (r"\b'cause\b", "because"),
    (r"\blemme\b", "let me"),
    (r"\bkinda\b", "kind of"),
    (r"\boutta\b", "out of"),
    (r"\by['\u2019]?all\b", "you all"),
    (r"\bpa['\u2019](?=\s|$)", "para"),
    (r"\bpa\s+lante\b", "para adelante"),
    (r"\bna['\u2019](?=\s|$)", "nada"),
    (r"\bto['\u2019](?=\s|$)", "todo"),
    (r"\btoa['\u2019](?=\s|$)", "toda"),
]

SEMANTIC_REPLACEMENTS = [
    (r"\bfuck you\b", "anger rejection"),
    (r"\bfucked up\b", "hurt broken"),
    (r"\bcut you off\b", "distance rejection"),
    (r"\bkill(?:ed|ing)?\s+my vibe\b", "ruin mood frustration"),
    (r"\bheartbreak\b", "sadness heartbreak"),
    (r"\bbroke my heart\b", "sadness heartbreak"),
    (r"\bmiss you\b", "longing sadness"),
    (r"\bte odio\b", "odio rechazo"),
    (r"\bme duele\b", "dolor tristeza"),
    (r"\bme rompi(?:ste|o) el corazon\b", "tristeza corazon roto"),
    (r"\bperre(?:o|ar|ando|ea|eando)\b", "baile sensual fiesta"),
    (r"\bbellaque(?:o|ar|ando)?\b", "deseo seduccion fiesta"),
    (r"\bbellac[oa]s?\b", "persona atractiva deseo"),
    (r"\bjangue(?:o|ar|ando)?\b", "fiesta diversion amigos"),
    (r"\bparise(?:o|ar|ando)?\b", "fiesta celebracion"),
    (r"\btete(?:o|ar|ando)?\b", "fiesta intensa baile"),
    (r"\bfronte(?:o|ar|ando)?\b", "confianza presumir exito"),
    (r"\bsandungue(?:o|ar|ando)?\b", "baile sensual alegria"),
    (r"\bguayand[oa]\b", "baile sensual cerca"),
    (r"\bvacil(?:on|ona|ar|ando|a)\b", "diversion fiesta"),
    (r"\bflow\b", "estilo confianza"),
    (r"\bmamacita\b|\bmami\b|\bpapi\b|\bbebecita\b|\bbebesita\b", "persona deseada"),
    (r"\bbandolero\b|\bbandida\b|\bbandido\b", "rebeldia pasion"),
    (r"\bculona\b|\bculo\b", "atraccion fisica"),
    (r"\bpartyseo\b", "fiesta celebracion"),
    (r"\brompe(?:\s+la)?\b", "exito energia"),
    (r"\bde toa\b", "completo total"),
    (r"\blit\b", "exciting fun party"),
    (r"\bturnt\s+up\b|\bturned\s+up\b|\bturnt\b", "party celebration energy"),
    (r"\bvib(?:e|es|in|ing)\b", "good mood enjoying"),
    (r"\bflex(?:in|ing)?\b", "confidence success"),
    (r"\bdrip\b", "style confidence"),
    (r"\bshawty\b|\bshorty\b", "desired person"),
    (r"\bbaddie\b|\bbad bitch(?:es)?\b", "attractive confident person"),
    (r"\btwerk(?:ing)?\b", "dance sensual dance"),
    (r"\bgrind(?:ing)?\b", "dance close"),
    (r"\bfreak\b", "sexual desire"),
    (r"\bhomie\b|\bbruh\b|\bbro\b", "friend"),
    (r"\bwhip\b", "car status"),
    (r"\bracks?\b|\bbands?\b", "money success"),
    (r"\bstunt(?:in|ing)?\b", "showing success confidence"),
    (r"\bbossed?\s+up\b", "success confidence power"),
    (r"\bdrop it low\b", "dance sensual dance"),
    (r"\bshake(?:\s+that)?\s+ass\b", "dance sensual movement"),
    (r"\bthrow it back\b", "dance sensual movement"),
    (r"\bmake it clap\b", "dance sensual movement"),
    (r"\bopps?\b", "enemy conflict"),
    (r"\bsmoke (?:you|him|her|them)\b", "threat violence"),
    (r"\bcatch(?:ing)?\s+a\s+body\b", "violence homicide"),
    (r"\bdrive by\b", "violence attack"),
    (r"\bdraco\b|\bglock\b|\bchopper\b|\bsemi\b", "weapon violence"),
    (r"\bgoon\b", "street violence"),
]

PROFANITY_INTENSIFIERS = [
    (r"\bfuckin['g]?\b", "very"),
    (r"\bmotherfuckin['g]?\b", "very intense"),
    (r"\bdamn\b", "very"),
    (r"\bhella\b", "very"),
]


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _canonical_line(line: str) -> str:
    line = _strip_accents(line.lower())
    line = re.sub(r"[^\w\s]", " ", line)
    return MULTISPACE_RE.sub(" ", line).strip()


def _is_adlib_line(line: str) -> bool:
    tokens = re.findall(r"[A-Za-z']+", _strip_accents(line.lower()))
    if not tokens or len(tokens) > 6:
        return False
    adlib_count = sum(1 for token in tokens if token in ADLIB_TOKENS)
    return adlib_count / len(tokens) >= 0.8


def _apply_replacements(line: str, replacements: list[tuple[str, str]], stats: dict, stat_key: str) -> str:
    for pattern, replacement in replacements:
        line, count = re.subn(pattern, replacement, line, flags=re.IGNORECASE)
        stats[stat_key] += count
    return line


def _normalize_line(line: str, stats: dict) -> str:
    original = line
    line = html.unescape(line)
    line = line.replace("\u2019", "'").replace("\u2018", "'")
    line = line.replace("\u201c", '"').replace("\u201d", '"')
    line = URL_RE.sub(" ", line)
    line = BRACKETED_META_RE.sub(" ", line)
    line = REPEATED_CHAR_RE.sub(r"\1\1", line)
    line = REPEATED_WORD_RE.sub(r"\1 \1", line)

    line = _apply_replacements(line, CONTRACTION_REPLACEMENTS, stats, "contraction_hits")
    line = _apply_replacements(line, SEMANTIC_REPLACEMENTS, stats, "slang_hits")
    line = _apply_replacements(line, PROFANITY_INTENSIFIERS, stats, "intensifier_hits")

    line = re.sub(r"\s*[-~]+\s*", " ", line)
    line = MULTISPACE_RE.sub(" ", line).strip(" .,-;:!?")

    if line != original:
        stats["lines_changed"] += 1

    return line


def _select_lines(lines: list[str], stats: dict) -> list[str]:
    selected = []
    seen = Counter()

    for line in lines:
        canonical = _canonical_line(line)
        if not canonical or len(canonical) < 3:
            stats["removed_noise_lines"] += 1
            continue
        if seen[canonical] >= MAX_LINE_OCCURRENCES:
            stats["duplicate_lines_trimmed"] += 1
            continue
        seen[canonical] += 1
        selected.append(line)

    return selected


def _truncate_text(text: str, limit: int = MAX_ANALYSIS_CHARS) -> str:
    if len(text) <= limit:
        return text

    cut = text[:limit]
    last_boundary = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "), cut.rfind("\n"))
    if last_boundary >= limit * 0.6:
        return cut[:last_boundary].strip()
    return cut.strip()


def preprocess_lyrics_for_comprehend(text: str) -> dict:
    original_text = (text or "").strip()
    stats = {
        "original_chars": len(original_text),
        "final_chars": 0,
        "original_lines": 0,
        "final_lines": 0,
        "removed_noise_lines": 0,
        "duplicate_lines_trimmed": 0,
        "slang_hits": 0,
        "contraction_hits": 0,
        "intensifier_hits": 0,
        "lines_changed": 0,
        "used_fallback": False,
    }

    if not original_text:
        stats["used_fallback"] = True
        return {"text": "", "stats": stats}

    cleaned = html.unescape(original_text).replace("\r\n", "\n").replace("\r", "\n")
    raw_lines = [line.strip() for line in cleaned.split("\n")]
    stats["original_lines"] = len(raw_lines)

    normalized_lines = []
    for line in raw_lines:
        if not line:
            continue
        if SECTION_HEADER_RE.match(line):
            stats["removed_noise_lines"] += 1
            continue
        if PURE_PUNCT_RE.match(line):
            stats["removed_noise_lines"] += 1
            continue
        if _is_adlib_line(line):
            stats["removed_noise_lines"] += 1
            continue

        normalized = _normalize_line(line, stats)
        if not normalized:
            stats["removed_noise_lines"] += 1
            continue
        if _is_adlib_line(normalized):
            stats["removed_noise_lines"] += 1
            continue
        normalized_lines.append(normalized)

    selected_lines = _select_lines(normalized_lines, stats)
    final_text = ". ".join(selected_lines)
    final_text = MULTISPACE_RE.sub(" ", final_text).strip()
    final_text = _truncate_text(final_text)

    if len(final_text) < MIN_ANALYSIS_CHARS:
        fallback = _truncate_text(MULTISPACE_RE.sub(" ", original_text))
        final_text = fallback
        stats["used_fallback"] = True

    stats["final_chars"] = len(final_text)
    stats["final_lines"] = len(selected_lines)

    return {"text": final_text, "stats": stats}
