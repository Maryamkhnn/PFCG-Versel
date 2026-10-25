

import re
import json
from html import unescape

from sqlalchemy import text

from app.database import db


# ============================================================
# GET USER CONTENT
# ==========================================a==================

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


def analyze_seo(content, keyword, seo_title="", meta_description="", fallback_title=""):
    """PFCG editorial rubric v3. Thresholds are product heuristics, not Google rules."""
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Please enter content first.")
    if not isinstance(keyword, str) or not keyword.strip():
        raise ValueError("Please enter a target keyword.")
    if len(content) > 200000 or len(keyword) > 200:
        raise ValueError("Use at most 200,000 content characters and 200 keyword characters.")
    plain = clean_html(content)
    words = get_words(plain)
    if not words:
        raise ValueError("Please enter readable content.")
    # This rubric's syllable estimator supports English only.
    letters = [c for c in plain if c.isalpha()]
    if letters and sum(c.isascii() for c in letters) / len(letters) < .9:
        raise ValueError("This version supports English content only.")
    keyword = normalize_text(keyword)
    pattern = r"(?<!\w)" + r"\s+".join(re.escape(x) for x in keyword.split()) + r"(?!\w)"
    def matches(value):
        return len(re.findall(pattern, normalize_text(value), re.I))
    count = matches(plain)
    density = round(count / len(words) * 100, 2)
    headings = extract_seo_headings(content)
    blocks = re.split(r"\n\s*\n|</p\s*>|</div\s*>|<br\s*/?>", content, flags=re.I)
    paragraphs = [clean_html(b) for b in blocks if clean_html(b)]
    long_paragraphs = [{"number": i+1, "words": len(get_words(p))}
                       for i,p in enumerate(paragraphs) if len(get_words(p)) > 120]
    sentences = [s.strip() for s in re.split(r"[.!?]+", plain) if get_words(s)]
    long_sentences = [{"number": i+1, "words": len(get_words(s)), "excerpt": s[:140]}
                      for i,s in enumerate(sentences) if len(get_words(s)) > 30]
    readability = calculate_readability(words, plain)
    title = normalize_text(seo_title or fallback_title)
    meta = normalize_text(meta_description)
    checks = []
    def add(category, earned, maximum, detail):
        checks.append({"category": category, "earned": earned, "maximum": maximum,
                       "status": "Pass" if earned == maximum else "Review", "detail": detail})
    title_points = (10 if title else 0) + (10 if matches(title) else 0)
    add("Title", title_points, 20,
        "Title provided; exact target phrase present." if title_points == 20 else
        "Add a descriptive title and review how it relates to the target phrase. Exact matching is only a proxy for relevance.")
    intro = matches(" ".join(words[:100])) > 0
    key_points = (15 if count else 0) + (5 if intro else 0)
    add("Keyword coverage", key_points, 20,
        f"{count} exact phrase matches; {density}% occurrence density. No ideal density target is scored."
        + (" Introduce the topic clearly near the start." if not intro else " Topic phrase appears near the start."))
    heading_needed = len(words) >= 300
    heading_points = 15 if not heading_needed or headings else 0
    add("Section structure", heading_points, 15,
        f"{len(headings)} possible headings detected. Plain-text detection is approximate."
        if headings else "Short content: headings are optional." if not heading_needed else
        "Consider descriptive section headings for this longer article.")
    read_points = 15 if readability >= 60 else 10 if readability >= 45 else 5 if readability >= 30 else 0
    add("Reading ease", read_points, 15,
        f"Estimated English Flesch score: {readability}/100. Technical vocabulary can lower it; retain necessary terms.")
    paragraph_points = round(15 * (1-len(long_paragraphs)/max(1,len(paragraphs))))
    add("Paragraph length", paragraph_points, 15,
        "; ".join(f"Paragraph {p['number']}: {p['words']} words; consider splitting." for p in long_paragraphs[:5])
        or "No paragraph exceeds PFCG's 120-word review threshold.")
    # Description presence is assessed; character length is informational, never a Google limit.
    add("Meta description", 10 if meta else 0, 10,
        f"Description supplied ({len(meta)} characters). Review accuracy and usefulness manually."
        if meta else "Add a short, accurate summary for use when publishing. No fixed Google character limit is assumed.")
    normalized = [normalize_text(s).lower() for s in sentences]
    duplicates = len(normalized)-len(set(normalized))
    add("Sentence repetition", 5 if not duplicates else 0, 5,
        f"{duplicates} repeated sentence occurrences detected." if duplicates else "No exact repeated sentences detected.")
    score = sum(c["earned"] for c in checks)
    status = "Strong content checks" if score >= 85 else "Good content checks" if score >= 70 else "Needs improvement" if score >= 50 else "Needs substantial review"
    suggestions = [c["detail"] for c in checks if c["status"] == "Review"]
    suggestions += [f"Sentence {s['number']} has {s['words']} words: consider simplifying. {s['excerpt']}" for s in long_sentences[:5]]
    suggestions.append("Manually review factual accuracy, search intent and completeness. These are not measured by this score.")
    return {"scoring_version": "pfcg-content-v3", "word_count": len(words),
            "keyword_count": count, "keyword_density": density,
            "heading_count": len(headings), "paragraph_count": len(paragraphs),
            "readability_score": readability, "seo_score": score, "seo_status": status,
            "keyword_in_first_part": intro, "keyword_in_headings": any(matches(h) for h in headings),
            "checks": checks, "score_breakdown": {c["category"]: {"earned":c["earned"], "maximum":c["maximum"]} for c in checks},
            "long_paragraphs": long_paragraphs, "long_sentences": long_sentences,
            "suggestions": suggestions, "seo_title": title, "meta_description": meta}


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
                    content,
                    report_json,
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
    :content,
    :report_json,
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
                "content": data.get("content"),
                "report_json": json.dumps({"keyword": data.get("keyword"), "content": data.get("content"), "report": data.get("report")}, ensure_ascii=False),
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
                report_json,
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
            "saved_report": json.loads(row["report_json"]) if isinstance(row["report_json"], str) and row["report_json"] else row["report_json"],
             "source_id": row["source_id"],
            "source_type": row["source_type"] or "manual",
            
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

