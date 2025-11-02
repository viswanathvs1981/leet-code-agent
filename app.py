from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from flask import Flask, jsonify, request, send_from_directory


logging.basicConfig(level=logging.INFO)


def load_local_problems() -> List[Dict[str, Any]]:
    data_path = Path(__file__).resolve().parent / "data" / "problems.json"
    with data_path.open("r", encoding="utf-8") as fh:
        return json.loads(fh.read())


def normalise_sequence(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [str(item) for item in value.values() if item]
    if isinstance(value, Iterable):
        return [str(item) for item in value if item]
    return []


def normalise_mcp_problem(entry: Dict[str, Any]) -> Dict[str, Any] | None:
    if not isinstance(entry, dict):
        return None

    problem_id = entry.get("id") or entry.get("questionId") or entry.get("frontendQuestionId")
    slug = entry.get("slug") or entry.get("titleSlug")
    title = entry.get("title") or entry.get("name") or entry.get("question")
    url = entry.get("url")
    if not url and slug:
        url = f"https://leetcode.com/problems/{slug}/"

    if not title or not url:
        return None

    topics = normalise_sequence(
        entry.get("topic")
        or entry.get("topics")
        or entry.get("category")
        or entry.get("categoryTags")
        or entry.get("tags")
    )
    patterns = normalise_sequence(
        entry.get("patterns")
        or entry.get("patternTags")
        or entry.get("techniques")
        or entry.get("strategies")
    )

    summary = (
        entry.get("summary")
        or entry.get("synopsis")
        or entry.get("description")
        or entry.get("shortDescription")
        or "Generated from leetcode-mcp-server data."
    )

    hints = normalise_sequence(entry.get("key_steps") or entry.get("hints") or entry.get("solutionOutline"))

    return {
        "id": problem_id or slug or title,
        "title": title,
        "url": url,
        "difficulty": entry.get("difficulty") or entry.get("level") or entry.get("difficultyLevel") or "Unknown",
        "topic": topics[0] if topics else "General",
        "patterns": patterns or ["General Strategy"],
        "summary": summary,
        "key_steps": hints,
    }


def fetch_problems_from_mcp(base_url: str) -> List[Dict[str, Any]]:
    url = urljoin(base_url.rstrip("/") + "/", "problems")
    logging.info("Fetching problems from leetcode-mcp-server at %s", url)
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    problem_payload = payload.get("problems") if isinstance(payload, dict) else payload
    if not isinstance(problem_payload, list):
        raise ValueError("Unexpected response format from leetcode-mcp-server")

    problems: List[Dict[str, Any]] = []
    for raw in problem_payload:
        normalised = normalise_mcp_problem(raw)
        if normalised:
            problems.append(normalised)

    if not problems:
        raise ValueError("No valid problems returned by leetcode-mcp-server")

    logging.info("Loaded %s problems from leetcode-mcp-server", len(problems))
    return problems


def load_problems() -> Tuple[List[Dict[str, Any]], str]:
    endpoint = os.environ.get("LEETCODE_MCP_SERVER")
    if endpoint:
        try:
            problems = fetch_problems_from_mcp(endpoint)
            return problems, f"leetcode-mcp-server ({endpoint})"
        except (URLError, HTTPError, TimeoutError, ValueError) as exc:
            logging.warning("Falling back to local dataset because MCP fetch failed: %s", exc)

    problems = load_local_problems()
    return problems, "local dataset (data/problems.json)"


def build_category_summary(problems: List[Dict[str, Any]]) -> Dict[str, Any]:
    categories: Dict[str, Dict[str, Any]] = {}
    for problem in problems:
        topic = problem["topic"]
        entry = categories.setdefault(
            topic,
            {"count": 0, "difficulties": Counter(), "patterns": Counter()},
        )
        entry["count"] += 1
        entry["difficulties"][problem["difficulty"]] += 1
        entry["patterns"].update(problem["patterns"])
    # Convert counters to serialisable structures
    for topic, entry in categories.items():
        entry["difficulties"] = dict(sorted(entry["difficulties"].items()))
        entry["patterns"] = dict(entry["patterns"].most_common())
    return dict(sorted(categories.items(), key=lambda item: item[1]["count"], reverse=True))


def build_pattern_summary(problems: List[Dict[str, Any]]) -> Dict[str, Any]:
    patterns: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "topics": Counter(), "examples": []})
    for problem in problems:
        for pattern in problem["patterns"]:
            entry = patterns[pattern]
            entry["count"] += 1
            entry["topics"][problem["topic"]] += 1
            if len(entry["examples"]) < 5:
                entry["examples"].append({
                    "id": problem["id"],
                    "title": problem["title"],
                    "difficulty": problem["difficulty"],
                    "topic": problem["topic"],
                    "url": problem["url"],
                    "summary": problem["summary"],
                })
    # Convert counters to sorted lists
    for pattern, entry in patterns.items():
        entry["topics"] = dict(entry["topics"].most_common())
        entry["why_it_matters"] = (
            "Appears in {} problems across {} topic(s).".format(
                entry["count"], len(entry["topics"])
            )
        )
    return dict(sorted(patterns.items(), key=lambda item: item[1]["count"], reverse=True))


