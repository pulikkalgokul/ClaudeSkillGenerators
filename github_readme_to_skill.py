#!/usr/bin/env python3
"""
GitHub README to SKILL.md Converter

Converts GitHub README.md files to Claude Skills format with multiple MD files.

This script handles the following GitHub-specific syntax:

Badge removal:
- ![badge](url) badges at the top of READMEs
- [![badge](img-url)](link-url) linked badges

GitHub Alert conversions:
- > [!NOTE] -> > **Note:**
- > [!TIP] -> > **Tip:**
- > [!IMPORTANT] -> > **Important:**
- > [!WARNING] -> > **Warning:**
- > [!CAUTION] -> > **Caution:**

Link conversions:
- [text](#section-name) -> preserved (internal anchors)
- [text](./path/to/file.md) -> converted to relative paths
- [text](https://github.com/org/repo/...) -> preserved or converted

Section splitting:
- Splits README into multiple files based on H2 (##) headers
- Creates a structured SKILL.md with links to all sections
- Preserves code blocks and examples

Usage:
    python github_readme_to_skill.py <input_readme> <output_dir> [options]

Example:
    python github_readme_to_skill.py README.md ./swift-mocking-skill --skill-name "swift-mocking"
    python github_readme_to_skill.py path/to/README.md ./output --skill-name "my-library"
"""

import argparse
import os
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Section:
    """Represents a section of the README."""
    title: str
    level: int
    content: str
    anchor: str
    subsections: list["Section"] = field(default_factory=list)
    parent: Optional["Section"] = None


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug (GitHub-style anchor)."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def extract_title_and_description(content: str) -> tuple[str, str]:
    """Extract the main title (H1) and first paragraph description."""
    lines = content.split("\n")
    title = ""
    description = ""
    found_title = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if not stripped:
            continue
        
        if stripped.startswith("![") or stripped.startswith("[!["):
            continue
        
        if stripped.startswith("# ") and not found_title:
            title = stripped[2:].strip()
            found_title = True
            continue
        
        if found_title and not stripped.startswith("#"):
            if not stripped.startswith("-") and not stripped.startswith("["):
                if not stripped.startswith(">") and not stripped.startswith("|"):
                    if len(stripped) > 20:
                        description = stripped
                        break
    
    return title, description


def remove_badges(content: str) -> str:
    """Remove GitHub badges from the top of the README."""
    lines = content.split("\n")
    result_lines = []
    in_badge_section = True
    
    for line in lines:
        stripped = line.strip()
        
        if in_badge_section:
            if re.match(r"^\[!\[.*?\]\(.*?\)\]\(.*?\)$", stripped):
                continue
            if re.match(r"^!\[.*?\]\(.*?\)$", stripped):
                continue
            if not stripped:
                continue
            in_badge_section = False
        
        result_lines.append(line)
    
    return "\n".join(result_lines)


def convert_github_alerts(content: str) -> str:
    """Convert GitHub-flavored alerts to standard blockquotes."""
    alert_types = {
        "NOTE": "Note",
        "TIP": "Tip", 
        "IMPORTANT": "Important",
        "WARNING": "Warning",
        "CAUTION": "Caution",
    }
    
    for gh_type, display_type in alert_types.items():
        pattern = rf">\s*\[!{gh_type}\]\s*\n"
        replacement = f"> **{display_type}:** "
        content = re.sub(pattern, replacement, content)
        
        pattern_inline = rf">\s*\[!{gh_type}\]"
        replacement_inline = f"> **{display_type}:**"
        content = re.sub(pattern_inline, replacement_inline, content)
    
    return content


def convert_relative_links(content: str, section_files: dict[str, str]) -> str:
    """Convert internal anchor links to file links where appropriate."""
    
    def replace_anchor_link(match: re.Match) -> str:
        text = match.group(1)
        anchor = match.group(2)
        
        anchor_clean = anchor.lstrip("#")
        
        if anchor_clean in section_files:
            return f"[{text}]({section_files[anchor_clean]})"
        
        return match.group(0)
    
    pattern = r"\[([^\]]+)\]\((#[^)]+)\)"
    return re.sub(pattern, replace_anchor_link, content)


