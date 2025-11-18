import logging
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from .healer import find_best_match, build_selector, remember

logger = logging.getLogger(__name__)

RECOVERABLE_EXCEPTIONS = (NoSuchElementException, StaleElementReferenceException)


def find_healed(driver, engine, ref_name, locators):
    """
    Try existing locators, learned selectors, and finally AI healing to
    locate an element. Returns a Selenium WebElement.
    """

    # 0. Check memory (persistent learning)
    memory = engine["memory"]
    if ref_name in memory:
        learned = memory[ref_name]
        try:
            # Start with the last known-good selector to minimize DOM scans.
            logger.debug("Trying learned locator for %s: %s", ref_name, learned)
            return driver.find_element(By.XPATH, learned)
        except RECOVERABLE_EXCEPTIONS:
            # If the stored locator stopped working we fall back to defaults and relearn.
            logger.info("Learned locator for %s no longer matches. Falling back to defaults.", ref_name)

    # 1. Try original locators first
    for loc in locators:
        try:
            # Attempt each provided locator in declared order.
            logger.debug("Trying locator for %s: %s", ref_name, loc)
            el = driver.find_element(By.XPATH, loc)
            # Persist the locator so next runs can skip straight to the working one.
            remember(engine, ref_name, loc)
            return el
        except RECOVERABLE_EXCEPTIONS:
            # Missing elements are fine—we simply try the next locator in the list.
            logger.debug("Locator for %s failed: %s", ref_name, loc)

    logger.warning("All configured locators failed for %s. AI-Heal activated.", ref_name)

    # 2. AI scanning + prediction
    el = find_best_match(engine, ref_name)
    if not el:
        # If scanning still yields nothing we raise immediately to fail fast.
        raise Exception(f"AI-Heal failed: cannot detect element '{ref_name}'")

    # 3. Build new locator
    new_xpath = build_selector(el)
    logger.info("AI-Heal generated fallback selector for %s: %s", ref_name, new_xpath)

    remember(engine, ref_name, new_xpath)
    message = f"AI-Heal success: selector persisted for {ref_name}"
    logger.info(message)
    print(message)

    # 4. Return healed element
    # Perform a fresh lookup using the new selector to return a live WebElement.
    return driver.find_element(By.XPATH, new_xpath)
