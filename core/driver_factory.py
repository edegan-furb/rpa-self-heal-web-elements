import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

# Default implicit wait in seconds if the caller does not override via parameter/env.
DEFAULT_WAIT_SECONDS = 10


def _should_run_headless(headless_override):
    """
    Decide if Chrome should be spawned headless.

    Priority is:
    1. Explicit function argument (headless_override)
    2. Environment variable CHROME_HEADLESS
    3. Default to False.
    """
    if headless_override is not None:
        return headless_override
    env_value = os.environ.get("CHROME_HEADLESS", "").lower()
    return env_value in {"1", "true", "yes"}


def get_driver(*, headless=None, implicit_wait=None):
    """
    Build a Chrome driver with sane defaults that can be tuned via arguments
    or the CHROME_HEADLESS/SELENIUM_IMPLICIT_WAIT environment variables.
    """
    # Instantiate Chrome options so we can toggle headless mode and other flags.
    options = webdriver.ChromeOptions()

    # Make sure the browser opens maximized unless headless overrides window size.
    options.add_argument("--start-maximized")

    # Suppress automation banners / noisy logging to keep console output clean.
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )

    # Apply headless configuration if requested either via params or env vars.
    if _should_run_headless(headless):
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

    # Allow callers to inject a custom ChromeDriver binary via CHROME_DRIVER_PATH.
    driver_path = os.environ.get("CHROME_DRIVER_PATH")
    service = Service(executable_path=driver_path) if driver_path else None

    # Start the Chrome WebDriver using the assembled service/options.
    driver = webdriver.Chrome(service=service, options=options)

    # Use provided implicit wait or fall back to defaults/env overrides.
    wait_time = implicit_wait or int(os.environ.get("SELENIUM_IMPLICIT_WAIT", DEFAULT_WAIT_SECONDS))
    driver.implicitly_wait(wait_time)

    # Always return the configured driver so callers can navigate/interact.
    return driver