def apply_ai_metadata_scoring(result):
    review = result.get("ai_review") or {}
    available = review.get("status") == "available"

    ai_checks = {
        check["category"]: check
        for check in review.get("checks", [])
        if isinstance(check, dict) and "category" in check
    }

    categories = {
        "Title": ("Title relevance", 20),
        "Meta description": ("Meta description", 10)
    }

    updated_checks = []
    old_metadata_details = set()
    metadata_suggestions = []
    major_issue = False

    for original in result.get("checks", []):
        check = dict(original)
        category = check.get("category")

        if category in categories:
            ai_category, maximum = categories[category]
            finding = ai_checks.get(ai_category)

            old_metadata_details.add(check.get("detail", ""))

            if not available or not finding:
                check.update({
                    "earned": 0,
                    "maximum": maximum,
                    "status": "Not assessed",
                    "detail": (
                        "AI relevance assessment unavailable. "
                        "No points awarded for this category; "
                        "the total is provisional."
                    )
                })

                metadata_suggestions.append(
                    f"{category}: relevance was not assessed."
                )

            else:
                severity = finding.get("severity")

                points = {
                    "none": maximum,
                    "minor": maximum // 2,
                    "major": 0,
                    "missing": 0
                }

                if severity not in points:
                    raise ValueError(
                        "Invalid AI metadata assessment."
                    )

                major_issue = (
                    major_issue or severity == "major"
                )

                check.update({
                    "earned": points[severity],
                    "maximum": maximum,
                    "status": finding["status"],
                    "severity": severity,
                    "detail": finding["explanation"]
                })

                suggestion = finding.get("suggestion", "")

                if suggestion:
                    metadata_suggestions.append(
                        f"{category}: {suggestion}"
                    )

        updated_checks.append(check)

    total = sum(
        check["earned"]
        for check in updated_checks
    )

    provisional = any(
        check.get("status") == "Not assessed"
        for check in updated_checks
    )

    if provisional:
        status = "Provisional — AI relevance not assessed"
    elif major_issue:
        status = "Needs metadata correction"
    elif total >= 85:
        status = "Strong content checks"
    elif total >= 70:
        status = "Good content checks"
    elif total >= 50:
        status = "Needs improvement"
    else:
        status = "Needs substantial review"

    suggestions = [
        suggestion
        for suggestion in result.get("suggestions", [])
        if suggestion not in old_metadata_details
    ]

    result.update({
        "scoring_version": "pfcg-content-v4-ai-metadata",
        "score_provisional": provisional,
        "checks": updated_checks,
        "seo_score": total,
        "seo_status": status,
        "score_breakdown": {
            check["category"]: {
                "earned": check["earned"],
                "maximum": check["maximum"]
            }
            for check in updated_checks
        },
        "suggestions": metadata_suggestions + suggestions
    })

    return result