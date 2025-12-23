"""
Template Matcher

Finds similar files from the repository to use as templates for generation.
This enables the hybrid approach: use templates when available, rules as fallback.

The template matcher queries the database for files with similar dimensions
and extracts patterns (feeds, speeds, passes) that can be applied to new parts.
"""

import sqlite3
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TemplateMatch:
    """Represents a matched template file."""
    program_number: str
    file_path: str
    round_size: float
    thickness: str
    cb_mm: float
    ob_mm: Optional[float]
    spacer_type: str
    similarity_score: float
    content: Optional[str] = None


@dataclass
class ExtractedPattern:
    """Patterns extracted from a template file."""
    # Drilling parameters
    drill_rpm: Optional[int] = None
    drill_feed: Optional[float] = None
    drill_peck: Optional[float] = None

    # Boring parameters
    bore_rpm: Optional[int] = None
    bore_css: Optional[int] = None
    bore_feed_rough: Optional[float] = None
    bore_feed_finish: Optional[float] = None

    # Turning parameters
    turn_rpm: Optional[int] = None
    turn_css: Optional[int] = None
    turn_feed: Optional[float] = None


class TemplateMatcher:
    """
    Finds and matches template files from the repository.

    Uses the database to find similar files, then extracts patterns
    from the matched files for use in generation.
    """

    def __init__(self, db_path: str, repository_path: Optional[str] = None):
        """
        Initialize the template matcher.

        Args:
            db_path: Path to the SQLite database
            repository_path: Path to the repository folder (inferred from db if None)
        """
        self.db_path = db_path
        self.repository_path = repository_path

        if repository_path is None:
            # Infer repository path from database path
            db_dir = os.path.dirname(db_path)
            self.repository_path = os.path.join(db_dir, "repository")

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        return sqlite3.connect(self.db_path)

    def find_similar(
        self,
        round_size: float,
        cb_mm: float,
        thickness: Optional[str] = None,
        ob_mm: Optional[float] = None,
        spacer_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[TemplateMatch]:
        """
        Find similar files from the repository.

        Similarity is based on:
        1. Same round size (exact match preferred)
        2. Similar CB (within tolerance)
        3. Same spacer type if specified
        4. Similar OB if hub-centric

        Args:
            round_size: Target round size in inches
            cb_mm: Target center bore in mm
            thickness: Target thickness (optional)
            ob_mm: Target outer bore in mm (for hub-centric)
            spacer_type: Target spacer type
            limit: Maximum number of matches to return

        Returns:
            List of TemplateMatch objects, sorted by similarity
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Build query based on provided parameters
        query = """
            SELECT
                program_number,
                file_path,
                round_size,
                thickness,
                cb_mm,
                ob_mm,
                spacer_type,
                ABS(round_size - ?) as round_diff,
                ABS(cb_mm - ?) as cb_diff
            FROM gcode_files
            WHERE round_size IS NOT NULL
              AND cb_mm IS NOT NULL
        """
        params = [round_size, cb_mm]

        # Add spacer type filter if specified
        if spacer_type:
            query += " AND spacer_type = ?"
            params.append(spacer_type)

        # Order by similarity (round size match is most important)
        query += """
            ORDER BY
                CASE WHEN round_size = ? THEN 0 ELSE 1 END,
                round_diff,
                cb_diff
            LIMIT ?
        """
        params.extend([round_size, limit])

        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        except sqlite3.Error:
            conn.close()
            return []

        matches = []
        for row in rows:
            # Calculate similarity score (0-1, higher is better)
            round_diff = row[7]
            cb_diff = row[8]

            # Scoring: exact round match = 0.5 base, CB closeness = up to 0.5
            round_score = 0.5 if round_diff == 0 else max(0, 0.3 - round_diff * 0.1)
            cb_score = max(0, 0.5 - cb_diff * 0.02)
            similarity = round_score + cb_score

            matches.append(TemplateMatch(
                program_number=row[0],
                file_path=row[1],
                round_size=row[2],
                thickness=row[3],
                cb_mm=row[4],
                ob_mm=row[5],
                spacer_type=row[6],
                similarity_score=round(similarity, 3),
            ))

        conn.close()
        return matches

    def find_exact_match(
        self,
        round_size: float,
        cb_mm: float,
        ob_mm: Optional[float] = None,
        thickness: Optional[str] = None,
    ) -> Optional[TemplateMatch]:
        """
        Find an exact match in the repository.

        An exact match has the same round size, CB, and optionally OB.

        Returns:
            TemplateMatch if found, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                program_number,
                file_path,
                round_size,
                thickness,
                cb_mm,
                ob_mm,
                spacer_type
            FROM gcode_files
            WHERE round_size = ?
              AND ABS(cb_mm - ?) < 0.2
        """
        params = [round_size, cb_mm]

        if ob_mm is not None:
            query += " AND ABS(ob_mm - ?) < 0.2"
            params.append(ob_mm)

        query += " LIMIT 1"

        try:
            cursor.execute(query, params)
            row = cursor.fetchone()
        except sqlite3.Error:
            conn.close()
            return None

        conn.close()

        if row:
            return TemplateMatch(
                program_number=row[0],
                file_path=row[1],
                round_size=row[2],
                thickness=row[3],
                cb_mm=row[4],
                ob_mm=row[5],
                spacer_type=row[6],
                similarity_score=1.0,
            )

        return None

    def load_template_content(self, match: TemplateMatch) -> Optional[str]:
        """
        Load the content of a matched template file.

        Args:
            match: TemplateMatch object

        Returns:
            File content as string, or None if file not found
        """
        if match.file_path and os.path.exists(match.file_path):
            filepath = match.file_path
        else:
            # Try to find in repository
            filename = f"{match.program_number}.nc"
            filepath = os.path.join(self.repository_path, filename)

        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()

        return None

    def extract_patterns(self, content: str) -> ExtractedPattern:
        """
        Extract machining patterns from template content.

        Parses the G-code to extract feeds, speeds, and other parameters
        that can be applied to similar parts.

        Args:
            content: G-code file content

        Returns:
            ExtractedPattern with extracted values
        """
        import re

        pattern = ExtractedPattern()

        lines = content.split('\n')

        for i, line in enumerate(lines):
            line_upper = line.upper().strip()

            # Extract drilling parameters (near T101)
            if 'T101' in line_upper:
                # Look for S and F values in nearby lines
                for j in range(i, min(i + 5, len(lines))):
                    nearby = lines[j].upper()

                    # Extract RPM
                    rpm_match = re.search(r'S(\d+)', nearby)
                    if rpm_match and pattern.drill_rpm is None:
                        pattern.drill_rpm = int(rpm_match.group(1))

                    # Extract feed
                    feed_match = re.search(r'F([\d.]+)', nearby)
                    if feed_match and pattern.drill_feed is None:
                        pattern.drill_feed = float(feed_match.group(1))

                    # Extract peck depth (Q value in G83)
                    peck_match = re.search(r'Q([\d.]+)', nearby)
                    if peck_match and pattern.drill_peck is None:
                        pattern.drill_peck = float(peck_match.group(1))

            # Extract boring parameters (near T121)
            if 'T121' in line_upper and 'BORE' in line_upper:
                for j in range(i, min(i + 10, len(lines))):
                    nearby = lines[j].upper()

                    # Extract max RPM (G50 S value)
                    if 'G50' in nearby:
                        rpm_match = re.search(r'S(\d+)', nearby)
                        if rpm_match:
                            pattern.bore_rpm = int(rpm_match.group(1))

                    # Extract CSS (G96 S value)
                    if 'G96' in nearby:
                        css_match = re.search(r'S(\d+)', nearby)
                        if css_match:
                            pattern.bore_css = int(css_match.group(1))

                    # Extract feed (first F value after tool call)
                    feed_match = re.search(r'F([\d.]+)', nearby)
                    if feed_match:
                        feed_val = float(feed_match.group(1))
                        if pattern.bore_feed_rough is None:
                            pattern.bore_feed_rough = feed_val
                        elif pattern.bore_feed_finish is None and feed_val < pattern.bore_feed_rough:
                            pattern.bore_feed_finish = feed_val

            # Extract turning parameters (near T303)
            if 'T303' in line_upper:
                for j in range(i, min(i + 8, len(lines))):
                    nearby = lines[j].upper()

                    # Extract RPM
                    if 'G97' in nearby:
                        rpm_match = re.search(r'S(\d+)', nearby)
                        if rpm_match and pattern.turn_rpm is None:
                            pattern.turn_rpm = int(rpm_match.group(1))

                    # Extract CSS
                    if 'G96' in nearby:
                        css_match = re.search(r'S(\d+)', nearby)
                        if css_match and pattern.turn_css is None:
                            pattern.turn_css = int(css_match.group(1))

                    # Extract feed
                    feed_match = re.search(r'F([\d.]+)', nearby)
                    if feed_match and pattern.turn_feed is None:
                        pattern.turn_feed = float(feed_match.group(1))

        return pattern

    def get_best_template(
        self,
        round_size: float,
        cb_mm: float,
        ob_mm: Optional[float] = None,
        spacer_type: Optional[str] = None,
    ) -> Tuple[Optional[TemplateMatch], Optional[ExtractedPattern]]:
        """
        Get the best matching template with extracted patterns.

        Args:
            round_size: Target round size
            cb_mm: Target center bore
            ob_mm: Target outer bore (optional)
            spacer_type: Target spacer type (optional)

        Returns:
            Tuple of (TemplateMatch, ExtractedPattern) or (None, None)
        """
        # Try exact match first
        exact = self.find_exact_match(round_size, cb_mm, ob_mm)
        if exact:
            content = self.load_template_content(exact)
            if content:
                patterns = self.extract_patterns(content)
                return (exact, patterns)

        # Fall back to similar matches
        similar = self.find_similar(round_size, cb_mm, ob_mm=ob_mm, spacer_type=spacer_type, limit=3)
        for match in similar:
            content = self.load_template_content(match)
            if content:
                patterns = self.extract_patterns(content)
                return (match, patterns)

        return (None, None)
