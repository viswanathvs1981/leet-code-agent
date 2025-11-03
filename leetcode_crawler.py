import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from config import leetcode_config, app_config

logger = logging.getLogger(__name__)

class LeetCodeCrawler:
    """Crawler for fetching LeetCode problems and their details"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def fetch_all_problems(self) -> List[Dict[str, Any]]:
        """Fetch all problems from LeetCode API"""
        logger.info("Fetching all problems from LeetCode API...")

        try:
            response = self.session.get(leetcode_config.api_url, timeout=30)
            response.raise_for_status()

            data = response.json()
            problems = []

            for problem in data.get('stat_status_pairs', []):
                stat = problem.get('stat', {})
                difficulty = self._get_difficulty_level(problem.get('difficulty', {}))

                problem_data = {
                    'id': str(stat.get('frontend_question_id', '')),
                    'title': stat.get('question__title', ''),
                    'title_slug': stat.get('question__title_slug', ''),
                    'url': f"{leetcode_config.base_url}/problems/{stat.get('question__title_slug', '')}/",
                    'difficulty': difficulty,
                    'acceptance_rate': problem.get('acceptance_rate', 0),
                    'is_paid_only': problem.get('paid_only', False),
                    'topic_tags': [],  # Will be filled by detailed fetch
                    'content': '',     # Will be filled by detailed fetch
                    'examples': [],    # Will be filled by detailed fetch
                    'constraints': [], # Will be filled by detailed fetch
                }

                # Skip paid-only problems for now
                if not problem_data['is_paid_only']:
                    problems.append(problem_data)

            logger.info(f"Fetched {len(problems)} problems from LeetCode API")
            return problems

        except Exception as e:
            logger.error(f"Failed to fetch problems from LeetCode API: {e}")
            return []

    def fetch_problem_details(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch detailed information for a specific problem"""
        try:
            # Add small delay to be respectful to LeetCode servers
            time.sleep(0.5)

            response = self.session.get(problem['url'], timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract problem content
            content_div = soup.find('div', {'class': 'content__u3I1'})
            if content_div:
                problem['content'] = self._clean_html(content_div.get_text())

            # Extract topic tags
            topic_tags = soup.find_all('span', {'class': 'tag__2PqS'})
            problem['topic_tags'] = [tag.get_text().strip() for tag in topic_tags]

            # Extract examples
            examples = self._extract_examples(soup)
            problem['examples'] = examples

            # Extract constraints
            constraints = self._extract_constraints(soup)
            problem['constraints'] = constraints

            # Extract hints if available
            hints = self._extract_hints(soup)
            problem['hints'] = hints

            logger.debug(f"Fetched details for problem: {problem['title']}")
            return problem

        except Exception as e:
            logger.error(f"Failed to fetch details for problem {problem.get('title', 'Unknown')}: {e}")
            return problem

    def fetch_all_problem_details(self, problems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fetch detailed information for all problems concurrently"""
        logger.info(f"Fetching detailed information for {len(problems)} problems...")

        detailed_problems = []
        max_workers = min(app_config.max_concurrent_requests, len(problems))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_problem = {
                executor.submit(self.fetch_problem_details, problem): problem
                for problem in problems
            }

            for future in as_completed(future_to_problem):
                try:
                    detailed_problem = future.result()
                    detailed_problems.append(detailed_problem)
                except Exception as e:
                    logger.error(f"Error processing problem: {e}")

        logger.info(f"Completed fetching details for {len(detailed_problems)} problems")
        return detailed_problems

    def _get_difficulty_level(self, difficulty_obj: Dict[str, Any]) -> str:
        """Convert difficulty object to string"""
        level_map = {1: 'Easy', 2: 'Medium', 3: 'Hard'}
        level = difficulty_obj.get('level', 1)
        return level_map.get(level, 'Unknown')

    def _clean_html(self, html_text: str) -> str:
        """Clean HTML text content"""
        if not html_text:
            return ""

        # Remove extra whitespace and newlines
        cleaned = re.sub(r'\s+', ' ', html_text.strip())

        # Remove HTML entities
        cleaned = re.sub(r'&[a-zA-Z0-9#]+;', '', cleaned)

        return cleaned

    def _extract_examples(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract examples from problem page"""
        examples = []

        # Look for example sections
        example_sections = soup.find_all(['div', 'pre'], string=re.compile(r'Example', re.I))

        for section in example_sections:
            example_text = section.get_text().strip()
            if example_text and len(example_text) > 10:  # Filter out very short examples
                examples.append({
                    'text': example_text,
                    'input': self._extract_example_input(example_text),
                    'output': self._extract_example_output(example_text),
                    'explanation': self._extract_example_explanation(example_text)
                })

        # Also look for code examples
        code_blocks = soup.find_all('pre')
        for code_block in code_blocks:
            code_text = code_block.get_text().strip()
            if code_text and 'Input:' in code_text:
                examples.append({
                    'text': code_text,
                    'input': self._extract_example_input(code_text),
                    'output': self._extract_example_output(code_text),
                    'explanation': self._extract_example_explanation(code_text)
                })

        return examples

    def _extract_example_input(self, example_text: str) -> str:
        """Extract input from example text"""
        input_match = re.search(r'Input:\s*(.*?)(?=Output:|$)', example_text, re.DOTALL)
        return input_match.group(1).strip() if input_match else ""

    def _extract_example_output(self, example_text: str) -> str:
        """Extract output from example text"""
        output_match = re.search(r'Output:\s*(.*?)(?=Explanation:|$)', example_text, re.DOTALL)
        return output_match.group(1).strip() if output_match else ""

    def _extract_example_explanation(self, example_text: str) -> str:
        """Extract explanation from example text"""
        explanation_match = re.search(r'Explanation:\s*(.*)', example_text, re.DOTALL)
        return explanation_match.group(1).strip() if explanation_match else ""

    def _extract_constraints(self, soup: BeautifulSoup) -> List[str]:
        """Extract constraints from problem page"""
        constraints = []

        # Look for constraint sections
        constraint_headers = soup.find_all(['strong', 'b'], string=re.compile(r'Constraints?', re.I))

        for header in constraint_headers:
            # Get the next sibling elements that contain constraints
            constraint_list = header.find_next(['ul', 'ol'])
            if constraint_list:
                for item in constraint_list.find_all('li'):
                    constraints.append(item.get_text().strip())

        # Also look for constraint text directly
        constraint_text = soup.find_all(text=re.compile(r'Constraints?', re.I))
        for text in constraint_text:
            parent = text.parent
            if parent and parent.name in ['p', 'div']:
                constraints.extend(self._split_constraints(parent.get_text()))

        return list(set(constraints))  # Remove duplicates

    def _split_constraints(self, text: str) -> List[str]:
        """Split constraint text into individual constraints"""
        # Remove "Constraints:" prefix
        text = re.sub(r'^Constraints?:?\s*', '', text, flags=re.I)

        # Split by common separators
        constraints = re.split(r'[;\n•·]', text)

        # Clean up each constraint
        return [c.strip() for c in constraints if c.strip()]

    def _extract_hints(self, soup: BeautifulSoup) -> List[str]:
        """Extract hints from problem page"""
        hints = []

        # Look for hint sections
        hint_sections = soup.find_all(['div', 'p'], string=re.compile(r'Hint', re.I))

        for section in hint_sections:
            hint_text = section.get_text().strip()
            if hint_text:
                # Split multiple hints
                individual_hints = re.split(r'Hint\s*\d+:?', hint_text, flags=re.I)
                hints.extend([h.strip() for h in individual_hints if h.strip()])

        return hints

    def crawl_all_problems(self) -> List[Dict[str, Any]]:
        """Complete crawl: get all problems and their details"""
        logger.info("Starting complete LeetCode crawl...")

        # First, get basic problem list
        problems = self.fetch_all_problems()

        if not problems:
            logger.error("Failed to fetch basic problem list")
            return []

        # Then fetch detailed information
        detailed_problems = self.fetch_all_problem_details(problems)

        logger.info(f"Completed crawling {len(detailed_problems)} problems")
        return detailed_problems
