import logging
from core.base_page import ensure_engine, highlight_healed

# Create a module-level logger so every call reports the same way.
logger = logging.getLogger(__name__)

# Fallback locators (from most to least specific) for the login button.
LOGIN_LOCATORS = [
    "//button[@id='Entrar']",
    "//button[contains(text(),'Entrar')]",
    "//button[contains(@class,'Entrar')]",
]


def click_login(driver, engine=None):
    """
    Click the login button using the AI healing locators for resilience.
    """
    # Build or reuse the AI engine so we have self-heal capabilities.
    engine = ensure_engine(driver, engine)

    # Highlight the healed element for visibility instead of clicking it.
    highlight_healed(
        driver,
        "login-button",
        LOGIN_LOCATORS,
        duration=10,
        engine=engine,
    )

    # Surface a success indicator both via logging and stdout for clarity.
    message = "Login button highlighted for 10 seconds"
    logger.info(message)
    print(message)
