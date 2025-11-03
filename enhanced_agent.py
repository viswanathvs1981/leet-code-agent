import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI
from config import openai_config
from azure_services import cosmos_service, blob_service

logger = logging.getLogger(__name__)

class EnhancedAgent:
    """Intelligent Q&A agent with RAG capabilities for LeetCode problems and patterns"""

    def __init__(self):
        self.client = None
        if openai_config.api_key:
            try:
                self.client = OpenAI(
                    api_key=openai_config.api_key,
                    api_base=openai_config.api_base
                )
                logger.info("Connected to OpenAI for enhanced agent")
            except Exception as e:
                logger.error(f"Failed to connect to OpenAI: {e}")
        else:
            logger.warning("OpenAI API key not configured")

    def ask_question(self, question: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Answer a question using RAG (Retrieval-Augmented Generation)"""
        if not self.client:
            return {
                "answer": "AI service is not available. Please check configuration.",
                "related_problems": [],
                "related_patterns": [],
                "confidence": 0.0
            }

        try:
            # Step 1: Retrieve relevant information
            retrieved_info = self._retrieve_relevant_info(question)

            # Step 2: Generate answer using retrieved context
            answer, confidence = self._generate_answer(question, retrieved_info, user_context)

            # Step 3: Extract related items
            related_problems = self._extract_related_problems(retrieved_info)
            related_patterns = self._extract_related_patterns(retrieved_info)

            return {
                "answer": answer,
                "related_problems": related_problems[:5],  # Limit results
                "related_patterns": related_patterns[:3],
                "confidence": confidence,
                "sources": retrieved_info.get("sources", [])
            }

        except Exception as e:
            logger.error(f"Failed to answer question: {e}")
            return {
                "answer": f"Sorry, I encountered an error while processing your question: {str(e)}",
                "related_problems": [],
                "related_patterns": [],
                "confidence": 0.0
            }

    def _retrieve_relevant_info(self, question: str) -> Dict[str, Any]:
        """Retrieve relevant problems, patterns, and tutorials"""
        retrieved = {
            "problems": [],
            "patterns": [],
            "tutorials": [],
            "solutions": [],
            "sources": []
        }

        # Search for relevant problems
        relevant_problems = self._search_problems(question)
        retrieved["problems"] = relevant_problems[:10]  # Limit for context

        # Search for relevant patterns
        relevant_patterns = self._search_patterns(question)
        retrieved["patterns"] = relevant_patterns[:5]

        # Get tutorials for relevant patterns
        for pattern in relevant_patterns:
            tutorial = blob_service.get_tutorial(pattern["name"])
            if tutorial:
                retrieved["tutorials"].append({
                    "pattern": pattern["name"],
                    "content": tutorial[:2000]  # Limit tutorial content
                })

        # Get solutions for relevant problems
        for problem in relevant_problems[:3]:  # Only get solutions for top problems
            solution = blob_service.get_solution(problem["id"])
            if solution:
                retrieved["solutions"].append({
                    "problem_id": problem["id"],
                    "title": problem["title"],
                    "content": solution[:1500]  # Limit solution content
                })

        # Track sources
        retrieved["sources"] = [
            f"{len(retrieved['problems'])} problems",
            f"{len(retrieved['patterns'])} patterns",
            f"{len(retrieved['tutorials'])} tutorials",
            f"{len(retrieved['solutions'])} solutions"
        ]

        return retrieved

    def _search_problems(self, question: str) -> List[Dict[str, Any]]:
        """Search for problems relevant to the question"""
        # Get all problems from CosmosDB
        all_problems = cosmos_service.get_all_problems()
        if not all_problems:
            return []

        scored_problems = []

        # Score each problem based on relevance to the question
        for problem in all_problems:
            score = self._calculate_problem_relevance(question, problem)
            if score > 0:
                scored_problems.append((score, problem))

        # Sort by relevance score
        scored_problems.sort(key=lambda x: x[0], reverse=True)
        return [problem for _, problem in scored_problems]

    def _search_patterns(self, question: str) -> List[Dict[str, Any]]:
        """Search for patterns relevant to the question"""
        all_patterns = cosmos_service.get_all_patterns()
        if not all_patterns:
            return []

        scored_patterns = []

        for pattern in all_patterns:
            score = self._calculate_pattern_relevance(question, pattern)
            if score > 0:
                scored_patterns.append((score, pattern))

        scored_patterns.sort(key=lambda x: x[0], reverse=True)
        return [pattern for _, pattern in scored_patterns]

    def _calculate_problem_relevance(self, question: str, problem: Dict[str, Any]) -> float:
        """Calculate how relevant a problem is to the question"""
        score = 0.0
        question_lower = question.lower()

        # Title relevance
        title = problem.get("title", "").lower()
        if any(word in title for word in question_lower.split()):
            score += 2.0

        # Topic relevance
        topic = problem.get("ai_topic", "").lower()
        if topic and topic in question_lower:
            score += 1.5

        # Pattern relevance
        patterns = problem.get("ai_patterns", [])
        for pattern in patterns:
            if pattern.lower() in question_lower:
                score += 1.0

        # Difficulty matching
        if "easy" in question_lower and problem.get("difficulty") == "Easy":
            score += 0.5
        if "medium" in question_lower and problem.get("difficulty") == "Medium":
            score += 0.5
        if "hard" in question_lower and problem.get("difficulty") == "Hard":
            score += 0.5

        # Content relevance (partial match)
        content = problem.get("content", "").lower()
        question_words = set(question_lower.split())
        content_words = set(content.split())
        overlap = len(question_words.intersection(content_words))
        score += overlap * 0.1

        return score

    def _calculate_pattern_relevance(self, question: str, pattern: Dict[str, Any]) -> float:
        """Calculate how relevant a pattern is to the question"""
        score = 0.0
        question_lower = question.lower()

        # Pattern name relevance
        pattern_name = pattern.get("name", "").lower()
        if pattern_name in question_lower:
            score += 3.0

        # Description relevance
        description = pattern.get("description", "").lower()
        if any(word in description for word in question_lower.split()):
            score += 1.0

        # Frequency boost for common patterns
        frequency = pattern.get("frequency", "").lower()
        if "common" in frequency or "very common" in frequency:
            score += 0.5

        return score

    def _generate_answer(self, question: str, retrieved_info: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None) -> Tuple[str, float]:
        """Generate an answer using retrieved information"""
        try:
            # Create context from retrieved information
            context = self._build_context(retrieved_info, user_context)

            # Add user context if available
            user_info = ""
            if user_context:
                user_info = f"\nUser Context: Skill level - {user_context.get('skill_level', 'intermediate')}, " \
                           f"Preferred language - {user_context.get('preferred_language', 'Python')}"

            response = self.client.chat.completions.create(
                model=openai_config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert LeetCode tutor and algorithm instructor. Use the provided context to give comprehensive, helpful answers about algorithms, data structures, and problem-solving techniques. Be encouraging and provide practical advice."
                    },
                    {
                        "role": "user",
                        "content": f"Question: {question}{user_info}\n\nContext:\n{context}\n\nPlease provide a comprehensive answer based on the context above."
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )

            answer = response.choices[0].message.content

            # Calculate confidence based on context richness
            confidence = self._calculate_confidence(retrieved_info)

            return answer, confidence

        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            return "I apologize, but I encountered an error while generating your answer. Please try rephrasing your question.", 0.0

    def _build_context(self, retrieved_info: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None) -> str:
        """Build context string from retrieved information"""
        context_parts = []

        # Add pattern information
        if retrieved_info.get("patterns"):
            context_parts.append("## Relevant Patterns:")
            for pattern in retrieved_info["patterns"][:3]:
                context_parts.append(f"- **{pattern['name']}**: {pattern.get('description', '')}")
                if pattern.get('examples'):
                    context_parts.append(f"  Examples: {', '.join(pattern['examples'][:3])}")

        # Add problem information
        if retrieved_info.get("problems"):
            context_parts.append("\n## Relevant Problems:")
            for problem in retrieved_info["problems"][:5]:
                context_parts.append(f"- **{problem['title']}** ({problem.get('difficulty', 'Medium')})")
                if problem.get('ai_summary'):
                    context_parts.append(f"  {problem['ai_summary'][:150]}...")

        # Add tutorial excerpts
        if retrieved_info.get("tutorials"):
            context_parts.append("\n## Tutorial Information:")
            for tutorial in retrieved_info["tutorials"][:2]:
                context_parts.append(f"- **{tutorial['pattern']} Tutorial**: {tutorial['content'][:500]}...")

        # Add solution insights
        if retrieved_info.get("solutions"):
            context_parts.append("\n## Solution Insights:")
            for solution in retrieved_info["solutions"][:2]:
                context_parts.append(f"- **{solution['title']}**: {solution['content'][:300]}...")

        return "\n".join(context_parts)

    def _calculate_confidence(self, retrieved_info: Dict[str, Any]) -> float:
        """Calculate confidence score based on retrieved information"""
        confidence = 0.0

        # Base confidence
        confidence += 0.3

        # Boost based on amount of relevant information
        if retrieved_info.get("patterns"):
            confidence += min(len(retrieved_info["patterns"]) * 0.1, 0.3)
        if retrieved_info.get("problems"):
            confidence += min(len(retrieved_info["problems"]) * 0.05, 0.2)
        if retrieved_info.get("tutorials"):
            confidence += min(len(retrieved_info["tutorials"]) * 0.1, 0.2)
        if retrieved_info.get("solutions"):
            confidence += min(len(retrieved_info["solutions"]) * 0.1, 0.2)

        return min(confidence, 1.0)

    def _extract_related_problems(self, retrieved_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract related problems from retrieved info"""
        related = []
        for problem in retrieved_info.get("problems", []):
            related.append({
                "id": problem.get("id"),
                "title": problem.get("title"),
                "difficulty": problem.get("difficulty"),
                "url": problem.get("url"),
                "summary": problem.get("ai_summary", "")[:100]
            })
        return related

    def _extract_related_patterns(self, retrieved_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract related patterns from retrieved info"""
        related = []
        for pattern in retrieved_info.get("patterns", []):
            related.append({
                "name": pattern.get("name"),
                "description": pattern.get("description", "")[:100],
                "difficulty": pattern.get("difficulty"),
                "examples": pattern.get("examples", [])[:3]
            })
        return related

    def get_study_recommendations(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Get personalized study recommendations"""
        # This would analyze user progress and recommend next steps
        # For now, return basic recommendations
        return {
            "recommended_patterns": ["Two Pointers", "Sliding Window", "Dynamic Programming"],
            "next_problems": ["Two Sum", "Valid Palindrome", "Climbing Stairs"],
            "study_plan": "Focus on array manipulation patterns this week"
        }
