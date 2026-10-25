# ============================================================
# PFCG PLAGIARISM SERVICE - V6
# Reliable Web Evidence + Coverage Aware Scoring
# ============================================================

import os
from dotenv import load_dotenv

load_dotenv()
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from rapidfuzz import fuzz
import base64
from urllib.parse import urlparse, parse_qs, unquote
from difflib import SequenceMatcher


# ============================================================
# CONFIGURATION
# ============================================================

MAX_SENTENCES_TO_CHECK = 12

MAX_SEARCH_RESULTS = 5
MAX_PAGES_PER_SENTENCE = 5
MAX_TOTAL_PAGES = 25

SEARCH_TIMEOUT = 4
PAGE_TIMEOUT = 8

SEARCH_WORKERS = 4
PAGE_WORKERS = 6

MIN_SENTENCE_WORDS = 7
MIN_PAGE_WORDS = 35
MAX_PAGE_WORDS = 8000

SEARCH_RETRIES = 1

# Match thresholds
STRONG_SIMILARITY = 78
MEDIUM_SIMILARITY = 68

MIN_EXACT_PHRASE_WORDS = 5
MIN_DISTINCTIVE_OVERLAP = 4

_thread_local = threading.local()


# ============================================================
# REQUEST SESSION
# ============================================================

def get_session():

    if not hasattr(_thread_local, "session"):

        session = requests.Session()

        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        })

        _thread_local.session = session

    return _thread_local.session


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value):

    if not value:
        return ""

    value = str(value).lower()

    value = (
        value
        .replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("–", "-")
        .replace("—", "-")
    )

    value = re.sub(
        r"[^a-z0-9\s'-]",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def tokenize(value):

    normalized = normalize_text(value)

    if not normalized:
        return []

    return normalized.split()


# ============================================================
# COMMON WORDS
# ============================================================

COMMON_WORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in",
    "on", "for", "with", "from", "by", "is", "are",
    "was", "were", "be", "been", "being", "this", "that",
    "these", "those", "it", "its", "they", "their",
    "there", "as", "at", "which", "who", "can", "may",
    "might", "will", "would", "should", "has", "have",
    "had", "do", "does", "did", "into", "also", "than",
    "then", "such", "more", "most", "very", "many",
    "some", "other", "each", "both", "over", "under",
    "through", "about", "between", "while", "where",
    "when", "how", "why", "our", "your", "my", "we",
    "you", "he", "she", "them", "his", "her"
}


# ============================================================
# SENTENCE SPLITTING
# ============================================================

def split_sentences(text):

    if not text:
        return []

    text = str(text).strip()

    # Keep line breaks so headings/titles can be identified.
    blocks = re.split(
        r"\n+",
        text
    )

    sentences = []

    for block in blocks:

        block = block.strip()

        if not block:
            continue

        word_count = len(tokenize(block))

        # Skip heading/title-like standalone lines.
        # A heading usually has no sentence-ending punctuation.
        if (
            word_count <= 12
            and not re.search(r'[.!?]["”’\']?$', block)
        ):
            continue

        parts = re.split(
            r'(?<=[.!?])(?:["”’\']*)\s+',
            block
        )

        for part in parts:

            part = re.sub(
                r"\s+",
                " ",
                part
            ).strip()

            if not part:
                continue

            if len(tokenize(part)) >= MIN_SENTENCE_WORDS:
                sentences.append(part)

    return sentences


# ============================================================
# SELECT REPRESENTATIVE SENTENCES
# ============================================================

def get_important_sentences(text):

    sentences = split_sentences(text)

    if len(sentences) <= MAX_SENTENCES_TO_CHECK:
        return sentences

    selected = []

    total = len(sentences)

    for i in range(MAX_SENTENCES_TO_CHECK):

        position = round(
            i * (total - 1)
            / (MAX_SENTENCES_TO_CHECK - 1)
        )

        sentence = sentences[position]

        if sentence not in selected:
            selected.append(sentence)

    return selected

