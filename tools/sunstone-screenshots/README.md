# Sunstone Screenshot Automation

This directory is an initial local framework for replacing Sunstone screenshots in
the OpenNebula documentation. It is intentionally split into small layers:

- an inventory scanner that finds image references in `content/**/*.md`
- a manifest that records which documentation image is produced by which recipe
- Playwright recipes that drive Sunstone and save replacement screenshots
- a static visual QA report for current-vs-replacement review

The VM provisioning piece is represented in the manifest as an environment hook.
That lets us start using the inventory, recipe, capture, and QA workflow locally
while the OpenNebula VM template and nightly-build installation commands are
settled.

## Directory Layout

```text
tools/sunstone-screenshots/
├── bin/sunstone-screenshots          # CLI entry point
├── manifest.example.json             # Example screenshot database
├── recipes/                          # Playwright recipe JSON files
├── requirements.txt                  # Optional Playwright dependency
├── schemas/manifest.schema.json      # Manifest shape
└── sunstone_screenshots/             # Python implementation
```

Generated screenshots and QA reports should live under `.sunstone-screenshots/`,
which is ignored by Git.

## Local Workflow

### 1. Seed the screenshot inventory

Scan the documentation for likely Sunstone screenshots and export CSV for the
spreadsheet:

```bash
tools/sunstone-screenshots/bin/sunstone-screenshots scan \
  --only-sunstone \
  --format csv \
  --output /tmp/sunstone-screenshots.csv
```

The scanner recognizes Markdown image syntax and Hugo `{{< image >}}`
shortcodes, including `path` and `pathDark` variants. It normalizes `/images/...`
references to `assets/images/...` so the inventory can be checked against files
in this repository.

### 2. Curate the manifest

Use the spreadsheet as the human-friendly working view, then convert approved
rows into a manifest like `manifest.example.json`.

Each manifest row answers:

- `doc`: where the screenshot is referenced in the documentation
- `image` and optional `darkImage`: which repo assets will be replaced
- `environment`: what OpenNebula/Sunstone setup is needed
- `recipe` and `capture`: which Playwright workflow creates the image
- `tags`: useful subsets such as `quickstart`, `oneform`, or `networking`

Validate the manifest before capture:

```bash
tools/sunstone-screenshots/bin/sunstone-screenshots validate \
  tools/sunstone-screenshots/manifest.example.json
```

### 3. Run recipes against Sunstone

Install Playwright when you are ready to run captures:

```bash
python3 -m pip install -r tools/sunstone-screenshots/requirements.txt
python3 -m playwright install chromium
```

For the current MVP, point the runner at an already available Sunstone endpoint:

```bash
SUNSTONE_URL=http://localhost:2616 \
SUNSTONE_USER=oneadmin \
SUNSTONE_PASSWORD=opennebula \
tools/sunstone-screenshots/bin/sunstone-screenshots capture \
  tools/sunstone-screenshots/manifest.example.json \
  --tag quickstart \
  --output-root .sunstone-screenshots/runs/local
```

Recipe captures are executed sequentially within a recipe file, so a wizard can
be represented as one `setup` block followed by ordered `captures`. Manifest
entries point to the capture where the screenshot should be taken.

The sequence example shows this pattern with one recipe and several manifest
entries:

- `manifest.sequence-example.json`
- `recipes/quickstart-vms-sequence.json`

Run the whole sequence with:

```bash
SUNSTONE_URL=http://localhost:2616 \
SUNSTONE_USER=oneadmin \
SUNSTONE_PASSWORD=opennebula \
tools/sunstone-screenshots/bin/sunstone-screenshots capture \
  tools/sunstone-screenshots/manifest.sequence-example.json \
  --tag quickstart-sequence \
  --debug
```

The browser executes the recipe once, in capture order. Each manifest entry
selects one capture point by name, for example `login-page`, `dashboard`,
`instances-menu`, or `vm-templates`.

### Visually debug recipes

To watch a recipe run live in a browser, add `--debug` to the normal capture
command:

```bash
SUNSTONE_URL=http://localhost:2616 \
SUNSTONE_USER=oneadmin \
SUNSTONE_PASSWORD=opennebula \
tools/sunstone-screenshots/bin/sunstone-screenshots capture \
  tools/sunstone-screenshots/manifest.example.json \
  --tag quickstart \
  --debug
```

`--debug` opens a visible browser, slows Playwright actions down, and prints
each recipe step before it runs. For a lighter version that only shows the
browser, use `--headed`. To tune the speed yourself:

```bash
tools/sunstone-screenshots/bin/sunstone-screenshots capture \
  tools/sunstone-screenshots/manifest.example.json \
  --tag quickstart \
  --headed \
  --slow-mo 1000
```

For step-by-step debugging with Playwright Inspector:

```bash
tools/sunstone-screenshots/bin/sunstone-screenshots capture \
  tools/sunstone-screenshots/manifest.example.json \
  --tag quickstart \
  --debug \
  --pause-after-step
```

You can also pause around one specific step in the recipe:

