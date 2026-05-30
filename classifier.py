"""
NDSS 2026 Paper Classifier
Uses DeepSeek API to classify papers into broad research categories
and specific sub-areas based on title and abstract.
"""

import json
import os
import time
import requests
from tqdm import tqdm

import config


# ---------------------------------------------------------------------------
# Pre-defined taxonomy (used as a starting point; model can extend it)
# ---------------------------------------------------------------------------
DEFAULT_TAXONOMY = {
    "Machine Learning and Security": [
        "Adversarial ML", "Federated Learning", "Privacy-Preserving ML",
        "ML for Malware/Intrusion Detection", "Backdoor Attacks", "Model Extraction",
        "Differential Privacy", "ML-based Binary Analysis", "Model Attribution",
        "Poisoning Attacks", "Membership Inference",
    ],
    "LLMs and AI Safety": [
        "LLM Jailbreak", "Prompt Injection", "LLM Safety/Alignment",
        "LLM-based Security Tools", "LLM for Vulnerability Detection",
        "LLM Security Architecture", "AI Agents Security",
    ],
    "Web Security": [
        "Browser Security", "Web Attack Detection", "JavaScript Security",
        "Web Tracking", "XSS/CSRF", "Web API Security", "Site Isolation",
        "Web Authentication", "Phishing", "WebAssembly Security",
    ],
    "Network Security": [
        "TLS/HTTPS", "DNS Security", "Wi-Fi Security", "Intrusion Detection",
        "DDoS Defense", "Traffic Analysis", "Network Protocol Security",
        "BGP/Routing Security", "Mobile Network Security",
    ],
    "Systems Security": [
        "OS Security", "Virtualization Security", "Trusted Execution (TEE)",
        "Hardware Security", "Cloud Security", "Container Security",
        "Side Channels", "Rowhammer", "Firmware Security",
    ],
    "Software Security": [
        "Vulnerability Detection", "Fuzzing", "Binary Analysis",
        "Program Analysis", "Exploitation", "Patch Analysis",
        "Supply Chain Security", "Static/Dynamic Analysis", "Sanitizers",
    ],
    "Cryptography and Privacy": [
        "Applied Cryptography", "Searchable Encryption", "Homomorphic Encryption",
        "Zero-Knowledge Proofs", "Secure Multiparty Computation",
        "Messaging Security", "Authentication Protocols", "Post-Quantum Crypto",
    ],
    "IoT and CPS Security": [
        "Automotive Security", "IoT Security", "Industrial Control Systems",
        "Drone Security", "Robotics Security", "Smart Home Security",
        "Medical Device Security", "Building Automation",
    ],
    "Blockchain and Distributed Systems": [
        "Smart Contract Security", "DeFi Security", "Consensus Security",
        "Blockchain Privacy", "Cryptocurrency Security", "P2P Security",
    ],
    "Usable Security and Privacy": [
        "Security Usability", "Privacy Perceptions", "Authentication UX",
        "Security Warnings", "Developer Practices", "Threat Intelligence",
    ],
    "Digital Forensics and Abuse": [
        "Malware Analysis", "Fraud Detection", "Online Abuse", "Disinformation",
        "CSAM Detection", "Censorship Circumvention", "Spam Detection",
    ],
    "Formal Methods and Verification": [
        "Protocol Verification", "Security Proofs", "Symbolic Execution",
        "Model Checking", "Security Policy", "Compliance Verification",
    ],
}


