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
from flask_cors import CORS

# Import our new components
from mcp_client import LeetCodeMCPClient
from problem_analyzer import ProblemAnalyzer
from tutorial_generator import TutorialGenerator
from solution_generator import SolutionGenerator
from enhanced_agent import EnhancedAgent
from pattern_mastery_tracker import PatternMasteryTracker
from azure_services import cosmos_service, blob_service


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
CORS(app)  # Enable CORS for frontend requests

# Global data stores
PROBLEMS: List[Dict[str, Any]]
CATEGORIES: Dict[str, Any]
PATTERNS: Dict[str, Any]
TUTORIAL: Dict[str, Any]
DATA_SOURCE: str
LAST_REFRESHED_AT: datetime

# Initialize new services
mcp_client = LeetCodeMCPClient(base_url=os.getenv("LEETCODE_MCP_SERVER", "http://localhost:3333"))
problem_analyzer = ProblemAnalyzer()
tutorial_generator = TutorialGenerator()
solution_generator = SolutionGenerator()
enhanced_agent = EnhancedAgent()
mastery_tracker = PatternMasteryTracker()


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


# New API endpoints for enhanced functionality

@app.route("/api/crawl-problems", methods=["POST"])
def crawl_problems() -> Any:
    """Fetch LeetCode problems using MCP server"""
    try:
        logger.info("Fetching LeetCode problems via MCP server...")

        # Check if MCP server is available
        if not mcp_client.is_healthy():
            return jsonify({
                "status": "error",
                "message": "MCP server is not available. Please ensure the leetcode-mcp-server is running."
            }), 503

        # Get all problems via MCP
        payload = request.get_json(silent=True) or {}
        category = payload.get("category", "all-code-essentials")
        limit = payload.get("limit", 1000)  # Default to 1000 problems

        problems = mcp_client.get_all_problems(category=category, limit=limit)

        if not problems:
            return jsonify({
                "status": "error",
                "message": "No problems retrieved from MCP server"
            }), 500

        # Save to CosmosDB
        saved_count = 0
        for problem in problems:
            if cosmos_service.save_problem(problem):
                saved_count += 1

        # Analyze problems with AI (sample for performance)
        analysis_sample = problems[:min(100, len(problems))]  # Analyze first 100 problems
        analyzed_problems = problem_analyzer.analyze_problems_batch(analysis_sample)

        # Identify patterns from analyzed problems
        patterns = problem_analyzer.identify_patterns(analyzed_problems)

        # Save patterns to CosmosDB
        patterns_saved = 0
        for pattern in patterns:
            if cosmos_service.save_pattern(pattern):
                patterns_saved += 1

        # Update global data
        global PROBLEMS, CATEGORIES, PATTERNS, TUTORIAL, DATA_SOURCE, LAST_REFRESHED_AT
        PROBLEMS = analyzed_problems + [p for p in problems if p not in analyzed_problems]
        CATEGORIES = build_category_summary(PROBLEMS)
        PATTERNS = build_pattern_summary(PROBLEMS)
        TUTORIAL = build_tutorial(CATEGORIES, PATTERNS)
        DATA_SOURCE = "LeetCode MCP Server + AI Analysis"
        LAST_REFRESHED_AT = datetime.utcnow().replace(microsecond=0)

        return jsonify({
            "status": "success",
            "problems_fetched": len(problems),
            "problems_saved": saved_count,
            "problems_analyzed": len(analyzed_problems),
            "patterns_identified": len(patterns),
            "patterns_saved": patterns_saved,
            "data_source": DATA_SOURCE,
            "last_refreshed": LAST_REFRESHED_AT.isoformat()
        })

    except Exception as e:
        logger.error(f"Failed to fetch problems via MCP: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/analyze-problems", methods=["POST"])
