from __future__ import annotations

import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from web_app import ImageSplitterHandler


class handler(ImageSplitterHandler):
    pass
