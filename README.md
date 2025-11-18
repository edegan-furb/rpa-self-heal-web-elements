# RPA Self-Heal Web Elements

Automation demo that shows how to keep brittle web locators alive.  
The project wraps Selenium with a lightweight "healing" engine that:

- Stores every successful locator in `engine/memory.json` for future runs.
- Falls back to AI-style fuzzy matching when all configured selectors fail.
- Persists the new selector so the workflow becomes more resilient over time.

## Project structure

```
main.py               # Entry point – launches Chrome and runs the login flow
core/                 # Driver factory plus engine-aware base helpers
engine/               # DOM scanning + similarity scoring + persistent memory
pages/login_page.py   # Page object demonstrating healed clicks
```

## Requirements

- Python 3.10+
- Google Chrome installed locally
- [ChromeDriver](https://sites.google.com/chromium.org/driver/) that matches your Chrome version  
  (optional: point `CHROME_DRIVER_PATH` to a custom binary)
- `pip install selenium`

## Running the demo

```bash
python -m venv .venv
.venv\Scripts\activate        # or source .venv/bin/activate on Linux/macOS
pip install --upgrade pip selenium
python main.py
```

The script opens `https://www.figma.com/login`, lets the healing engine find the **Entrar** button, clicks it, and then shuts the browser down.

## Configuration

Environment variables that influence behavior:

| Variable | Description |
| --- | --- |
| `CHROME_HEADLESS` | Set to `1/true/yes` to run Chrome in headless mode. |
| `CHROME_DRIVER_PATH` | Absolute path to a custom ChromeDriver binary. |
| `SELENIUM_IMPLICIT_WAIT` | Override the default 10s implicit wait. |

You can also pass `headless` or `implicit_wait` directly to `core.driver_factory.get_driver()` if you are integrating the modules elsewhere.

## How healing works

1. `core.base_page.click_healed()` asks `engine.finder.find_healed()` for an element.
2. The finder tries:
   - The last known-good selector from `engine/memory.json`.
   - Every locator provided by the page object (`pages/login_page.py`).
   - A DOM scan + fuzzy scoring (`engine.healer.find_best_match`) when everything else fails.
3. The newly discovered selector is saved via `engine.healer.remember()`, so the next test run starts with the healed version.

Because the engine stores JSON on disk, delete `engine/memory.json` whenever you want to reset the learned locators.

## Extending the example

- Build more page objects inside `pages/` and reuse the helpers in `core.base_page`.
- Swap out the login URL in `main.py` for an internal system you want to stabilize.
- Experiment with different scoring weights in `engine/healer.py` to favor other attributes (aria-label, data-testid, etc.).

Feel free to tailor the README with organization-specific setup steps or CI instructions once you adopt this pattern.
