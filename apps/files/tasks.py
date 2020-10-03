import logging
import os

from nbconvert import HTMLExporter

logger = logging.getLogger(__file__)


def convert_ipynb_to_html(ipynb_src_path, html_dest_path):
    """
    Converts *.ipynb to html and saves the new file in the same directory with
    `html_ext` extension.
    """
    if not os.path.exists(html_dest_path):
        try:
            html_exporter = HTMLExporter()
            nb_node, _ = html_exporter.from_filename(ipynb_src_path)
            with open(html_dest_path, 'w') as f:
                f.write(nb_node)
            return True
        except (FileNotFoundError, AttributeError):
            return False
    return True
