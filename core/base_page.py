import time

from engine import create_engine, find_healed as engine_find_healed


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


def click_healed(driver, ref_name, locators, engine=None):
    """
    Resolve an element via AI healing and click it.
    """
    # Make sure we have a valid engine before attempting to locate anything.
    engine = ensure_engine(driver, engine)

    # Delegate to the core engine to actually resolve the element using
    # learned selectors, provided locators, or AI fallback.
    element = engine_find_healed(driver, engine, ref_name, locators)

    # Execute the click action once the WebElement is available.
    element.click()

    # Return the element so callers can continue interacting if needed.
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
