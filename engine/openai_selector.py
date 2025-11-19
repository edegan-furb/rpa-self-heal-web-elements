import json
import logging
import os
from textwrap import dedent
from typing import Dict, List, Optional

from selenium.webdriver.common.by import By

try:
    from .openai_secret import OPENAI_API_KEY as FILE_API_KEY
except ImportError:  # pragma: no cover - only triggered if the file is removed.
    FILE_API_KEY = None

logger = logging.getLogger(__name__)

# Attributes that provide useful hints about what an element represents.
INSPECTED_ATTRIBUTES = [
    "id",
    "name",
    "value",
    "type",
    "class",
    "aria-label",
    "aria-labelledby",
    "role",
    "data-testid",
    "data-test",
    "data-qa",
    "placeholder",
    "title",
]

# XPath that roughly targets interactive controls so we do not dump
# the entire DOM into the prompt we send to OpenAI.
INTERACTIVE_XPATH = (
    "//button|//a|//input|//*[@role='button']|"
    "//*[@type='button']|//*[@type='submit']|"
    "//*[contains(translate(@class,"
    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'button')]"
)

DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
MAX_CANDIDATES = int(os.environ.get("OPENAI_MAX_CANDIDATES", "25"))
MAX_TOKENS = int(os.environ.get("OPENAI_MAX_OUTPUT_TOKENS", "400"))
DOM_SNAPSHOT_CHARS = int(os.environ.get("OPENAI_DOM_SNAPSHOT_CHARS", "20000"))


class OpenAISelectorError(RuntimeError):
    """Raised when the OpenAI-driven selector cannot be produced."""


def _require_openai_client():
    """
    Lazily import and configure the OpenAI client so we do not make the
    dependency mandatory for users who keep the legacy heuristic flow.
    """
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - exercised at runtime only.
        raise OpenAISelectorError(
            "The 'openai' package is required to enable OpenAI-based healing."
        ) from exc

    api_key = FILE_API_KEY or os.environ.get("OPENAI_API_KEY")
    if not api_key or "REPLACE_WITH_YOUR_OPENAI_KEY" in api_key:
        raise OpenAISelectorError(
            "Define your OpenAI key in engine/openai_secret.py (OPENAI_API_KEY) "
            "or via the OPENAI_API_KEY environment variable."
        )

    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def _summarize_element(element) -> Dict[str, str]:
    """
    Extract a compact description of an element (tag, short text, and key attributes)
    so we can feed it to the language model without overwhelming the prompt budget.
    """
    summary = {"tag": element.tag_name}

    text = (element.text or "").strip()
    if text:
        summary["text"] = text[:160]

    inner_text = (element.get_attribute("innerText") or "").strip()
    if inner_text and inner_text != text:
        summary["inner_text"] = inner_text[:200]

    text_content = (element.get_attribute("textContent") or "").strip()
    if text_content and text_content not in {text, inner_text}:
        summary["text_content"] = text_content[:200]

    attributes = {}
    for attr in INSPECTED_ATTRIBUTES:
        value = element.get_attribute(attr)
        if value:
            attributes[attr] = value.strip()

    if attributes:
        summary["attributes"] = attributes

    outer_html = element.get_attribute("outerHTML")
    if outer_html:
        summary["outer_html_preview"] = outer_html[:280]

    return summary


def _collect_candidates(driver, reference: str) -> List[Dict[str, str]]:
    """
    Collect a limited number of DOM nodes that roughly match the reference text.
    """
    ref_lower = reference.lower()
    candidates = []

    all_elements = driver.find_elements(By.XPATH, INTERACTIVE_XPATH)

    for element in all_elements:
        summary = _summarize_element(element)
        haystack_parts = [summary.get("text", "")]
        haystack_parts.extend(summary.get("attributes", {}).values())
        haystack = " ".join(part for part in haystack_parts if part)
        if ref_lower in haystack.lower():
            candidates.append(summary)

        if len(candidates) >= MAX_CANDIDATES:
            break

    if not candidates:
        # If we could not find candidates via substring matching, take the first batch
        # of interactive controls so the model still gets some context to reason with.
        for element in all_elements[:MAX_CANDIDATES]:
            candidates.append(_summarize_element(element))

    return candidates


def _get_dom_snapshot(driver) -> str:
    """
    Capture a truncated snapshot of the full DOM so the LLM can reason over
    the entire page when metadata alone is insufficient.
    """
    try:
        dom = driver.page_source
    except Exception as exc:  # pragma: no cover - best effort utility
        logger.exception("Unable to capture DOM snapshot: %s", exc)
        return ""
    if len(dom) > DOM_SNAPSHOT_CHARS:
        return dom[:DOM_SNAPSHOT_CHARS]
    return dom


def _build_prompt(
    reference: str,
    locators: Optional[List[str]],
    cand_json: str,
    dom_snapshot: str,
) -> List[Dict[str, str]]:
    """
    Compose the conversation payload expected by OpenAI's responses/chat APIs.
    """
    system_message = dedent(
        """
        You are an expert QA automation engineer. Given metadata for DOM elements,
        you must choose the most stable XPath that targets the requested element.
        Prefer ids, data-testid attributes, roles, and text matches (including descendant text)
        over brittle indexes. Use contains() or descendant predicates when the button text
        is rendered by nested spans.
        Respond in JSON with "xpath" and "reason" keys.
        """
    ).strip()

    user_message = dedent(
        f"""
        Target description: {reference}
        Failed locators provided by the test: {locators or []}

        Candidate elements (JSON list):
        {cand_json}

        DOM snapshot (truncated to {len(dom_snapshot)} chars):
        {dom_snapshot}
        """
    ).strip()

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]


def _invoke_openai(messages: List[Dict[str, str]], model: str):
    """
    Call the OpenAI API and parse the JSON response that contains the xpath suggestion.
    """
    client = _require_openai_client()
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=messages,
        response_format={"type": "json_object"},
        max_tokens=MAX_TOKENS,
    )
    content = response.choices[0].message.content
    return json.loads(content)


def suggest_xpath(driver, reference: str, locators: Optional[List[str]] = None) -> Optional[str]:
    """
    Use OpenAI to suggest the best XPath for a reference element name.
    Returns a string XPath or None if AI selection is not available.
    """
    try:
        candidates = _collect_candidates(driver, reference)
    except Exception as exc:
        logger.exception("Unable to gather DOM candidates for %s: %s", reference, exc)
        return None

    if not candidates:
        logger.info("OpenAI healing skipped because no DOM candidates are available.")
        return None

    cand_json = json.dumps(candidates, ensure_ascii=False, indent=2)
    dom_snapshot = _get_dom_snapshot(driver)
    messages = _build_prompt(reference, locators, cand_json, dom_snapshot)

    try:
        payload = _invoke_openai(messages, DEFAULT_MODEL)
    except OpenAISelectorError as exc:
        logger.info("OpenAI selector disabled: %s", exc)
        return None
    except Exception as exc:  # pragma: no cover - depends on remote API.
        logger.exception("OpenAI selector request failed: %s", exc)
        return None

    xpath = (payload.get("xpath") or "").strip()
    if not xpath:
        logger.info("OpenAI did not return a valid XPath: %s", payload)
        return None

    logger.info("OpenAI suggested XPath for %s: %s", reference, xpath)
    reason = payload.get("reason")
    if reason:
        logger.debug("OpenAI reason for %s: %s", reference, reason)

    return xpath