```json
{ "action": "hover", "selector": "div[data-cy='sidebar']", "pauseAfter": true }
```

Use this when a recipe fails before you can inspect the page:

```bash
tools/sunstone-screenshots/bin/sunstone-screenshots capture \
  tools/sunstone-screenshots/manifest.example.json \
  --tag quickstart \
  --debug \
  --keep-open-on-failure
```

### Debug selectors

Use the selector debugger when a recipe cannot find or fill fields:

```bash
SUNSTONE_URL=http://localhost:2616 \
tools/sunstone-screenshots/bin/debug-selector \
  --recipe tools/sunstone-screenshots/recipes/quickstart-landing.json
```

The debugger opens the page, prints all input-like elements, then reports how
many elements each recipe selector matches with useful attributes such as
`name`, `type`, `placeholder`, labels, visibility, and bounding boxes.

To test a single selector and try filling it:

```bash
SUNSTONE_URL=http://localhost:2616 \
tools/sunstone-screenshots/bin/debug-selector \
  "input[name='user']" \
  "input[name='token'], input[type='password']" \
  --try-fill "input[name='user']" oneadmin \
  --try-fill "input[name='token'], input[type='password']" opennebula
```

Add `--pause` to open Playwright Inspector after the report is printed.

### 4. Review replacements

Generate a static visual QA report:

```bash
tools/sunstone-screenshots/bin/sunstone-screenshots qa-report \
  tools/sunstone-screenshots/manifest.example.json \
  --replacement-root .sunstone-screenshots/runs/local \
  --output .sunstone-screenshots/qa/index.html
```

Open `.sunstone-screenshots/qa/index.html` in a browser. The report shows the
current checked-in screenshot next to the replacement. Approve/reject choices
are stored in browser local storage for quick review during a local run.

Once the run is accepted, copy the generated `assets/images/...` tree from the
run directory into the repository and review the Git diff.

## Recipe Format

Recipes are JSON files with optional `setup` steps and ordered `captures`.

```json
{
  "id": "example-workflow",
  "setup": [
    { "action": "goto", "url": "${SUNSTONE_URL}" }
  ],
  "captures": [
    {
      "id": "first-step",
      "steps": [
        { "action": "click", "role": "button", "name": "Create" },
        { "action": "waitForSelector", "selector": "[data-testid='wizard']" }
      ],
      "screenshot": {
        "selector": "body"
      }
    }
  ]
}
```

Supported actions in the initial runner:

- `goto`
- `waitForSelector`
- `waitForURL`
- `waitForLoadState`
- `waitTime`
- `hover`
- `moveMouse`
- `defocus`
- `setColorScheme`
- `pause`
- `click`
- `fill`
- `press`
- `evaluate`

### Locator Format

Recipe steps can locate elements in two different ways.

The recommended style uses Playwright's user-facing locators. These are not
written as one selector string; they use recipe keys that map to Playwright
locator methods:

```json
{ "action": "click", "role": "button", "name": "Sign In Now", "exact": true }
{ "action": "click", "dataCy": "login-button" }
{ "action": "fill", "label": "Username", "value": "${SUNSTONE_USER}" }
{ "action": "fill", "text": "Username", "value": "${SUNSTONE_USER}" }
```

These correspond roughly to Playwright code like:

```js
await page.getByRole("button", { name: "Sign In Now", exact: true }).click();
await page.getByLabel("Username").fill(user);
await page.getByText("Username").fill(user);
```

The `dataCy` key is a convenience added by this screenshot runner for Sunstone
elements that have Cypress-style `data-cy` attributes. This recipe step:

```json
{ "action": "click", "dataCy": "login-button" }
```

is equivalent to this selector step:

```json
{ "action": "click", "selector": "[data-cy='login-button']" }
```

If the `data-cy` attribute is on a specific button, both of these work:

```json
{ "action": "click", "dataCy": "login-button" }
{ "action": "click", "selector": "button[data-cy='login-button']" }
```

If the `data-cy` attribute is on a wrapper around the button, select the button
inside it:

```json
{ "action": "click", "selector": "[data-cy='login-actions'] button:has-text('Sign In Now')" }
```

To discover available Cypress attributes on the current page, run:

```bash
SUNSTONE_URL=http://localhost:2616 \
tools/sunstone-screenshots/bin/debug-selector "[data-cy]"
```

For the Sunstone login button, prefer:

```json
{
  "action": "click",
  "role": "button",
  "name": "Sign In Now",
  "exact": true
}
```

The lower-level style uses a `selector` string. In this runner, `selector` is
passed to Playwright's `page.locator(selector)`, so it uses Playwright CSS/XPath
selector syntax:

```json
{ "action": "click", "selector": "button:has-text('Sign In Now')" }
{ "action": "click", "selector": "[data-cy='login-button']" }
{ "action": "fill", "selector": "input[name='user']", "value": "${SUNSTONE_USER}" }
{ "action": "fill", "selector": "input[type='password']", "value": "${SUNSTONE_PASSWORD}" }
{ "action": "waitForSelector", "selector": "[data-testid='wizard']" }
```

