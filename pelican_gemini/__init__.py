
__title__ = 'pelican_gemini'
__version__ = '0.1.0'
__author__ = 'Kevin Houlihan'
__credits__ = ["Kevin Houlihan", ]
__maintainer__ = "Kevin Houlihan"
__email__ = "kevin@crimsoncookie.com"
__status__ = "Development"
__license__ = 'MIT'
__copyright__ = 'Copyright 2021'

from ._reader import register
from ._content import _patch_content
_patch_content()
del _patch_content
