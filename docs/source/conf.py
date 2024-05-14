# Configuration file for the Sphinx documentation builder.

import os
import sys

import django

# Note: You may need to change the path to match
# your project's structure

# For discovery of Python modules when building from with docs/.
sys.path.insert(0, os.path.abspath(".."))
# For discovery of Python modules when building from root using make -C docs/ (which makes the CWD docs/source, i.e.,
# where this file is).
sys.path.insert(1, os.path.abspath("../.."))

# -- Custom stuff for django.
# Borrowed from https://daniel.feldroy.com/posts/2023-01-configuring-sphinx-auto-doc-with-django

# This tells Django where to find the settings file
os.environ["DJANGO_SETTINGS_MODULE"] = "biospecdb.settings.dev"

# This activates Django and makes it possible for Sphinx to
# autodoc your project
django.setup()
# -- END Custom stuff for django.

# -- Project information
from biospecdb import __project__, __version__

project = __project__
copyright = '2023, SSEC-JHU'
author = 'SSEC-JHU'

release = __version__
version = __version__

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output

# select theme from options below
html_theme = 'sphinx_rtd_theme'
#html_theme = 'sphinx_book_theme'
html_static_path = ['../_static']
html_css_files = ['../_static/custom.css']
html_logo = '../_static/SSEC_logo_vert_white_lg_1184x661.png'
html_title = f'{project} {release}'
html_theme_options = {}
if html_theme == 'sphinx_book_theme':
    html_theme_options.update({
        'logo': {
            'image_light': '../_static/SSEC_logo_horiz_blue_1152x263.png',
            'image_dark': '../_static/SSEC_logo_vert_white_lg_1184x661.png',
            'text': f'{html_title}',
        },
        'repository_url': 'https://github.com/rispadd/biospecdb',
        'use_repository_button': True,
    })


# -- Options for EPUB output
epub_show_urls = 'footnote'

# -- Optiosn for autosummary

autosummary_generate = True
autodoc_inherit_docstrings = True