Useful selector string patterns:

- `input[name='user']`: element type plus attribute match.
- `input[type='password']`: password input by type.
- `[data-cy='login-button']`: any element with a Cypress `data-cy` attribute.
- `button[data-cy='login-button']`: a button with that `data-cy` attribute.
- `[data-cy='login-actions'] button`: a button inside a `data-cy` wrapper.
- `[data-testid='login-button']`: any element with a stable test id.
- `button:has-text('Sign In Now')`: button containing visible text.
- `button:has-text('Sign In Now'):visible`: same, but only visible matches.
- `css=button:has-text('Sign In Now')`: explicit CSS selector prefix.
- `xpath=//button[contains(., 'Sign In Now')]`: explicit XPath selector prefix.

In CSS selectors, a comma means "or". For example,
`input[name='user'], input[type='text']` matches the username field and every
text input. Since the runner uses the first match for `click` and `fill`, broad
fallbacks can accidentally fill the wrong field. Prefer a single stable selector
when possible, or use a fallback only when both sides identify the same field.

Good references:

- Playwright locators: https://playwright.dev/docs/locators
- Playwright CSS/XPath and other selector strings:
  https://playwright.dev/docs/other-locators
- MDN CSS selectors reference:
  https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_selectors

Prefer role, label, placeholder, or `data-testid` locators where possible.
Text/CSS selectors are useful for early prototypes, but they are more fragile
during UI copy or DOM structure changes.

### Theme, Defocus, and Cropping

When a manifest entry has both `image` and `darkImage`, the runner captures the
same capture point twice. Before writing each file it now applies the matching
browser color scheme:

- `image` uses Playwright `color_scheme="light"`
- `darkImage` uses Playwright `color_scheme="dark"`

If Sunstone needs extra UI actions to settle or toggle the visible theme, add
`themeSteps` to the recipe, capture, or `screenshot` block. These steps run
immediately before the screenshot for that variant:

```json
{
  "themeSteps": {
    "light": [
      { "action": "waitTime", "timeout": 250 }
    ],
    "dark": [
      { "action": "waitTime", "timeout": 250 }
    ]
  }
}
```

`themeSteps` can use normal recipe actions, so if Sunstone requires clicking a
theme toggle rather than only responding to browser color scheme, put those
clicks in the `dark` or `light` list.

To move the mouse away from hover-opened menus, use viewport percentages:

```json
{ "action": "defocus", "xPercent": 50, "yPercent": 50 }
```

`defocus` and `moveMouse` both move the mouse. They accept either percentages or
pixels:

```json
{ "action": "moveMouse", "xPercent": 95, "yPercent": 50 }
{ "action": "moveMouse", "x": 1200, "y": 500 }
```

Percentage coordinates are based on the current viewport. `xPercent: 0` is the
left edge, `xPercent: 100` is the right edge, `yPercent: 0` is the top, and
`yPercent: 100` is the bottom.

To crop a screenshot to a screen region, add a `clip` object to the screenshot
configuration. Percent bounds are usually best for screenshots that may run at
different viewport sizes:

```json
"screenshot": {
  "selector": "body",
  "clip": {
    "leftPercent": 0,
    "rightPercent": 100,
    "topPercent": 8,
    "bottomPercent": 92
  }
}
```

Pixel bounds are also supported:

```json
"screenshot": {
  "clip": {
    "left": 240,
    "right": 1440,
    "top": 80,
    "bottom": 900
  }
}
```

The bounds are left/right/top/bottom, not x/y/width/height. If `clip` is set,
the crop is taken from the viewport. If `clip` is not set, `selector` and
`buffer` work as before.

## VM Provisioning Path

The intended provisioning layer is:

1. Launch an OpenNebula VM from a named template.
2. Wait for network reachability and SSH.
3. Connect to internal repositories, for example with the local `sshuttle`
   profile.
4. Install the requested nightly or specific OpenNebula build.
5. Seed deterministic test data for the recipe group.
6. Export `SUNSTONE_URL`, `SUNSTONE_USER`, and `SUNSTONE_PASSWORD`.
7. Run the Playwright capture command.
8. Tear down or snapshot the VM.

The manifest already has `environment.provisionCommand` and
`environment.teardownCommand` fields so this can become a pluggable backend
without changing recipe files. In CI/CD, that same hook can be replaced by a
runner-specific setup job.

## Authoring Guidelines

- Keep one recipe per documentation workflow, not one recipe per image.
- Use deterministic resource names and reset them during recipe setup.
- Fix viewport, locale, theme, and timezone for every run.
- Prefer API/CLI setup for cloud state, then use Playwright only for the UI path
  that the documentation is showing.
- Capture into `.sunstone-screenshots/runs/<run-id>/assets/images/...` first;
  only promote images to `assets/images/...` after QA.
- Add separate manifest entries when light and dark screenshots need different
  UI setup. A shared `darkImage` field is useful when the same capture state can
  be reused for both variants.