# ============================================================
# DISTINCTIVE WORDS
# ============================================================

def distinctive_words(text):

    return [
        word
        for word in tokenize(text)
        if word not in COMMON_WORDS
        and len(word) >= 4
    ]


# ============================================================
# SEARCH PHRASE
# ============================================================

def best_search_phrase(sentence):

    words = tokenize(sentence)

    if not words:
        return ""

    if len(words) <= 10:
        return " ".join(words)

    best = []
    best_score = -1

    for size in (10, 9, 8, 7, 6):

        if len(words) < size:
            continue

        for i in range(len(words) - size + 1):

            window = words[i:i + size]

            useful = sum(
                1
                for word in window
                if word not in COMMON_WORDS
                and len(word) >= 4
            )

            score = useful * 10 + size

            if score > best_score:

                best_score = score
                best = window

    return " ".join(best)


# ============================================================
# BUILD SEARCH QUERIES
# ============================================================

def build_queries(sentence, topic=""):

    queries = []

    phrase = best_search_phrase(sentence)

    if phrase:
     queries.append(f'"{phrase}"')

    useful = distinctive_words(sentence)

    if useful:

        keyword_query = " ".join(
            useful[:10]
        )

        if topic:

            topic_words = distinctive_words(topic)

            if topic_words:

                keyword_query = (
                    " ".join(topic_words[:3])
                    + " "
                    + keyword_query
                )

        queries.append(keyword_query)

    # Third query: slightly shorter exact phrase.
    words = tokenize(sentence)

    if len(words) >= 7:

        short_phrase = best_search_phrase(
            " ".join(words[:max(7, len(words) // 2)])
        )

        if short_phrase:
            queries.append(
                f'"{short_phrase}"'
            )

    output = []
    seen = set()

    for query in queries:

        key = normalize_text(query)

        if not key or key in seen:
            continue

        seen.add(key)
        output.append(query)

    return output[:2]


# ============================================================
# URL HELPERS
# ============================================================

def usable_url(url):

    if not url:
        return False

    try:

        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return False

        domain = parsed.netloc.lower()

        if not domain:
            return False

        blocked = {
            "bing.com",
            "www.bing.com",
            "duckduckgo.com",
            "www.duckduckgo.com",
            "google.com",
            "www.google.com",
        }

        if domain in blocked:
            return False

        return True

    except Exception:
        return False


def normalize_url(url):

    try:

        parsed = urlparse(url)

        return urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            "",
            "",
            ""
        ))

    except Exception:
        return url

# ============================================================
# Tavily SEARCH
# ============================================================


def search_tavily(query):
    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        print("[TAVILY ERROR] API key missing")
        return {
            "success": False,
            "results": []
        }

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            headers={
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "query": query,
                "search_depth": "basic",
                "max_results": MAX_SEARCH_RESULTS,
                "include_answer": False,
                "include_raw_content": False
            },
            timeout=15
        )

        if response.status_code != 200:
            print(
                "[TAVILY ERROR]",
                "HTTP",
                response.status_code,
                response.text[:150]
            )
            return {
                "success": False,
                "results": []
            }

        cleaned = []

        for item in response.json().get("results", []):
            url = item.get("url", "")

            if not usable_url(url):
                continue

            cleaned.append({
                "url": url,
                "title": item.get("title", ""),
                "snippet": item.get("content", ""),
                "engine": "Tavily"
            })

        return {
            "success": True,
            "results": cleaned
        }

    except requests.RequestException as error:
        print(
            "[TAVILY ERROR]",
            type(error).__name__,
            str(error)[:150]
        )

        return {
            "success": False,
            "results": []
        }

# ============================================================
# DDGS SEARCH
# ============================================================

