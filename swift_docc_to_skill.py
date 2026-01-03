#!/usr/bin/env python3
"""
Swift DocC to SKILL.md Converter

Converts Apple's Documentation.docc format to Claude Skills format.

This script handles the following DocC-specific syntax:

Directives (removed/processed):
- @Metadata { ... } - Page metadata blocks
- @Snippet(path: ...) - Code snippet references
- @Image, @Video - Media directives
- @Available, @TitleHeading, @DisplayName - Page configuration
- @Row, @Column, @Links - Layout directives
- @Tutorial, @Section, @Steps - Tutorial directives
- @Comment { ... } - Documentation comments
- All other @ directives with braces or parentheses

Link conversions:
- <doc:PageName> -> [Page Title](PageName.md)
- <doc:PageName#Section> -> [Section](PageName.md#Section)
- <doc:#Section> -> [Section](#Section)
- ``Symbol`` -> `Symbol` (symbol links to code formatting)
- ``Path/Symbol`` -> `Path.Symbol`
- [text](doc:PageName) -> [text](PageName.md)

Formatting conversions:
- term lists: "- term Name: Definition" -> "- **Name**: Definition"
- Asides are preserved as blockquotes

Usage:
    python swift_docc_to_skill.py <input_docc_dir> <output_dir> [options]

Example:
    python swift_docc_to_skill.py Documentation.docc . --skill-name "programming-swift-embedded"
    python swift_docc_to_skill.py TSPL.docc ./output --skill-name "programming-swift"
"""

import argparse
import os
import re
import shutil
from pathlib import Path
from typing import Optional


def find_main_doc_file(docc_dir: Path) -> Optional[Path]:
    """
    Find the main documentation file in a DocC directory.
    
    Detection strategy (in order):
    1. File with @TechnologyRoot metadata directive
    2. File where H1 title is a double-backtick symbol link (# ``ModuleName``)
    3. File matching the .docc directory name (e.g., SlothCreator.md for SlothCreator.docc)
    4. Fall back to first markdown file found
    """
    candidates_with_tech_root = []
    candidates_with_symbol_title = []
    
    for md_file in docc_dir.glob("*.md"):
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read(3000)
                
                if "@TechnologyRoot" in content:
                    candidates_with_tech_root.append(md_file)
                    continue
                
                lines = content.split("\n")
                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    if stripped.startswith("#") and not stripped.startswith("##"):
                        if re.match(r"^#\s*``[^`]+``\s*$", stripped):
                            candidates_with_symbol_title.append(md_file)
                        break
                    if stripped.startswith("@"):
                        continue
                    break
        except Exception:
            continue
    
    if candidates_with_tech_root:
        return candidates_with_tech_root[0]
    
    if candidates_with_symbol_title:
        return candidates_with_symbol_title[0]
    
    docc_name = docc_dir.stem
    if docc_name.endswith(".docc"):
        docc_name = docc_name[:-5]
    matching_file = docc_dir / f"{docc_name}.md"
    if matching_file.exists():
        return matching_file
    
    md_files = list(docc_dir.glob("*.md"))
    if md_files:
        return md_files[0]
    
    return None


def build_document_map(docc_dir: Path) -> dict[str, Path]:
    """
    Build a mapping of document names to their file paths.
    e.g., {"Introduction": Path("GettingStarted/Introduction.md")}
    """
    doc_map = {}
    
    for md_file in docc_dir.rglob("*.md"):
        rel_path = md_file.relative_to(docc_dir)
        doc_name = md_file.stem
        doc_map[doc_name] = rel_path
    
    for md_file in docc_dir.rglob("*.md-wip"):
        rel_path = md_file.relative_to(docc_dir)
        doc_name = md_file.stem.replace(".md-wip", "").replace(".md", "")
        if "-wip" in md_file.name:
            doc_name = md_file.name.replace(".md-wip", "")
        doc_map[doc_name] = rel_path
    
    return doc_map