CLASSIFICATION_SYSTEM_PROMPT = """You are an expert in computer security research classification, helping to categorize papers from the NDSS (Network and Distributed System Security) Symposium.

You will be given a batch of papers, each with a title and abstract. Your task is to classify each paper into:
1. A **broad_category** — choose from the existing taxonomy below, or create a NEW broad category if needed
2. A **sub_area** — the specific research sub-area within that broad category

## Rules:
- Use consistent category names across batches. Prefer existing categories when possible.
- The sub_area should be specific and concise (2-5 words, e.g., "Federated Learning", "TLS Fingerprinting", "LLM Jailbreaking").
- When creating a new broad_category, make it general enough to potentially cover other papers too (e.g., "Wireless Security" not "Wi-Fi 6E Specifics").
- When adding a sub_area not in the existing taxonomy, it's fine — the taxonomy is not exhaustive.
- IMPORTANT: A paper may belong to multiple areas. Pick the PRIMARY one that best represents its core contribution.

## Output Format:
Return a valid JSON object with a "classifications" array. Each element must have:
- "pid": the paper's pid (string)
- "broad_category": string
- "sub_area": string

Example:
```json
{
  "classifications": [
    {"pid": "23756", "broad_category": "LLMs and AI Safety", "sub_area": "LLM Jailbreaking"},
    {"pid": "23609", "broad_category": "Machine Learning and Security", "sub_area": "Federated Learning"}
  ]
}
```

Only return the JSON object — no extra text, no markdown fences.
"""


def build_taxonomy_text(taxonomy: dict, new_categories: list[str] = None) -> str:
    """Format the taxonomy dictionary as readable text for the prompt."""
    lines = ["## Existing Taxonomy"]
    for cat, subs in sorted(taxonomy.items()):
        lines.append(f"- **{cat}**: {', '.join(subs)}")
    if new_categories:
        lines.append("\n## Recently added categories (use sparingly)")
        for c in new_categories:
            lines.append(f"- **{c}**")
    return "\n".join(lines)


def classify_batch(
    papers_batch: list[dict],
    taxonomy: dict,
    new_categories: list[str] = None,
) -> list[dict]:
    """
    Send a batch of papers to DeepSeek API for classification.
    Returns list of {pid, broad_category, sub_area} dicts.
    """
    # Build paper list text
    paper_texts = []
    for p in papers_batch:
        abstract = p.get("abstract", "")
        # Truncate long abstracts to save tokens
        if len(abstract) > 800:
            abstract = abstract[:800] + "..."
        paper_texts.append(
            f"**pid={p['pid']}**\n"
            f"Title: {p['title']}\n"
            f"Abstract: {abstract}\n"
        )
    papers_block = "\n---\n".join(paper_texts)

    taxonomy_text = build_taxonomy_text(taxonomy, new_categories)

    user_prompt = f"""{taxonomy_text}

## Papers to classify (batch of {len(papers_batch)}):

{papers_block}

Classify each paper above. Return the JSON with classifications for all {len(papers_batch)} papers."""

    for attempt in range(config.RETRY_TIMES):
        try:
            resp = requests.post(
                f"{config.DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 4096,
                },
                timeout=120,
            )
            resp.raise_for_status()
            result = resp.json()
            content = result["choices"][0]["message"]["content"].strip()

            # Strip markdown code fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                if content.startswith("json"):
                    content = content[4:].strip()

            parsed = json.loads(content)
            return parsed.get("classifications", [])

        except (json.JSONDecodeError, KeyError) as e:
            if attempt < config.RETRY_TIMES - 1:
                time.sleep(config.RETRY_DELAY * (attempt + 1))
            else:
                print(f"  [ERROR] Failed to parse response after {config.RETRY_TIMES} attempts: {e}")
                print(f"  Raw response (first 500 chars): {content[:500] if 'content' in dir() else 'N/A'}")
                return []
        except requests.RequestException as e:
            if attempt < config.RETRY_TIMES - 1:
                time.sleep(config.RETRY_DELAY * (attempt + 1))
            else:
                print(f"  [ERROR] API request failed: {e}")
                return []

    return []


