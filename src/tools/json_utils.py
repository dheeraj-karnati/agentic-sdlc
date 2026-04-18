"""Robust JSON parsing for LLM outputs.

Smaller LLMs (Ollama) often produce JSON with trailing commas,
single-line comments, or other minor syntax issues. This module
provides a best-effort parser that handles those cases.
"""

import json
import re


def extract_json(text: str) -> str:
    """Extract JSON content from LLM response text.

    Handles markdown code blocks, leading/trailing prose, and
    both object ({}) and array ([]) JSON.
    """
    if not isinstance(text, str):
        return str(text)

    # Strip markdown code fences
    if "```" in text:
        # Try to find JSON inside code blocks first
        match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)```", text)
        if match:
            text = match.group(1).strip()

    # Find the outermost JSON structure
    # Pick whichever delimiter appears first in the text
    obj_start = text.find("{")
    arr_start = text.find("[")

    if obj_start == -1 and arr_start == -1:
        return text

    # Choose the structure that starts first
    if arr_start != -1 and (obj_start == -1 or arr_start < obj_start):
        end = text.rfind("]")
        if end > arr_start:
            return text[arr_start : end + 1]
    elif obj_start != -1:
        end = text.rfind("}")
        if end > obj_start:
            return text[obj_start : end + 1]

    return text


def fix_json(text: str) -> str:
    """Fix common JSON issues from LLM outputs.

    Handles:
    - Trailing commas before } or ]
    - Single-line // comments
    - Unquoted property names (simple cases)
    - Truncated JSON (attempts to close open brackets)
    """
    # Remove single-line comments
    text = re.sub(r"//[^\n]*", "", text)

    # Remove trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # Try to close truncated JSON by balancing brackets
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")

    if open_braces > 0 or open_brackets > 0:
        # Strip any trailing incomplete key-value pair
        text = re.sub(r",\s*\"[^\"]*\"?\s*:?\s*$", "", text)
        text += "]" * max(0, open_brackets)
        text += "}" * max(0, open_braces)

    return text


def parse_llm_json(text: str) -> dict | list:
    """Parse JSON from LLM output with best-effort error recovery.

    Args:
        text: Raw LLM response that should contain JSON.

    Returns:
        Parsed JSON as dict or list.

    Raises:
        json.JSONDecodeError: If JSON cannot be parsed after all fixes.
    """
    extracted = extract_json(text)

    # Try direct parse first
    try:
        return json.loads(extracted)
    except json.JSONDecodeError:
        pass

    # Try with fixes
    fixed = fix_json(extracted)
    return json.loads(fixed)
