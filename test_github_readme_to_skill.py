#!/usr/bin/env python3
"""
Unit tests for github_readme_to_skill.py

Tests the best practices improvements including:
- Description generation with third-person voice and "when to use" context
- Section filtering to exclude boilerplate
- Table of contents generation for long files
- SKILL.md size warnings
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from github_readme_to_skill import (
    generate_skill_description,
    should_skip_section_entirely,
    should_split_section,
    add_table_of_contents,
    Section,
    slugify,
    extract_title_and_description,
    remove_badges,
    convert_github_alerts,
    process_readme,
)


class TestGenerateSkillDescription(unittest.TestCase):
    """Test the generate_skill_description function for best practices compliance."""

    def test_adds_when_to_use_context(self):
        """Test that 'when to use' context is automatically added."""
        result = generate_skill_description(
            title="Swift Mocking",
            description="A library for creating mock objects in Swift",
            skill_name="swift-mocking"
        )
        self.assertIn("use when", result.lower())
        self.assertIn("swift mocking", result.lower())

    def test_converts_to_third_person(self):
        """Test that first-person phrases are converted to third person."""
        result = generate_skill_description(
            title="Test Tool",
            description="This is a tool for testing",
            skill_name="test-tool"
        )
        self.assertNotIn("This is", result)
        # After removing "This is ", it becomes "a tool for testing"
        # which then gets "Provides" prepended -> "Provides a tool for testing"
        self.assertTrue(
            result.startswith("Provides") or
            result.startswith("A ") or
            result.startswith("a ")  # Handle lowercase 'a'
        )

    def test_removes_we_provide(self):
        """Test that 'We provide' is removed."""
        result = generate_skill_description(
            title="Test Tool",
            description="We provide a comprehensive testing framework",
            skill_name="test-tool"
        )
        self.assertNotIn("We provide", result)

    def test_fallback_with_no_description(self):
        """Test fallback description when none is provided."""
        result = generate_skill_description(
            title="Swift Mocking",
            description="",
            skill_name="swift-mocking"
        )
        self.assertIn("swift mocking", result.lower())
        self.assertIn("use when", result.lower())
        self.assertGreater(len(result), 20)

    def test_respects_1024_char_limit(self):
        """Test that descriptions are truncated to 1024 characters."""
        long_desc = "A " * 600  # Create a very long description
        result = generate_skill_description(
            title="Test",
            description=long_desc,
            skill_name="test"
        )
        self.assertLessEqual(len(result), 1024)

    def test_includes_key_terms(self):
        """Test that key terms from skill name are included."""
        result = generate_skill_description(
            title="Python Testing Framework",
            description="Comprehensive testing utilities",
            skill_name="python-testing"
        )
        self.assertIn("python testing", result.lower())


class TestShouldSkipSectionEntirely(unittest.TestCase):
    """Test the boilerplate section filtering."""

    def test_skips_license_section(self):
        """Test that License sections are skipped."""
        section = Section(title="License", level=2, content="MIT License", anchor="license")
        self.assertTrue(should_skip_section_entirely(section))

    def test_skips_contributing_section(self):
        """Test that Contributing sections are skipped."""
        section = Section(title="Contributing", level=2, content="", anchor="contributing")
        self.assertTrue(should_skip_section_entirely(section))

    def test_skips_acknowledgments(self):
        """Test that Acknowledgments sections are skipped."""
        section = Section(title="Acknowledgments", level=2, content="", anchor="acknowledgments")
        self.assertTrue(should_skip_section_entirely(section))

    def test_skips_changelog(self):
        """Test that Changelog sections are skipped."""
        section = Section(title="Changelog", level=2, content="", anchor="changelog")
        self.assertTrue(should_skip_section_entirely(section))

    def test_does_not_skip_regular_sections(self):
        """Test that regular sections are not skipped."""
        section = Section(title="Installation", level=2, content="Install instructions", anchor="installation")
        self.assertFalse(should_skip_section_entirely(section))

        section = Section(title="Usage", level=2, content="Usage instructions", anchor="usage")
        self.assertFalse(should_skip_section_entirely(section))

    def test_case_insensitive_matching(self):
        """Test that section matching is case-insensitive."""
        section = Section(title="LICENSE", level=2, content="", anchor="license")
        self.assertTrue(should_skip_section_entirely(section))


class TestShouldSplitSection(unittest.TestCase):
    """Test the section splitting logic."""

    def test_only_splits_level_2_sections(self):
        """Test that only level 2 sections are split."""
        section = Section(title="Test", level=1, content="x" * 300, anchor="test")
        self.assertFalse(should_split_section(section, 200))

        section = Section(title="Test", level=3, content="x" * 300, anchor="test")
        self.assertFalse(should_split_section(section, 200))

    def test_respects_min_section_length(self):
        """Test that min_section_length is respected."""
        section = Section(title="Test", level=2, content="x" * 150, anchor="test")
        self.assertFalse(should_split_section(section, 200))

        section = Section(title="Test", level=2, content="x" * 250, anchor="test")
        self.assertTrue(should_split_section(section, 200))

    def test_does_not_split_boilerplate(self):
        """Test that boilerplate sections are never split."""
        section = Section(title="License", level=2, content="x" * 500, anchor="license")
        self.assertFalse(should_split_section(section, 200))


class TestAddTableOfContents(unittest.TestCase):
    """Test the table of contents generation."""

    def test_no_toc_for_short_files(self):
        """Test that TOC is not added for files under 100 lines."""
        section = Section(title="Test", level=2, content="Line\n" * 50, anchor="test")
        result = add_table_of_contents("Line\n" * 50, section)
        self.assertNotIn("## Contents", result)

    def test_adds_toc_for_long_files(self):
        """Test that TOC is added for files over 100 lines."""
        subsection1 = Section(title="Subsection 1", level=3, content="", anchor="subsection-1")
        subsection2 = Section(title="Subsection 2", level=3, content="", anchor="subsection-2")
        section = Section(
            title="Main Section",
            level=2,
            content="Line\n" * 120,
            anchor="main-section",
            subsections=[subsection1, subsection2]
        )
        content = "# Main Section\n" + "Line\n" * 120
        result = add_table_of_contents(content, section)

        self.assertIn("## Contents", result)
        self.assertIn("Subsection 1", result)
        self.assertIn("Subsection 2", result)

    def test_no_toc_without_subsections(self):
        """Test that TOC is not added if there are no subsections."""
        section = Section(title="Test", level=2, content="Line\n" * 120, anchor="test")
        content = "# Test\n" + "Line\n" * 120
        result = add_table_of_contents(content, section)
        self.assertNotIn("## Contents", result)

    def test_toc_has_anchor_links(self):
        """Test that TOC entries are proper anchor links."""
        subsection = Section(title="Getting Started", level=3, content="", anchor="getting-started")
        section = Section(
            title="Main",
            level=2,
            content="Line\n" * 120,
            anchor="main",
            subsections=[subsection]
        )
        content = "# Main\n" + "Line\n" * 120
        result = add_table_of_contents(content, section)

        self.assertIn("[Getting Started](#getting-started)", result)


class TestSlugify(unittest.TestCase):
    """Test the slugify function for URL-friendly anchor generation."""

    def test_converts_to_lowercase(self):
        """Test that text is converted to lowercase."""
        self.assertEqual(slugify("Test Section"), "test-section")

    def test_replaces_spaces_with_hyphens(self):
        """Test that spaces are replaced with hyphens."""
        self.assertEqual(slugify("Multiple Word Title"), "multiple-word-title")

    def test_removes_special_characters(self):
        """Test that special characters are removed."""
        self.assertEqual(slugify("Test! Section?"), "test-section")

    def test_handles_multiple_hyphens(self):
        """Test that multiple consecutive hyphens are collapsed."""
        self.assertEqual(slugify("Test---Section"), "test-section")


class TestExtractTitleAndDescription(unittest.TestCase):
    """Test title and description extraction from README content."""

    def test_extracts_h1_title(self):
        """Test that H1 title is extracted."""
        content = "# My Project\n\nA great project for testing."
        title, _ = extract_title_and_description(content)
        self.assertEqual(title, "My Project")

    def test_extracts_first_paragraph(self):
        """Test that first meaningful paragraph is extracted as description."""
        content = "# My Project\n\nThis is a comprehensive testing framework."
        _, description = extract_title_and_description(content)
        self.assertEqual(description, "This is a comprehensive testing framework.")

    def test_skips_badges(self):
        """Test that badges are skipped when extracting description."""
        content = "# Project\n\n![badge](url)\n\nActual description here."
        _, description = extract_title_and_description(content)
        self.assertEqual(description, "Actual description here.")

    def test_ignores_short_lines(self):
        """Test that very short lines are ignored."""
        content = "# Project\n\nOK\n\nThis is the actual description."
        _, description = extract_title_and_description(content)
        self.assertEqual(description, "This is the actual description.")


class TestRemoveBadges(unittest.TestCase):
    """Test badge removal from README content."""

    def test_removes_simple_badges(self):
        """Test that simple badge syntax is removed."""
        content = "![Build](badge-url)\n\n# Project"
        result = remove_badges(content)
        self.assertNotIn("![Build]", result)
        self.assertIn("# Project", result)

    def test_removes_linked_badges(self):
        """Test that linked badge syntax is removed."""
        content = "[![Build](img)](link)\n\n# Project"
        result = remove_badges(content)
        self.assertNotIn("[![Build]", result)
        self.assertIn("# Project", result)

    def test_preserves_content_after_badges(self):
        """Test that content after badges is preserved."""
        content = "![Badge](url)\n\n# Title\n\nContent here"
        result = remove_badges(content)
        self.assertIn("# Title", result)
        self.assertIn("Content here", result)


class TestConvertGithubAlerts(unittest.TestCase):
    """Test GitHub alert conversion to standard blockquotes."""

    def test_converts_note_alert(self):
        """Test that NOTE alerts are converted."""
        content = "> [!NOTE]\n> This is a note"
        result = convert_github_alerts(content)
        self.assertIn("**Note:**", result)
        self.assertNotIn("[!NOTE]", result)

    def test_converts_warning_alert(self):
        """Test that WARNING alerts are converted."""
        content = "> [!WARNING]\n> This is a warning"
        result = convert_github_alerts(content)
        self.assertIn("**Warning:**", result)

    def test_converts_tip_alert(self):
        """Test that TIP alerts are converted."""
        content = "> [!TIP]\n> This is a tip"
        result = convert_github_alerts(content)
        self.assertIn("**Tip:**", result)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow."""

    def setUp(self):
        """Create a temporary directory for test outputs."""
        self.test_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.test_dir) / "output"

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_processes_readme_with_boilerplate_filtering(self):
        """Test that boilerplate sections are filtered in the output."""
        readme_content = """# Test Project

A testing framework for Python.

## Installation

Install via pip.

## Usage

Use it like this.

## License

MIT License

## Contributing

Please contribute!
"""
        process_readme(
            content=readme_content,
            output_dir=self.output_dir,
            skill_name="test-project",
            single_file=False
        )

        skill_md = self.output_dir / "SKILL.md"
        self.assertTrue(skill_md.exists())

        content = skill_md.read_text()
        # Should include regular sections
        self.assertIn("Installation", content)
        self.assertIn("Usage", content)
        # Should NOT include boilerplate
        self.assertNotIn("License", content)
        self.assertNotIn("Contributing", content)

    def test_generates_proper_description(self):
        """Test that generated SKILL.md has proper description."""
        readme_content = """# Swift Mocking

A mocking library for Swift unit tests.

## Installation

Install instructions.
"""
        process_readme(
            content=readme_content,
            output_dir=self.output_dir,
            skill_name="swift-mocking",
        )

        skill_md = self.output_dir / "SKILL.md"
        content = skill_md.read_text()

        # Check YAML frontmatter
        self.assertIn("name: swift-mocking", content)
        self.assertIn("description:", content)
        # Should have "when to use" context
        self.assertIn("use when", content.lower())

    def test_available_documentation_heading(self):
        """Test that 'Available Documentation' heading is used."""
        readme_content = """# Test Project

Description here.

## Installation

Install instructions.

## Usage

Usage instructions.
"""
        process_readme(
            content=readme_content,
            output_dir=self.output_dir,
            skill_name="test-project",
        )

        skill_md = self.output_dir / "SKILL.md"
        content = skill_md.read_text()

        self.assertIn("## Available Documentation", content)
        self.assertNotIn("## Documentation Structure", content)

    def test_no_generic_usage_notes(self):
        """Test that generic usage notes are not included."""
        readme_content = """# Test Project

Description.

## Installation

Install instructions.
"""
        process_readme(
            content=readme_content,
            output_dir=self.output_dir,
            skill_name="test-project",
        )

        skill_md = self.output_dir / "SKILL.md"
        content = skill_md.read_text()

        # Should NOT have generic usage notes
        self.assertNotIn("Start with the main documentation", content)
        self.assertNotIn("## Usage Notes", content)


def run_tests():
    """Run all tests with verbose output."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