def parse_sections(content: str) -> list[Section]:
    """Parse README content into hierarchical sections."""
    lines = content.split("\n")
    sections = []
    current_section: Optional[Section] = None
    current_content_lines = []
    root_content_lines = []
    
    header_pattern = re.compile(r"^(#{1,6})\s+(.+)$")
    
    for line in lines:
        match = header_pattern.match(line)
        
        if match:
            if current_section:
                current_section.content = "\n".join(current_content_lines).strip()
                current_content_lines = []
            elif current_content_lines:
                root_content_lines = current_content_lines
                current_content_lines = []
            
            level = len(match.group(1))
            title = match.group(2).strip()
            anchor = slugify(title)
            
            new_section = Section(
                title=title,
                level=level,
                content="",
                anchor=anchor
            )
            
            if level == 1:
                sections.append(new_section)
                current_section = new_section
            elif level == 2:
                sections.append(new_section)
                current_section = new_section
            else:
                if current_section and current_section.level < level:
                    new_section.parent = current_section
                    current_section.subsections.append(new_section)
                else:
                    parent = current_section
                    while parent and parent.level >= level:
                        parent = parent.parent
                    if parent:
                        new_section.parent = parent
                        parent.subsections.append(new_section)
                    else:
                        sections.append(new_section)
                
                current_section = new_section
        else:
            current_content_lines.append(line)
    
    if current_section:
        current_section.content = "\n".join(current_content_lines).strip()
    
    return sections


def section_to_markdown(section: Section, include_title: bool = True) -> str:
    """Convert a section and its subsections to markdown."""
    lines = []
    
    if include_title:
        lines.append(f"{'#' * section.level} {section.title}")
        lines.append("")
    
    if section.content:
        lines.append(section.content)
        lines.append("")
    
    for subsection in section.subsections:
        lines.append(section_to_markdown(subsection, include_title=True))
    
    return "\n".join(lines)


def should_split_section(section: Section) -> bool:
    """Determine if a section should be split into its own file."""
    if section.level != 2:
        return False
    
    skip_sections = {
        "license",
        "contributing", 
        "acknowledgments",
        "acknowledgements",
        "credits",
        "authors",
        "changelog",
        "table of contents",
        "contents",
        "toc",
    }
    
    if section.anchor in skip_sections or section.title.lower() in skip_sections:
        return False
    
    content_length = len(section.content) + sum(
        len(section_to_markdown(s)) for s in section.subsections
    )
    
    return content_length > 200


def clean_section_content(content: str) -> str:
    """Clean up section content for output."""
    content = convert_github_alerts(content)
    
    content = re.sub(r"\n{3,}", "\n\n", content)
    
    return content.strip()


def generate_section_filename(section: Section) -> str:
    """Generate a filename for a section."""
    name = slugify(section.title)
    return f"{name}.md"


def process_readme(
    input_file: Path,
    output_dir: Path,
    skill_name: str,
    skill_description: Optional[str] = None,
    min_section_length: int = 200,
    keep_badges: bool = False,
    single_file: bool = False,
) -> None:
    """Process a README file and generate skill files."""
    print(f"GitHub README to SKILL Converter")
    print(f"=" * 50)
    print(f"Input:  {input_file}")
    print(f"Output: {output_dir}")
    print()
    
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    if not keep_badges:
        content = remove_badges(content)
    
    content = convert_github_alerts(content)
    
    title, description = extract_title_and_description(content)
    if not skill_description:
        skill_description = description or f"Documentation for {skill_name}"
    
    print(f"Title: {title}")
    print(f"Description: {skill_description[:80]}...")
    print()
    
    sections = parse_sections(content)
    
    print(f"Found {len(sections)} top-level sections")
    for section in sections:
        print(f"  - {section.title} (level {section.level}, {len(section.subsections)} subsections)")
    print()
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    section_files: dict[str, str] = {}
    created_files: list[tuple[str, str, Section]] = []
    
    if not single_file:
        for section in sections:
            if section.level == 1:
                continue
            
            if should_split_section(section):
                filename = generate_section_filename(section)
                section_files[section.anchor] = filename
                created_files.append((filename, section.title, section))
    
    print("Processing sections...")
    
    for filename, section_title, section in created_files:
        section_content = section_to_markdown(section, include_title=True)
        section_content = clean_section_content(section_content)
        section_content = convert_relative_links(section_content, section_files)
        
        output_path = output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(section_content + "\n")
        
        print(f"  Created: {filename}")
    
    generate_skill_md(
        output_dir=output_dir,
        skill_name=skill_name,
        skill_description=skill_description,
        title=title,
        sections=sections,
        section_files=section_files,
        original_content=content,
    )
    
    print()
    print("Conversion complete!")
    print(f"Output directory: {output_dir}")


