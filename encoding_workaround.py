"""
On systems that don't have utf8 configured as default, this script will
need to be executed to force the generation of correct tab files.
"""

import codecs
from functools import partial
from ply import lex
from calmjs.parse import es5

lex.open = partial(codecs.open, encoding='utf8')
es5('')