def build_tutorial(categories: Dict[str, Any], patterns: Dict[str, Any]) -> Dict[str, Any]:
    sorted_categories = list(categories.items())
    category_highlights = [
        {
            "topic": topic,
            "count": data["count"],
            "key_patterns": list(data["patterns"].keys())[:3],
        }
        for topic, data in sorted_categories
    ]

    top_patterns = list(patterns.items())[:5]
    pattern_spotlight = [
        {
            "pattern": name,
            "why_it_matters": (
                "Appears in {} problems across {} topic(s).".format(
                    data["count"], len(data["topics"])
                )
            ),
            "top_topics": list(data["topics"].keys())[:3],
            "examples": data["examples"],
        }
        for name, data in top_patterns
    ]

    study_plan = [
        {
            "title": "Build core intuition",
            "steps": [
                "Start with easy problems in the most common categories: {}.".format(
                    ", ".join(topic for topic, _ in sorted_categories[:3])
                ),
                "Focus on one pattern at a time—try solving multiple problems that require {}.".format(
                    pattern_spotlight[0]["pattern"] if pattern_spotlight else "a shared technique"
                ),
                "Document the decision points you make for each solution to internalize the pattern.",
            ],
        },
        {
            "title": "Layer on complexity",
            "steps": [
                "Move to medium problems and look for variations of familiar patterns.",
                "Identify how constraints change the data structure or traversal strategy.",
                "Compare multiple patterns that solve the same problem to understand trade-offs.",
            ],
        },
        {
            "title": "Synthesize across patterns",
            "steps": [
                "Pick hard problems that blend categories, such as combining graph searches with dynamic programming.",
                "Create quick-reference cards highlighting when to choose each pattern.",
                "Teach the concept to someone else or write your own summary as a final checkpoint.",
            ],
        },
    ]

    return {
        "category_highlights": category_highlights,
        "pattern_spotlight": pattern_spotlight,
        "study_plan": study_plan,
    }


