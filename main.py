import logging

from core import get_driver
from engine import create_engine
from pages.login_page import click_login, populate_credentials

# Configure application-wide logging format/level so every module shares it.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def run():
    """
    Opens the login page, populates credentials, and clicks Entrar via healing.
    """
    # Spin up a fresh Chrome driver instance for the session.
    driver = get_driver(headless=True)

    # Create the AI engine that stores locator memory and accesses the DOM.
    ai_engine = create_engine(driver)

    # Navigate to the demo login page that we want to interact with.
    # driver.get("https://the-internet.herokuapp.com/login")
    driver.get("https://www.instagram.com/")

    # Populate the username + password fields using the healed populate helper.
    populate_credentials(
        driver,
        username="demo_user",
        password="super_secret",
        engine=ai_engine,
    )

    # Let the healing engine resolve the button and click it.
    click_login(driver, ai_engine)

    # Always close the browser session to release resources after the highlight.
    driver.quit()


if __name__ == "__main__":
    # Entry point guard so the script can be imported without side effects.
    run()