def analyze_problems() -> Any:
    """Analyze existing problems with AI"""
    try:
        # Get problems from CosmosDB
        problems = cosmos_service.get_all_problems()
        if not problems:
            return jsonify({"status": "error", "message": "No problems found to analyze"}), 404

        logger.info(f"Analyzing {len(problems)} problems...")
        analyzed_problems = problem_analyzer.analyze_problems_batch(problems)

        # Save analyzed problems back to CosmosDB
        saved_count = 0
        for problem in analyzed_problems:
            if cosmos_service.save_problem(problem):
                saved_count += 1

        # Identify patterns
        patterns = problem_analyzer.identify_patterns(analyzed_problems)

        # Save patterns to CosmosDB
        patterns_saved = 0
        for pattern in patterns:
            if cosmos_service.save_pattern(pattern):
                patterns_saved += 1

        return jsonify({
            "status": "success",
            "problems_analyzed": len(analyzed_problems),
            "problems_saved": saved_count,
            "patterns_identified": len(patterns),
            "patterns_saved": patterns_saved
        })

    except Exception as e:
        logger.error(f"Failed to analyze problems: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/generate-tutorials", methods=["POST"])
def generate_tutorials() -> Any:
    """Generate tutorials for all patterns"""
    try:
        patterns = cosmos_service.get_all_patterns()
        problems = cosmos_service.get_all_problems()

        if not patterns:
            return jsonify({"status": "error", "message": "No patterns found to generate tutorials"}), 404

        logger.info(f"Generating tutorials for {len(patterns)} patterns...")
        tutorials = tutorial_generator.generate_all_tutorials(patterns, problems)

        return jsonify({
            "status": "success",
            "tutorials_generated": len(tutorials),
            "patterns": list(tutorials.keys())
        })

    except Exception as e:
        logger.error(f"Failed to generate tutorials: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/generate-solutions", methods=["POST"])
def generate_solutions() -> Any:
    """Generate solutions for problems"""
    try:
        problems = cosmos_service.get_all_problems()
        if not problems:
            return jsonify({"status": "error", "message": "No problems found to generate solutions"}), 404

        logger.info(f"Generating solutions for {len(problems)} problems...")
        solutions = solution_generator.generate_solutions_batch(problems, limit=100)  # Limit for demo

        return jsonify({
            "status": "success",
            "solutions_generated": len(solutions),
            "problem_ids": list(solutions.keys())
        })

    except Exception as e:
        logger.error(f"Failed to generate solutions: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/tutorial/<pattern_name>")
def get_tutorial(pattern_name: str) -> Any:
    """Get a tutorial for a specific pattern"""
    try:
        tutorial = tutorial_generator.get_tutorial(pattern_name)
        if tutorial:
            return jsonify({"tutorial": tutorial})
        else:
            return jsonify({"error": "Tutorial not found"}), 404
    except Exception as e:
        logger.error(f"Failed to get tutorial: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/solution/<problem_id>")
def get_solution(problem_id: str) -> Any:
    """Get a solution for a specific problem"""
    try:
        solution = solution_generator.get_solution(problem_id)
        if solution:
            return jsonify({"solution": solution})
        else:
            return jsonify({"error": "Solution not found"}), 404
    except Exception as e:
        logger.error(f"Failed to get solution: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/ask-agent", methods=["POST"])
def ask_agent() -> Any:
    """Enhanced Q&A with the intelligent agent"""
    try:
        payload = request.get_json(silent=True) or {}
        question = payload.get("question", "")
        user_context = payload.get("user_context", {})

        if not question:
            return jsonify({"error": "Question is required"}), 400

        response = enhanced_agent.ask_question(question, user_context)
        return jsonify(response)

    except Exception as e:
        logger.error(f"Agent question failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/user-progress/<user_id>")
def get_user_progress(user_id: str) -> Any:
    """Get user learning progress"""
    try:
        progress = mastery_tracker.get_user_progress(user_id)
        if progress:
            return jsonify(progress)
        else:
            return jsonify({"error": "User progress not found"}), 404
    except Exception as e:
        logger.error(f"Failed to get user progress: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/user-progress/<user_id>/mastered-patterns")
