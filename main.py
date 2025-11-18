import logging

from core.driver_factory import get_driver
from engine import create_engine
from pages.login_page import click_login

# Configure application-wide logging format/level so every module shares it.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def run():
    """
    Opens the Figma login page and clicks the Entrar button.
    """
    # Spin up a fresh Chrome driver instance for the session.
    driver = get_driver()

    # Create the AI engine that stores locator memory and accesses the DOM.
    ai_engine = create_engine(driver)

    # Navigate to the demo login page that we want to interact with.
    # driver.get("https://the-internet.herokuapp.com/login")
    driver.get("https://www.figma.com/login")
    
    
    # Let the healing engine resolve the button and click it.
    click_login(driver, ai_engine)

    # Always close the browser session to release resources.
    driver.quit()


if __name__ == "__main__":
    # Entry point guard so the script can be imported without side effects.
    run()
