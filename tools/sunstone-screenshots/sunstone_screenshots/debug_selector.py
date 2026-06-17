from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


VARIABLE_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
DEFAULT_INPUT_SELECTOR = "input, textarea, [contenteditable='true'], [role='textbox']"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="debug-selector",
        description="Debug Playwright selectors against a Sunstone page.",
    )
    parser.add_argument(
        "selectors",
        nargs="*",
        help="Playwright selector strings to test, for example \"input[name='user']\".",
    )
    parser.add_argument("--url", default=os.environ.get("SUNSTONE_URL"), help="URL to open. Defaults to SUNSTONE_URL.")
    parser.add_argument("--recipe", help="Also test every selector found in a recipe JSON file.")
    parser.add_argument("--timeout", type=int, default=15000, help="Navigation and selector timeout in milliseconds.")
    parser.add_argument("--limit", type=int, default=8, help="Maximum matched elements to describe per selector.")
    parser.add_argument("--headless", action="store_true", help="Run without showing the browser.")
    parser.add_argument("--pause", action="store_true", help="Open Playwright Inspector after the initial checks.")
    parser.add_argument(
        "--try-fill",
        nargs=2,
        action="append",
        metavar=("SELECTOR", "VALUE"),
        help="Fill a selector with a value after reporting matches. Can be repeated.",
    )
    parser.add_argument(
        "--screenshot",
        default=".sunstone-screenshots/debug/selector-debug.png",
        help="Where to save a debug screenshot.",
    )
    parser.add_argument(
        "--no-list-inputs",
        action="store_true",
        help="Do not print the automatic input/textarea inventory.",
    )
    args = parser.parse_args(argv)

    if not args.url:
        print("error: pass --url or set SUNSTONE_URL", file=sys.stderr)
        return 2

    selectors = list(args.selectors)
    if args.recipe:
        selectors.extend(_selectors_from_recipe(Path(args.recipe)))
    selectors = _dedupe(selectors)

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "error: Playwright is not installed. Run "
            "`python3 -m pip install -r tools/sunstone-screenshots/requirements.txt` "
            "and then `python3 -m playwright install chromium`.",
            file=sys.stderr,
        )
        return 1

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=args.headless)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.set_default_timeout(args.timeout)

        try:
            print(f"Opening {args.url}")
            page.goto(_expand(args.url), wait_until="domcontentloaded", timeout=args.timeout)
            _wait_for_quiet_page(page)

            if not args.no_list_inputs:
                _report_selector(page, DEFAULT_INPUT_SELECTOR, args.limit, "All input-like elements")

            for selector in selectors:
                _report_selector(page, _expand(selector), args.limit, f"Selector: {selector}")

            for selector, value in args.try_fill or []:
                _try_fill(page, _expand(selector), _expand(value))

            screenshot = Path(args.screenshot)
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot), full_page=True)
            print(f"\nSaved debug screenshot: {screenshot}")

            if args.pause:
                print("Pausing in Playwright Inspector. Resume there to close this script.")
                page.pause()
        except PlaywrightTimeoutError as exc:
            print(f"timeout: {exc}", file=sys.stderr)
            return 1
        finally:
            context.close()
            browser.close()

    return 0


def _selectors_from_recipe(path: Path) -> list[str]:
    recipe = json.loads(path.read_text(encoding="utf-8"))
    selectors: list[str] = []

    def collect_step(step: dict[str, Any]) -> None:
        selector = step.get("selector")
        if selector:
            selectors.append(str(selector))
        data_cy = step.get("dataCy")
        if data_cy:
            selectors.append(f"[data-cy={_css_string(str(data_cy))}]")

    for step in recipe.get("setup", []):
        if isinstance(step, dict):
            collect_step(step)

    for capture in recipe.get("captures", []):
        if not isinstance(capture, dict):
            continue
        for step in capture.get("steps", []):
            if isinstance(step, dict):
                collect_step(step)
        screenshot = capture.get("screenshot")
        if isinstance(screenshot, dict) and screenshot.get("selector"):
            selectors.append(str(screenshot["selector"]))

    return selectors


def _report_selector(page: Any, selector: str, limit: int, title: str) -> None:
    print(f"\n== {title} ==")
    print(selector)
    locator = page.locator(selector)
    try:
        count = locator.count()
    except Exception as exc:
        print(f"selector error: {exc}")
        return

    print(f"matches: {count}")
    for index in range(min(count, limit)):
        element = locator.nth(index)
        try:
            info = element.evaluate(
                """el => {
                  const labels = [];
                  if (el.id) {
                    for (const label of document.querySelectorAll(`label[for="${CSS.escape(el.id)}"]`)) {
                      labels.push(label.innerText.trim());
                    }
                  }
                  const wrappingLabel = el.closest("label");
                  if (wrappingLabel) labels.push(wrappingLabel.innerText.trim());

                  return {
                    tag: el.tagName.toLowerCase(),
                    id: el.id || "",
                    name: el.getAttribute("name") || "",
                    type: el.getAttribute("type") || "",
                    role: el.getAttribute("role") || "",
                    dataCy: el.getAttribute("data-cy") || "",
                    dataTestId: el.getAttribute("data-testid") || "",
                    ariaLabel: el.getAttribute("aria-label") || "",
                    placeholder: el.getAttribute("placeholder") || "",
                    autocomplete: el.getAttribute("autocomplete") || "",
                    className: typeof el.className === "string" ? el.className : "",
                    value: "value" in el ? el.value : "",
                    text: el.innerText || el.textContent || "",
                    labels
                  };
                }"""
            )
            visible = element.is_visible()
            enabled = element.is_enabled()
            box = element.bounding_box()
            print(f"[{index}] {info['tag']} visible={visible} enabled={enabled} box={_format_box(box)}")
            print(
                "    "
                + " ".join(
                    part
                    for part in (
                        _attr("id", info["id"]),
                        _attr("name", info["name"]),
                        _attr("type", info["type"]),
                        _attr("role", info["role"]),
                        _attr("data-cy", info["dataCy"]),
                        _attr("data-testid", info["dataTestId"]),
                        _attr("aria-label", info["ariaLabel"]),
                        _attr("placeholder", info["placeholder"]),
                        _attr("autocomplete", info["autocomplete"]),
                    )
                    if part
                )
            )
            if info["labels"]:
                print(f"    labels={info['labels']}")
            if info["value"]:
                print(f"    value={info['value']!r}")
            if info["text"].strip():
                print(f"    text={info['text'].strip()[:160]!r}")
            if info["className"]:
                print(f"    class={info['className'][:160]!r}")
        except Exception as exc:
            print(f"[{index}] error while describing element: {exc}")


def _try_fill(page: Any, selector: str, value: str) -> None:
    print(f"\n== Try Fill ==")
    print(f"{selector} -> {value!r}")
    locator = page.locator(selector).first
    locator.fill(value)
    actual = locator.input_value()
    print(f"filled value: {actual!r}")


def _wait_for_quiet_page(page: Any) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass


def _expand(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        return os.environ.get(match.group(1), match.group(0))

    return VARIABLE_RE.sub(replace, value)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped


def _attr(name: str, value: str) -> str:
    if not value:
        return ""
    return f"{name}={value!r}"


def _format_box(box: dict[str, float] | None) -> str:
    if not box:
        return "none"
    return f"{box['x']:.0f},{box['y']:.0f} {box['width']:.0f}x{box['height']:.0f}"


def _css_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\a ")
    return f'"{escaped}"'


if __name__ == "__main__":
    raise SystemExit(main())