def classify_all_papers(papers: list[dict], force: bool = False) -> list[dict]:
    """
    Classify all papers using DeepSeek API in batches.
    Uses a dynamic taxonomy that grows as new categories are discovered.
    Returns the papers list with 'broad_category' and 'sub_area' fields added.
    """
    # Load previously classified results
    classified_cache = {}
    if os.path.exists(config.CLASSIFIED_JSON):
        with open(config.CLASSIFIED_JSON, "r", encoding="utf-8") as f:
            classified_cache = json.load(f)

    taxonomy = classified_cache.get("taxonomy", dict(DEFAULT_TAXONOMY))
    new_categories = classified_cache.get("new_categories", [])
    classified_map = classified_cache.get("classifications", {})

    # Determine which papers need classification
    papers_to_classify = []
    for p in papers:
        pid = p["pid"]
        if not force and pid in classified_map:
            # Already classified
            p["broad_category"] = classified_map[pid]["broad_category"]
            p["sub_area"] = classified_map[pid]["sub_area"]
        else:
            papers_to_classify.append(p)

    if not papers_to_classify:
        print(f"[INFO] All {len(papers)} papers already classified. Use --force to re-classify.")
        return papers

    print(f"[INFO] Classifying {len(papers_to_classify)} papers "
          f"in batches of {config.CLASSIFY_BATCH_SIZE}...")

    # Process in batches
    batches = [
        papers_to_classify[i:i + config.CLASSIFY_BATCH_SIZE]
        for i in range(0, len(papers_to_classify), config.CLASSIFY_BATCH_SIZE)
    ]

    for batch in tqdm(batches, desc="Classifying"):
        results = classify_batch(batch, taxonomy, new_categories)

        for r in results:
            pid = r.get("pid", "")
            broad_cat = r.get("broad_category", "Other")
            sub_area = r.get("sub_area", "General")

            # Update taxonomy with new categories
            if broad_cat not in taxonomy:
                taxonomy[broad_cat] = []
                if broad_cat not in new_categories:
                    new_categories.append(broad_cat)
                    print(f"  [NEW CATEGORY] {broad_cat}")

            if sub_area not in taxonomy.get(broad_cat, []):
                taxonomy.setdefault(broad_cat, []).append(sub_area)

            classified_map[pid] = {
                "broad_category": broad_cat,
                "sub_area": sub_area,
            }

            # Update paper dict in main list
            if pid in {p["pid"] for p in papers}:
                for p in papers:
                    if p["pid"] == pid:
                        p["broad_category"] = broad_cat
                        p["sub_area"] = sub_area
                        break

            # Handle line breaks in abstract (insert blank line between paragraphs)
            if isinstance(sub_area, str) and "\n" in sub_area:
                r["sub_area"] = sub_area.replace("\n", "\n\n")

        # Save cache after each batch
        with open(config.CLASSIFIED_JSON, "w", encoding="utf-8") as f:
            json.dump({
                "taxonomy": taxonomy,
                "new_categories": new_categories,
                "classifications": classified_map,
            }, f, ensure_ascii=False, indent=2)

        if config.BATCH_DELAY > 0:
            time.sleep(config.BATCH_DELAY)

    # Ensure all papers have classification
    for p in papers:
        if "broad_category" not in p:
            p["broad_category"] = "Other"
        if "sub_area" not in p:
            p["sub_area"] = "General"

    # Report statistics
    from collections import Counter
    cat_counts = Counter(p.get("broad_category", "Other") for p in papers)
    print("\n[INFO] Classification complete. Distribution:")
    for cat, count in cat_counts.most_common():
        print(f"  {cat}: {count} papers")

    return papers


if __name__ == "__main__":
    # Quick test with sample data
    sample = [
        {
            "pid": "test1",
            "title": "A Unified Defense Framework Against Membership Inference in Federated Learning",
            "abstract": "Federated learning (FL) enables collaborative model training without sharing raw data, "
                       "but it is vulnerable to membership inference attacks (MIAs). We propose a unified defense "
                       "framework combining knowledge distillation and contribution-aware aggregation to mitigate "
                       "MIAs while preserving model utility.",
        },
        {
            "pid": "test2",
            "title": "ACE: A Security Architecture for LLM-Integrated App Systems",
            "abstract": "The proliferation of Large Language Model (LLM) integrated applications introduces "
                       "novel security challenges. We present ACE, a security architecture that enforces "
                       "least-privilege access control and input/output sanitization for LLM-integrated systems.",
        },
    ]
    results = classify_batch(sample, DEFAULT_TAXONOMY)
    print(json.dumps(results, ensure_ascii=False, indent=2))
