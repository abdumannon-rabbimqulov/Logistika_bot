"""Pytest sozlamalari.

SQLAlchemy relationshiplari satr nomlari bilan bog'langan (`relationship("User")`),
shuning uchun bitta modelni ishlatishdan oldin registrdagi BARCHA modul import
qilingan bo'lishi kerak — aks holda mapper "failed to locate a name ('User')"
xatosi bilan yiqiladi. Loyihada bu odatda `config/main.py` orqali sodir bo'ladi;
testlarda esa shu yerda qilinadi.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Admin_panel.models  # noqa: F401,E402
import driver.models  # noqa: F401,E402
import order.dispatch_models  # noqa: F401,E402
import order.models  # noqa: F401,E402
import users.models  # noqa: F401,E402
