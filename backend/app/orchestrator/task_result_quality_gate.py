"""Task Result Quality Gate.

Validates that a worker's completed.md delivery actually addresses the three
product accountability dimensions declared in the task template:

  - User Value Delivered
  - Product Maturity Impact Achieved
  - Expected Change Evidence

The gate only activates when the task contract contains non-empty dimension
fields (i.e., the task was sourced from the structured task pool). Plain
backlog tasks without structured templates are not affected.

Rejection codes:
  RESULT_MISSING_DIMENSIONS  — one or more required section headers are absent
  RESULT_SHALLOW_DIMENSIONS  — sections exist but contain only placeholder text
                               or fewer than _MIN_SECTION_CHARS characters
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Ordered list of (markdown section header, contract key) pairs.
# A dimension is only validated when contract[contract_key] is non-empty.
REQUIRED_DIMENSIONS: list[tuple[str, str]] = [
    ('User Value Delivered', 'user_value'),
    ('Product Maturity Impact Achieved', 'product_maturity_impact'),
    ('Expected Change Evidence', 'expected_change'),
]

# Minimum real content characters per dimension section
_MIN_SECTION_CHARS = 80

# Substrings that indicate the section was never filled in by the Worker
_PLACEHOLDER_MARKERS: list[str] = [
    'placeholder',
    'replace this line',
    'todo',
    'tbd',
    'fill in',
    '待填寫',
    'pending',
    'n/a',
    'delivery packaged for orchestrator gate',
    '<!-- ',
]

GATE_RESULT_SHALLOW = 'RESULT_SHALLOW'


@dataclass(frozen=True)
class ResultGateResult:
    passed: bool
    rejection_code: str = ''
    rejection_reason: str = ''
    missing_sections: list[str] = field(default_factory=list)
    shallow_sections: list[str] = field(default_factory=list)


def evaluate_task_result(completed_markdown: str, contract: dict) -> ResultGateResult:
    """Validate that the delivery addresses all contracted product dimensions.

    Only dimensions whose contract field is non-empty are checked. If none are
    present (e.g., a plain backlog task), the result is always PASS.

    Args:
        completed_markdown: Contents of the worker's completed.md file.
        contract: The task contract dict (loaded from contract.json).

    Returns:
        ResultGateResult with passed=True when all checked dimensions have
        substantive evidence, or a failing result with a specific rejection_code.
    """
    dimensions_to_check = [
        (section_name, contract_key)
        for section_name, contract_key in REQUIRED_DIMENSIONS
        if contract.get(contract_key, '').strip()
    ]

    if not dimensions_to_check:
        # Task was not sourced from the structured pool — skip result gate
        return ResultGateResult(passed=True)

    missing: list[str] = []
    shallow: list[str] = []

    for section_name, _ in dimensions_to_check:
        content = _extract_section_content(completed_markdown, section_name)
        if content is None:
            missing.append(section_name)
        elif _is_placeholder_or_shallow(content):
            shallow.append(section_name)

    if missing:
        missing_fmt = ', '.join(f'"{s}"' for s in missing)
        return ResultGateResult(
            passed=False,
            rejection_code='RESULT_MISSING_DIMENSIONS',
            rejection_reason=(
                f'Delivery is missing required product dimension sections: {missing_fmt}. '
                'Worker must include "## User Value Delivered", '
                '"## Product Maturity Impact Achieved", and '
                '"## Expected Change Evidence" in completed.md with substantive evidence.'
            ),
            missing_sections=missing,
            shallow_sections=shallow,
        )

    if shallow:
        shallow_fmt = ', '.join(f'"{s}"' for s in shallow)
        return ResultGateResult(
            passed=False,
            rejection_code='RESULT_SHALLOW_DIMENSIONS',
            rejection_reason=(
                f'Delivery has placeholder or insufficient content in: {shallow_fmt}. '
                f'Each dimension section must contain ≥{_MIN_SECTION_CHARS} chars of real evidence, '
                'not template scaffolding. Worker must describe specific, observable outcomes.'
            ),
            missing_sections=[],
            shallow_sections=shallow,
        )

    return ResultGateResult(passed=True)


def extract_draft_dimension(draft_markdown: str, label: str) -> str:
    """Extract the value of a labeled dimension from a task draft template.

    Matches lines like "User Value: ..." and collects the text until the
    next blank line or the next dimension label.

    Args:
        draft_markdown: Full draft_markdown string from a TaskDraft.
        label: Dimension label without trailing colon, e.g. 'User Value'.

    Returns:
        Stripped text of the dimension value, or empty string if not found.
    """
    # Match "label:" at start of a content line, capture up to blank line or next "Word Word:"
    pattern = re.compile(
        rf'^{re.escape(label)}\s*[:：]\s*(.+?)(?=\n\n|\n[A-Z][^\n:]*\s*[:：]|\Z)',
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    m = pattern.search(draft_markdown)
    if not m:
        return ''
    return re.sub(r'\s+', ' ', m.group(1).strip())


def _extract_section_content(markdown: str, section_name: str) -> str | None:
    """Extract text under a '## <section_name>' header in completed.md.

    Uses a line-by-line approach to reliably handle all MULTILINE/DOTALL edge cases.
    Returns None if the header is absent, otherwise returns the stripped content
    (which may be empty if nothing follows the header before the next heading).
    """
    target_re = re.compile(r'^#{1,4}\s+' + re.escape(section_name) + r'\s*$', re.IGNORECASE)
    next_heading_re = re.compile(r'^#{1,6}\s+')

    lines = markdown.split('\n')
    in_section = False
    collected: list[str] = []

    for line in lines:
        if target_re.match(line.strip()):
            in_section = True
            continue
        if in_section:
            if next_heading_re.match(line):
                break
            collected.append(line)

    if not in_section:
        return None
    return '\n'.join(collected).strip()


def _is_placeholder_or_shallow(content: str) -> bool:
    """Return True when content is too short or contains placeholder markers."""
    if len(content) < _MIN_SECTION_CHARS:
        return True
    lowered = content.lower()
    return any(marker in lowered for marker in _PLACEHOLDER_MARKERS)
