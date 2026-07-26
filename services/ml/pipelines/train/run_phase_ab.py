"""CLI wrappers for CI / Make targets."""

from crimelens_ml.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["run-phase-ab"]))
