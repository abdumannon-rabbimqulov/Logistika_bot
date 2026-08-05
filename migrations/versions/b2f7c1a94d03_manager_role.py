"""Manager va dispatcher rollarini PostgreSQL `userrole` enum tipiga qo'shish

Muammo: `users/models.py` dagi `UserRole` enum'ida `MANAGER` va `DISPATCHER`
qiymatlari ancha vaqtdan beri turibdi, lekin ularni bazaga qo'shadigan migratsiya
hech qachon yozilmagan. Natijada `userrole` tipi faqat eski qiymatlarni biladi va
foydalanuvchiga menejer rolini bermoqchi bo'lgan `UPDATE users SET role='manager'`
`invalid input value for enum userrole` xatosi bilan yiqiladi.

(Ilova birinchi ishga tushishida `Base.metadata.create_all` tipni to'liq ro'yxat
bilan yaratganda muammo sezilmasligi mumkin — shuning uchun `IF NOT EXISTS`.)

`ALTER TYPE ... ADD VALUE` PostgreSQL 12 gacha tranzaksiya ichida bajarilmaydi va
12+ da ham o'sha tranzaksiyada darhol ishlatib bo'lmaydi, shuning uchun
`autocommit_block()` ichida bajariladi.

`downgrade` bo'sh: PostgreSQL enum'dan qiymatni olib tashlash imkoniyati yo'q
(tipni qayta yaratib, unga tayangan barcha ustunlarni ko'chirish kerak bo'lardi —
rolni orqaga qaytarish uchun bu juda qimmat va xavfli).

Revision ID: b2f7c1a94d03
Revises: a7c4e91b2d10
Create Date: 2026-08-04

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b2f7c1a94d03"
down_revision: Union[str, Sequence[str], None] = "a7c4e91b2d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW_ROLES = ("manager", "dispatcher")


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for value in NEW_ROLES:
            op.execute(f"ALTER TYPE userrole ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # PostgreSQL enum qiymatini o'chirib bo'lmaydi — qarang: yuqoridagi izoh.
    pass
