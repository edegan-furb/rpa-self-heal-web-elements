import time

from engine import create_engine, find_healed as engine_find_healed
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def ensure_engine(driver, engine=None):
    """
    Return the provided engine or create a fresh one tied to the driver.
    We treat the engine as cached state containing the driver + locator memory.
    """
    # If the caller already passed an engine, just reuse it to avoid reloading memory.
    if engine is not None:
        return engine

    # Otherwise build a brand new engine wired to this driver instance.
    return create_engine(driver)


def _scroll_into_view(driver, element):
    """
    Scroll an element into view to improve interaction reliability.
    """
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
        element,
    )


def _try_js_click(driver, element):
    """
    Fallback interaction when Selenium cannot perform a native click.
    """
    driver.execute_script("arguments[0].click();", element)


def click_healed(driver, ref_name, locators, *, timeout=10, retries=3, engine=None):
    """
    Resolve an element via AI healing and click it.
    """
    # Make sure we have a valid engine before attempting to locate anything.
    engine = ensure_engine(driver, engine)

    # Attempt the click with limited retries to recover from stale/intercepted states.
    for attempt in range(retries):
        element = engine_find_healed(driver, engine, ref_name, locators)
        try:
            _scroll_into_view(driver, element)
            WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(element))
            element.click()
            return element
        except StaleElementReferenceException:
            # Retry by re-locating the element on the next loop iteration.
            if attempt >= retries - 1:
                raise
        except ElementClickInterceptedException:
            # Give overlays time to disappear, then try again or fall back to JS.
            if attempt >= retries - 1:
                _try_js_click(driver, element)
                return element
            time.sleep(0.5)
        except TimeoutException:
            # If the element never becomes clickable, attempt a JS click at the end.
            if attempt >= retries - 1:
                _try_js_click(driver, element)
                return element

    return element


def populate_healed(driver, ref_name, locators, value, *, clear_first=True, engine=None):
    """
    Resolve an element via AI healing and populate it with the provided value.

    By default the element is cleared before sending the new value to avoid
    accidental concatenation with any pre-filled text.
    """

    if value is None:
        raise ValueError("populate_healed requires a non-None value to send")

    # Make sure we have a valid engine before attempting to locate anything.
    engine = ensure_engine(driver, engine)

    # Reuse the shared healing helper to locate the target element.
    element = find_healed(driver, ref_name, locators, engine=engine)

    # Clear the field to prevent appending to existing input unless disabled.
    if clear_first:
        element.clear()

    # Send the requested value to the target element.
    element.send_keys(value)

    # Return the element so callers can continue interacting if needed.
    return element


def find_healed(driver, ref_name, locators, engine=None):
    """
    Locate an element via the healing strategy without interacting with it.
    """
    # Ensure we have an engine context to use.
    engine = ensure_engine(driver, engine)

    # Simply proxy to the core engine helper and return the WebElement.
    return engine_find_healed(driver, engine, ref_name, locators)


def _apply_highlight(driver, element, color):
    """
    Inject temporary styling that outlines the element for visual emphasis.
    """
    driver.execute_script(
        """
        const el = arguments[0];
        const color = arguments[1];
        if (!el.hasAttribute('data-heal-original-style')) {
            el.setAttribute('data-heal-original-style', el.getAttribute('style') || '');
        }
        el.style.transition = el.style.transition || 'all 0.2s ease-in-out';
        el.style.outline = '3px solid ' + color;
        el.style.outlineOffset = '2px';
        el.style.boxShadow = '0 0 0 6px ' + color + '40';
        """,
        element,
        color,
    )


def _remove_highlight(driver, element):
    """
    Restore the original inline style so the highlight disappears cleanly.
    """
    driver.execute_script(
        """
        const el = arguments[0];
        const original = el.getAttribute('data-heal-original-style');
        if (original !== null) {
            el.setAttribute('style', original);
            el.removeAttribute('data-heal-original-style');
        } else {
            el.style.outline = '';
            el.style.outlineOffset = '';
            el.style.boxShadow = '';
        }
        """,
        element,
    )


def highlight_healed(driver, ref_name, locators, *, duration=10, color="#ff4d4d", engine=None):
    """
    Locate an element via the healing flow and highlight it for visual inspection.
    """
    element = find_healed(driver, ref_name, locators, engine=engine)
    _apply_highlight(driver, element, color)
    try:
        time.sleep(duration)
    finally:
        _remove_highlight(driver, element)
    return element
