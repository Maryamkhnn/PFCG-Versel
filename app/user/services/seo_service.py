import re
from html import unescape

from sqlalchemy import text

from app.database import db


# ============================================================
# GET USER CONTENT
# ============================================================

def get_user_content(user_email):

    if not user_email:
        return []

    rows = db.session.execute(
        text("""
            SELECT *
            FROM
            (
                SELECT
                    gc.id AS source_id,
                    'ai' AS source_type,
                    CONCAT('ai-', gc.id) AS content_key,
                    COALESCE(NULLIF(TRIM(gc.topic), ''),
                             'Untitled Content') AS topic,
                    gc.content,
                    gc.word_count,
                    COALESCE(NULLIF(TRIM(gc.content_type), ''),
                             'Content') AS content_type,
                    gc.created_at,
                    EXISTS (
                        SELECT 1
                        FROM saved_documents AS sd
                        WHERE sd.user_id = gc.user_id
                          AND sd.source_type = 'ai'
                          AND CAST(sd.content AS BINARY)
                              = CAST(gc.content AS BINARY)
                    ) AS is_saved
                FROM generated_content AS gc
                WHERE LOWER(TRIM(gc.user_email))
                    = LOWER(TRIM(:user_email))

                UNION ALL

                SELECT
                    hh.id AS source_id,
                    'humanized' AS source_type,
                    CONCAT('humanized-', hh.id) AS content_key,
                    COALESCE(
                        NULLIF(TRIM((
                            SELECT gc2.topic
                            FROM generated_content AS gc2
                            WHERE LOWER(TRIM(gc2.user_email))
                                = LOWER(TRIM(hh.user_email))
                              AND CAST(gc2.content AS BINARY)
                                = CAST(hh.original_content AS BINARY)
                            ORDER BY gc2.id DESC
                            LIMIT 1
                        )), ''),
                        CONCAT('Humanized Content #', hh.id)
                    ) AS topic,
                    hh.humanized_content AS content,
                    hh.word_count,
                    'Humanized' AS content_type,
                    hh.created_at,
                    EXISTS (
                        SELECT 1
                        FROM saved_documents AS sd
                        WHERE sd.user_id = hh.user_id
                          AND sd.source_type = 'humanized'
                          AND CAST(sd.content AS BINARY)
                              = CAST(hh.humanized_content AS BINARY)
                    ) AS is_saved
                FROM humanized_history AS hh
                WHERE LOWER(TRIM(hh.user_email))
                    = LOWER(TRIM(:user_email))
            ) AS user_content
            ORDER BY created_at DESC, source_id DESC
        """),
        {"user_email": user_email}
    ).mappings().all()

    return [
        {
            "id": row["source_id"],
            "source_id": row["source_id"],
            "source_type": row["source_type"],
            "content_key": row["content_key"],
            "topic": row["topic"] or "Untitled Content",
            "content": row["content"] or "",
            "word_count": row["word_count"] or 0,
            "content_type": row["content_type"] or "Content",
            "created_at": (
                row["created_at"].isoformat()
                if row["created_at"]
                else ""
            ),
            "is_saved": bool(row["is_saved"])
        }
        for row in rows
    ]


# ============================================================
# GET ONE USER-OWNED DOCUMENT
# ============================================================

