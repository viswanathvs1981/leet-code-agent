import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from azure_services import cosmos_service

logger = logging.getLogger(__name__)

class PatternMasteryTracker:
    """Tracks user progress and mastery of algorithmic patterns"""

    def __init__(self):
        self.container_name = "user_progress"

    def update_user_progress(self, user_id: str, problem_id: str, success: bool,
                           time_spent: Optional[int] = None, attempts: int = 1) -> bool:
        """Update user progress after solving a problem"""
        try:
            # Get problem details
            problem = cosmos_service.get_problem(problem_id)
            if not problem:
                logger.warning(f"Problem {problem_id} not found for progress tracking")
                return False

            # Get or create user progress
            user_progress = self._get_user_progress(user_id)
            if not user_progress:
                user_progress = self._create_user_progress(user_id)

            # Update problem attempts
            self._update_problem_attempt(user_progress, problem, success, time_spent, attempts)

            # Update pattern mastery
            self._update_pattern_mastery(user_progress, problem, success)

            # Calculate overall stats
            self._calculate_overall_stats(user_progress)

            # Save updated progress
            return self._save_user_progress(user_progress)

        except Exception as e:
            logger.error(f"Failed to update user progress: {e}")
            return False

    def get_user_progress(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's learning progress"""
        return self._get_user_progress(user_id)

    def get_mastered_patterns(self, user_id: str) -> List[Dict[str, Any]]:
        """Get patterns the user has mastered"""
        user_progress = self._get_user_progress(user_id)
        if not user_progress:
            return []

        mastered = []
        for pattern_name, mastery in user_progress.get("pattern_mastery", {}).items():
            if mastery.get("mastery_level", 0) >= 80:  # 80% mastery threshold
                mastered.append({
                    "pattern": pattern_name,
                    "mastery_percentage": mastery["mastery_level"],
                    "problems_solved": mastery.get("problems_solved", 0),
                    "last_practiced": mastery.get("last_updated")
                })

        return sorted(mastered, key=lambda x: x["mastery_percentage"], reverse=True)

    def get_learning_recommendations(self, user_id: str) -> Dict[str, Any]:
        """Get personalized learning recommendations"""
        user_progress = self._get_user_progress(user_id)
        if not user_progress:
            return self._get_default_recommendations()

        # Analyze current progress
        weak_patterns = self._identify_weak_patterns(user_progress)
        next_patterns = self._suggest_next_patterns(user_progress)
        review_problems = self._get_review_problems(user_progress)

        return {
            "weak_patterns": weak_patterns,
            "next_patterns_to_learn": next_patterns,
            "problems_to_review": review_problems,
            "study_streak": user_progress.get("study_streak", 0),
            "total_problems_solved": user_progress.get("total_problems_solved", 0),
            "mastery_progress": self._calculate_mastery_progress(user_progress)
        }

    def get_study_plan(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Generate a personalized study plan"""
        user_progress = self._get_user_progress(user_id)
        if not user_progress:
            return self._get_default_study_plan(days)

        recommendations = self.get_learning_recommendations(user_id)

        # Create daily plan
        daily_plan = []
        current_date = datetime.utcnow()

        for day in range(days):
            day_date = current_date + timedelta(days=day)

            # Alternate between weak pattern practice and new pattern learning
            if day % 2 == 0 and recommendations["weak_patterns"]:
                # Focus on weak patterns
                pattern = recommendations["weak_patterns"][0]
                problems = self._get_pattern_problems(pattern["pattern"], user_progress)
                daily_plan.append({
                    "date": day_date.isoformat(),
                    "focus": f"Strengthen {pattern['pattern']}",
                    "problems": problems[:3],  # 3 problems per day
                    "goal": "Review and solve problems to improve mastery"
                })
            else:
                # Learn new patterns or review
                if recommendations["next_patterns_to_learn"]:
                    pattern = recommendations["next_patterns_to_learn"][0]
                    problems = self._get_pattern_problems(pattern, user_progress, solved=False)
                    daily_plan.append({
                        "date": day_date.isoformat(),
                        "focus": f"Learn {pattern}",
                        "problems": problems[:2],  # 2 problems for new patterns
                        "goal": "Study the pattern and solve introductory problems"
                    })
                else:
                    # Review old problems
                    daily_plan.append({
                        "date": day_date.isoformat(),
                        "focus": "Review and consolidate",
                        "problems": recommendations["problems_to_review"][:3],
                        "goal": "Review previously solved problems to maintain knowledge"
                    })

        return {
            "study_plan": daily_plan,
            "estimated_completion_days": days,
            "total_problems": sum(len(day["problems"]) for day in daily_plan)
        }

    def _get_user_progress(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user progress from database"""
        try:
            # Use CosmosDB to get user progress
            # For now, return a mock structure - in production this would query the database
            return {
                "user_id": user_id,
                "total_problems_solved": 45,
                "study_streak": 7,
                "last_study_date": datetime.utcnow().isoformat(),
                "pattern_mastery": {
                    "Two Pointers": {
                        "mastery_level": 85,
                        "problems_solved": 12,
                        "total_attempts": 15,
                        "average_time": 25,
                        "last_updated": datetime.utcnow().isoformat()
                    },
                    "Sliding Window": {
                        "mastery_level": 60,
                        "problems_solved": 8,
                        "total_attempts": 12,
                        "average_time": 35,
                        "last_updated": (datetime.utcnow() - timedelta(days=2)).isoformat()
                    },
                    "Dynamic Programming": {
                        "mastery_level": 30,
                        "problems_solved": 3,
                        "total_attempts": 8,
                        "average_time": 45,
                        "last_updated": (datetime.utcnow() - timedelta(days=5)).isoformat()
                    }
                },
                "problem_attempts": {
                    "1": {"solved": True, "attempts": 2, "time_spent": 15, "solved_date": "2024-01-15"},
                    "2": {"solved": True, "attempts": 1, "time_spent": 20, "solved_date": "2024-01-16"},
                },
                "weakest_topics": ["Dynamic Programming", "Graph Algorithms"]
            }
        except Exception as e:
            logger.error(f"Failed to get user progress: {e}")
            return None

    def _create_user_progress(self, user_id: str) -> Dict[str, Any]:
        """Create new user progress record"""
        return {
            "user_id": user_id,
            "total_problems_solved": 0,
            "study_streak": 0,
            "last_study_date": None,
            "pattern_mastery": {},
            "problem_attempts": {},
            "created_date": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }

    def _update_problem_attempt(self, user_progress: Dict[str, Any], problem: Dict[str, Any],
                              success: bool, time_spent: Optional[int], attempts: int) -> None:
        """Update problem attempt record"""
        problem_id = problem["id"]

        if "problem_attempts" not in user_progress:
            user_progress["problem_attempts"] = {}

        attempt_record = user_progress["problem_attempts"].get(problem_id, {
            "solved": False,
            "attempts": 0,
            "best_time": None,
            "first_solved_date": None,
            "last_attempt_date": None
        })

        attempt_record["attempts"] += attempts
        attempt_record["last_attempt_date"] = datetime.utcnow().isoformat()

        if success:
            attempt_record["solved"] = True
            if not attempt_record["first_solved_date"]:
                attempt_record["first_solved_date"] = datetime.utcnow().isoformat()

            if time_spent and (not attempt_record["best_time"] or time_spent < attempt_record["best_time"]):
                attempt_record["best_time"] = time_spent

            user_progress["total_problems_solved"] = user_progress.get("total_problems_solved", 0) + 1

        user_progress["problem_attempts"][problem_id] = attempt_record

    def _update_pattern_mastery(self, user_progress: Dict[str, Any], problem: Dict[str, Any], success: bool) -> None:
        """Update pattern mastery based on problem solving"""
        patterns = problem.get("ai_patterns", [])
        if not patterns:
            return

        for pattern_name in patterns:
            if "pattern_mastery" not in user_progress:
                user_progress["pattern_mastery"] = {}

            mastery = user_progress["pattern_mastery"].get(pattern_name, {
                "mastery_level": 0,
                "problems_solved": 0,
                "total_attempts": 0,
                "successful_solves": 0,
                "average_time": 0,
                "last_updated": datetime.utcnow().isoformat()
            })

            mastery["total_attempts"] += 1
            if success:
                mastery["successful_solves"] += 1
                mastery["problems_solved"] += 1

            # Calculate mastery level (simplified formula)
            solve_rate = mastery["successful_solves"] / mastery["total_attempts"]
            experience_factor = min(mastery["problems_solved"] / 10, 1.0)  # Cap at 10 problems
            mastery["mastery_level"] = int((solve_rate * 0.7 + experience_factor * 0.3) * 100)

            mastery["last_updated"] = datetime.utcnow().isoformat()
            user_progress["pattern_mastery"][pattern_name] = mastery

    def _calculate_overall_stats(self, user_progress: Dict[str, Any]) -> None:
        """Calculate overall user statistics"""
        # Update study streak
        last_study = user_progress.get("last_study_date")
        if last_study:
            last_date = datetime.fromisoformat(last_study.replace('Z', '+00:00'))
            days_diff = (datetime.utcnow() - last_date).days
            if days_diff <= 1:
                user_progress["study_streak"] = user_progress.get("study_streak", 0) + 1
            elif days_diff > 1:
                user_progress["study_streak"] = 1
        else:
            user_progress["study_streak"] = 1

        user_progress["last_study_date"] = datetime.utcnow().isoformat()

    def _save_user_progress(self, user_progress: Dict[str, Any]) -> bool:
        """Save user progress to database"""
        try:
            # In production, this would save to CosmosDB
            # For now, just return success
            user_progress["last_updated"] = datetime.utcnow().isoformat()
            return True
        except Exception as e:
            logger.error(f"Failed to save user progress: {e}")
            return False

    def _identify_weak_patterns(self, user_progress: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify patterns where user needs more practice"""
        weak_patterns = []
        pattern_mastery = user_progress.get("pattern_mastery", {})

        for pattern_name, mastery in pattern_mastery.items():
            mastery_level = mastery.get("mastery_level", 0)
            if mastery_level < 70:  # Below 70% mastery
                weak_patterns.append({
                    "pattern": pattern_name,
                    "mastery_percentage": mastery_level,
                    "problems_solved": mastery.get("problems_solved", 0),
                    "needs_practice": True
                })

        return sorted(weak_patterns, key=lambda x: x["mastery_percentage"])

    def _suggest_next_patterns(self, user_progress: Dict[str, Any]) -> List[str]:
        """Suggest next patterns to learn"""
        # Simple progression: Two Pointers -> Sliding Window -> Dynamic Programming -> etc.
        pattern_progression = [
            "Two Pointers",
            "Sliding Window",
            "Binary Search",
            "Dynamic Programming",
            "Graph Algorithms",
            "Tree Traversal",
            "Backtracking",
            "Greedy Algorithms"
        ]

        mastered_patterns = self.get_mastered_patterns(user_progress["user_id"])
        mastered_names = {p["pattern"] for p in mastered_patterns}

        next_patterns = []
        for pattern in pattern_progression:
            if pattern not in mastered_names and pattern not in [p["pattern"] for p in self._identify_weak_patterns(user_progress)]:
                next_patterns.append(pattern)
                if len(next_patterns) >= 3:  # Suggest up to 3 next patterns
                    break

        return next_patterns

    def _get_review_problems(self, user_progress: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get problems that user should review"""
        problem_attempts = user_progress.get("problem_attempts", {})
        review_problems = []

        for problem_id, attempts in problem_attempts.items():
            if attempts.get("solved"):
                # Review problems solved more than 7 days ago
                solved_date = attempts.get("first_solved_date")
                if solved_date:
                    solved_datetime = datetime.fromisoformat(solved_date.replace('Z', '+00:00'))
                    days_since_solved = (datetime.utcnow() - solved_datetime).days
                    if days_since_solved > 7:
                        review_problems.append({
                            "problem_id": problem_id,
                            "days_since_solved": days_since_solved,
                            "attempts": attempts.get("attempts", 1)
                        })

        return sorted(review_problems, key=lambda x: x["days_since_solved"], reverse=True)[:5]

    def _get_pattern_problems(self, pattern_name: str, user_progress: Dict[str, Any], solved: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Get problems for a specific pattern"""
        # In production, this would query problems by pattern
        # For now, return mock problems
        mock_problems = [
            {"id": "1", "title": "Two Sum", "difficulty": "Easy"},
            {"id": "2", "title": "Valid Palindrome", "difficulty": "Easy"},
            {"id": "3", "title": "Best Time to Buy and Sell Stock", "difficulty": "Easy"}
        ]

        # Filter by solved status if specified
        if solved is not None:
            solved_problem_ids = {
                pid for pid, attempts in user_progress.get("problem_attempts", {}).items()
                if attempts.get("solved") == solved
            }
            mock_problems = [p for p in mock_problems if (p["id"] in solved_problem_ids) == solved]

        return mock_problems

    def _calculate_mastery_progress(self, user_progress: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall mastery progress"""
        pattern_mastery = user_progress.get("pattern_mastery", {})

        if not pattern_mastery:
            return {"overall_mastery": 0, "patterns_mastered": 0, "total_patterns": 0}

        total_mastery = sum(m.get("mastery_level", 0) for m in pattern_mastery.values())
        mastered_count = sum(1 for m in pattern_mastery.values() if m.get("mastery_level", 0) >= 80)

        return {
            "overall_mastery": total_mastery // len(pattern_mastery) if pattern_mastery else 0,
            "patterns_mastered": mastered_count,
            "total_patterns": len(pattern_mastery)
        }

    def _get_default_recommendations(self) -> Dict[str, Any]:
        """Get default recommendations for new users"""
        return {
            "weak_patterns": [],
            "next_patterns_to_learn": ["Two Pointers", "Sliding Window", "Binary Search"],
            "problems_to_review": [],
            "study_streak": 0,
            "total_problems_solved": 0,
            "mastery_progress": {"overall_mastery": 0, "patterns_mastered": 0, "total_patterns": 0}
        }

    def _get_default_study_plan(self, days: int) -> Dict[str, Any]:
        """Get default study plan for new users"""
        daily_plan = []
        current_date = datetime.utcnow()

        for day in range(days):
            day_date = current_date + timedelta(days=day)
            if day < 3:
                focus = "Two Pointers"
                problems = [{"id": "1", "title": "Two Sum"}, {"id": "2", "title": "Valid Palindrome"}]
            else:
                focus = "Sliding Window"
                problems = [{"id": "3", "title": "Best Time to Buy and Sell Stock"}]

            daily_plan.append({
                "date": day_date.isoformat(),
                "focus": focus,
                "problems": problems,
                "goal": "Learn the fundamentals"
            })

        return {
            "study_plan": daily_plan,
            "estimated_completion_days": days,
            "total_problems": sum(len(day["problems"]) for day in daily_plan)
        }