def get_mastered_patterns(user_id: str) -> Any:
    """Get patterns the user has mastered"""
    try:
        mastered = mastery_tracker.get_mastered_patterns(user_id)
        return jsonify({"mastered_patterns": mastered})
    except Exception as e:
        logger.error(f"Failed to get mastered patterns: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/user-progress/<user_id>/recommendations")
def get_learning_recommendations(user_id: str) -> Any:
    """Get personalized learning recommendations"""
    try:
        recommendations = mastery_tracker.get_learning_recommendations(user_id)
        return jsonify(recommendations)
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/user-progress/<user_id>/study-plan")
def get_study_plan(user_id: str) -> Any:
    """Get personalized study plan"""
    try:
        days = int(request.args.get("days", 7))
        study_plan = mastery_tracker.get_study_plan(user_id, days)
        return jsonify(study_plan)
    except Exception as e:
        logger.error(f"Failed to get study plan: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/user-progress/<user_id>/update", methods=["POST"])
def update_user_progress(user_id: str) -> Any:
    """Update user progress after solving a problem"""
    try:
        payload = request.get_json(silent=True) or {}
        problem_id = payload.get("problem_id")
        success = payload.get("success", False)
        time_spent = payload.get("time_spent")
        attempts = payload.get("attempts", 1)

        if not problem_id:
            return jsonify({"error": "problem_id is required"}), 400

        success = mastery_tracker.update_user_progress(user_id, problem_id, success, time_spent, attempts)
        if success:
            return jsonify({"status": "success"})
        else:
            return jsonify({"error": "Failed to update progress"}), 500

    except Exception as e:
        logger.error(f"Failed to update user progress: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/problem-solutions/<title_slug>")
def get_problem_solutions(title_slug: str) -> Any:
    """Get community solutions for a problem"""
    try:
        payload = request.args
        limit = int(payload.get("limit", 10))
        order_by = payload.get("order_by", "HOT")

        solutions = mcp_client.get_problem_solutions(title_slug, limit=limit, order_by=order_by)
        return jsonify({"solutions": solutions})
    except Exception as e:
        logger.error(f"Failed to get solutions for {title_slug}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/solution/<path:solution_id>")
def get_problem_solution(solution_id: str) -> Any:
    """Get detailed content of a specific solution"""
    try:
        # Try topic ID first, then slug
        solution = mcp_client.get_problem_solution(topic_id=solution_id)
        if not solution:
            solution = mcp_client.get_problem_solution(slug=solution_id)

        if solution:
            return jsonify({"solution": solution})
        else:
            return jsonify({"error": "Solution not found"}), 404
    except Exception as e:
        logger.error(f"Failed to get solution {solution_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/user-profile/<username>")
def get_user_profile(username: str) -> Any:
    """Get user profile information"""
    try:
        profile = mcp_client.get_user_profile(username)
        if profile:
            return jsonify(profile)
        else:
            return jsonify({"error": "User profile not found"}), 404
    except Exception as e:
        logger.error(f"Failed to get user profile for {username}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/user-contest-ranking/<username>")
def get_user_contest_ranking(username: str) -> Any:
    """Get user's contest ranking information"""
    try:
        attended = request.args.get("attended", "true").lower() == "true"
        ranking = mcp_client.get_user_contest_ranking(username, attended=attended)
        if ranking:
            return jsonify(ranking)
        else:
            return jsonify({"error": "Contest ranking not found"}), 404
    except Exception as e:
        logger.error(f"Failed to get contest ranking for {username}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/user-submissions/<username>")
def get_user_submissions(username: str) -> Any:
    """Get user's recent submissions"""
    try:
        limit = int(request.args.get("limit", 10))
        submission_type = request.args.get("type", "recent")  # recent, accepted

        if submission_type == "accepted":
            submissions = mcp_client.get_recent_ac_submissions(username, limit=limit)
        else:
            submissions = mcp_client.get_recent_submissions(username, limit=limit)

        return jsonify({"submissions": submissions})
    except Exception as e:
        logger.error(f"Failed to get submissions for {username}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/problem-progress")
