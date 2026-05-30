"""
NDSS 2026 Markdown Output Generator
Generates a well-formatted markdown file grouping papers by broad category,
with a two-column table: [paper title + link] | [sub-area].
"""

import os
from collections import Counter


def generate_markdown(papers: list[dict], output_path: str) -> str:
    """
    Generate markdown from classified papers.
    Returns the path to the generated file.
    """
    # Group papers by broad_category
    grouped: dict[str, list[dict]] = {}
    for p in papers:
        cat = p.get("broad_category", "Other")
        grouped.setdefault(cat, []).append(p)

    # Sort categories: by paper count (descending), alphabetically for ties
    sorted_cats = sorted(grouped.keys(), key=lambda c: (-len(grouped[c]), c))

    # Build markdown
    lines = []
    lines.append("# NDSS 2026 Accepted Papers")
    lines.append("")
    lines.append(f"> **Total papers: {len(papers)}** | ")
    lines.append(f"> Categories: {len(sorted_cats)} | ")
    lines.append(f"> Generated automatically from [NDSS 2026 Accepted Papers]"
                 f"(https://www.ndss-symposium.org/ndss2026/accepted-papers/)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Table of Contents
    lines.append("## Table of Contents")
    lines.append("")
    for cat in sorted_cats:
        count = len(grouped[cat])
        anchor = cat.lower().replace(" ", "-").replace("/", "")
        lines.append(f"- [{cat} ({count})](#{anchor})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Each category as a section
    for cat in sorted_cats:
        cat_papers = grouped[cat]
        lines.append(f"## {cat}")
        lines.append("")
        lines.append(f"*{len(cat_papers)} papers*")
        lines.append("")
        lines.append("| Paper | Sub-area |")
        lines.append("|-------|----------|")

        # Sort papers by sub_area then title
        cat_papers.sort(key=lambda p: (p.get("sub_area", ""), p.get("title", "")))

        for p in cat_papers:
            title = p.get("title", "Unknown")
            url = p.get("url", "")
            sub_area = p.get("sub_area", "General")

            # Escape markdown special chars in title
            title_escaped = title.replace("|", "\\|")

            # Format: [title](url) | sub_area
            if url:
                title_md = f"[{title_escaped}]({url})"
            else:
                title_md = title_escaped

            lines.append(f"| {title_md} | {sub_area} |")

        lines.append("")
        lines.append("---")
        lines.append("")

    # Statistics section
    lines.append("## Statistics")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|----------|-------|")
    for cat in sorted_cats:
        lines.append(f"| {cat} | {len(grouped[cat])} |")
    lines.append(f"| **Total** | **{len(papers)}** |")
    lines.append("")

    # Sub-area distribution within each category
    lines.append("## Sub-Area Details")
    lines.append("")
    for cat in sorted_cats:
        lines.append(f"### {cat}")
        lines.append("")
        sub_counter = Counter(p.get("sub_area", "General") for p in grouped[cat])
        lines.append("| Sub-area | Count |")
        lines.append("|----------|-------|")
        for sub, count in sub_counter.most_common():
            lines.append(f"| {sub} | {count} |")
        lines.append("")

    # Write to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    content = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[INFO] Markdown written to: {output_path}")
    return output_path


if __name__ == "__main__":
    # Quick test
    sample_papers = [
        {
            "pid": "1",
            "title": "Test Federated Learning Defense",
            "url": "https://example.com/1",
            "broad_category": "Machine Learning and Security",
            "sub_area": "Federated Learning",
        },
        {
            "pid": "2",
            "title": "LLM Jailbreak Attack Study",
            "url": "https://example.com/2",
            "broad_category": "LLMs and AI Safety",
            "sub_area": "LLM Jailbreaking",
        },
        {
            "pid": "3",
            "title": "Another ML Privacy Paper",
            "url": "https://example.com/3",
            "broad_category": "Machine Learning and Security",
            "sub_area": "Differential Privacy",
        },
    ]
    generate_markdown(sample_papers, "output/test_NDSS2026.md")
    print("Test output generated at output/test_NDSS2026.md")
