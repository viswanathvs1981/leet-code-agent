"""
LeetCode MCP Server Client Integration

This module provides a client for the leetcode-mcp-server which offers comprehensive
access to LeetCode data including problems, solutions, user data, and more.

GitHub: https://github.com/jinzcdev/leetcode-mcp-server
"""

import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from config import app_config

logger = logging.getLogger(__name__)

class LeetCodeMCPClient:
    """Client for interacting with the LeetCode MCP Server"""

    def __init__(self, base_url: str = "http://localhost:3333"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 30

    def _call_tool(self, tool_name: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call an MCP server tool"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": parameters or {}
                }
            }

            response = self.session.post(
                f"{self.base_url}/jsonrpc",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            result = response.json()
            if "error" in result:
                logger.error(f"MCP Tool error: {result['error']}")
                return {}

            # Extract the actual content from MCP response format
            content = result.get("result", {}).get("content", [])
            if content and len(content) > 0:
                text_content = content[0].get("text", "{}")
                try:
                    return json.loads(text_content)
                except json.JSONDecodeError:
                    return {"raw_content": text_content}

            return {}

        except Exception as e:
            logger.error(f"Failed to call MCP tool {tool_name}: {e}")
            return {}

    def _get_resource(self, uri: str) -> Dict[str, Any]:
        """Get an MCP resource"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "resources/read",
                "params": {
                    "uri": uri
                }
            }

            response = self.session.post(
                f"{self.base_url}/jsonrpc",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            result = response.json()
            if "error" in result:
                logger.error(f"MCP Resource error: {result['error']}")
                return {}

            content = result.get("result", {}).get("contents", [])
            if content and len(content) > 0:
                text_content = content[0].get("text", "{}")
                try:
                    return json.loads(text_content)
                except json.JSONDecodeError:
                    return {"raw_content": text_content}

            return {}

        except Exception as e:
            logger.error(f"Failed to get MCP resource {uri}: {e}")
            return {}

    # ===== PROBLEM DATA ACCESS =====

    def get_all_problems(self, category: str = "all-code-essentials", limit: int = 100) -> List[Dict[str, Any]]:
        """Get all problems with enhanced metadata"""
        logger.info(f"Fetching problems from MCP server (category: {category}, limit: {limit})")

        problems = []
        offset = 0

        while len(problems) < limit:
            batch = self._call_tool("search_problems", {
                "category": category,
                "limit": min(50, limit - len(problems)),  # API might have limits
                "offset": offset
            })

            if not batch or not isinstance(batch, dict):
                break

            problem_list = batch.get("problems", [])
            if not problem_list:
                break

            # Enhance each problem with full details
            for problem in problem_list:
                if len(problems) >= limit:
                    break

                enhanced_problem = self._enhance_problem_data(problem)
                if enhanced_problem:
                    problems.append(enhanced_problem)

            offset += len(problem_list)
            if len(problem_list) < 50:  # No more results
                break

        logger.info(f"Retrieved {len(problems)} problems from MCP server")
        return problems

    def get_problem_detail(self, title_slug: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific problem"""
        try:
            # Use resource URI for problem details
            uri = f"problem://{title_slug}"
            problem_data = self._get_resource(uri)

            if problem_data:
                return self._enhance_problem_data(problem_data)
            return None

        except Exception as e:
            logger.error(f"Failed to get problem detail for {title_slug}: {e}")
            return None

    def _enhance_problem_data(self, problem: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Enhance problem data with additional information"""
        try:
            # Normalize problem data structure
            enhanced = {
                "id": str(problem.get("questionId", problem.get("id", ""))),
                "title": problem.get("title", ""),
                "title_slug": problem.get("titleSlug", ""),
                "url": f"https://leetcode.com/problems/{problem.get('titleSlug', '')}/",
                "difficulty": problem.get("difficulty", "Unknown"),
                "acceptance_rate": problem.get("acceptanceRate", 0),
                "is_paid_only": problem.get("isPaidOnly", False),
                "topic_tags": [tag.get("name", "") for tag in problem.get("topicTags", []) if tag.get("name")],
                "content": problem.get("content", ""),
                "examples": problem.get("examples", []),
                "constraints": problem.get("constraints", []),
                "hints": problem.get("hints", []),
                "similar_questions": problem.get("similarQuestions", []),
                "solution_available": problem.get("solutionAvailable", False),
                "category": problem.get("category", "Unknown"),
                "likes": problem.get("likes", 0),
                "dislikes": problem.get("dislikes", 0),
                "stats": problem.get("stats", {})
            }

            # Ensure we have minimum required data
            if not enhanced["id"] or not enhanced["title"]:
                return None

            return enhanced

        except Exception as e:
            logger.error(f"Failed to enhance problem data: {e}")
            return None

    # ===== SOLUTION DATA ACCESS =====

    def get_problem_solutions(self, title_slug: str, limit: int = 10, order_by: str = "HOT") -> List[Dict[str, Any]]:
        """Get community solutions for a problem"""
        try:
            solutions = self._call_tool("list_problem_solutions", {
                "questionSlug": title_slug,
                "limit": limit,
                "orderBy": order_by
            })

            if solutions and isinstance(solutions, dict):
                return solutions.get("solutions", [])
            return []

        except Exception as e:
            logger.error(f"Failed to get solutions for {title_slug}: {e}")
            return []

    def get_problem_solution(self, topic_id: str = None, slug: str = None) -> Optional[Dict[str, Any]]:
        """Get detailed content of a specific solution"""
        try:
            params = {}
            if topic_id:
                params["topicId"] = topic_id
            elif slug:
                params["slug"] = slug
            else:
                return None

            solution = self._call_tool("get_problem_solution", params)
            return solution if solution else None

        except Exception as e:
            logger.error(f"Failed to get solution content: {e}")
            return None

    # ===== USER DATA ACCESS =====

    def get_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user profile information"""
        try:
            return self._call_tool("get_user_profile", {"username": username})
        except Exception as e:
            logger.error(f"Failed to get user profile for {username}: {e}")
            return None

    def get_user_contest_ranking(self, username: str, attended: bool = True) -> Optional[Dict[str, Any]]:
        """Get user's contest ranking information"""
        try:
            return self._call_tool("get_user_contest_ranking", {
                "username": username,
                "attended": attended
            })
        except Exception as e:
            logger.error(f"Failed to get contest ranking for {username}: {e}")
            return None

    def get_recent_submissions(self, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's recent submissions"""
        try:
            submissions = self._call_tool("get_recent_submissions", {
                "username": username,
                "limit": limit
            })

            if submissions and isinstance(submissions, dict):
                return submissions.get("submissions", [])
            return []

        except Exception as e:
            logger.error(f"Failed to get recent submissions for {username}: {e}")
            return []

    def get_recent_ac_submissions(self, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's recent accepted submissions"""
        try:
            submissions = self._call_tool("get_recent_ac_submissions", {
                "username": username,
                "limit": limit
            })

            if submissions and isinstance(submissions, dict):
                return submissions.get("submissions", [])
            return []

        except Exception as e:
            logger.error(f"Failed to get recent AC submissions for {username}: {e}")
            return []

    # ===== PROBLEM PROGRESS & SUBMISSIONS =====

    def get_problem_progress(self, offset: int = 0, limit: int = 100, question_status: str = None,
                           difficulty: List[str] = None) -> Dict[str, Any]:
        """Get user's problem-solving progress"""
        try:
            params = {
                "offset": offset,
                "limit": limit
            }

            if question_status:
                params["questionStatus"] = question_status
            if difficulty:
                params["difficulty"] = difficulty

            return self._call_tool("get_problem_progress", params)

        except Exception as e:
            logger.error(f"Failed to get problem progress: {e}")
            return {}

    def get_all_submissions(self, limit: int = 20, offset: int = 0, question_slug: str = None,
                           lang: str = None, status: str = None) -> Dict[str, Any]:
        """Get paginated list of user submissions"""
        try:
            params = {
                "limit": limit,
                "offset": offset
            }

            if question_slug:
                params["questionSlug"] = question_slug
            if lang:
                params["lang"] = lang
            if status:
                params["status"] = status

            return self._call_tool("get_all_submissions", params)

        except Exception as e:
            logger.error(f"Failed to get all submissions: {e}")
            return {}

    # ===== NOTES MANAGEMENT =====

    def search_notes(self, keyword: str = "", limit: int = 10, skip: int = 0, order_by: str = "DESCENDING") -> List[Dict[str, Any]]:
        """Search user notes"""
        try:
            notes = self._call_tool("search_notes", {
                "keyword": keyword,
                "limit": limit,
                "skip": skip,
                "orderBy": order_by
            })

            if notes and isinstance(notes, dict):
                return notes.get("notes", [])
            return []

        except Exception as e:
            logger.error(f"Failed to search notes: {e}")
            return []

    def get_note(self, question_id: str, limit: int = 10, skip: int = 0) -> List[Dict[str, Any]]:
        """Get notes for a specific problem"""
        try:
            notes = self._call_tool("get_note", {
                "questionId": question_id,
                "limit": limit,
                "skip": skip
            })

            if notes and isinstance(notes, dict):
                return notes.get("notes", [])
            return []

        except Exception as e:
            logger.error(f"Failed to get notes for problem {question_id}: {e}")
            return []

    def create_note(self, question_id: str, content: str, summary: str = "") -> Optional[Dict[str, Any]]:
        """Create a new note for a problem"""
        try:
            return self._call_tool("create_note", {
                "questionId": question_id,
                "content": content,
                "summary": summary
            })
        except Exception as e:
            logger.error(f"Failed to create note for problem {question_id}: {e}")
            return None

    def update_note(self, note_id: str, content: str, summary: str = "") -> Optional[Dict[str, Any]]:
        """Update an existing note"""
        try:
            return self._call_tool("update_note", {
                "noteId": note_id,
                "content": content,
                "summary": summary
            })
        except Exception as e:
            logger.error(f"Failed to update note {note_id}: {e}")
            return None

    # ===== METADATA RESOURCES =====

    def get_problem_categories(self) -> List[Dict[str, Any]]:
        """Get all problem categories"""
        try:
            categories = self._get_resource("categories://problems/all")
            return categories.get("categories", [])
        except Exception as e:
            logger.error(f"Failed to get problem categories: {e}")
            return []

    def get_problem_tags(self) -> List[Dict[str, Any]]:
        """Get all problem tags"""
        try:
            tags = self._get_resource("tags://problems/all")
            return tags.get("tags", [])
        except Exception as e:
            logger.error(f"Failed to get problem tags: {e}")
            return []

    def get_supported_languages(self) -> List[Dict[str, Any]]:
        """Get supported programming languages"""
        try:
            langs = self._get_resource("langs://problems/all")
            return langs.get("languages", [])
        except Exception as e:
            logger.error(f"Failed to get supported languages: {e}")
            return []

    # ===== UTILITY METHODS =====

    def is_healthy(self) -> bool:
        """Check if MCP server is healthy"""
        try:
            # Try to call a simple tool or check server status
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools"""
        try:
            response = self.session.post(
                f"{self.base_url}/jsonrpc",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                },
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            result = response.json()
            return result.get("result", {}).get("tools", [])

        except Exception as e:
            logger.error(f"Failed to get available tools: {e}")
            return []
