"""
Fuzzy search functionality for G-code Database Manager
Uses thefuzz library for fuzzy string matching with typo tolerance
"""

from thefuzz import fuzz, process
from typing import List, Tuple, Optional


class FuzzySearchManager:
    """Manages fuzzy search operations for G-code programs"""

    def __init__(self, threshold: int = 70):
        """
        Initialize fuzzy search manager

        Args:
            threshold: Minimum similarity score (0-100) to consider a match
        """
        self.threshold = threshold

    def search_programs(self, query: str, programs: List[Tuple[str, str]],
                       limit: int = 10) -> List[Tuple[str, str, int]]:
        """
        Search programs using fuzzy matching

        Args:
            query: Search query string
            programs: List of (program_number, title) tuples
            limit: Maximum number of results to return

        Returns:
            List of (program_number, title, score) tuples sorted by score
        """
        if not query or not programs:
            return []

        # Determine if query looks like a program number (short, starts with 'o' or digits)
        query_lower = query.lower().strip()
        looks_like_prog_num = (len(query) <= 10 and
                              (query_lower.startswith('o') or query_lower.isdigit()))

        results = []

        if looks_like_prog_num:
            # For program number queries, search program numbers directly first
            prog_numbers = [prog for prog, _ in programs]
            prog_matches = process.extract(
                query,
                prog_numbers,
                scorer=fuzz.ratio,  # Use ratio for more exact matching on program numbers
                limit=limit * 2  # Get more candidates
            )

            # Add matching programs with their titles
            for prog_num, score in prog_matches:
                if score >= max(60, self.threshold - 10):  # Lower threshold for program numbers
                    # Find the title for this program number
                    for prog, title in programs:
                        if prog == prog_num:
                            results.append((prog, title, score))
                            break

        # Also search in combined program + title for all queries
        # This catches matches in titles even when query looks like a program number
        searchable = [f"{prog} {title}" for prog, title in programs]
        matches = process.extract(
            query,
            searchable,
            scorer=fuzz.partial_ratio,
            limit=limit * 2
        )

        # Add results from title search
        for match_text, score in matches:
            if score >= self.threshold:
                # Find original program data
                for prog, title in programs:
                    if f"{prog} {title}" == match_text:
                        # Check if already added from program number search
                        if not any(r[0] == prog for r in results):
                            results.append((prog, title, score))
                        else:
                            # Update score if this one is higher
                            for i, (p, t, s) in enumerate(results):
                                if p == prog and score > s:
                                    results[i] = (prog, title, score)
                        break

        # Sort by score (highest first) and limit results
        results.sort(key=lambda x: x[2], reverse=True)
        return results[:limit]

    def search_titles(self, query: str, titles: List[str],
                     limit: int = 10) -> List[Tuple[str, int]]:
        """
        Search program titles with fuzzy matching

        Args:
            query: Search query string
            titles: List of program titles
            limit: Maximum number of results

        Returns:
            List of (title, score) tuples
        """
        if not query or not titles:
            return []

        matches = process.extract(
            query,
            titles,
            scorer=fuzz.partial_ratio,
            limit=limit
        )

        return [(title, score) for title, score in matches if score >= self.threshold]

    def search_program_numbers(self, query: str, program_numbers: List[str],
                              limit: int = 5) -> List[Tuple[str, int]]:
        """
        Search program numbers with fuzzy matching
        Uses stricter ratio scorer for program numbers

        Args:
            query: Search query (program number)
            program_numbers: List of program numbers to search
            limit: Maximum number of results

        Returns:
            List of (program_number, score) tuples
        """
        if not query or not program_numbers:
            return []

        # Use ratio scorer for more exact matching on program numbers
        matches = process.extract(
            query,
            program_numbers,
            scorer=fuzz.ratio,
            limit=limit
        )

        return [(prog, score) for prog, score in matches if score >= self.threshold]

    def find_similar(self, target: str, choices: List[str],
                    max_suggestions: int = 3) -> List[str]:
        """
        Find similar strings for "Did you mean?" suggestions

        Args:
            target: The string to find matches for
            choices: List of strings to search through
            max_suggestions: Maximum number of suggestions

        Returns:
            List of similar strings
        """
        if not target or not choices:
            return []

        matches = process.extract(
            target,
            choices,
            scorer=fuzz.ratio,
            limit=max_suggestions
        )

        # Return suggestions that are close but not exact matches
        suggestions = []
        for choice, score in matches:
            if score >= self.threshold and score < 100:
                suggestions.append(choice)

        return suggestions

    def get_best_match(self, query: str, choices: List[str]) -> Optional[str]:
        """
        Get single best match for a query

        Args:
            query: Search query
            choices: List of strings to search

        Returns:
            Best matching string or None if no good match
        """
        if not query or not choices:
            return None

        match = process.extractOne(query, choices, scorer=fuzz.ratio)

        if match and match[1] >= self.threshold:
            return match[0]

        return None

    def calculate_similarity(self, str1: str, str2: str) -> int:
        """
        Calculate similarity score between two strings

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score (0-100)
        """
        return fuzz.ratio(str1, str2)


if __name__ == "__main__":
    # Test the module
    fuzzy = FuzzySearchManager(threshold=70)

    test_programs = [
        ("o13002", "13.0 142/220MM 2.0 HC .5"),
        ("o61045", "6.00 DIA 63.4/80MM 1.5 HC"),
        ("o50000", "5.00 DIA 1.5IN 1.375 THK"),
    ]

    print("Test 1: Search programs")
    results = fuzzy.search_programs("13002", test_programs)
    for prog, title, score in results:
        print(f"  [{score}%] {prog}: {title}")

    print("\nTest 2: Find similar (typo)")
    results = fuzzy.search_programs("o1300", test_programs)
    for prog, title, score in results:
        print(f"  [{score}%] {prog}: {title}")

    print("\nTest 3: Search by dimension")
    results = fuzzy.search_programs("142mm", test_programs)
    for prog, title, score in results:
        print(f"  [{score}%] {prog}: {title}")
