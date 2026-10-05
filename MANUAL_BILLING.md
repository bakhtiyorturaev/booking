# Platforma to‘lovi

## Bepul va pullik rejim

Xodim panelida **Filiallar va zonalar**, **Sartaroshlar** yoki **To‘lovlar → Filiallar / Sartaroshlar** ro‘yxatidagi **Bepul** checkboxi bilan har bir obyekt alohida boshqariladi. Yangi filial va sartarosh bepul holatda yaratiladi. Uni faqat platforma xodimi o‘zgartiradi; xizmat egasi holatni ko‘radi.

Checkbox yoqilgan filial/sartarosh uchun platforma to‘lovi talab qilinmaydi. O‘chirilganda shu obyekt to‘langan muddatga ko‘ra yangi bron qabul qiladi. Global tugma va umumiy imtiyozli muddat endi qo‘llanmaydi. Bepul rejimni yoqish/o‘chirish eski to‘lovlar yoki muddatlarni o‘zgartirmaydi va moliyaviy yozuv yaratmaydi. Kabinet ochiq qoladi; mavjud bronlar bekor qilinmaydi.

Filiallar bepul/pullik holati alohida, lekin tarif va to‘langan muddat avvalgidek muassasa hisobida yuritiladi. Bir muassasaning pullik filiallari shu muddatdan foydalanadi; bepul filialga uning tugashi ta’sir qilmaydi. Har bir sartaroshning to‘langan muddati alohida. Biriktirilgan sartarosh uchun uning o‘z holati va tegishli filial holati tekshiriladi: bepul filial sartaroshning o‘z pullik hisobini bekor qilmaydi va aksincha.

## Xodimning ishi

1. **Mijozlar → Mijoz qo‘shish**: CLIENT akkaunti, telefon va parol.
2. **Muassasalar → Muassasa qo‘shish**: egasi, xizmat turi va hisob-kitob hududi.
3. **Sartaroshlar → Sartarosh qo‘shish**: akkaunt va sartaroshxona/filial; mustaqil sartarosh uchun hudud.
4. Pullik obyekt uchun **To‘lovlar → To‘lov kiritish**: muassasa yoki sartarosh, summa (so‘m), naqd/karta va ixtiyoriy izoh.

Har bir muassasa va har bir sartarosh alohida hisoblanadi. Sartaroshxonaga biriktirilgan sartarosh uchun ham alohida to‘lov kerak. Bunday sartaroshning o‘zi yoki uning filiali pullik bo‘lsa, tegishli to‘langan muddat amalda bo‘lishi kerak.

`Qo‘shilgan muddat = summa / 30 kunlik narx × 30 kun`. Summalar bazada tiyin bilan saqlanadi; muddat butun kunlargacha qisqartirilmaydi. Erta to‘lov amaldagi muddatning oxiridan, tugagan muddat esa to‘lov kiritilgan vaqtdan davom etadi. Tarif o‘zgarishi mavjud muddatni yoki tarixiy narxni o‘zgartirmaydi.

To‘lovni faqat xodim kiritadi; kim qabul qilgani sessiyadan olinadi. UUID `idempotency_key` takroriy so‘rovda muddatni qayta qo‘shmaydi; shu kalit bilan o‘zgartirilgan so‘rov 409 qaytaradi. To‘lov tarixi API va Django admin orqali tahrirlanmaydi yoki o‘chirilmaydi. Birinchi muassasa to‘lovi DRAFT/PENDING muassasani ACTIVE qiladi.

CLIENT o‘z obyektlarining to‘lov holatini ko‘radi. Sartarosh va sartaroshxona egasi kabinetda ish vaqti, hafta kunlari va ish holatini tahrirlaydi. Oxirgi 5 kun sariq, oxirgi 1 kun va tugagan muddat qizil; holat har daqiqada yangilanadi. Bepul rejimda to‘lov ogohlantirishlari ko‘rsatilmaydi.

## Tariflar

Superuser Django admin → **Hudud va xizmat tariflari** orqali xizmat turi, shahar/tuman va 30 kunlik narxni so‘mda belgilaydi. Tuman → shahar → barcha hududlar tartibida eng mos qoida olinadi. Sartarosh uchun xizmat turi `BARBER`; uning hududi alohida belgilangan joydan yoki filialidan olinadi. Qoida bo‘lmasa to‘lov kiritilmaydi. Xodimlar tarifni o‘zgartira olmaydi.

Muassasa uchun bitta xizmat turi va hisob-kitob hududi tanlanadi; filiallar soni narxni ko‘paytirmaydi. Xizmat katalogi Django admin’dan kengaytiriladi. Bron mijozining shaxsiy pulli obunasi talab qilinmaydi; eski consumer Payment/Subscription endpointlari yangi platforma hisobidan mustaqil.

API: `/api/v1/cabinet/branch-billing/`, `venue-billing/`, `barber-billing/`, `venue-payments/`, `venue-payments/summary/`. To‘lov so‘rovida `club` yoki `barber` UUID’laridan faqat bittasi, `amount` so‘m bilan decimal satr, `method` CASH/CARD yuboriladi. Javob summalari tiyin bilan.

Yangilash: `.venv/bin/python manage.py migrate` va `.venv/bin/python manage.py seed_system_messages`.

Checkbox API: `POST /api/v1/cabinet/branch-billing/<uuid>/free-mode/` yoki `barber-billing/<uuid>/free-mode/`, body: `{"is_free": true}`. Faqat xodimga ruxsat beriladi.