def search_ddgs(query):

    try:

        try:
            ddgs = DDGS(
                timeout=SEARCH_TIMEOUT
            )
        except TypeError:
            ddgs = DDGS()

        results = ddgs.text(
            query,
            max_results=MAX_SEARCH_RESULTS
        )

        cleaned = []

        for result in results or []:

            if not isinstance(result, dict):
                continue

            url = (
                result.get("href")
                or result.get("url")
                or ""
            )

            if not usable_url(url):
                continue

            cleaned.append({
                "url": url,
                "title": result.get("title", ""),
                "snippet": (
                    result.get("body")
                    or result.get("snippet")
                    or ""
                ),
                "engine": "DDGS"
            })

        # Search request completed successfully.
        # An empty list simply means no usable results were found.
        return {
            "success": True,
            "results": cleaned
        }

    except Exception as error:

        print(
            "[DDGS ERROR]",
            type(error).__name__,
            str(error)[:200]
        )

        # This means the search itself failed.
        return {
            "success": False,
            "results": []
        }


# ============================================================
# BING SEARCH
# ============================================================

def search_bing(query):

    def decode_bing_url(url):
        if not url:
            return ""

        parsed = urlparse(url)

        # Decode Bing tracking links.
        if parsed.netloc.lower() in ("bing.com", "www.bing.com"):
            if parsed.path.startswith("/ck/a"):
                encoded = parse_qs(parsed.query).get("u", [""])[0]

                if not encoded:
                    return ""

                if encoded.startswith("a1"):
                    encoded = encoded[2:]

                try:
                    encoded += "=" * (-len(encoded) % 4)
                    decoded = base64.urlsafe_b64decode(
                        encoded
                    ).decode("utf-8", errors="replace")

                    if decoded.startswith(("https://", "http://")):
                        return decoded

                except Exception:
                    return ""

                return ""

        return url

    try:
        response = get_session().get(
            "https://www.bing.com/search",
            params={
                "q": query,
                "count": MAX_SEARCH_RESULTS
            },
            timeout=(4, SEARCH_TIMEOUT)
        )

        if response.status_code != 200:
            return {
                "success": False,
                "results": []
            }

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        print(
        "[BING QUERY]",
        query[:180]
        )
        output = []
        seen_urls = set()

        for item in soup.select("li.b_algo"):

            link = item.select_one("h2 a")

            if not link:
                continue

            raw_url = link.get("href", "")
            url = decode_bing_url(raw_url)

            if not usable_url(url):
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)

            snippet_node = item.select_one(".b_caption p")

            snippet = (
                snippet_node.get_text(" ", strip=True)
                if snippet_node
                else ""
            )

            output.append({
                "url": url,
                "title": link.get_text(" ", strip=True),
                "snippet": snippet,
                "engine": "Bing"
            })
            print(
            "[BING SOURCE]",
            "Title:", link.get_text(" ", strip=True)[:80],
            "| URL:", url[:150]
            )

            if len(output) >= MAX_SEARCH_RESULTS:
                break

        print(
            f"[BING RESULTS] "
            f"Blocks: {len(soup.select('li.b_algo'))} "
            f"| Valid URLs: {len(output)}"
        )

        return {
            "success": True,
            "results": output
        }

    except Exception as error:

        print(
            "[BING ERROR]",
            type(error).__name__,
            str(error)[:200]
        )

        return {
            "success": False,
            "results": []
        }



# ============================================================
# SEARCH ONE QUERY
# ============================================================



def search_query(query):

    started = time.perf_counter()

    # First try Tavily
    response = search_tavily(query)

    print(
        f"[TAVILY TIMING] "
        f"{time.perf_counter() - started:.2f}s "
        f"| Results: {len(response['results'])} "
        f"| Success: {response['success']}"
    )

    # Use DDGS only when Tavily fails or finds no results
    if not response["results"]:

        print("[FALLBACK] Trying DDGS")

        fallback_started = time.perf_counter()

        fallback = search_ddgs(query)

        print(
            f"[DDGS TIMING] "
            f"{time.perf_counter() - fallback_started:.2f}s "
            f"| Results: {len(fallback['results'])} "
            f"| Success: {fallback['success']}"
        )

        if fallback["results"]:
            return fallback

        # Preserve a successful Tavily search with zero results
        if not response["success"]:
            return fallback

    return response



