import logging
from typing import Any, Dict, List

from openai import OpenAI
from config import openai_config
from azure_services import blob_service

logger = logging.getLogger(__name__)

class TutorialGenerator:
    """Generates comprehensive tutorials for algorithmic patterns"""

    def __init__(self):
        self.client = None
        if openai_config.api_key:
            try:
                self.client = OpenAI(
                    api_key=openai_config.api_key,
                    api_base=openai_config.api_base
                )
                logger.info("Connected to OpenAI for tutorial generation")
            except Exception as e:
                logger.error(f"Failed to connect to OpenAI: {e}")
        else:
            logger.warning("OpenAI API key not configured")

    def generate_tutorial(self, pattern: Dict[str, Any], example_problems: List[Dict[str, Any]]) -> Optional[str]:
        """Generate a comprehensive tutorial for a pattern"""
        if not self.client:
            logger.warning("OpenAI not available, cannot generate tutorial")
            return None

        try:
            # Create the tutorial generation prompt
            prompt = self._create_tutorial_prompt(pattern, example_problems)

            response = self.client.chat.completions.create(
                model=openai_config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert algorithm instructor. Create comprehensive, beginner-friendly tutorials that teach algorithmic patterns and techniques. Use clear explanations, step-by-step breakdowns, and practical examples."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Balanced creativity and consistency
                max_tokens=3000
            )

            tutorial_content = response.choices[0].message.content
            if tutorial_content:
                # Save to blob storage
                blob_name = blob_service.save_tutorial(pattern['name'], tutorial_content)
                if blob_name:
                    logger.info(f"Generated and saved tutorial for pattern: {pattern['name']}")
                    return tutorial_content

        except Exception as e:
            logger.error(f"Failed to generate tutorial for pattern {pattern.get('name', 'Unknown')}: {e}")

        return None

    def generate_all_tutorials(self, patterns: List[Dict[str, Any]], problems: List[Dict[str, Any]]) -> Dict[str, str]:
        """Generate tutorials for all patterns"""
        tutorials = {}

        for pattern in patterns:
            # Find example problems for this pattern
            example_problems = self._find_pattern_examples(pattern, problems)

            if example_problems:
                tutorial = self.generate_tutorial(pattern, example_problems)
                if tutorial:
                    tutorials[pattern['name']] = tutorial
            else:
                logger.warning(f"No example problems found for pattern: {pattern['name']}")

        logger.info(f"Generated {len(tutorials)} tutorials")
        return tutorials

    def get_tutorial(self, pattern_name: str) -> Optional[str]:
        """Retrieve a tutorial from storage"""
        return blob_service.get_tutorial(pattern_name)

    def _create_tutorial_prompt(self, pattern: Dict[str, Any], example_problems: List[Dict[str, Any]]) -> str:
        """Create a detailed prompt for tutorial generation"""
        prompt_parts = [
            f"# Pattern Tutorial: {pattern['name']}",
            f"**Description:** {pattern.get('description', 'A common algorithmic technique')}",
            f"**Difficulty Level:** {pattern.get('difficulty', 'Medium')}",
            f"**Frequency:** {pattern.get('frequency', 'Common')}",
            "",
            "## Example Problems",
        ]

        # Add example problems
        for i, problem in enumerate(example_problems[:5]):  # Limit to 5 examples
            prompt_parts.append(f"**{i+1}. {problem.get('title', 'Unknown Problem')}**")
            prompt_parts.append(f"   - Difficulty: {problem.get('difficulty', 'Unknown')}")
            prompt_parts.append(f"   - URL: {problem.get('url', '')}")
            if problem.get('ai_summary'):
                prompt_parts.append(f"   - Summary: {problem.get('ai_summary', '')[:200]}...")
            prompt_parts.append("")

        prompt_parts.extend([
            "## Tutorial Requirements",
            "",
            "Create a comprehensive tutorial that includes:",
            "",
            "1. **Introduction & When to Use**",
            "   - What the pattern is and when to recognize it",
            "   - Common problem types that use this pattern",
            "   - Why this pattern is efficient/useful",
            "",
            "2. **Core Concept & Intuition**",
            "   - Step-by-step breakdown of how the pattern works",
            "   - Visual or mental model to understand it",
            "   - Key principles and invariants",
            "",
            "3. **Implementation Steps**",
            "   - Detailed algorithm steps",
            "   - Code structure and key components",
            "   - Edge cases to consider",
            "",
            "4. **Detailed Examples**",
            "   - Walk through 2-3 complete examples",
            "   - Show the thought process for each step",
            "   - Common mistakes and how to avoid them",
            "",
            "5. **Practice Problems**",
            "   - Easy, Medium, and Hard problems using this pattern",
            "   - Progression path for mastery",
            "",
            "6. **Time & Space Complexity**",
            "   - Best/Average/Worst case analysis",
            "   - Optimization techniques",
            "",
            "7. **Variations & Related Patterns**",
            "   - Common variations of this pattern",
            "   - Related techniques to learn next",
            "",
            "## Format Requirements",
            "- Use Markdown formatting",
            "- Include code snippets in Python",
            "- Use clear headings and subheadings",
            "- Include tips, tricks, and common pitfalls",
            "- Make it beginner-friendly but comprehensive",
            "- End with a summary checklist"
        ])

        return "\n".join(prompt_parts)

    def _find_pattern_examples(self, pattern: Dict[str, Any], problems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find problems that use this pattern"""
        pattern_name = pattern['name'].lower()
        examples = []

        for problem in problems:
            # Check if this problem uses the pattern
            ai_patterns = problem.get('ai_patterns', [])
            manual_patterns = problem.get('patterns', [])

            all_patterns = [p.lower() for p in ai_patterns + manual_patterns]

            if pattern_name in all_patterns or any(pattern_name in p for p in all_patterns):
                examples.append(problem)

            # Also check if the problem's topic matches common pattern topics
            if len(examples) < 8:  # Get up to 8 examples
                topic = problem.get('ai_topic', '').lower()
                if topic and (pattern_name in topic or topic in pattern_name):
                    if problem not in examples:
                        examples.append(problem)

        # Sort by difficulty for progression
        difficulty_order = {'Easy': 0, 'Medium': 1, 'Hard': 2}
        examples.sort(key=lambda x: difficulty_order.get(x.get('difficulty', 'Medium'), 1))

        return examples[:8]  # Return up to 8 examples

    def update_tutorial(self, pattern_name: str, new_content: str) -> bool:
        """Update an existing tutorial"""
        success = blob_service.save_tutorial(pattern_name, new_content)
        if success:
            logger.info(f"Updated tutorial for pattern: {pattern_name}")
        return success

    def delete_tutorial(self, pattern_name: str) -> bool:
        """Delete a tutorial (not implemented in blob service yet)"""
        # For now, just log - deletion would require blob service enhancement
        logger.info(f"Tutorial deletion requested for: {pattern_name}")
        return False