def get_content_by_id(content_id, user_email, source_type="ai"):

    if not content_id or not user_email:
        return None

    if isinstance(content_id, bool):
        return None

    if not isinstance(content_id, (int, str)):
        return None

    try:
        content_id = int(content_id)
    except (TypeError, ValueError):
        return None

    if content_id <= 0:
        return None

    source_type = str(source_type or "ai").strip().lower()

    if source_type not in {"ai", "humanized"}:
        return None

    if source_type == "humanized":
        query = text("""
            SELECT
                hh.id,
                COALESCE(
                    NULLIF(TRIM((
                        SELECT gc.topic
                        FROM generated_content AS gc
                        WHERE LOWER(TRIM(gc.user_email))
                            = LOWER(TRIM(hh.user_email))
                          AND CAST(gc.content AS BINARY)
                            = CAST(hh.original_content AS BINARY)
                        ORDER BY gc.id DESC
                        LIMIT 1
                    )), ''),
                    CONCAT('Humanized Content #', hh.id)
                ) AS topic,
                hh.humanized_content AS content,
                hh.word_count,
                'Humanized' AS content_type,
                hh.created_at
            FROM humanized_history AS hh
            WHERE hh.id = :content_id
              AND LOWER(TRIM(hh.user_email))
                = LOWER(TRIM(:user_email))
            LIMIT 1
        """)
    else:
        query = text("""
            SELECT
                gc.id,
                gc.topic,
                gc.content,
                gc.word_count,
                gc.content_type,
                gc.created_at
            FROM generated_content AS gc
            WHERE gc.id = :content_id
              AND LOWER(TRIM(gc.user_email))
                = LOWER(TRIM(:user_email))
            LIMIT 1
        """)

    row = db.session.execute(
        query,
        {
            "content_id": content_id,
            "user_email": user_email
        }
    ).mappings().first()

    if not row:
        return None

    return {
        "id": row["id"],
        "source_id": row["id"],
        "source_type": source_type,
        "content_key": f"{source_type}-{row['id']}",
        "topic": row["topic"] or "Untitled Content",
        "content": row["content"] or "",
        "word_count": row["word_count"] or 0,
        "content_type": row["content_type"] or "Content",
        "created_at": (
            row["created_at"].isoformat()
            if row["created_at"]
            else ""
        )
    }


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(value):

    value = unescape(value or "")
    value = value.replace("\xa0", " ")
    value = value.replace("’", "'").replace("‘", "'")

    for dash in ("‑", "–", "—"):
        value = value.replace(dash, "-")

    return re.sub(r"\s+", " ", value).strip()


def clean_html(content):

    # Strip markup before decoding entities so encoded literal
    # text is not accidentally treated as an HTML tag.
    content = re.sub(
        r"<[^>]+>",
        " ",
        content or ""
    )

    return normalize_text(content)


def get_words(content):

    return re.findall(
        r"\b[\w'-]+\b",
        content or ""
    )


def count_syllables(word):

    word = re.sub(r"[^a-z]", "", word.lower())

    if not word:
        return 0

    syllables = len(re.findall(r"[aeiouy]+", word))

    if word.endswith("e") and syllables > 1:
        syllables -= 1

    return max(1, syllables)


def calculate_readability(words, content):
    """
    Approximate English Flesch Reading Ease score.
    Syllable and sentence detection are heuristic.
    """

    if not words:
        return 0

    sentences = [
        sentence
        for sentence in re.split(r"[.!?]+", content)
        if sentence.strip()
    ]

    sentence_count = max(1, len(sentences))
    word_count = len(words)

    syllable_count = sum(
        count_syllables(word)
        for word in words
    )

    score = (
        206.835
        - 1.015 * (word_count / sentence_count)
        - 84.6 * (syllable_count / word_count)
    )

    return round(max(0, min(score, 100)), 2)


# ============================================================
# HEADING DETECTION
# ============================================================

def extract_seo_headings(content):
    """
    Recognize HTML, Markdown and likely plain-text headings.

    Plain-text headings cannot be identified perfectly without
    explicit markup; short standalone lines are a heuristic.
    """

    content = content or ""

    html_headings = re.findall(
        r"<h([1-6])\b[^>]*>(.*?)</h\1\s*>",
        content,
        flags=re.IGNORECASE | re.DOTALL
    )

    if html_headings:
        return [
            clean_html(heading)
            for _, heading in html_headings
            if clean_html(heading)
        ]

    source = re.sub(
        r"<br\s*/?>|</(?:p|div|li)>",
        "\n",
        content,
        flags=re.IGNORECASE
    )

    source = re.sub(r"<[^>]+>", "", source)
    source = unescape(source)

    headings = []

    for raw_line in source.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        markdown_match = re.match(
            r"^#{1,6}\s+(.+?)(?:\s+#+)?$",
            line
        )

        if markdown_match:
            heading = normalize_text(markdown_match.group(1))

            if heading:
                headings.append(heading)

            continue

        # Ignore decorative separators.
        if re.fullmatch(r"[-*_=\s]+", line):
            continue

        # Ignore bullet-list items.
        if re.match(r"^(?:[-+*•])\s+", line):
            continue

        # Allow *Heading* and numbered section headings.
        line = line.strip("*_ ")
        line = re.sub(r"^\d+[.)]\s+", "", line)
        line = normalize_text(line)

        heading_words = get_words(line)

        if (
            1 <= len(heading_words) <= 16
            and len(line) <= 140
            and not line.endswith((".", "!", "?", ";", ","))
        ):
            headings.append(line)

    return headings


