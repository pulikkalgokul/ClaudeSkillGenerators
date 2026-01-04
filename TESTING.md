# Testing Guide

This document describes the test suite for the GitHub README to Skills converter.

## Overview

The test suite ensures that all best practices improvements are working correctly, including:
- ✅ Description generation with third-person voice and "when to use" context
- ✅ Boilerplate section filtering (License, Contributing, etc.)
- ✅ Table of contents generation for long files
- ✅ SKILL.md size warnings
- ✅ GitHub alert conversions
- ✅ Badge removal

## Running Tests

### Run all tests

```bash
python3 test_github_readme_to_skill.py
```

### Run with verbose output

```bash
python3 test_github_readme_to_skill.py -v
```

### Run specific test class

```bash
python3 -m unittest test_github_readme_to_skill.TestGenerateSkillDescription
```

### Run specific test method

```bash
python3 -m unittest test_github_readme_to_skill.TestGenerateSkillDescription.test_adds_when_to_use_context
```

## Test Coverage

### Test Classes

#### 1. `TestGenerateSkillDescription`
Tests the skill description generation following best practices.

**Tests:**
- `test_adds_when_to_use_context` - Verifies "when to use" context is added
- `test_converts_to_third_person` - Ensures third-person voice
- `test_removes_we_provide` - Removes first-person phrases
- `test_fallback_with_no_description` - Tests fallback description generation
- `test_respects_1024_char_limit` - Enforces YAML frontmatter limit
- `test_includes_key_terms` - Verifies key terms from skill name are included

**Example:**
```python
# Input
description = "This is a mocking library"
skill_name = "swift-mocking"

# Output
# "Provides a mocking library. Use when working with swift mocking or when the user mentions swift mocking"
```

#### 2. `TestShouldSkipSectionEntirely`
Tests boilerplate section filtering.

**Tests:**
- `test_skips_license_section` - Verifies License is skipped
- `test_skips_contributing_section` - Verifies Contributing is skipped
- `test_skips_acknowledgments` - Verifies Acknowledgments is skipped
- `test_skips_changelog` - Verifies Changelog is skipped
- `test_does_not_skip_regular_sections` - Ensures regular sections are kept
- `test_case_insensitive_matching` - Tests case-insensitive matching

**Skipped Sections:**
- License, Contributing, Acknowledgments, Credits, Authors
- Changelog, Table of Contents, Badges, Build Status, CI

#### 3. `TestShouldSplitSection`
Tests section splitting logic.

**Tests:**
- `test_only_splits_level_2_sections` - Only H2 sections are split
- `test_respects_min_section_length` - Honors min_section_length parameter
- `test_does_not_split_boilerplate` - Boilerplate sections never split

#### 4. `TestAddTableOfContents`
Tests table of contents generation for long files.

**Tests:**
- `test_no_toc_for_short_files` - No TOC if < 100 lines
- `test_adds_toc_for_long_files` - Adds TOC if > 100 lines
- `test_no_toc_without_subsections` - No TOC if no subsections
- `test_toc_has_anchor_links` - TOC entries are proper markdown links

**Example TOC:**
```markdown
## Contents

- [Getting Started](#getting-started)
- [Installation](#installation)
- [Configuration](#configuration)

---
```

#### 5. `TestSlugify`
Tests URL-friendly anchor generation.

**Tests:**
- `test_converts_to_lowercase` - Converts to lowercase
- `test_replaces_spaces_with_hyphens` - Spaces become hyphens
- `test_removes_special_characters` - Removes special chars
- `test_handles_multiple_hyphens` - Collapses multiple hyphens

#### 6. `TestExtractTitleAndDescription`
Tests title and description extraction from README.

**Tests:**
- `test_extracts_h1_title` - Extracts H1 as title
- `test_extracts_first_paragraph` - Extracts first paragraph as description
- `test_skips_badges` - Ignores badge images
- `test_ignores_short_lines` - Skips very short lines

#### 7. `TestRemoveBadges`
Tests badge removal from README content.

**Tests:**
- `test_removes_simple_badges` - Removes `![badge](url)` syntax
- `test_removes_linked_badges` - Removes `[![badge](img)](link)` syntax
- `test_preserves_content_after_badges` - Keeps content after badges

#### 8. `TestConvertGithubAlerts`
Tests GitHub alert conversion to standard blockquotes.

**Tests:**
- `test_converts_note_alert` - Converts `> [!NOTE]` to `> **Note:**`
- `test_converts_warning_alert` - Converts `> [!WARNING]` to `> **Warning:**`
- `test_converts_tip_alert` - Converts `> [!TIP]` to `> **Tip:**`

#### 9. `TestIntegration`
End-to-end integration tests.

**Tests:**
- `test_processes_readme_with_boilerplate_filtering` - Verifies boilerplate is filtered
- `test_generates_proper_description` - Checks YAML frontmatter description
- `test_available_documentation_heading` - Verifies heading change
- `test_no_generic_usage_notes` - Ensures generic notes are removed

## Test Statistics

```
Total Tests: 37
Test Classes: 9
Coverage Areas: 6 major features
```

## Expected Output

When all tests pass:

```
Ran 37 tests in 0.007s

OK
```

## Continuous Integration

To integrate with CI/CD:

```bash
# Add to your CI pipeline
python3 test_github_readme_to_skill.py
if [ $? -ne 0 ]; then
    echo "Tests failed!"
    exit 1
fi
```

## Adding New Tests

When adding new features:

1. Create a new test class if testing a new function
2. Add descriptive test method names: `test_<what_it_tests>`
3. Include docstrings explaining what is being tested
4. Use assertions that clearly indicate expected behavior
5. Run the full suite to ensure no regressions

**Example:**

```python
class TestNewFeature(unittest.TestCase):
    """Test the new feature functionality."""

    def test_feature_works_correctly(self):
        """Test that the feature produces expected output."""
        result = new_feature_function(input_data)
        self.assertEqual(result, expected_output)
```

## Troubleshooting

### Import Errors

If you get import errors:

```bash
# Make sure you're in the project directory
cd /path/to/SkillsGeneratorFromReadMe

# Run tests
python3 test_github_readme_to_skill.py
```

### Test Failures

If tests fail:

1. Read the error message carefully
2. Check which assertion failed
3. Run the specific test in verbose mode
4. Check if recent changes broke existing functionality

### Debugging Tests

Add print statements for debugging:

```python
def test_something(self):
    result = function_to_test()
    print(f"Result: {result}")  # Debug output
    self.assertEqual(result, expected)
```

## Best Practices

1. **Run tests before committing** - Ensures no regressions
2. **Write tests for new features** - Maintains code quality
3. **Keep tests focused** - One test per behavior
4. **Use descriptive names** - Makes failures easy to understand
5. **Test edge cases** - Empty inputs, very long inputs, special characters

## Next Steps

- [ ] Add performance benchmarks
- [ ] Add tests for error handling
- [ ] Test with real-world READMEs
- [ ] Add coverage reporting

## Related Documentation

- [README.md](README.md) - Main project documentation
- [github_readme_to_skill.py](github_readme_to_skill.py) - Source code
- [Claude Skills Best Practices](https://docs.anthropic.com/en/docs/build-with-claude/agent-skills) - Official guidelines