def generate_skill_md(
    output_dir: Path,
    skill_name: str,
    skill_description: str,
    title: str,
    sections: list[Section],
    section_files: dict[str, str],
    original_content: str,
) -> None:
    """Generate the SKILL.md file."""
    print("\nGenerating SKILL.md...")
    
    lines = [
        "---",
        f"name: {skill_name}",
        f"description: {skill_description}",
        "---",
        "",
        f"# {title}",
        "",
    ]
    
    if skill_description:
        lines.append(skill_description)
        lines.append("")
    
    lines.append("## Documentation Structure")
    lines.append("")
    
    for section in sections:
        if section.level == 1:
            continue
        
        if section.anchor in section_files:
            filename = section_files[section.anchor]
            short_desc = extract_section_summary(section)
            if short_desc:
                lines.append(f"- **{section.title}** ([{filename}]({filename})): {short_desc}")
            else:
                lines.append(f"- **{section.title}** ([{filename}]({filename}))")
        else:
            lines.append(f"- **{section.title}**")
        
        for subsection in section.subsections:
            if subsection.anchor in section_files:
                filename = section_files[subsection.anchor]
                lines.append(f"  - [{subsection.title}]({filename})")
            else:
                lines.append(f"  - {subsection.title}")
    
    lines.append("")
    
    inline_sections = []
    for section in sections:
        if section.level == 1:
            continue
        if section.anchor not in section_files:
            inline_sections.append(section)
    
    if inline_sections:
        lines.append("## Quick Reference")
        lines.append("")
        
        for section in inline_sections:
            section_md = section_to_markdown(section, include_title=True)
            section_md = clean_section_content(section_md)
            lines.append(section_md)
            lines.append("")
    
    lines.extend([
        "## Usage Notes",
        "",
        "- Start with the main documentation sections for an overview",
        "- Refer to specific sections for detailed information on each topic",
        "- Code examples are provided throughout the documentation",
        "",
    ])
    
    skill_md_path = output_dir / "SKILL.md"
    with open(skill_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"  Created: SKILL.md")


def extract_section_summary(section: Section) -> str:
    """Extract a brief summary from a section's content."""
    content = section.content.strip()
    
    if not content:
        return ""
    
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        
        if not line:
            continue
        if line.startswith(">"):
            continue
        if line.startswith("-") or line.startswith("*"):
            continue
        if line.startswith("```"):
            continue
        if line.startswith("|"):
            continue
        
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        line = re.sub(r"`([^`]+)`", r"\1", line)
        
        if len(line) > 20:
            if len(line) > 150:
                line = line[:147] + "..."
            return line
    
    return ""


def main():
    parser = argparse.ArgumentParser(
        description="Convert GitHub README to Claude Skills format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the README.md file"
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Output directory for converted files"
    )
    parser.add_argument(
        "--skill-name",
        type=str,
        default=None,
        help="Name for the skill (default: derived from README title)"
    )
    parser.add_argument(
        "--skill-description",
        type=str,
        default=None,
        help="Description for the skill (default: first paragraph of README)"
    )
    parser.add_argument(
        "--keep-badges",
        action="store_true",
        help="Keep badge images in the output"
    )
    parser.add_argument(
        "--single-file",
        action="store_true",
        help="Output everything in SKILL.md without splitting"
    )
    parser.add_argument(
        "--min-section-length",
        type=int,
        default=200,
        help="Minimum content length to split a section (default: 200)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    input_file = args.input_file.resolve()
    output_dir = args.output_dir.resolve()
    
    if not input_file.exists():
        print(f"Error: Input file does not exist: {input_file}")
        return 1
    
    skill_name = args.skill_name
    if not skill_name:
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()
        title, _ = extract_title_and_description(content)
        skill_name = slugify(title) if title else input_file.stem
    
    if args.dry_run:
        print("Dry run - no files will be modified")
        print()
        
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        content = remove_badges(content)
        content = convert_github_alerts(content)
        sections = parse_sections(content)
        
        print(f"Would create the following files in {output_dir}:")
        print(f"  - SKILL.md")
        for section in sections:
            if section.level == 2 and should_split_section(section):
                print(f"  - {generate_section_filename(section)}")
        return 0
    
    process_readme(
        input_file=input_file,
        output_dir=output_dir,
        skill_name=skill_name,
        skill_description=args.skill_description,
        min_section_length=args.min_section_length,
        keep_badges=args.keep_badges,
        single_file=args.single_file,
    )
    
    return 0


if __name__ == "__main__":
    exit(main())
