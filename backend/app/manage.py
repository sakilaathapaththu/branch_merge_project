"""Admin CLI.

    python -m app.manage create-user <username> --name "Full Name" --role admin --branch all
    python -m app.manage reset-password <username>

Passwords are asked interactively (never on the command line).
"""
import argparse
import getpass
import sys

from app.services import users


def _ask_password() -> str:
    p1 = getpass.getpass("Password (min 8 chars): ")
    if len(p1) < 8:
        sys.exit("Password too short")
    if getpass.getpass("Repeat password: ") != p1:
        sys.exit("Passwords do not match")
    return p1


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m app.manage")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create-user")
    c.add_argument("username")
    c.add_argument("--name", required=True)
    c.add_argument("--role", choices=["admin", "viewer"], default="viewer")
    c.add_argument("--branch", choices=["all", "001", "002"], default="all")
    r = sub.add_parser("reset-password")
    r.add_argument("username")
    a = ap.parse_args()

    if a.cmd == "create-user":
        if users.get_user(a.username):
            sys.exit(f"User {a.username} already exists")
        print(users.create_user(a.username, a.name, _ask_password(), a.role, a.branch))
    else:
        if not users.get_user(a.username):
            sys.exit(f"User {a.username} not found")
        users.update_user(a.username, password=_ask_password())
        print("Password updated")


if __name__ == "__main__":
    main()