# ============================================================
# SEARCH ONE SENTENCE
# ============================================================


def search_sentence(sentence, topic=""):
    started = time.perf_counter()
    queries = build_queries(sentence, topic)

    all_results = []
    seen = set()
    successful_request = False

    for attempt in range(SEARCH_RETRIES):

        for query in queries:
            response = search_query(query)

            if response.get("success"):
                successful_request = True

            results = response.get("results", [])

            for result in results:
                url = normalize_url(result.get("url", ""))

                if not url or url in seen:
                    continue

                seen.add(url)
                all_results.append(result)

            # Check whether current results contain
            # strong evidence of copied content.
            strong_match_found = False

            for result in all_results:
                match = compare_snippet(sentence, result)

                if match and (
                    match.get("reason") == "strong_exact_phrase"
                    or (
                        match.get("similarity", 0) >= 90
                        and match.get("exact_phrase_words", 0) >= 6
                    )
                ):
                    strong_match_found = True
                    break

            # Strong evidence found: save API credits
            # by skipping the second search query.
            if strong_match_found:
                print("[SEARCH] Strong snippet match found")
                break

        # Avoid retries if a search succeeded or
        # at least one result was collected.
        if successful_request or all_results:
            break

        if attempt < SEARCH_RETRIES - 1:
            time.sleep(0.5 * (attempt + 1))

    # Keep unique results, prioritizing those with
    # stronger evidence of matching content.
    def result_score(item):
        match = compare_snippet(sentence, item)

        if not match:
            return 0

        return match.get("similarity", 0)

    all_results.sort(
        key=result_score,
        reverse=True
    )

    all_results = all_results[:MAX_PAGES_PER_SENTENCE]

    print(
        f"[SEARCH TIMING] {time.perf_counter() - started:.2f}s "
        f"| Queries available: {len(queries)} "
        f"| Results: {len(all_results)} "
        f"| Successful: {successful_request}"
    )

    return {
        "searched": successful_request,
        "results": all_results
    }


# ============================================================
# FETCH PAGE
# ============================================================

