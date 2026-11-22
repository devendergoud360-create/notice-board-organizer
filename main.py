#!/usr/bin/env python3
"""Notice Board Organizer - console presentation layer.

Uses the application facade and Command registry; no business logic or I/O
details live here. Run: python main.py [--backend json|csv|sqlite]
"""

from __future__ import annotations

import argparse
import os
from datetime import date, timedelta
from typing import List

from application import App, bus, registry
from domain import VALID_CATEGORIES
from reporting import export_csv, export_markdown, export_text
from validation import ask_category, ask_date, ask_positive_int, ask_text, ask_yes_no

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
VERSION = "1.0.0"


class C:
    RESET = "\033[0m"; BOLD = "\033[1m"; CYAN = "\033[96m"
    GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"; DIM = "\033[2m"


def clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def banner() -> None:
    print(C.CYAN + r"""
   _   _  ___  _   _  ___  ___  ___  _____ ___  ___
  | \ | |/ _ \| \ | |/ _ \| _ \/ _ \| ____/ _ \| _ \ / __|
  |  \| | | | |  \| | (_) | | | | | |  _|| | | | | | \__ \
  | |\  | |_| | |\  |\__, | |_| |_| | |__| |_| | |_| |___/
  |_| \_|\___/|_| \_|  /_/|___/\___/|_____\___/|___/ |___/
    """ + C.RESET)
    print(C.BOLD + "       Notice Board Organizer" + C.RESET + f"  v{VERSION}")
    print(C.DIM + "       LocalImpact Challenge | Project #30" + C.RESET)
    print("-" * 62)


def pause() -> None:
    input(C.DIM + "\nPress Enter to continue..." + C.RESET)


def print_menu() -> None:
    print("\n" + C.BOLD + "  MAIN MENU" + C.RESET)
    for key, label in [
        ("1", "Add a new notice"), ("2", "View all notices"),
        ("3", "Search / filter notices"), ("4", "Update a notice"),
        ("5", "Delete a notice"), ("6", "Executive summary & warnings"),
        ("7", "Export reports (MD / TXT / CSV)"), ("8", "Bulk import from CSV"),
        ("9", "Load sample dataset"), ("0", "Exit"),
    ]:
        print(f"   {C.CYAN}{key}{C.RESET}. {label}")
    print("-" * 62)


def action_add(app: App) -> None:
    print(C.BOLD + "\n  ADD NEW NOTICE" + C.RESET)
    title = ask_text("Title", "title")
    category = ask_category("Category")
    posted = ask_date("Date posted", "date posted", date.today())
    expiry = ask_date("Expiry date", "expiry date", posted + timedelta(days=7))
    from validation import validate_date_range
    try:
        validate_date_range(posted, expiry)
    except Exception as exc:
        print(C.RED + f"  [!] {exc}" + C.RESET)
        return
    author = ask_text("Author", "author", "Admin")
    description = ask_text("Description", "description")
    created = registry.execute("add", app, {
        "title": title, "category": category,
        "date_posted": posted.isoformat(), "expiry_date": expiry.isoformat(),
        "author": author, "description": description,
    })
    print(C.GREEN + f"  [+] Added notice #{created['id']}: {created['title']}" + C.RESET)


def action_view(app: App) -> None:
    from reporting import format_table
    from domain import Notice
    items = [Notice.from_dict(d) for d in registry.execute("list", app)]
    print(C.BOLD + "\n  ALL NOTICES" + C.RESET)
    print(format_table(items))


def action_search(app: App) -> None:
    from reporting import format_table
    from domain import Notice
    keyword = input("Keyword (title/description/author, blank = any): ").strip()
    print("  Categories: " + ", ".join(VALID_CATEGORIES))
    category = input("Category (blank = any): ").strip().lower()
    if category:
        from validation import validate_category
        try:
            category = validate_category(category)
        except Exception as exc:
            print(C.RED + f"  [!] {exc}" + C.RESET)
            return
    results = [Notice.from_dict(d) for d in
               registry.execute("search", app, {"keyword": keyword, "category": category})]
    print(format_table(results))


def action_update(app: App) -> None:
    if not app.notices:
        print(C.YELLOW + "  No notices to update." + C.RESET)
        return
    nid = ask_positive_int("Enter notice ID to update")
    target = app.get(nid)
    if not target:
        print(C.RED + f"  [!] No notice with ID {nid}." + C.RESET)
        return
    print(f"  Editing #{nid}: {target.title}  (blank keeps current value)")
    changes = {}
    title = input(f"  Title [{target.title}]: ").strip()
    if title:
        changes["title"] = title
    cat = input(f"  Category [{target.category}]: ").strip()
    if cat:
        from validation import validate_category
        changes["category"] = validate_category(cat)
    for field in ("date_posted", "expiry_date"):
        raw = input(f"  {field} [{getattr(target, field)}]: ").strip()
        if raw:
            from validation import validate_date
            changes[field] = validate_date(raw, field).isoformat()
    author = input(f"  Author [{target.author}]: ").strip()
    if author:
        changes["author"] = author
    desc = input(f"  Description [{target.description}]: ").strip()
    if desc:
        changes["description"] = desc
    updated = app.update(nid, **changes)
    if updated:
        print(C.GREEN + f"  [+] Updated notice #{nid}." + C.RESET)


def action_delete(app: App) -> None:
    if not app.notices:
        print(C.YELLOW + "  No notices to delete." + C.RESET)
        return
    nid = ask_positive_int("Enter notice ID to delete")
    if ask_yes_no(f"  Delete notice #{nid}?"):
        if registry.execute("delete", app, {"id": nid}):
            print(C.GREEN + f"  [+] Deleted notice #{nid}." + C.RESET)
        else:
            print(C.RED + f"  [!] No notice with ID {nid}." + C.RESET)


def action_summary(app: App) -> None:
    from reporting import format_summary
    print(C.BOLD + "\n  ANALYTICS" + C.RESET)
    print(format_summary(registry.execute("summary", app)))
    warns = registry.execute("warnings", app)
    print()
    if warns:
        print(C.YELLOW + f"  [!] {len(warns)} THRESHOLD WARNING(S):" + C.RESET)
        for w in warns:
            print(f"    - #{w['id']} {w['title']}: {w['message']}")
    else:
        print(C.GREEN + "  [+] No threshold warnings." + C.RESET)


def action_export(app: App) -> None:
    from domain import NoticeService
    print(C.BOLD + "\n  EXPORT REPORTS" + C.RESET)
    print("   1. Markdown (.md)   2. Plain text (.txt)   3. CSV (.csv)")
    choice = input("  Format: ").strip()
    ext = {"1": "md", "2": "txt", "3": "csv"}.get(choice)
    if not ext:
        print(C.RED + "  [!] Invalid choice." + C.RESET)
        return
    default = os.path.join(DATA_DIR, f"notice_report.{ext}")
    path = input(f"  Output path [{default}]: ").strip() or default
    ordered = NoticeService.sort(app.notices)
    ok = {"md": export_markdown, "txt": export_text, "csv": export_csv}[ext](path, ordered)
    if ok:
        print(C.GREEN + f"  [+] Exported to {path}" + C.RESET)


def action_import(app: App) -> None:
    import csv
    path = input(f"  CSV path [{os.path.join(DATA_DIR, 'sample_notices.csv')}]: ").strip()
    path = path or os.path.join(DATA_DIR, "sample_notices.csv")
    replace = ask_yes_no("  Replace all current records?", default=False)
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except OSError as exc:
        print(C.RED + f"  [!] Could not read CSV: {exc}" + C.RESET)
        return
    result = app.import_rows(rows, replace=replace)
    print(C.GREEN + f"  [+] Imported {result['added']} record(s); "
          f"skipped {result['skipped']}." + C.RESET)
    for err in result["errors"][:5]:
        print(f"    - row {err['row']}: {err['error']}")


def action_load_sample(app: App) -> None:
    import seed_data
    path = os.path.join(DATA_DIR, "sample_notices.json")
    if not os.path.exists(path):
        seed_data.main()
    import json
    with open(path, "r", encoding="utf-8") as fh:
        rows = json.load(fh)
    if app.notices and not ask_yes_no("  Replace current records?", default=False):
        return
    result = app.import_rows(rows, replace=True)
    print(C.GREEN + f"  [+] Loaded {result['added']} sample records." + C.RESET)


def main() -> None:
    parser = argparse.ArgumentParser(description="Notice Board Organizer CLI")
    parser.add_argument("--backend", default="json", choices=["json", "csv", "sqlite"])
    parser.add_argument("--log", default=None, help="JSONL event log path")
    args = parser.parse_args()

    app = App(backend=args.backend, log_path=args.log)
    actions = {
        "1": action_add, "2": action_view, "3": action_search,
        "4": action_update, "5": action_delete, "6": action_summary,
        "7": action_export, "8": action_import, "9": action_load_sample,
    }
    print(f"  Loaded {len(app.notices)} saved record(s) from {app.backend.location()}")
    try:
        while True:
            banner()
            print_menu()
            choice = input("  Select an option: ").strip()
            if choice == "0":
                print(C.CYAN + "\n  Thank you for using Notice Board Organizer. Goodbye!\n" + C.RESET)
                break
            action = actions.get(choice)
            if not action:
                print(C.RED + "  [!] Invalid option. Please try again." + C.RESET)
                pause()
                continue
            try:
                action(app)
            except (KeyboardInterrupt, EOFError):
                print(C.YELLOW + "\n  [!] Input cancelled." + C.RESET)
            except Exception as exc:
                bus.emit("cli.error", {"error": str(exc)})
                print(C.RED + f"  [!] Unexpected error: {exc}" + C.RESET)
            pause()
    except (KeyboardInterrupt, EOFError):
        print(C.CYAN + "\n\n  Goodbye!\n" + C.RESET)


if __name__ == "__main__":
    main()
