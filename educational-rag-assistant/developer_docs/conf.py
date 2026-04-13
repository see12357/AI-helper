import os
import sys
sys.path.insert(0, os.path.abspath('../'))

project = 'Educational RAG Assistant'
copyright = '2024, Developer'
author = 'Developer'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
