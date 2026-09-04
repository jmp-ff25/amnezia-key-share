import argparse
import getpass
import secrets
import sys

from app.auth.security import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("hash-password", help="Interactively generate an Argon2id hash")
    sub.add_parser(
        "create-admin", help="Alias for hash-password (single admin is configured via env)"
    )
    sub.add_parser("generate-admin-path", help="Generate an unguessable ADMIN_PATH value")
    args = parser.parse_args()
    if args.command == "generate-admin-path":
        print(f"/control-{secrets.token_urlsafe(24)}")
        return
    if args.command in {"hash-password", "create-admin"}:
        password = getpass.getpass("New administrator password: ")
        confirm = getpass.getpass("Confirm password: ")
        if len(password) < 12:
            sys.exit("Password must contain at least 12 characters.")
        if password != confirm:
            sys.exit("Passwords do not match.")
        print("\nSet ADMIN_PASSWORD_HASH to this value:\n")
        print(hash_password(password))


if __name__ == "__main__":
    main()
