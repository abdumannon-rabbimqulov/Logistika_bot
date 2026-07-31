"""Bitta so'rovdagi BARCHA qoida buzilishlarini yig'ib qaytarish uchun umumiy turlar.

Nima uchun kerak: ilgari tekshiruvlar ketma-ket ishlab, birinchi muammoda darhol
`raise` qilardi. Foydalanuvchi bitta sababni ko'rib, uni tuzatib qayta yuborardi va
keyingi sabab chiqardi — bir necha marta urinishga to'g'ri kelardi. Endi tekshiruvlar
`Violation` qaytaradi, chaqiruvchi ularni ro'yxat qilib yig'adi va hammasini birdan
javobga soladi.

Modul ataylab ALOHIDA va hech narsaga bog'liq emas: `order_flow` `geofence` ni import
qiladi, shuning uchun umumiy turni ulardan birida saqlash aylanma importga olib kelardi.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Violation:
    """Bitta buzilgan qoida: kod, o'qiladigan sabab va aniq raqamlar.

    `code` — mashina uchun (frontend shunga qarab amal taklif qiladi, masalan
    `WRONG_WAYPOINT` da "kerakli nuqtaga o'tish" tugmasini ko'rsatadi).
    `message` — foydalanuvchiga ko'rsatiladigan o'zbekcha matn.
    `context` — sababni aniq qiladigan qiymatlar (masofa, ruxsat etilgan radius,
    kutilayotgan nuqta ID si). Javobda `code`/`message` yoniga yoyib beriladi.
    """

    code: str
    message: str
    context: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, **self.context}


class WaypointProblem(Exception):
    """Marshrut nuqtasi qadamini bajarib bo'lmadi — bir yoki bir nechta sabab bilan.

    Router buni 422 ga aylantiradi: `detail = {"message": ..., "errors": [...]}`.
    """

    def __init__(self, violations: list[Violation]):
        self.violations = violations
        # Bitta satrga birlashtirilgan matn — eski klientlar va loglar uchun.
        # Har bir sabab tugal gap, shuning uchun ular nuqta bilan ajratiladi:
        # "; " ishlatilsa ".; " kabi qo'sh tinish belgisi chiqardi.
        super().__init__(" ".join(v.message.rstrip() for v in violations))

    @property
    def message(self) -> str:
        return str(self)

    def as_detail(self) -> dict:
        return {"message": self.message, "errors": [v.as_dict() for v in self.violations]}
