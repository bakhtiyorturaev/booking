"""Developer bot compatibility imports.

Sozlamalar modeli umumiy tizim sozlamasi bo‘lgani uchun ``core`` ilovasida
saqlanadi. Eski importlar buzilmasligi uchun shu yerda qayta eksport qilinadi.
"""

from apps.core.models import DeveloperBotSettings

__all__ = ("DeveloperBotSettings",)
