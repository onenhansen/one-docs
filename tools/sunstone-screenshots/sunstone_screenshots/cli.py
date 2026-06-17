from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from .capture import CaptureError, capture_screenshots
from .docs_scan import ImageReference, scan_content
from .manifest import ManifestError, load_manifest, validate_manifest
from .qa_report import write_qa_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sunstone-screenshots",
        description="Inventory, capture, and review Sunstone screenshots in the OpenNebula docs.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root. Defaults to the current directory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan markdown files for image references.")
    scan_parser.add_argument("--content-dir", default="content", help="Content directory relative to the repo root.")
    scan_parser.add_argument("--format", choices=("json", "csv"), default="json")
    scan_parser.add_argument("--only-sunstone", action="store_true", help="Only include likely Sunstone UI screenshots.")
    scan_parser.add_argument("--output", help="Write output to a file instead of stdout.")

    validate_parser = subparsers.add_parser("validate", help="Validate a screenshot manifest.")
    validate_parser.add_argument("manifest", help="Path to manifest JSON.")

    report_parser = subparsers.add_parser("qa-report", help="Create a visual old-vs-new screenshot QA report.")
    report_parser.add_argument("manifest", help="Path to manifest JSON.")
    report_parser.add_argument(
        "--replacement-root",
        required=True,
        help="Root containing newly captured files, preserving repo-relative asset paths.",
    )
    report_parser.add_argument("--output", default=".sunstone-screenshots/qa/index.html")

    capture_parser = subparsers.add_parser("capture", help="Run Playwright recipes and store replacement screenshots.")
    capture_parser.add_argument("manifest", help="Path to manifest JSON.")
    capture_parser.add_argument("--output-root", default=".sunstone-screenshots/runs/local")
    capture_parser.add_argument("--id", action="append", dest="ids", help="Screenshot id to capture. Can be repeated.")
    capture_parser.add_argument("--tag", action="append", dest="tags", help="Capture screenshots with this tag. Can be repeated.")
    capture_parser.add_argument("--headed", action="store_true", help="Show the browser while recipes run.")
    capture_parser.add_argument("--browser", choices=("chromium", "firefox", "webkit"), default="chromium")
    capture_parser.add_argument("--debug", action="store_true", help="Show the browser, slow actions down, and print each recipe step.")
    capture_parser.add_argument("--slow-mo", type=int, default=0, help="Delay Playwright actions by this many milliseconds.")
    capture_parser.add_argument("--pause-before-step", action="store_true", help="Pause in Playwright Inspector before every recipe step.")
    capture_parser.add_argument("--pause-after-step", action="store_true", help="Pause in Playwright Inspector after every recipe step.")
    capture_parser.add_argument("--keep-open-on-failure", action="store_true", help="Leave the browser open if a recipe step fails.")

    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()

    try:
        if args.command == "scan":
            return _scan(args, repo_root)
        if args.command == "validate":
            return _validate(args, repo_root)
        if args.command == "qa-report":
            return _qa_report(args, repo_root)
        if args.command == "capture":
            return _capture(args, repo_root)
    except (ManifestError, CaptureError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


def _scan(args: argparse.Namespace, repo_root: Path) -> int:
    references = scan_content(repo_root, Path(args.content_dir))
    if args.only_sunstone:
        references = [reference for reference in references if reference.sunstone_candidate]

    if args.format == "json":
        payload = [_reference_to_dict(reference) for reference in references]
        text = json.dumps(payload, indent=2)
    else:
        text = _references_to_csv(references)

    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


def _validate(args: argparse.Namespace, repo_root: Path) -> int:
    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)
    errors = validate_manifest(manifest, repo_root, manifest_path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Manifest OK: {manifest_path}")
    return 0


def _qa_report(args: argparse.Namespace, repo_root: Path) -> int:
    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)
    write_qa_report(
        manifest=manifest,
        repo_root=repo_root,
        replacement_root=Path(args.replacement_root),
        output=Path(args.output),
    )
    print(f"Wrote QA report: {args.output}")
    return 0


def _capture(args: argparse.Namespace, repo_root: Path) -> int:
    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)
    errors = validate_manifest(manifest, repo_root, manifest_path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    capture_screenshots(
        manifest=manifest,
        manifest_path=manifest_path,
        repo_root=repo_root,
        output_root=Path(args.output_root),
        selected_ids=set(args.ids) if args.ids else None,
        selected_tags=set(args.tags) if args.tags else None,
        headed=args.headed,
        browser_name=args.browser,
        debug=args.debug,
        slow_mo=args.slow_mo,
        pause_before_step=args.pause_before_step,
        pause_after_step=args.pause_after_step,
        keep_open_on_failure=args.keep_open_on_failure,
    )
    return 0


def _reference_to_dict(reference: ImageReference) -> dict[str, object]:
    return {
        "doc": reference.doc,
        "line": reference.line,
        "kind": reference.kind,
        "alt": reference.alt,
        "sunstoneCandidate": reference.sunstone_candidate,
        "reasons": list(reference.reasons),
        "images": [
            {
                "role": variant.role,
                "rawPath": variant.raw_path,
                "assetPath": variant.asset_path,
                "exists": variant.exists,
            }
            for variant in reference.variants
        ],
    }


def _references_to_csv(references: list[ImageReference]) -> str:
    from io import StringIO

    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "doc",
            "line",
            "kind",
            "alt",
            "sunstone_candidate",
            "reasons",
            "roles",
            "raw_paths",
            "asset_paths",
            "exists",
        ],
    )
    writer.writeheader()
    for reference in references:
        writer.writerow(
            {
                "doc": reference.doc,
                "line": reference.line,
                "kind": reference.kind,
                "alt": reference.alt,
                "sunstone_candidate": str(reference.sunstone_candidate).lower(),
                "reasons": "|".join(reference.reasons),
                "roles": "|".join(variant.role for variant in reference.variants),
                "raw_paths": "|".join(variant.raw_path for variant in reference.variants),
                "asset_paths": "|".join(variant.asset_path or "" for variant in reference.variants),
                "exists": "|".join(str(variant.exists).lower() for variant in reference.variants),
            }
        )
    return buffer.getvalue().rstrip("\n")
