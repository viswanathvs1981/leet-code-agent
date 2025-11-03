import logging
from typing import Any, Dict, List

from openai import OpenAI
from config import openai_config
from azure_services import blob_service

logger = logging.getLogger(__name__)

class SolutionGenerator:
    """Generates comprehensive solutions for LeetCode problems"""

    def __init__(self):
        self.client = None
        if openai_config.api_key:
            try:
                self.client = OpenAI(
                    api_key=openai_config.api_key,
                    api_base=openai_config.api_base
                )
                logger.info("Connected to OpenAI for solution generation")
            except Exception as e:
                logger.error(f"Failed to connect to OpenAI: {e}")
        else:
            logger.warning("OpenAI API key not configured")

    def generate_solution(self, problem: Dict[str, Any]) -> Optional[str]:
        """Generate a comprehensive solution for a problem"""
        if not self.client:
            logger.warning("OpenAI not available, cannot generate solution")
            return None

        try:
            # Create the solution generation prompt
            prompt = self._create_solution_prompt(problem)

            response = self.client.chat.completions.create(
                model=openai_config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert algorithm instructor and competitive programmer. Create detailed, correct solutions that teach problem-solving techniques. Provide multiple approaches when applicable, with clear explanations and optimal implementations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,  # Lower temperature for accurate solutions
                max_tokens=4000
            )

            solution_content = response.choices[0].message.content
            if solution_content:
                # Save to blob storage
                problem_id = problem.get('id', 'unknown')
                blob_name = blob_service.save_solution(problem_id, solution_content)
                if blob_name:
                    logger.info(f"Generated and saved solution for problem: {problem.get('title', 'Unknown')}")
                    return solution_content

        except Exception as e:
            logger.error(f"Failed to generate solution for problem {problem.get('title', 'Unknown')}: {e}")

        return None

    def generate_solutions_batch(self, problems: List[Dict[str, Any]], limit: int = 50) -> Dict[str, str]:
        """Generate solutions for multiple problems"""
        solutions = {}

        # Prioritize by difficulty and importance
        prioritized_problems = self._prioritize_problems(problems)

        for i, problem in enumerate(prioritized_problems[:limit]):
            logger.info(f"Generating solution {i+1}/{min(limit, len(prioritized_problems))} for: {problem.get('title', 'Unknown')}")

            solution = self.generate_solution(problem)
            if solution:
                problem_id = problem.get('id', 'unknown')
                solutions[problem_id] = solution

        logger.info(f"Generated {len(solutions)} solutions")
        return solutions

    def get_solution(self, problem_id: str) -> Optional[str]:
        """Retrieve a solution from storage"""
        return blob_service.get_solution(problem_id)

    def _create_solution_prompt(self, problem: Dict[str, Any]) -> str:
        """Create a detailed prompt for solution generation"""
        prompt_parts = [
            f"# Solution for: {problem.get('title', 'Unknown Problem')}",
            f"**Problem ID:** {problem.get('id', 'Unknown')}",
            f"**Difficulty:** {problem.get('difficulty', 'Unknown')}",
            f"**URL:** {problem.get('url', '')}",
            "",
            "## Problem Description",
            problem.get('content', 'No description available')[:1500],  # Limit length
            "",
            "## Analysis",
        ]

        # Add AI insights if available
        if problem.get('ai_topic'):
            prompt_parts.append(f"**Topic:** {problem.get('ai_topic', '')}")
        if problem.get('ai_patterns'):
            prompt_parts.append(f"**Patterns:** {', '.join(problem.get('ai_patterns', []))}")
        if problem.get('ai_summary'):
            prompt_parts.append(f"**Summary:** {problem.get('ai_summary', '')}")
        if problem.get('ai_insights'):
            prompt_parts.append("**Key Insights:**")
            for insight in problem.get('ai_insights', []):
                prompt_parts.append(f"- {insight}")
        if problem.get('ai_prerequisites'):
            prompt_parts.append(f"**Prerequisites:** {', '.join(problem.get('ai_prerequisites', []))}")

        # Add examples
        if problem.get('examples'):
            prompt_parts.append("\n## Examples")
            for i, example in enumerate(problem.get('examples', [])[:3]):
                prompt_parts.append(f"**Example {i+1}:**")
                prompt_parts.append(f"```\n{example.get('text', '')}\n```")

        # Add constraints
        if problem.get('constraints'):
            prompt_parts.append("\n## Constraints")
            for constraint in problem.get('constraints', []):
                prompt_parts.append(f"- {constraint}")

        prompt_parts.extend([
            "",
            "## Solution Requirements",
            "",
            "Create a comprehensive solution that includes:",
            "",
            "1. **Problem Understanding**",
            "   - Clear restatement of the problem",
            "   - Key requirements and edge cases",
            "",
            "2. **Approach Analysis**",
            "   - Multiple solution approaches (Brute Force → Optimal)",
            "   - Time/Space complexity analysis for each",
            "   - Trade-offs and why one approach is better",
            "",
            "3. **Detailed Solution**",
            "   - Step-by-step algorithm explanation",
            "   - Code implementation with comments",
            "   - Variable naming and logic flow",
            "",
            "4. **Edge Cases & Testing**",
            "   - Important edge cases to consider",
            "   - Test cases with expected outputs",
            "",
            "5. **Optimization Insights**",
            "   - How to optimize further if needed",
            "   - Common mistakes and pitfalls",
            "",
            "6. **Alternative Approaches**",
            "   - Different algorithms that could solve this",
            "   - When each approach is preferable",
            "",
            "## Code Requirements",
            "- Provide complete, runnable Python code",
            "- Include proper error handling",
            "- Add detailed comments explaining each step",
            "- Use clear variable names",
            "- Include type hints where helpful",
            "- Handle edge cases gracefully",
            "",
            "## Format",
            "- Use Markdown formatting",
            "- Separate different approaches clearly",
            "- Include complexity analysis for each solution",
            "- End with a summary of key takeaways"
        ])

        return "\n".join(prompt_parts)

    def _prioritize_problems(self, problems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize problems for solution generation"""
        # Score problems based on various factors
        scored_problems = []

        for problem in problems:
            score = 0

            # Difficulty scoring (Easy = 1, Medium = 2, Hard = 3)
            difficulty = problem.get('difficulty', 'Medium')
            if difficulty == 'Easy':
                score += 1
            elif difficulty == 'Medium':
                score += 2
            elif difficulty == 'Hard':
                score += 3

            # Acceptance rate (higher is better, indicates importance)
            acceptance_rate = problem.get('acceptance_rate', 50)
            score += acceptance_rate / 20  # Scale to add 0-2.5 points

            # Has AI analysis (prefer analyzed problems)
            if problem.get('ai_patterns'):
                score += 1

            # Has examples (easier to generate solutions for)
            if problem.get('examples'):
                score += 0.5

            scored_problems.append((score, problem))

        # Sort by score descending
        scored_problems.sort(key=lambda x: x[0], reverse=True)
        return [problem for _, problem in scored_problems]

    def update_solution(self, problem_id: str, new_content: str) -> bool:
        """Update an existing solution"""
        success = blob_service.save_solution(problem_id, new_content)
        if success:
            logger.info(f"Updated solution for problem ID: {problem_id}")
        return success

    def delete_solution(self, problem_id: str) -> bool:
        """Delete a solution (not implemented in blob service yet)"""
        logger.info(f"Solution deletion requested for problem ID: {problem_id}")
        return False
