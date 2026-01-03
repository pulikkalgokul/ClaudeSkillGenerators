# Skills Generator From ReadMe

A collection of Python tools to convert documentation from various sources into Claude Skills format. This project helps you transform GitHub README files and Swift DocC documentation into structured skill files that can be used with Claude.

## Attribution

This project is based on the excellent work from the [agent-skills](https://github.com/nonameplum/agent-skills) repository by nonameplum.

**Note**: The `swift_docc_to_skill.py` script is taken directly from the [agent-skills repository](https://github.com/nonameplum/agent-skills/tree/main) and is provided here for convenience.

## Overview

This repository contains two converters:

1. **GitHub README to Skill Converter** (`github_readme_to_skill.py`) - Converts GitHub README.md files to Claude Skills format with intelligent section splitting
2. **Swift DocC to Skill Converter** (`swift_docc_to_skill.py`) - Converts Apple's Documentation.docc format to Claude Skills format

## Features

### GitHub README to Skill Converter

- Fetches README files from local paths or remote GitHub URLs
- Removes badge clutter automatically
- Converts GitHub-flavored alerts (NOTE, TIP, WARNING, etc.) to standard blockquotes
- Intelligently splits large READMEs into multiple organized files
- Preserves code blocks and examples
- Generates structured SKILL.md with navigation links

### Swift DocC to Skill Converter

- Processes Apple's DocC documentation format
- Removes DocC-specific metadata and directives
- Converts symbol links and documentation references
- Preserves code examples and formatting
- Generates organized skill structure with proper navigation

## Installation

### Requirements

- Python 3.7 or higher
- No external dependencies (uses only standard library)

### Setup

Clone this repository:

```bash
git clone <your-repo-url>
cd SkillsGeneratorFromReadMe
```

Make the scripts executable (optional):

```bash
chmod +x github_readme_to_skill.py
chmod +x swift_docc_to_skill.py
```

## Usage

### Converting GitHub READMEs

#### From a local file:

```bash
python3 github_readme_to_skill.py README.md ./output-skill --skill-name "my-skill"
```

#### From a GitHub URL:

```bash
# Using blob URL
python3 github_readme_to_skill.py https://github.com/owner/repo/blob/main/README.md ./output

# Using raw URL
python3 github_readme_to_skill.py https://raw.githubusercontent.com/owner/repo/main/README.md ./output
```

#### Options:

- `--skill-name` - Name for the skill (default: derived from README title)
- `--skill-description` - Description for the skill (default: first paragraph)
- `--keep-badges` - Keep badge images in the output
- `--single-file` - Output everything in SKILL.md without splitting
- `--min-section-length` - Minimum content length to split a section (default: 200)
- `--dry-run` - Show what would be done without making changes

### Converting Swift DocC Documentation

```bash
python3 swift_docc_to_skill.py Documentation.docc ./output-skill --skill-name "swift-documentation"
```

#### Options:

- `--skill-name` - Name for the skill (default: derived from directory name)
- `--skill-description` - Description for the skill
- `--main-doc` - Name of the main documentation file (default: auto-detect)
- `--skip-wip` - Skip work-in-progress (.md-wip) files
- `--strip-test-comments` - Remove HTML comment blocks containing test code
- `--skip-assets` - Skip copying assets directory
- `--keep-html-comments` - Keep HTML comments in output
- `--dry-run` - Show what would be done without making changes

## Examples

### Example 1: Convert a GitHub README

```bash
python3 github_readme_to_skill.py https://github.com/nonameplum/agent-skills/blob/main/README.md ./agent-skills-docs --skill-name "agent-skills"
```

This will:
1. Fetch the README from GitHub
2. Remove badges and convert GitHub alerts
3. Split the content into logical sections
4. Generate a structured SKILL.md with links to all sections

### Example 2: Convert Swift DocC

```bash
python3 swift_docc_to_skill.py TSPL.docc ./swift-programming-language --skill-name "programming-swift"
```

This will:
1. Process all markdown files in the DocC directory
2. Convert DocC-specific syntax to standard markdown
3. Generate a SKILL.md with proper navigation structure
4. Copy assets if present

## Output Structure

Both converters generate a structured output:

```
output-skill/
├── SKILL.md              # Main skill file with metadata and navigation
├── section-1.md          # Individual section files
├── section-2.md
└── Assets/               # Copied assets (if present)
```

The SKILL.md includes:
- Frontmatter with skill name and description
- Documentation structure with links to sections
- Usage notes

## License

Please refer to the original [agent-skills repository](https://github.com/nonameplum/agent-skills) for licensing information regarding the Swift DocC converter.

The GitHub README converter (`github_readme_to_skill.py`) is an extension/modification built upon concepts from the original repository.

## Troubleshooting

### Common Issues

1. **URL fetch fails**: Ensure you have internet connectivity and the GitHub URL is correct
2. **Permission denied**: Make sure you have write permissions to the output directory
3. **Encoding errors**: Ensure your input files are UTF-8 encoded

### Getting Help

If you encounter issues:
1. Check the error message for specific guidance
2. Try running with `--dry-run` to preview what would happen
3. Verify your Python version is 3.7 or higher

## Acknowledgments

Special thanks to:
- [nonameplum](https://github.com/nonameplum) for the original agent-skills repository and the Swift DocC converter
- The Anthropic team for Claude and the Claude Skills format
- The open-source community for inspiration and support
