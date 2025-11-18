import logging
from core.base_page import click_healed, ensure_engine

# Create a module-level logger so every call reports the same way.
logger = logging.getLogger(__name__)

# Fallback locators (from most to least specific) for the login button.
LOGIN_LOCATORS = [
    "//button[@id='login']",
    "//button[contains(text(),'Login')]",
    "//button[contains(@class,'login')]",
]


def click_login(driver, engine=None):
    """
    Click the login button using the AI healing locators for resilience.
    """
    # Build or reuse the AI engine so we have self-heal capabilities.
    engine = ensure_engine(driver, engine)

    # Perform the healed click which encapsulates locator retries/learning.
    click_healed(driver, "login_button", LOGIN_LOCATORS, engine=engine)

    # Surface a success indicator both via logging and stdout for clarity.
    message = "Login button clicked successfully"
    logger.info(message)
    print(message)