def extract_title_from_file(file_path: Path) -> str:
    """Extract the title (first H1 heading) from a markdown file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("# "):
                    return line[2:].strip()
    except Exception:
        pass
    
    return humanize_doc_name(file_path.stem)


def humanize_doc_name(doc_name: str) -> str:
    """Convert a document name to a human-readable title."""
    result = re.sub(r"([a-z])([A-Z])", r"\1 \2", doc_name)
    result = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", result)
    result = result.replace("-", " ").replace("_", " ")
    return result


def calculate_relative_path(from_file: Path, to_file: Path) -> str:
    """Calculate the relative path from one file to another."""
    from_dir = from_file.parent
    
    try:
        rel_path = os.path.relpath(to_file, from_dir)
        return rel_path.replace("\\", "/")
    except ValueError:
        return str(to_file).replace("\\", "/")


def remove_nested_directive(content: str, start_pos: int) -> tuple[int, int]:
    """
    Find the end position of a nested directive block starting at start_pos.
    Handles arbitrarily nested braces.
    Returns (start, end) positions of the directive block.
    """
    brace_count = 0
    in_string = False
    string_char = None
    i = start_pos
    found_open = False
    
    while i < len(content):
        char = content[i]
        
        if in_string:
            if char == string_char and (i == 0 or content[i - 1] != "\\"):
                in_string = False
            i += 1
            continue
        
        if char in ('"', "'"):
            in_string = True
            string_char = char
            i += 1
            continue
        
        if char == "{":
            brace_count += 1
            found_open = True
        elif char == "}":
            brace_count -= 1
            if found_open and brace_count == 0:
                return (start_pos, i + 1)
        
        i += 1
    
    return (start_pos, len(content))


def remove_docc_metadata(content: str, strip_test_comments: bool = False) -> str:
    """Remove DocC-specific metadata blocks and directives from content."""
    
    block_directives = [
        "Metadata",
        "Comment",
        "Row",
        "Column",
        "Links",
        "Options",
        "Tutorial",
        "Intro",
        "Section",
        "Steps",
        "Step",
        "ContentAndMedia",
        "Stack",
        "Assessments",
        "MultipleChoice",
        "Choice",
        "Justification",
        "Chapter",
        "Volume",
        "Resources",
    ]
    
    for directive in block_directives:
        pattern = rf"@{directive}\s*(\([^)]*\))?\s*\{{"
        while True:
            match = re.search(pattern, content)
            if not match:
                break
            start, end = remove_nested_directive(content, match.start())
            trailing_ws = re.match(r"\s*\n?", content[end:])
            if trailing_ws:
                end += trailing_ws.end()
            content = content[:start] + content[end:]
    
    inline_directives = [
        "Snippet",
        "Image",
        "Video",
        "Available",
        "TitleHeading",
        "DisplayName",
        "DocumentationExtension",
        "TechnologyRoot",
        "Redirected",
        "PageImage",
        "PageKind",
        "PageColor",
        "CallToAction",
        "SupportedLanguage",
        "AlternateRepresentation",
        "DeprecationSummary",
        "XcodeRequirement",
        "TutorialReference",
        "Code",
        "Documentation",
        "Downloads",
        "Forums",
        "SampleCode",
        "Videos",
    ]
    
    for directive in inline_directives:
        content = re.sub(
            rf"@{directive}\s*\([^)]*\)\s*\n?",
            "",
            content
        )
    
    content = re.sub(r"@\w+\s*\n", "", content)
    
    if strip_test_comments:
        content = re.sub(
            r"<!--\s*\n?\s*-\s*test:.*?-->",
            "",
            content,
            flags=re.DOTALL
        )
    
    content = re.sub(
        r"<!--\s*Copyright.*?-->",
        "",
        content,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    return content


def convert_doc_references(
    content: str,
    current_file: Path,
    doc_map: dict[str, Path],
    docc_dir: Path
) -> str:
    """
    Convert <doc:...> references to markdown links.
    
    Handles:
    - <doc:PageName> - link to article/page
    - <doc:PageName#Section-Name> - link to section in page
    - <doc:#Section-Name> - link to section in current page
    - <doc:tutorials/TutorialName> - link to tutorial
    """
    
    def replace_doc_ref(match: re.Match) -> str:
        full_ref = match.group(1)
        
        anchor = ""
        doc_name = full_ref
        
        if full_ref.startswith("#"):
            anchor = full_ref
            doc_name = ""
        elif "#" in full_ref:
            doc_name, anchor_part = full_ref.split("#", 1)
            anchor = f"#{anchor_part}"
        
        if full_ref.startswith("tutorials/") or full_ref.startswith("/tutorials/"):
            doc_name = full_ref.lstrip("/").replace("tutorials/", "")
        
        if not doc_name:
            display_name = humanize_doc_name(anchor[1:].replace("-", " "))
            return f"[{display_name}]({anchor})"
        
        if doc_name not in doc_map:
            print(f"  Warning: Unknown document reference: <doc:{full_ref}>")
            fallback_path = f"{doc_name}.md{anchor}" if doc_name else anchor
            display_name = humanize_doc_name(doc_name.replace("-", " "))
            return f"[{display_name}]({fallback_path})"
        
        target_path = doc_map[doc_name]
        target_full_path = docc_dir / target_path
        
        title = extract_title_from_file(target_full_path)
        if anchor:
            title = humanize_doc_name(anchor[1:].replace("-", " "))
        
        rel_path = calculate_relative_path(current_file, target_path)
        rel_path_with_anchor = f"{rel_path}{anchor}"
        
        return f"[{title}]({rel_path_with_anchor})"
    
    pattern = r"<doc:([^>]+)>"
    return re.sub(pattern, replace_doc_ref, content)


def remove_html_comments(content: str) -> str:
    """Remove HTML comments from content."""
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    return content


def convert_markdown_doc_links(
    content: str,
    current_file: Path,
    doc_map: dict[str, Path],
    docc_dir: Path
) -> str:
    """
    Convert markdown links with doc: prefix to standard links.
    
    Handles: [link text](doc:PageName) -> [link text](PageName.md)
    """
    
    def replace_md_doc_link(match: re.Match) -> str:
        link_text = match.group(1)
        doc_ref = match.group(2)
        
        anchor = ""
        doc_name = doc_ref
        
        if doc_ref.startswith("#"):
            return f"[{link_text}]({doc_ref})"
        elif "#" in doc_ref:
            doc_name, anchor_part = doc_ref.split("#", 1)
            anchor = f"#{anchor_part}"
        
        if doc_name not in doc_map:
            fallback_path = f"{doc_name}.md{anchor}"
            return f"[{link_text}]({fallback_path})"
        
        target_path = doc_map[doc_name]
        rel_path = calculate_relative_path(current_file, target_path)
        
        return f"[{link_text}]({rel_path}{anchor})"
    
    pattern = r"\[([^\]]+)\]\(doc:([^)]+)\)"
    return re.sub(pattern, replace_md_doc_link, content)


def convert_image_references(content: str) -> str:
    """Convert DocC image references to standard markdown."""
    content = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\.png\)",
        r"![\1](\2.png)",
        content
    )
    return content


def convert_symbol_links(content: str) -> str:
    """
    Convert DocC double-backtick symbol links to single-backtick code formatting.
    
    DocC uses ``Symbol`` for navigable symbol links. Since SKILL format
    doesn't support symbol navigation, we convert to inline code.
    
    Examples:
        ``Sloth`` -> `Sloth`
        ``Sloth/eat(_:quantity:)`` -> `Sloth.eat(_:quantity:)`
        ``/SlothCreator/Sloth`` -> `SlothCreator.Sloth`
    
    Note: Must not convert triple backticks (code fences) - only standalone
    double backticks that are symbol links.
    """
    def replace_symbol_link(match: re.Match) -> str:
        symbol_path = match.group(1)
        
        symbol_path = symbol_path.lstrip("/")
        
        symbol_path = symbol_path.replace("/", ".")
        
        return f"`{symbol_path}`"
    
    content = re.sub(r"(?<!`)``([^`\n]+)``(?!`)", replace_symbol_link, content)
    
    return content


def convert_term_lists(content: str) -> str:
    """
    Convert DocC term lists to standard definition formatting.
    
    DocC syntax: - term TermName: Definition text
    Converted to: **TermName**: Definition text
    """
    content = re.sub(
        r"^(\s*)-\s+term\s+([^:]+):\s*(.*)$",
        r"\1- **\2**: \3",
        content,
        flags=re.MULTILINE
    )
    return content


def normalize_asides(content: str) -> str:
    """
    Ensure DocC asides are properly formatted as blockquotes.
    
    Supported aside types:
    - Note, Important, Warning, Tip, Experiment, Earlier Versions
    """
    valid_asides = [
        "Note",
        "Important", 
        "Warning",
        "Tip",
        "Experiment",
        "Earlier Versions",
        "Earlier versions",
    ]
    
    for aside_type in valid_asides:
        pattern = rf"^>\s*{re.escape(aside_type)}:\s*"
        replacement = f"> **{aside_type}:** "
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    return content


def process_markdown_file(
    input_file: Path,
    output_file: Path,
    doc_map: dict[str, Path],
    docc_dir: Path,
    strip_test_comments: bool = False,
    strip_html_comments: bool = True,
) -> None:
    """Process a single markdown file."""
    print(f"  Processing: {input_file.relative_to(docc_dir)}")
    
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    content = remove_docc_metadata(content, strip_test_comments)
    
    output_rel = output_file.relative_to(output_file.parent.parent) if output_file.parent != output_file.parent.parent else output_file
    content = convert_doc_references(content, output_rel, doc_map, docc_dir)
    
    content = convert_markdown_doc_links(content, output_rel, doc_map, docc_dir)
    
    content = convert_symbol_links(content)
    
    content = convert_term_lists(content)
    
    content = normalize_asides(content)
    
    content = convert_image_references(content)
    
    if strip_html_comments:
        content = remove_html_comments(content)
    
    content = re.sub(r"\n{3,}", "\n\n", content)
    content = content.strip() + "\n"
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)


def parse_main_documentation(docc_dir: Path, main_doc_file: Optional[Path]) -> dict:
    """Parse the main documentation file to extract structure for SKILL.md generation."""
    if main_doc_file is None:
        main_doc_file = find_main_doc_file(docc_dir)
    
    if main_doc_file is None or not main_doc_file.exists():
        return {}
    
    with open(main_doc_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1) if title_match else "Documentation"
    
    symbol_match = re.match(r"^``([^`]+)``$", title.strip())
    if symbol_match:
        title = symbol_match.group(1)
    
    cleaned_content = remove_docc_metadata(content, strip_test_comments=False)
    lines = cleaned_content.split("\n")
    description = ""
    for i, line in enumerate(lines):
        if line.startswith("# "):
            for j in range(i + 1, min(i + 15, len(lines))):
                candidate = lines[j].strip()
                if not candidate:
                    continue
                if candidate.startswith("@") or candidate.startswith("#") or candidate.startswith("<!--"):
                    continue
                if candidate in ("{", "}"):
                    continue
                if len(candidate) < 5:
                    continue
                description = candidate
                break
            break
    
    sections = {}
    current_section = None
    
    for line in content.split("\n"):
        section_match = re.match(r"^###\s+(.+)$", line)
        if section_match:
            current_section = section_match.group(1)
            sections[current_section] = []
            continue
        
        doc_match = re.match(r"^-\s+<doc:([^>]+)>", line)
        if doc_match and current_section:
            sections[current_section].append(doc_match.group(1))
    
    return {
        "title": title,
        "description": description,
        "sections": sections,
        "main_doc_file": main_doc_file
    }


def extract_subtitle_from_file(file_path: Path) -> str:
    """Extract the subtitle (line after H1 heading) from a markdown file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("# "):
                for j in range(i + 1, min(i + 10, len(lines))):
                    next_line = lines[j].strip()
                    if not next_line:
                        continue
                    if next_line.startswith("#") or next_line.startswith("@") or next_line.startswith(">"):
                        continue
                    if next_line.startswith("-") or next_line.startswith("*") or next_line.startswith("<!--"):
                        continue
                    cleaned = re.sub(r"<doc:[^>]+>", "", next_line)
                    cleaned = re.sub(r"\s+", " ", cleaned).strip()
                    if cleaned and len(cleaned) > 10:
                        return cleaned
                break
    except Exception:
        pass
    
    return ""