def get_problem_progress() -> Any:
    """Get user's problem-solving progress"""
    try:
        offset = int(request.args.get("offset", 0))
        limit = int(request.args.get("limit", 100))
        question_status = request.args.get("status")  # ATTEMPTED, SOLVED
        difficulty = request.args.getlist("difficulty")  # Easy, Medium, Hard

        progress = mcp_client.get_problem_progress(
            offset=offset,
            limit=limit,
            question_status=question_status,
            difficulty=difficulty if difficulty else None
        )
        return jsonify(progress)
    except Exception as e:
        logger.error(f"Failed to get problem progress: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/notes/search")
def search_notes() -> Any:
    """Search user notes"""
    try:
        keyword = request.args.get("keyword", "")
        limit = int(request.args.get("limit", 10))
        skip = int(request.args.get("skip", 0))
        order_by = request.args.get("order_by", "DESCENDING")

        notes = mcp_client.search_notes(
            keyword=keyword,
            limit=limit,
            skip=skip,
            order_by=order_by
        )
        return jsonify({"notes": notes})
    except Exception as e:
        logger.error(f"Failed to search notes: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/notes/problem/<question_id>")
def get_problem_notes(question_id: str) -> Any:
    """Get notes for a specific problem"""
    try:
        limit = int(request.args.get("limit", 10))
        skip = int(request.args.get("skip", 0))

        notes = mcp_client.get_note(question_id, limit=limit, skip=skip)
        return jsonify({"notes": notes})
    except Exception as e:
        logger.error(f"Failed to get notes for problem {question_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/notes", methods=["POST"])
def create_note() -> Any:
    """Create a new note"""
    try:
        payload = request.get_json(silent=True) or {}
        question_id = payload.get("question_id")
        content = payload.get("content", "")
        summary = payload.get("summary", "")

        if not question_id or not content:
            return jsonify({"error": "question_id and content are required"}), 400

        result = mcp_client.create_note(question_id, content, summary)
        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "Failed to create note"}), 500
    except Exception as e:
        logger.error(f"Failed to create note: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/notes/<note_id>", methods=["PUT"])
def update_note(note_id: str) -> Any:
    """Update an existing note"""
    try:
        payload = request.get_json(silent=True) or {}
        content = payload.get("content", "")
        summary = payload.get("summary", "")

        if not content:
            return jsonify({"error": "content is required"}), 400

        result = mcp_client.update_note(note_id, content, summary)
        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "Failed to update note"}), 500
    except Exception as e:
        logger.error(f"Failed to update note {note_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/metadata/categories")
def get_problem_categories() -> Any:
    """Get all problem categories"""
    try:
        categories = mcp_client.get_problem_categories()
        return jsonify({"categories": categories})
    except Exception as e:
        logger.error(f"Failed to get problem categories: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/metadata/tags")
def get_problem_tags() -> Any:
    """Get all problem tags"""
    try:
        tags = mcp_client.get_problem_tags()
        return jsonify({"tags": tags})
    except Exception as e:
        logger.error(f"Failed to get problem tags: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/metadata/languages")
def get_supported_languages() -> Any:
    """Get supported programming languages"""
    try:
        languages = mcp_client.get_supported_languages()
        return jsonify({"languages": languages})
    except Exception as e:
        logger.error(f"Failed to get supported languages: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/system-status")
def get_system_status() -> Any:
    """Get system status and component health"""
    try:
        status = {
            "cosmos_db": cosmos_service.client is not None,
            "blob_storage": blob_service.client is not None,
            "openai": problem_analyzer.client is not None,
            "mcp_server": mcp_client.is_healthy(),
            "total_problems": len(PROBLEMS) if PROBLEMS else 0,
            "total_patterns": len(PATTERNS) if PATTERNS else 0,
            "data_source": DATA_SOURCE,
            "last_refreshed": LAST_REFRESHED_AT.isoformat() if LAST_REFRESHED_AT else None
        }
        return jsonify(status)
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
