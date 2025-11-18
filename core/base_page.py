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


def find_healed(driver, ref_name, locators, engine=None):
    """
    Locate an element via the healing strategy without interacting with it.
    """
    # Ensure we have an engine context to use.
    engine = ensure_engine(driver, engine)

    # Simply proxy to the core engine helper and return the WebElement.
    return engine_find_healed(driver, engine, ref_name, locators)
