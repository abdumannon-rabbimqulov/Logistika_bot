"""Admin panel uchun kirish tekshiruvi.

Mantiq `users/permissions.py` ga ko'chirildi — barcha rol qoidalari bitta joyda
turishi uchun. Bu yerdagi `is_admin` nomi saqlanadi, chunki unga `Admin_panel/router.py`
(barcha `/system` endpointlari) va `driver/router.py` (truck turi CRUD) tayanadi.

MUHIM: bu tekshiruv MANAGER rolini ATAYLAB o'tkazmaydi. `/system` ostida balans
to'g'rilash, komissiya va narx sozlamalari bor — menejer moliyaga umuman
tegmasligi kerak. Menejer uchun ruxsat etilgan amallar `/manager` da.

Bir xulq qattiqlashtirildi: ilgari bu yerda `get_current_user` ishlatilardi, ya'ni
banlangan/nofaol adminning eski tokeni hamon `/system` ga kirardi (login uni to'sardi,
lekin qo'lda olingan token to'silmasdi). Endi `get_current_active_user` orqali —
ban qo'yilgan zahoti admin huquqi ham amalda to'xtaydi.
"""

from fastapi import Depends

from users.models import User
from users.permissions import get_current_admin_user, is_admin_user

__all__ = ["is_admin", "is_admin_user"]


async def is_admin(current_user: User = Depends(get_current_admin_user)) -> User:
    return current_user
