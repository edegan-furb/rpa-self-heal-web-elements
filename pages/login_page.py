import logging
from core import click_healed, ensure_engine, populate_healed

# Create a module-level logger so every call reports the same way.
logger = logging.getLogger(__name__)

# Fallback locators (from most to least specific) for the login button.
LOGIN_LOCATORS = [
    "//button[@id='Entrar']",
    "//button[contains(text(),'Entrar')]",
    "//button[contains(@class,'Entrar')]",
]

# Healed locators for the username/email field.
USERNAME_LOCATORS = [
    "//input[@name='username']",
    "//input[@aria-label='Phone number, username, or email']",
    "//input[contains(@placeholder,'username') or contains(@aria-label,'username')]",
]

# Healed locators for the password field.
PASSWORD_LOCATORS = [
    "//input[@name='password']",
    "//input[@aria-label='Password']",
    "//input[@type='password']",
]


def click_login(driver, engine=None):
    """
    Click the login button using the AI healing locators for resilience.
    """
    # Build or reuse the AI engine so we have self-heal capabilities.
    engine = ensure_engine(driver, engine)

    # Click the healed element to submit the form.
    click_healed(
        driver,
        "login-button",
        LOGIN_LOCATORS,
        engine=engine,
    )

    # Surface a success indicator both via logging and stdout for clarity.
    message = "Login button clicked via healed locator"
    logger.info(message)
    print(message)


def populate_credentials(driver, username, password, *, clear_first=True, engine=None):
    """
    Fill in the username and password fields using healed locators.
    """

    engine = ensure_engine(driver, engine)

    populate_healed(
        driver,
        "username-field",
        USERNAME_LOCATORS,
        username,
        clear_first=clear_first,
        engine=engine,
    )
    populate_healed(
        driver,
        "password-field",
        PASSWORD_LOCATORS,
        password,
        clear_first=clear_first,
        engine=engine,
    )

    message = "Credentials populated via healed locators"
    logger.info(message)
    print(message)
