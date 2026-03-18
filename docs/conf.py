"""Sphinx configuration for UrbanSVI-QA documentation."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath("../src"))

# Project information
project = "UrbanSVI-QA"
copyright = "2025, UrbanSVI-QA Contributors"
author = "UrbanSVI-QA Contributors"
release = "0.1.0-alpha"
version = "0.1.0-alpha"

# General configuration
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "myst_parser",
    "nbsphinx",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# HTML output
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_title = "UrbanSVI-QA Documentation"

# Napoleon settings (for Google style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_use_ivar = False

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "geopandas": ("https://geopandas.org/en/stable/", None),
}

# MyST settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