def generate_skill_md(
    output_dir: Path,
    skill_name: str,
    skill_description: str,
    doc_structure: dict,
    doc_map: dict[str, Path],
    docc_dir: Path
) -> None:
    """Generate the SKILL.md file."""
    print("\nGenerating SKILL.md...")
    
    lines = [
        "---",
        f"name: {skill_name}",
        f"description: {skill_description}",
        "---",
        "",
        f"# {doc_structure.get('title', skill_name)}",
        "",
    ]
    
    if doc_structure.get("description"):
        lines.append(doc_structure["description"])
        lines.append("")
    
    lines.append("## Documentation Structure")
    lines.append("")
    
    for section_name, doc_names in doc_structure.get("sections", {}).items():
        lines.append(f"### {section_name}")
        lines.append("")
        
        for doc_name in doc_names:
            if doc_name in doc_map:
                target_path = doc_map[doc_name]
                target_full = docc_dir / target_path
                title = extract_title_from_file(target_full)
                
                short_desc = extract_subtitle_from_file(target_full)
                
                link_path = str(target_path).replace("\\", "/")
                if target_path.suffix == ".md-wip" or "-wip" in str(target_path):
                    lines.append(f"- **{title}** ([{link_path}]({link_path})): *(Work in Progress)*")
                elif short_desc:
                    lines.append(f"- **{title}** ([{link_path}]({link_path})): {short_desc}")
                else:
                    lines.append(f"- **{title}** ([{link_path}]({link_path}))")
            else:
                lines.append(f"- **{humanize_doc_name(doc_name)}**: *(Not found)*")
        
        lines.append("")
    
    lines.extend([
        "## Usage Notes",
        "",
        "- Documentation is organized progressively from getting started to advanced topics",
        "- Start with the Introduction or Getting Started section",
        "- Consult specific guides for detailed information",
        "",
        "## License & Attribution",
        "",
        "This skill contains content converted from DocC documentation format.",
        "",
    ])
    
    skill_md_path = output_dir / "SKILL.md"
    with open(skill_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"  Created: {skill_md_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert DocC documentation to Claude Skills format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Path to the .docc directory (e.g., Documentation.docc or TSPL.docc)"
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
        help="Name for the skill (default: derived from input directory)"
    )
    parser.add_argument(
        "--skill-description",
        type=str,
        default=None,
        help="Description for the skill"
    )
    parser.add_argument(
        "--main-doc",
        type=str,
        default=None,
        help="Name of the main documentation file (default: auto-detect)"
    )
    parser.add_argument(
        "--skip-wip",
        action="store_true",
        help="Skip work-in-progress (.md-wip) files"
    )
    parser.add_argument(
        "--strip-test-comments",
        action="store_true",
        help="Remove HTML comment blocks containing test code (swifttest)"
    )
    parser.add_argument(
        "--skip-assets",
        action="store_true",
        help="Skip copying assets directory"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--keep-html-comments",
        action="store_true",
        help="Keep HTML comments in output (default: remove them)"
    )
    
    args = parser.parse_args()
    
    docc_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    
    if not docc_dir.exists():
        print(f"Error: Input directory does not exist: {docc_dir}")
        return 1
    
    print(f"DocC to SKILL Converter")
    print(f"=" * 50)
    print(f"Input:  {docc_dir}")
    print(f"Output: {output_dir}")
    print()
    
    main_doc_file = None
    if args.main_doc:
        main_doc_file = docc_dir / args.main_doc
        if not main_doc_file.exists():
            print(f"Warning: Specified main doc not found: {main_doc_file}")
            main_doc_file = None
    
    if main_doc_file is None:
        main_doc_file = find_main_doc_file(docc_dir)
        if main_doc_file:
            print(f"Found main documentation file: {main_doc_file.name}")
        else:
            print("Warning: Could not find main documentation file")
    print()
    
    print("Building document map...")
    doc_map = build_document_map(docc_dir)
    print(f"  Found {len(doc_map)} documents")
    
    for name, path in sorted(doc_map.items()):
        print(f"    {name} -> {path}")
    print()
    
    doc_structure = parse_main_documentation(docc_dir, main_doc_file)
    
    if args.dry_run:
        print("Dry run - no files will be modified")
        print()
    
    print("Processing markdown files...")
    
    main_doc_name = main_doc_file.name if main_doc_file else None
    
    for md_file in docc_dir.rglob("*.md"):
        if main_doc_name and md_file.name == main_doc_name:
            continue
        
        rel_path = md_file.relative_to(docc_dir)
        output_file = output_dir / rel_path
        
        if not args.dry_run:
            process_markdown_file(
                md_file, output_file, doc_map, docc_dir,
                strip_test_comments=args.strip_test_comments,
                strip_html_comments=not args.keep_html_comments
            )
    
    for md_file in docc_dir.rglob("*.md-wip"):
        if args.skip_wip:
            print(f"  Skipping WIP: {md_file.relative_to(docc_dir)}")
            continue
        
        rel_path = md_file.relative_to(docc_dir)
        output_file = output_dir / rel_path
        
        if not args.dry_run:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(md_file, output_file)
            print(f"  Copied WIP: {rel_path}")
    
    if not args.skip_assets:
        assets_dir = docc_dir / "Assets"
        if assets_dir.exists() and assets_dir.is_dir():
            output_assets = output_dir / "Assets"
            if not args.dry_run:
                if output_assets.exists():
                    shutil.rmtree(output_assets)
                shutil.copytree(assets_dir, output_assets)
                print(f"  Copied Assets directory")
    
    skill_name = args.skill_name
    if not skill_name:
        if docc_dir.suffix == ".docc":
            skill_name = docc_dir.stem
        else:
            skill_name = docc_dir.parent.name if docc_dir.name in ["Documentation.docc", "TSPL.docc"] else docc_dir.name
        skill_name = skill_name.replace("Documentation", "").replace("TSPL", "swift-programming-language").strip("-_")
        if not skill_name:
            skill_name = "documentation"
    
    skill_description = args.skill_description
    if not skill_description:
        skill_description = doc_structure.get("description", f"Documentation for {skill_name}")
    
    if not args.dry_run:
        generate_skill_md(
            output_dir,
            skill_name,
            skill_description,
            doc_structure,
            doc_map,
            docc_dir
        )
    
    print()
    print("Conversion complete!")
    print(f"Output directory: {output_dir}")
    
    return 0


if __name__ == "__main__":
    exit(main())
