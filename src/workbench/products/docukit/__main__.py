"""python -m workbench.products.docukit  — lance Docukit."""

import sys

from workbench.products.docukit.api.run_api import run

if __name__ == "__main__":
    sys.exit(run())
