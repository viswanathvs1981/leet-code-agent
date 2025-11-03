import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI
from config import openai_config

logger = logging.getLogger(__name__)

class ProblemAnalyzer:
    """AI-powered analyzer for categorizing LeetCode problems"""

    def __init__(self):
        self.client = None
        if openai_config.api_key:
            try:
                self.client = OpenAI(
                    api_key=openai_config.api_key,
                    api_base=openai_config.api_base
                )
                logger.info("Connected to OpenAI service")
            except Exception as e:
                logger.error(f"Failed to connect to OpenAI: {e}")
        else:
            logger.warning("OpenAI API key not configured")

    def analyze_problem(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single problem and add AI-generated insights"""
        if not self.client:
            logger.warning("OpenAI not available, returning original problem")
            return problem

        try:
            # Prepare the problem data for analysis
            analysis_prompt = self._create_analysis_prompt(problem)

            response = self.client.chat.completions.create(
                model=openai_config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert LeetCode problem analyzer. Analyze the given problem and provide structured insights about its topic, patterns, and solution approach. Return your analysis in JSON format."
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent analysis
                max_tokens=1000
            )

            analysis_result = response.choices[0].message.content
            if analysis_result:
                insights = self._parse_analysis_result(analysis_result)
                problem.update(insights)

            logger.info(f"Analyzed problem: {problem.get('title', 'Unknown')}")
            return problem

        except Exception as e:
            logger.error(f"Failed to analyze problem {problem.get('title', 'Unknown')}: {e}")
            return problem

    def analyze_problems_batch(self, problems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze multiple problems and add AI insights"""
        if not self.client:
            logger.warning("OpenAI not available, returning original problems")
            return problems

        analyzed_problems = []
        batch_size = 10  # Process in batches to avoid rate limits

        for i in range(0, len(problems), batch_size):
            batch = problems[i:i + batch_size]
            logger.info(f"Analyzing batch {i//batch_size + 1} of {(len(problems) + batch_size - 1)//batch_size}")

            for problem in batch:
                analyzed_problem = self.analyze_problem(problem)
                analyzed_problems.append(analyzed_problem)

        logger.info(f"Completed analysis of {len(analyzed_problems)} problems")
        return analyzed_problems

    def identify_patterns(self, problems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify common patterns across all problems"""
        if not self.client:
            logger.warning("OpenAI not available, returning empty patterns")
            return []

        try:
            # Create a summary of all problems for pattern identification
            problems_summary = self._create_patterns_summary(problems)

            response = self.client.chat.completions.create(
                model=openai_config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at identifying algorithmic patterns in coding problems. Analyze the given problems and identify the key patterns, techniques, and approaches that appear frequently. Return a comprehensive list of patterns with descriptions and examples."
                    },
                    {
                        "role": "user",
                        "content": f"Analyze these {len(problems)} LeetCode problems and identify the key algorithmic patterns and techniques:\n\n{problems_summary}"
                    }
                ],
                temperature=0.2,
                max_tokens=2000
            )

            patterns_result = response.choices[0].message.content
            if patterns_result:
                patterns = self._parse_patterns_result(patterns_result)
                logger.info(f"Identified {len(patterns)} patterns")
                return patterns

        except Exception as e:
            logger.error(f"Failed to identify patterns: {e}")

        return []

    def _create_analysis_prompt(self, problem: Dict[str, Any]) -> str:
        """Create a detailed prompt for problem analysis"""
        prompt_parts = [
            f"Problem Title: {problem.get('title', 'Unknown')}",
            f"Difficulty: {problem.get('difficulty', 'Unknown')}",
            f"URL: {problem.get('url', '')}",
            f"Topic Tags: {', '.join(problem.get('topic_tags', []))}",
            f"Content: {problem.get('content', '')[:2000]}"  # Limit content length
        ]

        if problem.get('examples'):
            prompt_parts.append("Examples:")
            for i, example in enumerate(problem.get('examples', [])[:3]):  # Limit examples
                prompt_parts.append(f"Example {i+1}: {example.get('text', '')[:500]}")

        if problem.get('constraints'):
            prompt_parts.append(f"Constraints: {', '.join(problem.get('constraints', [])[:5])}")

        prompt_parts.append("""
Analyze this problem and provide:
1. Primary topic/category (e.g., Array, Graph, Dynamic Programming)
2. Key algorithmic patterns/techniques used to solve it
3. Solution approach summary (2-3 sentences)
4. Key insights or observations about the problem
5. Related concepts or prerequisites
6. Time and space complexity hints

Return the analysis as a JSON object with these fields:
{
  "ai_topic": "primary topic",
  "ai_patterns": ["pattern1", "pattern2"],
  "ai_summary": "solution approach summary",
  "ai_insights": ["insight1", "insight2"],
  "ai_prerequisites": ["concept1", "concept2"],
  "ai_complexity_hints": "time/space complexity hints"
}
""")

        return "\n\n".join(prompt_parts)

    def _parse_analysis_result(self, result: str) -> Dict[str, Any]:
        """Parse the JSON response from OpenAI analysis"""
        try:
            # Try to extract JSON from the response
            json_start = result.find('{')
            json_end = result.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_str = result[json_start:json_end]
                return json.loads(json_str)
            else:
                # Fallback: try to parse the entire response as JSON
                return json.loads(result)

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse analysis result as JSON: {result[:200]}...")
            return {}

    def _create_patterns_summary(self, problems: List[Dict[str, Any]]) -> str:
        """Create a summary of problems for pattern identification"""
        summary_parts = []

        # Group problems by their topics/patterns for better analysis
        topic_counts = {}
        pattern_counts = {}

        for problem in problems:
            topic = problem.get('ai_topic') or problem.get('topic')
            if topic:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

            patterns = problem.get('ai_patterns') or problem.get('patterns', [])
            for pattern in patterns:
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        summary_parts.append("Problem Distribution:")
        summary_parts.append(f"Topics: {dict(sorted(topic_counts.items(), key=lambda x: x[1], reverse=True))}")
        summary_parts.append(f"Patterns: {dict(sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True))}")

        # Add sample problems from different categories
        summary_parts.append("\nSample Problems by Topic:")
        topic_samples = {}
        for problem in problems[:50]:  # Sample first 50 problems
            topic = problem.get('ai_topic') or problem.get('topic')
            if topic and topic not in topic_samples:
                topic_samples[topic] = problem.get('title', 'Unknown')

        for topic, title in topic_samples.items():
            summary_parts.append(f"- {topic}: {title}")

        return "\n".join(summary_parts)

    def _parse_patterns_result(self, result: str) -> List[Dict[str, Any]]:
        """Parse the patterns identification result"""
        patterns = []

        try:
            # Try to parse as JSON first
            parsed = json.loads(result)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict) and 'patterns' in parsed:
                return parsed['patterns']

            # If not JSON, try to extract pattern information from text
            lines = result.split('\n')
            current_pattern = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Look for pattern headers (numbered or bulleted)
                if re.match(r'^(\d+\.|-|\*)\s*(.+)$', line):
                    if current_pattern:
                        patterns.append(current_pattern)

                    pattern_name = re.sub(r'^(\d+\.|-|\*)\s*', '', line)
                    current_pattern = {
                        'name': pattern_name,
                        'description': '',
                        'examples': [],
                        'difficulty': 'Medium',
                        'frequency': 'Common'
                    }
                elif current_pattern and line.startswith(('Description:', 'Examples:', 'Difficulty:', 'Frequency:')):
                    # Parse pattern details
                    if line.startswith('Description:'):
                        current_pattern['description'] = line.replace('Description:', '').strip()
                    elif line.startswith('Examples:'):
                        examples_text = line.replace('Examples:', '').strip()
                        current_pattern['examples'] = [e.strip() for e in examples_text.split(',') if e.strip()]
                    elif line.startswith('Difficulty:'):
                        current_pattern['difficulty'] = line.replace('Difficulty:', '').strip()
                    elif line.startswith('Frequency:'):
                        current_pattern['frequency'] = line.replace('Frequency:', '').strip()
                elif current_pattern and line:
                    # Continuation of description
                    if current_pattern['description']:
                        current_pattern['description'] += ' ' + line
                    else:
                        current_pattern['description'] = line

            if current_pattern:
                patterns.append(current_pattern)

        except Exception as e:
            logger.error(f"Failed to parse patterns result: {e}")

        # Ensure we have at least some basic patterns
        if not patterns:
            patterns = [
                {
                    'name': 'Two Pointers',
                    'description': 'Use two pointers to traverse arrays from different directions',
                    'examples': ['Valid Palindrome', 'Two Sum II'],
                    'difficulty': 'Easy',
                    'frequency': 'Very Common'
                },
                {
                    'name': 'Dynamic Programming',
                    'description': 'Break down problems into smaller subproblems and solve recursively with memoization',
                    'examples': ['Climbing Stairs', 'House Robber'],
                    'difficulty': 'Medium',
                    'frequency': 'Very Common'
                },
                {
                    'name': 'Sliding Window',
                    'description': 'Maintain a window of elements and slide it to find optimal solutions',
                    'examples': ['Maximum Subarray', 'Longest Substring Without Repeating Characters'],
                    'difficulty': 'Medium',
                    'frequency': 'Common'
                }
            ]

        return patterns
