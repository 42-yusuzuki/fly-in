"""CLI entry point for Fly-in."""

import sys


def main() -> None:
    """Run Fly-in."""
    if len(sys.argv) != 2:
        print("Usage: fly-in <map_file>")
        raise SystemExit(1)

    map_path = sys.argv[1]

    # TODO:
    # 1. Parse map
    # 2. Solve routing problem
    # 3. Build simulation
    # 4. Output visualization

    print(f"map: {map_path}")


if __name__ == "__main__":
    main()