def fetch_page(result):

    url = result.get(
        "url",
        ""
    )

    if not usable_url(url):
        return None

    try:

        response = get_session().get(
            url,
            timeout=(
                4,
                PAGE_TIMEOUT
            ),
            allow_redirects=True
        )

        if response.status_code != 200:
            return None

        content_type = (
            response.headers.get(
                "Content-Type",
                ""
            ).lower()
        )

        if (
            "html" not in content_type
            and "text" not in content_type
        ):
            return None

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        for tag in soup([
            "script",
            "style",
            "noscript",
            "svg",
            "nav",
            "footer"
        ]):
            tag.decompose()

        text = soup.get_text(
            " ",
            strip=True
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        words = text.split()

        if len(words) < MIN_PAGE_WORDS:
            return None

        if len(words) > MAX_PAGE_WORDS:

            text = " ".join(
                words[:MAX_PAGE_WORDS]
            )

        return {
            "url": url,
            "title": result.get(
                "title",
                ""
            ),
            "text": text
        }

    except Exception as error:

        print(
            "[PAGE ERROR]",
            url[:100],
            type(error).__name__
        )

        return None


# ============================================================
# FETCH ALL PAGES
# ============================================================

def fetch_pages(search_records):

    unique = {}

    for record in search_records.values():

        for result in record.get(
            "results",
            []
        ):

            url = normalize_url(
                result.get("url", "")
            )

            if not url:
                continue

            if url not in unique:

                unique[url] = result

            if len(unique) >= MAX_TOTAL_PAGES:
                break

        if len(unique) >= MAX_TOTAL_PAGES:
            break

    pages = []

    with ThreadPoolExecutor(
        max_workers=PAGE_WORKERS
    ) as executor:

        futures = [
            executor.submit(
                fetch_page,
                result
            )
            for result in unique.values()
        ]

        for future in as_completed(
            futures
        ):

            try:

                page = future.result()

                if page:
                    pages.append(page)

            except Exception:
                pass

    return pages


# ============================================================
# LONGEST EXACT SHARED PHRASE
# ============================================================

def longest_shared_phrase(
    target,
    source
):

    target_words = tokenize(target)
    source_words = tokenize(source)

    if not target_words or not source_words:
        return ""

    max_size = min(
        14,
        len(target_words)
    )

    source_text = (
        " "
        + " ".join(source_words)
        + " "
    )

    for size in range(
        max_size,
        MIN_EXACT_PHRASE_WORDS - 1,
        -1
    ):

        for i in range(
            len(target_words) - size + 1
        ):

            phrase_words = (
                target_words[i:i + size]
            )

            phrase = " ".join(
                phrase_words
            )

            distinctive = [
                word
                for word in phrase_words
                if word not in COMMON_WORDS
                and len(word) >= 4
            ]

            # Prevent generic five-word overlaps
            if len(distinctive) < 2:
                continue

            if (
                " " + phrase + " "
                in source_text
            ):
                return phrase

    return ""


# ============================================================
# WORD OVERLAP
# ============================================================

def distinctive_overlap(
    target,
    source
):

    target_words = set(
        distinctive_words(target)
    )

    source_words = set(
        distinctive_words(source)
    )

    if not target_words:
        return 0.0, 0

    common = (
        target_words
        .intersection(source_words)
    )

    percentage = (
        len(common)
        / len(target_words)
        * 100
    )

    return percentage, len(common)


# ============================================================
# COMPARE SENTENCE TO SOURCE TEXT
# ============================================================

def compare_text(target_sentence, source_text):

    target_normalized = normalize_text(target_sentence)
    source_normalized = normalize_text(source_text)

    if not target_normalized or not source_normalized:
        return None

    target_words = tokenize(target_sentence)
    source_words = tokenize(source_text)

    if not target_words or not source_words:
        return None

    target_length = len(target_words)

    # Compare against nearby words, not the entire webpage.
    window_size = max(12, target_length * 2)
    step_size = max(1, target_length // 2)

    best = None

    for start in range(0, len(source_words), step_size):

        window_words = source_words[
            start:start + window_size
        ]

        if not window_words:
            continue

        window_text = " ".join(window_words)

        phrase = longest_shared_phrase(
            target_sentence,
            window_text
        )

        similarity = float(
            fuzz.partial_ratio(
                target_normalized,
                window_text
            )
        )

        overlap, shared_count = distinctive_overlap(
            target_sentence,
            window_text
        )

        exact_words = (
            len(tokenize(phrase))
            if phrase
            else 0
        )
        matched_words = sum(
        block.size
        for block in SequenceMatcher(
        None,
        target_words,
        window_words,
        autojunk=False
        ).get_matching_blocks()
        )

        word_coverage = round(
    matched_words / target_length * 100,
    2
)

        valid = False
        reason = ""

        if (
            exact_words >= 7
            and shared_count >= 4
            and overlap >= 40
        ):
            valid = True
            reason = "strong_exact_phrase"

        elif (
            exact_words >= 6
            and similarity >= 75
            and shared_count >= 4
            and overlap >= 40
        ):
            valid = True
            reason = "exact_phrase_with_similarity"

        elif (
            similarity >= STRONG_SIMILARITY
            and shared_count >= MIN_DISTINCTIVE_OVERLAP
            and overlap >= 45
        ):
            valid = True
            reason = "strong_fuzzy_similarity"

        elif (
            similarity >= MEDIUM_SIMILARITY
            and overlap >= 65
            and shared_count >= 5
        ):
            valid = True
            reason = "high_word_overlap"

        if not valid:
            continue

        phrase_score = (
            exact_words / target_length * 100
        )

        evidence_strength = max(
            similarity,
            phrase_score
        )

        candidate = {
        "similarity": round(evidence_strength, 2),
        "fuzzy_similarity": round(similarity, 2),
        "word_coverage": word_coverage,
        "matched_words": matched_words,
        "overlap": round(overlap, 2),
        "shared_words": shared_count,
        "phrase": phrase,
        "exact_phrase_words": exact_words,
        "reason": reason
        }

        if (
            best is None
            or candidate["similarity"] > best["similarity"]
        ):
            best = candidate

    return best


# ============================================================
# CHECK SEARCH SNIPPET
# ============================================================

def compare_snippet(
    sentence,
    result
):

    snippet = result.get(
        "snippet",
        ""
    )

    if not snippet:
        return None

    analysis = compare_text(
        sentence,
        snippet
    )

    if not analysis:
        return None

    return {
        **analysis,
        "source_url": result.get(
            "url",
            ""
        ),
        "source_title": result.get(
            "title",
            ""
        ),
        "source_text": snippet,
        "evidence_type": "search_snippet"
    }


# ============================================================
# FIND BEST MATCH
# ============================================================

def find_best_match(
    sentence,
    search_results,
    pages
):

    best = None

    candidate_urls = {
        normalize_url(
            item.get("url", "")
        )
        for item in search_results
    }

    # ---------------------------------------------
    # Search snippets
    # ---------------------------------------------

    for result in search_results:

        candidate = compare_snippet(
            sentence,
            result
        )

        if not candidate:
            continue

        if (
        best is None
        or candidate["similarity"] >= best["similarity"]
        ):
         best = candidate

    # ---------------------------------------------
    # Fetched webpages
    # ---------------------------------------------

    for page in pages:

        page_url = normalize_url(
            page.get("url", "")
        )

        # Only compare pages returned for this
        # sentence's searches.
        if page_url not in candidate_urls:
            continue

        candidate = compare_text(
            sentence,
            page.get(
                "text",
                ""
            )
        )

        if not candidate:
            continue

        candidate.update({
            "source_url": page.get(
                "url",
                ""
            ),
            "source_title": page.get(
                "title",
                ""
            ),
            "source_text": "",
            "evidence_type": "web_page"
        })

        if (
            best is None
            or candidate["similarity"]
            > best["similarity"]
        ):
            best = candidate

    return best


# ============================================================
# SCORE CALCULATION
# ============================================================

def calculate_score(sentences, matches):

    if not sentences or not matches:
        return 0.0

    total_sample_words = sum(
        len(tokenize(sentence))
        for sentence in sentences
    )

    if total_sample_words <= 0:
        return 0.0

    copied_equivalent_words = 0.0
    seen_indexes = set()

    for match in matches:

        sentence_index = match.get("sentence_index")

        if sentence_index is not None:
            if sentence_index in seen_indexes:
                continue
            seen_indexes.add(sentence_index)

        sentence_words = max(
            0,
            int(match.get("sentence_word_count", 0))
        )

        similarity = max(
            0.0,
            min(100.0, float(match.get("similarity", 0)))
        )

        coverage = match.get("word_coverage")

        if coverage is not None:
            coverage = max(
                0.0,
                min(100.0, float(coverage))
            )

            effective_similarity = min(
                similarity,
                coverage
            )
        else:
            effective_similarity = similarity

        copied_equivalent_words += (
            sentence_words
            * effective_similarity
            / 100
        )

    score = (
        copied_equivalent_words
        / total_sample_words
        * 100
    )

    return round(
        max(0.0, min(100.0, score)),
        2
    )

# ============================================================
# MAIN CHECKER
# ============================================================

def check_plagiarism(
    text="",
    topic="",
    check_type=None
):

    started = time.time()

    text = str(
        text or ""
    ).strip()

    topic = str(
        topic or ""
    ).strip()

    check_type = str(
        check_type or "AI"
    ).upper().strip()

    if check_type not in (
        "AI",
        "HUMANIZED"
    ):
        check_type = "AI"

    print("\n======================================")
    print("PFCG PLAGIARISM CHECKER V6")
    print("======================================")
    print("Check Type:", check_type)
    print("Topic:", topic)
    print("Text Length:", len(text))

    # ========================================================
    # EMPTY TEXT
    # ========================================================

    if not text:

        return {
            "success": False,
            "check_type": check_type,
            "plagiarism_percentage": 0,
            "percentage": 0,
            "score": 0,
            "sources": [],
            "matches": [],
            "checked_sentences": 0,
            "important_sentences": 0,
            "covered_sentences": 0,
            "uncovered_sentences": 0,
            "matched_sentences": 0,
            "coverage": 0,
            "source_count": 0,
            "status": "empty_text",
            "message": "No content was provided."
        }

    # ========================================================
    # SELECT SENTENCES
    # ========================================================

    sentences = get_important_sentences(
        text
    )

    total_sentences = len(
        sentences
    )

    print(
        "Selected Sentences:",
        total_sentences
    )

    if total_sentences == 0:

        return {
            "success": False,
            "check_type": check_type,
            "plagiarism_percentage": 0,
            "percentage": 0,
            "score": 0,
            "sources": [],
            "matches": [],
            "checked_sentences": 0,
            "important_sentences": 0,
            "covered_sentences": 0,
            "uncovered_sentences": 0,
            "matched_sentences": 0,
            "coverage": 0,
            "source_count": 0,
            "status": "insufficient_text",
            "message": (
                "The content does not contain enough "
                "complete sentences to check."
            )
        }

    # ========================================================
    # SEARCH EVERY SENTENCE
    # ========================================================

    search_records = {}

    def run_search(index, sentence):

        result = search_sentence(
            sentence,
            topic
        )

        return (
            index,
            result
        )

    with ThreadPoolExecutor(
        max_workers=SEARCH_WORKERS
    ) as executor:

        futures = [
            executor.submit(
                run_search,
                index,
                sentence
            )
            for index, sentence
            in enumerate(sentences)
        ]

        for future in as_completed(
            futures
        ):

            try:

                index, result = (
                    future.result()
                )

                search_records[
                    index
                ] = result

            except Exception as error:

                print(
                    "[SEARCH TASK ERROR]",
                    repr(error)
                )

    # Ensure every sentence has a record.
    for index in range(
        total_sentences
    ):

        if index not in search_records:

            search_records[index] = {
                "searched": False,
                "results": []
            }

    # ========================================================
    # COVERAGE
    # ========================================================

    covered_indexes = [
        index
        for index, record
        in search_records.items()
        if record.get("searched")
    ]

    covered_sentences = len(
        covered_indexes
    )

    coverage = (
        covered_sentences
        / total_sentences
        * 100
    )

    print(
        "Search Coverage:",
        f"{covered_sentences}/"
        f"{total_sentences}",
        f"({coverage:.2f}%)"
    )


    # ========================================================
    # FETCH CANDIDATE PAGES
    # ========================================================

    pages = fetch_pages(
        search_records
    )

    print(
        "Fetched Pages:",
        len(pages)
    )

    # ========================================================
    # MATCH ANALYSIS
    # ========================================================

    matches = []

    for index, sentence in enumerate(
        sentences
    ):

        record = search_records[
            index
        ]

        results = record.get(
            "results",
            []
        )

        best = find_best_match(
            sentence,
            results,
            pages
        )

        if not best:

            print(
                f"[NO MATCH] Sentence "
                f"{index + 1}"
            )

            continue

        best.update({
            "sentence_index":
                index + 1,

            "target_sentence":
                sentence,

            "matched_text":
                best.get(
                    "phrase",
                    ""
                ),

            "sentence_word_count":
                len(
                    tokenize(
                        sentence
                    )
                )
        })

        matches.append(best)

        print(
            f"[MATCH] Sentence "
            f"{index + 1}: "
            f"{best['similarity']:.2f}%"
        )

        print(
            "  Reason:",
            best.get(
                "reason",
                ""
            )
        )

        print(
            "  Source:",
            best.get(
                "source_url",
                ""
            )
        )
        print(
        "  Evidence Type:",
        best.get("evidence_type", "")
        )

        print(
        "  Exact Phrase:",
        best.get("phrase", "")
        )

        print(
        "  Exact Phrase Words:",
        best.get("exact_phrase_words", 0)
        )

        print(
        "  Fuzzy Similarity:",
        best.get("fuzzy_similarity", 0)
        )

        print(
        "  Word Overlap:",
        best.get("overlap", 0)
        )

    # ========================================================
    # FINAL SCORE
    # ========================================================

    scored_sentences = [
    sentences[index]
    for index in covered_indexes
    ]
    
    final_score = calculate_score(
    scored_sentences,
    matches
    )

    # ========================================================
    # SOURCES
    # ========================================================

    sources = []

    seen_sources = set()

    for match in sorted(
        matches,
        key=lambda item:
            item.get(
                "similarity",
                0
            ),
        reverse=True
    ):

        url = match.get(
            "source_url",
            ""
        )

        if not url:
            continue

        key = normalize_url(url)

        if key in seen_sources:
            continue

        seen_sources.add(key)

        sources.append({
            "title":
                match.get(
                    "source_title",
                    ""
                )
                or "Matched Source",

            "url":
                url,

            "similarity":
                round(
                    float(
                        match.get(
                            "similarity",
                            0
                        )
                    ),
                    2
                ),

            "matched_text":
                match.get(
                    "matched_text",
                    ""
                ),

            "source_text":
                match.get(
                    "source_text",
                    ""
                ),

            "reason":
                match.get(
                    "reason",
                    ""
                ),

            "sentence_index":
                match.get(
                    "sentence_index",
                    0
                ),

            "evidence_type":
                match.get(
                    "evidence_type",
                    ""
                )
        })

    processing_time = round(
        time.time() - started,
        2
    )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    print("\n======================================")
    print("PLAGIARISM CHECK COMPLETE")
    print("======================================")
    print(
        "Coverage:",
        f"{coverage:.2f}%"
    )
    print(
        "Matched Sentences:",
        f"{len(matches)}/"
        f"{total_sentences}"
    )
    print(
        "Final Score:",
        f"{final_score}%"
    )
    print(
        "Sources:",
        len(sources)
    )
    print(
        "Time:",
        processing_time,
        "seconds"
    )
    print("======================================")

    return {
        "success": True,

        "check_type":
            check_type,

        "plagiarism_percentage":
            final_score,

        "percentage":
            final_score,

        "score":
            final_score,

        "checked_sentences":
        covered_sentences,

        "important_sentences":
        total_sentences,

        "covered_sentences":
        covered_sentences,

        "uncovered_sentences":
        (
        total_sentences
        - covered_sentences
        ),

        "matched_sentences":
        len(matches),

        "coverage":
        round(
        coverage,
        2
        ),

        "source_count":
            len(sources),

        "sources":
            sources,

        "matches":
            matches,

        "status": (
        "incomplete_search"
        if covered_sentences < total_sentences
        else (
        "complete_web_evidence"
        if matches
        else "complete_no_validated_match"
        )
        ),

        "coverage_note": (
        "Some selected sentences could not be searched successfully. "
        "The plagiarism score may be incomplete."
        if covered_sentences < total_sentences
        else
        "Search results were obtained for all selected sentences. "
        "This does not guarantee complete web coverage."
        ),
        
        "processing_time":
            processing_time
    }


# ============================================================
# COMPATIBILITY FUNCTIONS
# ============================================================

def detect_plagiarism(
    text="",
    topic="",
    check_type=None
):

    return check_plagiarism(
        text=text,
        topic=topic,
        check_type=check_type
    )


def calculate_plagiarism(
    text="",
    topic="",
    check_type=None
):

    return check_plagiarism(
        text=text,
        topic=topic,
        check_type=check_type
    )