def has_keyword_in_heading(content, keyword_pattern):

    return any(
        re.search(
            keyword_pattern,
            heading,
            flags=re.IGNORECASE
        )
        for heading in extract_seo_headings(content)
    )


# ============================================================
# PARAGRAPH COUNT
# Existing counting approach retained.
# ============================================================

def count_paragraphs(content):

    blocks = re.split(
        r"(?:\r?\n\s*\r?\n|</p>|<br\s*/?>)",
        content,
        flags=re.IGNORECASE
    )

    paragraphs = [
        clean_html(block)
        for block in blocks
        if clean_html(block)
    ]

    return max(1, len(paragraphs))


def analyze_seo(
    content,
    keyword,
    seo_title="",
    meta_description="",
    fallback_title=""
):
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Please load or enter content first.")

    if not isinstance(keyword, str) or not keyword.strip():
        raise ValueError("Please enter a target keyword.")

    content = content.strip()
    keyword = normalize_text(keyword)
    plain_content = clean_html(content)

    words = get_words(plain_content)
    word_count = len(words)

    if not word_count:
        raise ValueError("Please enter readable content.")

    keyword_pattern = (
        r"(?<![a-zA-Z0-9])"
        + re.escape(keyword)
        + r"(?![a-zA-Z0-9])"
    )

    def contains_keyword(value):
        return bool(
            re.search(
                keyword_pattern,
                value,
                flags=re.IGNORECASE
            )
        )

    keyword_count = len(
        re.findall(
            keyword_pattern,
            plain_content,
            flags=re.IGNORECASE
        )
    )

    keyword_density = round(
        keyword_count / word_count * 100,
        2
    )

    keyword_in_first_part = contains_keyword(
        " ".join(words[:100])
    )

    headings = extract_seo_headings(content)
    heading_count = len(headings)

        # Match the exact keyword first.
    keyword_in_headings = any(
        contains_keyword(heading)
        for heading in headings
    )

    # Recognize abbreviations explicitly defined in the document.
    # Example: Artificial intelligence (AI).
    # Keyword counts and density remain exact-match measurements.
    if (
        not keyword_in_headings
        and re.fullmatch(r"[A-Za-z]{2,8}", keyword)
    ):
        abbreviation = keyword.upper()

        definition_pattern = (
            r"((?:[A-Za-z][A-Za-z'-]*\s+){1,7}"
            r"[A-Za-z][A-Za-z'-]*)"
            r"\s*\(\s*"
            + re.escape(abbreviation)
            + r"\s*\)"
        )

        definitions = re.finditer(
            definition_pattern,
            plain_content,
            flags=re.IGNORECASE
        )

        for definition in definitions:
            preceding_words = definition.group(1).split()

            # Take the words immediately before the abbreviation.
            expanded_words = preceding_words[-len(abbreviation):]

            initials = "".join(
                word[0] for word in expanded_words
            ).upper()

            if initials != abbreviation:
                continue

            expanded_phrase = " ".join(expanded_words)

            expanded_pattern = (
                r"(?<!\w)"
                + re.escape(expanded_phrase)
                + r"(?!\w)"
            )

            if any(
                re.search(
                    expanded_pattern,
                    normalize_text(heading),
                    flags=re.IGNORECASE
                )
                for heading in headings
            ):
                keyword_in_headings = True
                break

    paragraph_count = count_paragraphs(content)

    readability_score = calculate_readability(
        words,
        plain_content
    )

    # PFCG heuristic rubric v2: 65 possible points, not search-engine criteria.
    # Title and metadata checks are excluded entirely.
    score = 0

    # Keyword use: 25 points.
    if keyword_count > 0:
        score += 5

    if keyword_in_first_part:
        score += 8

    if keyword_count >= 2:
        score += 3

    if 0.5 <= keyword_density <= 2.5:
        score += 9
    elif 0.3 <= keyword_density < 0.5:
        score += 4
    elif 2.5 < keyword_density <= 3:
        score += 4
    elif keyword_density > 3:
        score -= 10

    # Headings: 15 points.
    if heading_count >= 2:
        score += 5

    if keyword_in_headings:
        score += 10

    # Readability: 15 points.
    if readability_score >= 60:
        score += 15
    elif readability_score >= 45:
        score += 10
    elif readability_score >= 30:
        score += 5

    # Paragraph structure: 10 points.
    if paragraph_count >= 3:
        score += 10
    elif paragraph_count >= 2:
        score += 5

    # Length is reported, not scored: the requested length is not supplied
    # to this analyzer, and a longer document is not automatically better.
    seo_score = round(max(0, min(score, 65)) / 65 * 100)

    if seo_score >= 85:
        seo_status = "Excellent SEO"
    elif seo_score >= 70:
        seo_status = "Good SEO"
    elif seo_score >= 50:
        seo_status = "Needs Improvement"
    else:
        seo_status = "Poor SEO"

    suggestions = []

    if keyword_count == 0:
        suggestions.append(
            "The exact target keyword was not found. "
            "Choose a phrase relevant to the content and "
            "include it naturally."
        )
    else:
        if not keyword_in_first_part:
            suggestions.append(
                "Introduce the target keyword naturally "
                "within the first 100 words."
            )

        if keyword_density < 0.5:
            suggestions.append(
                "The target phrase appears infrequently under "
                "this application's rules. Review relevance "
                "without adding forced repetition."
            )
        elif 2.5 < keyword_density <= 3:
            suggestions.append(
                "Keyword density is between 2.5% and 3%. This application's "
                "rubric awards 4/9 density points here. Check for unnecessary "
                "repetition; do not remove useful technical terms just for the score."
            )
        elif keyword_density > 3:
            suggestions.append(
                "Review repeated uses of the target keyword "
                "and remove unnecessary repetition."
            )

    if heading_count < 2:
        suggestions.append(
            "Where appropriate, organize the content using "
            "clear headings on separate lines."
        )

    if not keyword_in_headings:
        suggestions.append(
            "Use the target keyword in a relevant heading "
            "where it reads naturally."
        )

    if paragraph_count < 3:
        suggestions.append(
            "Where the format allows, divide long content "
            "into readable paragraphs."
        )

    if readability_score < 60:
        suggestions.append(
            f"Estimated reading ease is {readability_score}/100. This heuristic "
            "uses sentence length and estimated syllables; technical vocabulary "
            "can lower it. Review overloaded sentences and preserve necessary terms."
        )

    if keyword_count == 1:
        suggestions.append(
            "The exact keyword appears once (0/3 repeat-use points). "
            "Only use it again if it helps explain the topic naturally."
        )

    if not suggestions:
        suggestions.append(
            "No additional suggestions were triggered. "
            "Review accuracy and relevance before publishing."
        )

    keyword_points = (
        (5 if keyword_count else 0)
        + (8 if keyword_in_first_part else 0)
        + (3 if keyword_count >= 2 else 0)
        + (9 if 0.5 <= keyword_density <= 2.5 else
           4 if 0.3 <= keyword_density < 0.5 or 2.5 < keyword_density <= 3 else
           -10 if keyword_density > 3 else 0)
    )
    heading_points = (5 if heading_count >= 2 else 0) + (10 if keyword_in_headings else 0)
    readability_points = (15 if readability_score >= 60 else 10 if readability_score >= 45
                          else 5 if readability_score >= 30 else 0)
    paragraph_points = 10 if paragraph_count >= 3 else 5 if paragraph_count >= 2 else 0
    suggestions.insert(0,
        f"Score breakdown: keyword use {keyword_points}/25; headings {heading_points}/15; "
        f"reading ease {readability_points}/15; paragraph structure {paragraph_points}/10. "
        "Length is not scored. These are PFCG checks, not search-engine ranking factors."
    )
    return {
        "scoring_version": "pfcg-content-v2",
        "score_breakdown": {
            "keyword_use": keyword_points, "headings": heading_points,
            "readability": readability_points, "paragraphs": paragraph_points,
            "maximum": 65
        },
        "word_count": word_count,
        "keyword_count": keyword_count,
        "keyword_density": keyword_density,
        "heading_count": heading_count,
        "paragraph_count": paragraph_count,
        "keyword_in_first_part": keyword_in_first_part,
        "keyword_in_headings": keyword_in_headings,
        "readability_score": readability_score,
        "seo_score": seo_score,
        "seo_status": seo_status,
        "suggestions": suggestions
    }