def answer_question(
    question: str,
    categories: Dict[str, Any],
    patterns: Dict[str, Any],
    problems: List[Dict[str, Any]],
) -> Dict[str, Any]:
    normalized = question.strip().lower()
    if not normalized:
        return {
            "answer": "Try asking about a topic (e.g. dynamic programming) or a specific pattern (e.g. sliding window).",
            "related_problems": [],
        }

    topic_hits = [topic for topic in categories if topic.lower() in normalized]
    pattern_hits = [pattern for pattern in patterns if pattern.lower() in normalized]

    related: List[Dict[str, Any]] = []
    if topic_hits or pattern_hits:
        for problem in problems:
            if problem["topic"] in topic_hits or any(p in pattern_hits for p in problem["patterns"]):
                related.append({
                    "id": problem["id"],
                    "title": problem["title"],
                    "difficulty": problem["difficulty"],
                    "topic": problem["topic"],
                    "url": problem["url"],
                })
    else:
        keywords = {
            "easy": "Easy",
            "medium": "Medium",
            "hard": "Hard",
        }
        difficulties = {diff for word, diff in keywords.items() if word in normalized}
        if difficulties:
            for problem in problems:
                if problem["difficulty"] in difficulties:
                    related.append({
                        "id": problem["id"],
                        "title": problem["title"],
                        "difficulty": problem["difficulty"],
                        "topic": problem["topic"],
                        "url": problem["url"],
                    })

    if not related:
        fallback = (
            "I could not find an exact match. Try referencing a topic (array, graph) or a pattern (two pointers, dynamic programming)."
        )
        return {"answer": fallback, "related_problems": []}

    summary_parts: List[str] = []
    if topic_hits:
        for topic in topic_hits:
            data = categories[topic]
            summary_parts.append(
                "For {} problems, focus on {}. Common patterns: {}.".format(
                    topic,
                    ", ".join(data["difficulties"].keys()),
                    ", ".join(list(data["patterns"].keys())[:3]) or "varied techniques",
                )
            )
    if pattern_hits:
        for pattern in pattern_hits:
            data = patterns[pattern]
            summary_parts.append(
                "{} appears in {} problems across {} topic(s). Practice with examples like {}.".format(
                    pattern,
                    data["count"],
                    len(data["topics"]),
                    ", ".join(example["title"] for example in data["examples"][:2]),
                )
            )

    if not summary_parts:
        summary_parts.append(
            "Here are problems matching your query. Consider refining the question with a topic or pattern keyword for deeper insights."
        )

    return {"answer": " ".join(summary_parts), "related_problems": related[:8]}


app = Flask(__name__, static_folder="static", static_url_path="")

PROBLEMS: List[Dict[str, Any]]
CATEGORIES: Dict[str, Any]
PATTERNS: Dict[str, Any]
TUTORIAL: Dict[str, Any]
DATA_SOURCE: str
LAST_REFRESHED_AT: datetime


def initialise_data() -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any], Dict[str, Any], str, datetime]:
    problems, source = load_problems()
    categories = build_category_summary(problems)
    patterns = build_pattern_summary(problems)
    tutorial = build_tutorial(categories, patterns)
    timestamp = datetime.utcnow().replace(microsecond=0)
    return problems, categories, patterns, tutorial, source, timestamp


(
    PROBLEMS,
    CATEGORIES,
    PATTERNS,
    TUTORIAL,
    DATA_SOURCE,
    LAST_REFRESHED_AT,
) = initialise_data()


@app.route("/")
def index() -> Any:
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/problems")
def get_problems() -> Any:
    return jsonify({"problems": PROBLEMS})


@app.route("/api/meta")
def get_meta() -> Any:
    return jsonify(
        {
            "source": DATA_SOURCE,
            "last_refreshed": LAST_REFRESHED_AT.isoformat() if LAST_REFRESHED_AT else None,
        }
    )


@app.route("/api/categories")
def get_categories() -> Any:
    return jsonify({"categories": CATEGORIES})


@app.route("/api/patterns")
def get_patterns() -> Any:
    return jsonify({"patterns": PATTERNS})


@app.route("/api/tutorial")
def get_tutorial() -> Any:
    return jsonify({"tutorial": TUTORIAL})


@app.route("/api/questions", methods=["POST"])
def ask_question() -> Any:
    payload = request.get_json(silent=True) or {}
    question = payload.get("question", "")
    response = answer_question(question, CATEGORIES, PATTERNS, PROBLEMS)
    return jsonify(response)


@app.route("/api/refresh", methods=["POST"])
def refresh_data() -> Any:
    global PROBLEMS, CATEGORIES, PATTERNS, TUTORIAL, DATA_SOURCE, LAST_REFRESHED_AT
    (
        PROBLEMS,
        CATEGORIES,
        PATTERNS,
        TUTORIAL,
        DATA_SOURCE,
        LAST_REFRESHED_AT,
    ) = initialise_data()
    return jsonify(
        {
            "status": "ok",
            "source": DATA_SOURCE,
            "last_refreshed": LAST_REFRESHED_AT.isoformat() if LAST_REFRESHED_AT else None,
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
