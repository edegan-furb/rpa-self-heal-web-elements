import json
import logging
from difflib import SequenceMatcher
from pathlib import Path
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

MEMORY_FILE = Path(__file__).resolve().with_name("memory.json")


def create_engine(driver):
    """
    Build an AI locator engine backed by the given driver.
    Keeps a reference to the driver plus the in-memory knowledge base.
    """
    return {"driver": driver, "memory": load_memory()}



# Memory (persistent learning)
def load_memory():
    """
    Load the persisted locator dictionary from disk if present.
    """
    if not MEMORY_FILE.exists():
        # First run: nothing saved yet, so start with an empty dict.
        return {}
    with MEMORY_FILE.open("r", encoding="utf-8") as f:
        # Deserialize the JSON payload into a Python dictionary.
        return json.load(f)


def save_memory(memory):
    """
    Persist the in-memory locator map so future sessions can reuse it.
    """
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with MEMORY_FILE.open("w", encoding="utf-8") as f:
        # Write formatted JSON for readability/debugging.
        json.dump(memory, f, indent=4)


def remember(engine, ref_name, selector):
    """
    Store the latest working selector for a reference element.
    """
    engine["memory"][ref_name] = selector
    save_memory(engine["memory"])
    logger.info("Learned locator for '%s': %s", ref_name, selector)



# Scoring logic
def similarity(a, b):
    """
    Simple fuzzy match score used for ranking DOM candidates.
    """
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def score(element, reference):
    """
    Combine fuzzy matches across several attributes into a numeric score.
    """
    score_value = 0

    text = element.text or ""
    score_value += similarity(text, reference) * 3

    id_attr = element.get_attribute("id") or ""
    score_value += similarity(id_attr, reference) * 5

    class_attr = element.get_attribute("class") or ""
    score_value += similarity(class_attr, reference) * 3

    name_attr = element.get_attribute("name") or ""
    score_value += similarity(name_attr, reference) * 2

    value_attr = element.get_attribute("value") or ""
    score_value += similarity(value_attr, reference) * 3

    return score_value



# DOM scanning
def find_best_match(engine, reference):
    """
    Scan the DOM and return the element whose attributes best match the reference name.
    """
    logger.debug("AI-Heal scanning DOM for %s", reference)

    driver = engine["driver"]
    candidates = driver.find_elements(By.XPATH, "//*")
    best_el = None
    best_score = 0

    for el in candidates:
        try:
            # Compute a holistic similarity score between this element and the reference text.
            el_score = score(el, reference)

            # If this element beats our current best score, promote it to the new winner.
            if el_score > best_score:
                best_el = el
                best_score = el_score
        except Exception:
            # Elements without accessible attributes (detached/stale) are skipped silently.
            continue

    return best_el


# Build strong new selector
def build_selector(element):
    """
    Generate a stable XPath for the recovered element, preferring id/text/class.
    """
    tag = element.tag_name
    id_attr = element.get_attribute("id")
    class_attr = element.get_attribute("class")
    text = element.text.strip()

    if id_attr:
        # IDs are unique and therefore the strongest selector we can generate.
        return f"//*[@id='{id_attr}']"

    if text and len(text) < 40:
        # If text is short and unique enough, anchor on normalized text within the tag.
        return f"//{tag}[contains(normalize-space(), '{text}')]"

    if class_attr:
        # Fall back to the first class token for a reasonably specific contains selector.
        cls = class_attr.split()[0]
        return f"//{tag}[contains(@class, '{cls}')]"

    # Absolute last resort: pick the first matching tag in the DOM which at least
    # returns something so the workflow keeps moving.
    return f"(//{tag})[1]"