# ============================================================
# SAVE SEO ANALYSIS
# ============================================================

def save_seo_analysis(data):

    source_type = str(
        data.get("source_type") or "manual"
    ).strip().lower()

    if source_type not in {"ai", "humanized", "manual"}:
        raise ValueError("Invalid SEO content source.")

    source_id = data.get("source_id")

    if source_type == "manual":
        source_id = None
    elif not source_id:
        raise ValueError("SEO source ID is required.")

    try:
        db.session.execute(
            text("""
                INSERT INTO seo_history
                (
                    user_email,
                    content_id,
                    source_type,
                    source_id,
                    content_topic,
                    word_count,
                    seo_score,
                    readability_score,
                    keyword_density,
                    keyword_count,
                    seo_status
                )
                VALUES
                (
                    :user_email,
                    :content_id,
                    :source_type,
                    :source_id,
                    :content_topic,
                    :word_count,
                    :seo_score,
                    :readability_score,
                    :keyword_density,
                    :keyword_count,
                    :seo_status
                )
            """),
            {
                "user_email": data.get("user_email"),
                "content_id": data.get("content_id"),
                "source_type": source_type,
                "source_id": source_id,
                "content_topic": data.get("content_topic"),
                "word_count": data.get("word_count", 0),
                "seo_score": data.get("seo_score", 0),
                "readability_score": data.get(
                    "readability_score", 0
                ),
                "keyword_density": data.get(
                    "keyword_density", 0
                ),
                "keyword_count": data.get(
                    "keyword_count", 0
                ),
                "seo_status": data.get("seo_status", "")
            }
        )

        db.session.commit()

    except Exception:
        db.session.rollback()
        raise


# ============================================================
# GET SEO HISTORY
# ============================================================

def get_seo_history(user_email):

    if not user_email:
        return []

    rows = db.session.execute(
        text("""
            SELECT
                id,
                content_id,
                source_type,
                source_id,
                content_topic,
                word_count,
                seo_score,
                readability_score,
                keyword_density,
                keyword_count,
                seo_status,
                created_at

            FROM seo_history

            WHERE user_email = :user_email

            ORDER BY created_at DESC, id DESC
        """),
        {"user_email": user_email}
    ).mappings().all()

    return [
        {
            "id": row["id"],
            "content_id": row["content_id"],
            "source_type": row["source_type"] or "manual",
            "source_id": row["source_id"],
            "content_topic": (
                row["content_topic"]
                or "Untitled Content"
            ),
            "word_count": row["word_count"] or 0,
            "seo_score": float(row["seo_score"] or 0),
            "readability_score": float(
                row["readability_score"] or 0
            ),
            "keyword_density": float(
                row["keyword_density"] or 0
            ),
            "keyword_count": row["keyword_count"] or 0,
            "seo_status": row["seo_status"] or "",
            "created_at": (
                row["created_at"].isoformat()
                if row["created_at"]
                else ""
            )
        }
        for row in rows
    ]
