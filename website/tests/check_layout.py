"""Optional browser regression check against an already-running local portal.

Install Playwright and Chromium (see README). This does not change data or load models.
"""

import argparse
import os

from playwright.sync_api import expect, sync_playwright


def check(url):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH"))
        try:
            for width in (360, 768, 1440):
                page = browser.new_page(viewport={"width": width, "height": 860})
                problems = []
                page.on("pageerror", lambda error, sink=problems: sink.append(str(error)))
                for route, ready in [
                    ("/", "#home-chart svg"),
                    ("/explore", "#explore-chart svg"),
                    ("/predict", "#model-panels .out-row"),
                    ("/models", "[data-status].status"),
                ]:
                    page.goto(url.rstrip("/") + route)
                    expect(page.locator(ready).first).to_be_visible()
                    expect(page.locator("nav [aria-current=page]")).to_have_attribute(
                        "href", route
                    )
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= window.innerWidth"
                    ), (width, route, "page overflow")
                    if route == "/explore":
                        page.select_option("[name=cation]", "Li")
                        page.select_option("[name=anion]", "PF6")
                        page.select_option("[name=solvent]", "EC")
                        expect(page.locator("#count")).to_have_text("8 records")
                        for tab in ("trend", "solvents", "distribution"):
                            page.locator(f"[data-plot={tab}]").click()
                            expect(page.locator("#plot-caption")).to_contain_text(
                                "8 reported values"
                            )
                            expect(
                                page.locator("#explore-chart details")
                            ).to_be_visible()
                    if route == "/predict":
                        expect(page.locator("#model-panels .status")).to_have_text(
                            ["NOT LOADED", "NOT LOADED"]
                        )
                        page.locator("#example").click()
                        expect(page.locator("#form-result")).to_contain_text(
                            "Inputs copied"
                        )
                        page.fill("[name=viscosity_mpa_s]", "0")
                        page.locator("button[type=submit]").click()
                        assert not page.locator("[name=viscosity_mpa_s]").evaluate(
                            "(el) => el.checkValidity()"
                        )
                        page.fill("[name=viscosity_mpa_s]", "1.2")
                        page.locator("button[type=submit]").click()
                        expect(page.locator("#form-result")).to_contain_text(
                            "no conductivity was predicted"
                        )
                assert not problems, problems
                page.close()
                print(
                    f"{width}px: all four pages and interactive checks passed",
                    flush=True,
                )
        finally:
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", default="http://127.0.0.1:8000")
    check(parser.parse_args().url)
