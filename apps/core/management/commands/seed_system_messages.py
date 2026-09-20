from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import SystemMessage


SYSTEM_MESSAGES = [
    # Auth
    {
        "code": 'auth.admin_must_be_staff',
        "text_uz": 'Administrator uchun is_staff yoqilgan bo‘lishi kerak.',
        "text_ru": 'Для администратора параметр is_staff должен быть включён.',
        "text_en": 'is_staff must be enabled for an administrator.',
    },
    {
        "code": 'auth.admin_must_be_superuser',
        "text_uz": 'Administrator uchun is_superuser yoqilgan bo‘lishi kerak.',
        "text_ru": 'Для администратора параметр is_superuser должен быть включён.',
        "text_en": 'is_superuser must be enabled for an administrator.',
    },
    {
        "code": 'auth.authenticated_user_required',
        "text_uz": 'Telefonni o‘zgartirish uchun autentifikatsiyadan o‘tgan foydalanuvchi talab qilinadi.',
        "text_ru": 'Для изменения телефона требуется авторизованный пользователь.',
        "text_en": 'An authenticated user is required to change the phone number.',
    },
    {
        "code": 'auth.city_too_long',
        "text_uz": 'Shahar nomi 120 belgidan oshmasligi kerak.',
        "text_ru": 'Название города не должно превышать 120 символов.',
        "text_en": 'The city name must not exceed 120 characters.',
    },
    {
        "code": 'auth.current_password_invalid',
        "text_uz": 'Joriy parol noto‘g‘ri.',
        "text_ru": 'Текущий пароль неверен.',
        "text_en": 'The current password is incorrect.',
    },
    {
        "code": 'auth.device_name_too_long',
        "text_uz": 'Qurilma nomi 120 belgidan oshmasligi kerak.',
        "text_ru": 'Название устройства не должно превышать 120 символов.',
        "text_en": 'The device name must not exceed 120 characters.',
    },
    {
        "code": 'auth.email_already_registered',
        "text_uz": 'Bu email boshqa foydalanuvchiga tegishli.',
        "text_ru": 'Этот адрес электронной почты принадлежит другому пользователю.',
        "text_en": 'This email address belongs to another user.',
    },
    {
        "code": 'auth.email_or_phone_required',
        "text_uz": 'Email yoki telefon raqamidan birini kiriting.',
        "text_ru": 'Укажите адрес электронной почты или номер телефона.',
        "text_en": 'Enter either an email address or a phone number.',
    },
    {
        "code": 'auth.google_config_loaded',
        "text_uz": 'Google authentication sozlamasi olindi.',
        "text_ru": 'Настройки Google-аутентификации получены.',
        "text_en": 'Google authentication configuration loaded.',
    },
    {
        "code": 'auth.google_email_not_found',
        "text_uz": 'Google akkauntida email manzili topilmadi.',
        "text_ru": 'В аккаунте Google не найден адрес электронной почты.',
        "text_en": 'No email address was found in the Google account.',
    },
    {
        "code": 'auth.google_email_not_verified',
        "text_uz": 'Google email manzili tasdiqlanmagan.',
        "text_ru": 'Адрес электронной почты Google не подтверждён.',
        "text_en": 'The Google email address is not verified.',
    },
    {
        "code": 'auth.google_invalid_credential',
        "text_uz": 'Google orqali kirish ma’lumoti noto‘g‘ri yoki muddati tugagan.',
        "text_ru": 'Данные для входа через Google недействительны или устарели.',
        "text_en": 'The Google sign-in credential is invalid or expired.',
    },
    {
        "code": 'auth.google_login_success',
        "text_uz": 'Google orqali muvaffaqiyatli kirildi.',
        "text_ru": 'Вход через Google выполнен.',
        "text_en": 'Successfully signed in with Google.',
    },
    {
        "code": 'auth.google_temporarily_unavailable',
        "text_uz": 'Google orqali kirish vaqtincha ishlamayapti.',
        "text_ru": 'Вход через Google временно недоступен.',
        "text_en": 'Google sign-in is temporarily unavailable.',
    },
    {
        "code": 'auth.google_user_id_not_found',
        "text_uz": 'Google foydalanuvchi identifikatori topilmadi.',
        "text_ru": 'Идентификатор пользователя Google не найден.',
        "text_en": 'The Google user identifier was not found.',
    },
    {
        "code": 'auth.invalid_birth_date',
        "text_uz": 'Tug‘ilgan sana noto‘g‘ri.',
        "text_ru": 'Некорректная дата рождения.',
        "text_en": 'The date of birth is invalid.',
    },
    {
        "code": 'auth.invalid_credentials',
        "text_uz": 'Telefon raqami yoki parol noto‘g‘ri.',
        "text_ru": 'Неверный номер телефона или пароль.',
        "text_en": 'The phone number or password is incorrect.',
    },
    {
        "code": 'auth.invalid_email_format',
        "text_uz": 'Email manzili noto‘g‘ri formatda.',
        "text_ru": 'Неверный формат адреса электронной почты.',
        "text_en": 'Invalid email address format.',
    },
    {
        "code": 'auth.invalid_phone_format',
        "text_uz": 'Telefon raqami noto‘g‘ri formatda.',
        "text_ru": 'Неверный формат номера телефона.',
        "text_en": 'Invalid phone number format.',
    },
    {
        "code": 'auth.invalid_username_format',
        "text_uz": 'Username 3–30 ta harf, raqam yoki pastki chiziqdan iborat bo‘lishi kerak.',
        "text_ru": 'Имя пользователя должно содержать от 3 до 30 букв, цифр или символов подчёркивания.',
        "text_en": 'Username must contain 3–30 letters, numbers, or underscores.',
    },
    {
        "code": 'auth.login_success',
        "text_uz": 'Tizimga muvaffaqiyatli kirildi.',
        "text_ru": 'Вход выполнен успешно.',
        "text_en": 'Signed in successfully.',
    },
    {
        "code": 'auth.logout_success',
        "text_uz": 'Tizimdan muvaffaqiyatli chiqildi.',
        "text_ru": 'Вы успешно вышли из системы.',
        "text_en": 'Successfully signed out.',
    },
    {
        "code": 'auth.name_too_long',
        "text_uz": 'Ism 150 belgidan oshmasligi kerak.',
        "text_ru": 'Имя не должно превышать 150 символов.',
        "text_en": 'The name must not exceed 150 characters.',
    },
    {
        "code": 'auth.otp_4_digits_required',
        "text_uz": '4 xonali OTP kodni kiriting.',
        "text_ru": 'Введите четырёхзначный OTP-код.',
        "text_en": 'Enter the 4-digit OTP code.',
    },
    {
        "code": 'auth.otp_already_used',
        "text_uz": 'Ushbu OTP kod avval ishlatilgan.',
        "text_ru": 'Этот OTP-код уже был использован.',
        "text_en": 'This OTP code has already been used.',
    },
    {
        "code": 'auth.otp_attempts_exceeded',
        "text_uz": 'OTP tekshirish urinishlari soni oshib ketdi.',
        "text_ru": 'Превышено количество попыток проверки OTP.',
        "text_en": 'The maximum number of OTP verification attempts has been exceeded.',
    },
    {
        "code": 'auth.otp_expired',
        "text_uz": 'OTP kodning amal qilish muddati tugagan.',
        "text_ru": 'Срок действия OTP-кода истёк.',
        "text_en": 'The OTP code has expired.',
    },
    {
        "code": 'auth.otp_invalid',
        "text_uz": 'OTP kod noto‘g‘ri.',
        "text_ru": 'Неверный OTP-код.',
        "text_en": 'Invalid OTP code.',
    },
    {
        "code": 'auth.otp_not_found',
        "text_uz": 'OTP so‘rovi topilmadi.',
        "text_ru": 'Запрос OTP не найден.',
        "text_en": 'OTP request was not found.',
    },
    {
        "code": 'auth.otp_purpose_invalid',
        "text_uz": 'OTP so‘rovining maqsadi noto‘g‘ri.',
        "text_ru": 'Неверное назначение запроса OTP.',
        "text_en": 'Invalid OTP request purpose.',
    },
    {
        "code": 'auth.otp_purpose_mismatch',
        "text_uz": 'OTP ushbu amal uchun yaratilmagan.',
        "text_ru": 'OTP-код не предназначен для этой операции.',
        "text_en": 'The OTP code was not created for this operation.',
    },
    {
        "code": 'auth.otp_resend_cooldown',
        "text_uz": 'OTP kodni qayta yuborish uchun biroz kuting.',
        "text_ru": 'Подождите перед повторной отправкой OTP-кода.',
        "text_en": 'Wait before requesting another OTP code.',
    },
    {
        "code": 'auth.otp_send_failed',
        "text_uz": 'OTP yuborishda xatolik yuz berdi.',
        "text_ru": 'Произошла ошибка при отправке OTP-кода.',
        "text_en": 'An error occurred while sending the OTP code.',
    },
    {
        "code": 'auth.otp_sent',
        "text_uz": 'OTP kod yuborildi.',
        "text_ru": 'OTP-код отправлен.',
        "text_en": 'The OTP code has been sent.',
    },
    {
        "code": 'auth.password_insecure',
        "text_uz": 'Parol xavfsizlik talablariga javob bermaydi.',
        "text_ru": 'Пароль не соответствует требованиям безопасности.',
        "text_en": 'The password does not meet the security requirements.',
    },
    {
        "code": 'auth.password_required',
        "text_uz": 'Parolni kiriting.',
        "text_ru": 'Введите пароль.',
        "text_en": 'Enter a password.',
    },
    {
        "code": 'auth.password_reset_success',
        "text_uz": 'Parol muvaffaqiyatli tiklandi.',
        "text_ru": 'Пароль успешно восстановлен.',
        "text_en": 'The password was reset successfully.',
    },
    {
        "code": 'auth.password_saved_success',
        "text_uz": 'Parol muvaffaqiyatli saqlandi.',
        "text_ru": 'Пароль успешно сохранён.',
        "text_en": 'The password was saved successfully.',
    },
    {
        "code": 'auth.phone_already_exists',
        "text_uz": 'Bu telefon raqami bilan akkaunt mavjud.',
        "text_ru": 'Аккаунт с этим номером телефона уже существует.',
        "text_en": 'An account with this phone number already exists.',
    },
    {
        "code": 'auth.phone_already_registered',
        "text_uz": 'Ushbu telefon raqami boshqa foydalanuvchiga tegishli.',
        "text_ru": 'Этот номер телефона принадлежит другому пользователю.',
        "text_en": 'This phone number belongs to another user.',
    },
    {
        "code": 'auth.phone_already_verified',
        "text_uz": 'Bu telefon raqami profilingizda allaqachon tasdiqlangan.',
        "text_ru": 'Этот номер телефона уже подтверждён в вашем профиле.',
        "text_en": 'This phone number is already verified in your profile.',
    },
    {
        "code": 'auth.phone_login_success',
        "text_uz": 'Telefon orqali muvaffaqiyatli kirildi.',
        "text_ru": 'Вход по номеру телефона выполнен.',
        "text_en": 'Successfully signed in by phone.',
    },
    {
        "code": 'auth.phone_required',
        "text_uz": 'Telefon raqamini kiriting.',
        "text_ru": 'Введите номер телефона.',
        "text_en": 'Enter a phone number.',
    },
    {
        "code": 'auth.phone_verified_create_password',
        "text_uz": 'Telefon raqami tasdiqlandi. Endi parol yarating.',
        "text_ru": 'Номер телефона подтверждён. Теперь создайте пароль.',
        "text_en": 'Phone number verified. Now create a password.',
    },
    {
        "code": 'auth.phone_verified_success',
        "text_uz": 'Telefon raqami muvaffaqiyatli tasdiqlandi.',
        "text_ru": 'Номер телефона успешно подтверждён.',
        "text_en": 'The phone number was verified successfully.',
    },
    {
        "code": 'auth.profile_updated_success',
        "text_uz": 'Profil muvaffaqiyatli yangilandi.',
        "text_ru": 'Профиль успешно обновлён.',
        "text_en": 'The profile was updated successfully.',
    },
    {
        "code": 'auth.refresh_token_missing',
        "text_uz": 'Refresh token kiritilmagan yoki noto‘g‘ri.',
        "text_ru": 'Refresh-токен отсутствует или недействителен.',
        "text_en": 'The refresh token is missing or invalid.',
    },
    {
        "code": 'auth.register_success',
        "text_uz": 'Ro‘yxatdan o‘tish yakunlandi.',
        "text_ru": 'Регистрация завершена.',
        "text_en": 'Registration completed successfully.',
    },
    {
        "code": 'auth.security_check_required',
        "text_uz": 'Xavfsizlik tekshiruvidan qayta o‘ting.',
        "text_ru": 'Повторите проверку безопасности.',
        "text_en": 'Complete the security check again.',
    },
    {
        "code": 'auth.session_expired',
        "text_uz": 'Session tugagan yoki bekor qilingan.',
        "text_ru": 'Сессия истекла или была отозвана.',
        "text_en": 'The session has expired or been revoked.',
    },
    {
        "code": 'auth.session_id_missing',
        "text_uz": 'Token ichida session identifikatori mavjud emas.',
        "text_ru": 'В токене отсутствует идентификатор сессии.',
        "text_en": 'The token does not contain a session identifier.',
    },
    {
        "code": 'auth.session_revoked_token_reused',
        "text_uz": 'Refresh token qayta ishlatilgani sababli session bekor qilindi.',
        "text_ru": 'Сессия отозвана из-за повторного использования refresh-токена.',
        "text_en": 'The session was revoked because the refresh token was reused.',
    },
    {
        "code": 'auth.telegram_data_invalid',
        "text_uz": 'Telegram tasdiqlash ma’lumoti yaroqsiz yoki eskirgan.',
        "text_ru": 'Данные подтверждения Telegram недействительны или устарели.',
        "text_en": 'Telegram verification data is invalid or expired.',
    },
    {
        "code": 'auth.telegram_not_configured',
        "text_uz": 'Telegram Login sozlanmagan.',
        "text_ru": 'Вход через Telegram не настроен.',
        "text_en": 'Telegram Login is not configured.',
    },
    {
        "code": 'auth.telegram_phone_already_linked',
        "text_uz": 'Bu telefon raqami boshqa akkauntga ulangan.',
        "text_ru": 'Этот номер телефона привязан к другому аккаунту.',
        "text_en": 'This phone number is linked to another account.',
    },
    {
        "code": 'auth.telegram_phone_permission_required',
        "text_uz": 'Telegram’da tasdiqlangan telefon raqamini ulashga ruxsat bering.',
        "text_ru": 'Разрешите доступ к подтверждённому номеру телефона в Telegram.',
        "text_en": 'Allow access to your verified Telegram phone number.',
    },
    {
        "code": 'auth.tokens_refreshed_success',
        "text_uz": 'Tokenlar muvaffaqiyatli yangilandi.',
        "text_ru": 'Токены успешно обновлены.',
        "text_en": 'The tokens were refreshed successfully.',
    },
    {
        "code": 'auth.unauthorized',
        "text_uz": 'Bu amal uchun tizimga kirish kerak.',
        "text_ru": 'Для выполнения этого действия необходимо войти в систему.',
        "text_en": 'Authentication is required for this action.',
    },
    {
        "code": 'auth.user_blocked',
        "text_uz": 'Foydalanuvchi bloklangan.',
        "text_ru": 'Пользователь заблокирован.',
        "text_en": 'The user is blocked.',
    },
    {
        "code": 'auth.user_deleted',
        "text_uz": 'Foydalanuvchi o‘chirilgan.',
        "text_ru": 'Пользователь удалён.',
        "text_en": 'The user has been deleted.',
    },
    {
        "code": 'auth.user_inactive',
        "text_uz": 'Foydalanuvchi faol emas.',
        "text_ru": 'Пользователь неактивен.',
        "text_en": 'The user is inactive.',
    },
    {
        "code": 'auth.user_not_found',
        "text_uz": 'Bu telefon raqami bilan foydalanuvchi topilmadi.',
        "text_ru": 'Пользователь с этим номером телефона не найден.',
        "text_en": 'No user was found with this phone number.',
    },
    {
        "code": 'auth.username_required',
        "text_uz": 'Username kiritilishi shart.',
        "text_ru": 'Необходимо указать имя пользователя.',
        "text_en": 'Username is required.',
    },
    # Bookings
    {
        "code": 'bookings.active_booking_exists',
        "text_uz": 'Sizda allaqachon faol bron yoki hold mavjud.',
        "text_ru": 'У вас уже есть активное бронирование или удержание.',
        "text_en": 'You already have an active booking or hold.',
    },
    {
        "code": 'bookings.cancel_too_late',
        "text_uz": 'Bronni boshlanishidan kamida bir soat oldin bekor qilish mumkin.',
        "text_ru": 'Бронирование можно отменить не позднее чем за час до начала.',
        "text_en": 'The booking can be cancelled at least one hour before it starts.',
    },
    {
        "code": 'bookings.checkin_before_start_time',
        "text_uz": 'Bron boshlanish vaqtidan oldin check-in qilib bo‘lmaydi.',
        "text_ru": 'Нельзя выполнить check-in до начала бронирования.',
        "text_en": 'A booking cannot be checked in before its start time.',
    },
    {
        "code": 'bookings.date_outside_advance_limit',
        "text_uz": 'Tanlangan sana oldindan bron qilish chegarasidan tashqarida.',
        "text_ru": 'Выбранная дата выходит за предел предварительного бронирования.',
        "text_en": 'The selected date is outside the advance booking limit.',
    },
    {
        "code": 'bookings.duration_invalid_for_branch',
        "text_uz": 'Bron davomiyligi filial qoidalariga mos emas.',
        "text_ru": 'Продолжительность бронирования не соответствует правилам филиала.',
        "text_en": 'The booking duration does not match the branch rules.',
    },
    {
        "code": 'bookings.duration_must_be_integer',
        "text_uz": 'Bron davomiyligi butun son bo‘lishi kerak.',
        "text_ru": 'Продолжительность бронирования должна быть целым числом.',
        "text_en": 'The booking duration must be an integer.',
    },
    {
        "code": 'bookings.duration_not_slot_aligned',
        "text_uz": 'Bron davomiyligi vaqt qadamiga mos emas.',
        "text_ru": 'Продолжительность бронирования не соответствует шагу времени.',
        "text_en": 'The booking duration does not match the time interval.',
    },
    {
        "code": 'bookings.duration_out_of_range',
        "text_uz": 'Bron davomiyligi ruxsat etilgan oraliqda emas.',
        "text_ru": 'Продолжительность бронирования вне допустимого диапазона.',
        "text_en": 'The booking duration is outside the allowed range.',
    },
    {
        "code": 'bookings.end_time_before_start_time',
        "text_uz": 'Tugash vaqti boshlanish vaqtidan keyin bo‘lishi kerak.',
        "text_ru": 'Время окончания должно быть позже времени начала.',
        "text_en": 'The end time must be later than the start time.',
    },
    {
        "code": 'bookings.hold_expired_or_used',
        "text_uz": 'Hold muddati tugagan yoki avval ishlatilgan.',
        "text_ru": 'Срок удержания истёк или оно уже было использовано.',
        "text_en": 'The hold has expired or was already used.',
    },
    {
        "code": 'bookings.id_invalid',
        "text_uz": 'Bron identifikatori noto‘g‘ri yoki yuborilmagan.',
        "text_ru": 'Идентификатор бронирования неверен или отсутствует.',
        "text_en": 'The booking identifier is invalid or missing.',
    },
    {
        "code": 'bookings.insufficient_seats',
        "text_uz": 'Tanlangan vaqtda yetarli bo‘sh joy qolmagan.',
        "text_ru": 'На выбранное время недостаточно свободных мест.',
        "text_en": 'There are not enough available places at the selected time.',
    },
    {
        "code": 'bookings.invalid_data',
        "text_uz": 'Yuborilgan bron ma’lumotlari noto‘g‘ri.',
        "text_ru": 'Переданные данные бронирования недействительны.',
        "text_en": 'The submitted booking data is invalid.',
    },
    {
        "code": 'bookings.invalid_date_format',
        "text_uz": 'Sanani YYYY-MM-DD formatida yuboring.',
        "text_ru": 'Передайте дату в формате YYYY-MM-DD.',
        "text_en": 'Provide the date in YYYY-MM-DD format.',
    },
    {
        "code": 'bookings.invalid_filter',
        "text_uz": 'Bron filtri noto‘g‘ri.',
        "text_ru": 'Неверный фильтр бронирований.',
        "text_en": 'The booking filter is invalid.',
    },
    {
        "code": 'bookings.invalid_quantity',
        "text_uz": 'Tanlangan joylar soni noto‘g‘ri.',
        "text_ru": 'Неверное количество выбранных мест.',
        "text_en": 'The selected quantity is invalid.',
    },
    {
        "code": 'bookings.invalid_status_transition',
        "text_uz": 'Bronni ushbu holatga o‘tkazish mumkin emas.',
        "text_ru": 'Бронирование нельзя перевести в этот статус.',
        "text_en": 'The booking cannot transition to this status.',
    },
    {
        "code": 'bookings.invalid_time_range',
        "text_uz": 'Bron boshlanish yoki tugash vaqti noto‘g‘ri.',
        "text_ru": 'Неверное время начала или окончания бронирования.',
        "text_en": 'The booking start or end time is invalid.',
    },
    {
        "code": 'bookings.noshow_grace_period_not_passed',
        "text_uz": 'No-show kutish vaqti hali tugamagan.',
        "text_ru": 'Период ожидания для no-show ещё не истёк.',
        "text_en": 'The no-show grace period has not elapsed.',
    },
    {
        "code": 'bookings.not_found',
        "text_uz": 'So‘ralgan bron ma’lumoti topilmadi.',
        "text_ru": 'Запрошенные данные бронирования не найдены.',
        "text_en": 'The requested booking resource was not found.',
    },
    {
        "code": 'bookings.number_immutable',
        "text_uz": 'Booking raqamini o‘zgartirib bo‘lmaydi.',
        "text_ru": 'Номер бронирования нельзя изменить.',
        "text_en": 'The booking number cannot be changed.',
    },
    {
        "code": 'bookings.only_confirmed_can_cancel',
        "text_uz": 'Faqat tasdiqlangan bronni bekor qilish mumkin.',
        "text_ru": 'Отменить можно только подтверждённое бронирование.',
        "text_en": 'Only a confirmed booking can be cancelled.',
    },
    {
        "code": 'bookings.outside_working_hours',
        "text_uz": 'Tanlangan vaqt filial ish vaqtidan tashqarida.',
        "text_ru": 'Выбранное время находится вне часов работы филиала.',
        "text_en": 'The selected time is outside the branch working hours.',
    },
    {
        "code": 'bookings.permission_denied',
        "text_uz": 'Bu bron ma’lumotlarini ko‘rish yoki o‘zgartirishga ruxsatingiz yo‘q.',
        "text_ru": 'У вас нет прав на просмотр или изменение этого бронирования.',
        "text_en": 'You do not have permission to view or change this booking.',
    },
    {
        "code": 'bookings.quantity_exceeds_capacity',
        "text_uz": 'Tanlangan joylar soni zona sig‘imidan katta.',
        "text_ru": 'Количество выбранных мест превышает вместимость зоны.',
        "text_en": 'The selected quantity exceeds the zone capacity.',
    },
    {
        "code": 'bookings.start_not_slot_aligned',
        "text_uz": 'Bron boshlanish vaqti vaqt qadamiga mos emas.',
        "text_ru": 'Время начала бронирования не соответствует шагу времени.',
        "text_en": 'The booking start time does not match the time interval.',
    },
    {
        "code": 'bookings.zone_closed_at_time',
        "text_uz": 'Tanlangan vaqtda zona vaqtincha yopilgan.',
        "text_ru": 'Зона временно закрыта в выбранное время.',
        "text_en": 'The zone is temporarily closed at the selected time.',
    },
    {
        "code": 'bookings.zone_not_available',
        "text_uz": 'Zona hozir bron qilish uchun faol emas.',
        "text_ru": 'Зона сейчас недоступна для бронирования.',
        "text_en": 'The zone is not currently available for booking.',
    },
    # Clubs
    {
        "code": 'clubs.above_maximum',
        "text_uz": 'Qiymat ruxsat etilgan maksimumdan katta.',
        "text_ru": 'Значение превышает допустимый максимум.',
        "text_en": 'The value exceeds the allowed maximum.',
    },
    {
        "code": 'clubs.active_city_only',
        "text_uz": 'Faqat faol shaharni tanlash mumkin.',
        "text_ru": 'Можно выбрать только активный город.',
        "text_en": 'Only an active city can be selected.',
    },
    {
        "code": 'clubs.active_club_only_favorites',
        "text_uz": 'Faqat faol klubni sevimlilarga qo‘shish mumkin.',
        "text_ru": 'В избранное можно добавить только активный клуб.',
        "text_en": 'Only an active club can be added to favorites.',
    },
    {
        "code": 'clubs.active_district_only',
        "text_uz": 'Faqat faol tumanni tanlash mumkin.',
        "text_ru": 'Можно выбрать только активный район.',
        "text_en": 'Only an active district can be selected.',
    },
    {
        "code": 'clubs.active_user_only_staff',
        "text_uz": 'Faqat faol foydalanuvchini klub xodimi qilish mumkin.',
        "text_ru": 'Сотрудником клуба можно назначить только активного пользователя.',
        "text_en": 'Only an active user can be assigned as club staff.',
    },
    {
        "code": 'clubs.admin_only_status_change',
        "text_uz": 'Klubni faollashtirish yoki bloklash faqat administratorga ruxsat etilgan.',
        "text_ru": 'Активировать или приостанавливать клуб может только администратор.',
        "text_en": 'Only an administrator may activate or suspend a club.',
    },
    {
        "code": 'clubs.below_minimum',
        "text_uz": 'Qiymat ruxsat etilgan minimumdan kichik.',
        "text_ru": 'Значение меньше допустимого минимума.',
        "text_en": 'The value is below the allowed minimum.',
    },
    {
        "code": 'clubs.branch_not_belong_to_club',
        "text_uz": 'Filial tanlangan klubga tegishli emas.',
        "text_ru": 'Филиал не принадлежит выбранному клубу.',
        "text_en": 'The branch does not belong to the selected club.',
    },
    {
        "code": 'clubs.distance_filter_requires_coords',
        "text_uz": 'Masofa bo‘yicha filtrlash uchun latitude va longitude kerak.',
        "text_ru": 'Для фильтрации по расстоянию требуются широта и долгота.',
        "text_en": 'Latitude and longitude are required for distance filtering.',
    },
    {
        "code": 'clubs.distance_ordering_requires_coords',
        "text_uz": 'Masofa bo‘yicha saralash uchun latitude va longitude kerak.',
        "text_ru": 'Для сортировки по расстоянию требуются широта и долгота.',
        "text_en": 'Latitude and longitude are required for distance ordering.',
    },
    {
        "code": 'clubs.district_not_belong_to_city',
        "text_uz": 'Tanlangan tuman tanlangan shaharga tegishli emas.',
        "text_ru": 'Выбранный район не относится к выбранному городу.',
        "text_en": 'The selected district does not belong to the selected city.',
    },
    {
        "code": 'clubs.end_time_before_start_time',
        "text_uz": 'Tugash vaqti boshlanish vaqtidan keyin bo‘lishi kerak.',
        "text_ru": 'Время окончания должно быть позже времени начала.',
        "text_en": 'The end time must be later than the start time.',
    },
    {
        "code": 'clubs.image_size_exceeded',
        "text_uz": 'Rasm hajmi 5 MBdan oshmasligi kerak.',
        "text_ru": 'Размер изображения не должен превышать 5 МБ.',
        "text_en": 'The image size must not exceed 5 MB.',
    },
    {
        "code": 'clubs.invalid_data',
        "text_uz": 'Yuborilgan klub ma’lumotlari noto‘g‘ri.',
        "text_ru": 'Переданные данные клуба недействительны.',
        "text_en": 'The submitted club data is invalid.',
    },
    {
        "code": 'clubs.invalid_image_format',
        "text_uz": 'Faqat JPG, PNG yoki WEBP formatidagi rasmni yuklang.',
        "text_ru": 'Загрузите изображение только в формате JPG, PNG или WEBP.',
        "text_en": 'Upload an image in JPG, PNG, or WEBP format only.',
    },
    {
        "code": 'clubs.invalid_integer',
        "text_uz": 'Qiymat butun son bo‘lishi kerak.',
        "text_ru": 'Значение должно быть целым числом.',
        "text_en": 'The value must be an integer.',
    },
    {
        "code": 'clubs.invalid_ordering',
        "text_uz": 'Saralash qiymati qo‘llab-quvvatlanmaydi.',
        "text_ru": 'Указанный вариант сортировки не поддерживается.',
        "text_en": 'The requested ordering value is not supported.',
    },
    {
        "code": 'clubs.invalid_service_type',
        "text_uz": 'Xizmat turi COMPUTER yoki PLAYSTATION bo‘lishi kerak.',
        "text_ru": 'Тип услуги должен быть COMPUTER или PLAYSTATION.',
        "text_en": 'The service type must be COMPUTER or PLAYSTATION.',
    },
    {
        "code": 'clubs.invalid_weekdays',
        "text_uz": 'Hafta kunlari 0 dan 6 gacha bo‘lgan sonlar bilan berilishi kerak.',
        "text_ru": 'Дни недели должны быть числами от 0 до 6.',
        "text_en": 'Weekdays must be integers from 0 to 6.',
    },
    {
        "code": 'clubs.lat_lng_both_required',
        "text_uz": 'Latitude va longitude birga yuborilishi kerak.',
        "text_ru": 'Широта и долгота должны быть переданы вместе.',
        "text_en": 'Latitude and longitude must be provided together.',
    },
    {
        "code": 'clubs.max_duration_less_than_min',
        "text_uz": 'Maksimal bron vaqti minimal bron vaqtidan kam bo‘lmasligi kerak.',
        "text_ru": 'Максимальная длительность брони не может быть меньше минимальной.',
        "text_en": 'The maximum booking duration must not be less than the minimum.',
    },
    {
        "code": 'clubs.min_duration_not_divisible_by_interval',
        "text_uz": 'Minimal bron vaqti vaqt qadamiga qoldiqsiz bo‘linishi kerak.',
        "text_ru": 'Минимальная длительность брони должна делиться на шаг времени без остатка.',
        "text_en": 'The minimum booking duration must be divisible by the slot interval.',
    },
    {
        "code": 'clubs.min_price_greater_than_max',
        "text_uz": 'Minimal narx maksimal narxdan katta bo‘lishi mumkin emas.',
        "text_ru": 'Минимальная цена не может превышать максимальную.',
        "text_en": 'The minimum price cannot exceed the maximum price.',
    },
    {
        "code": 'clubs.not_found',
        "text_uz": 'So‘ralgan klub ma’lumoti topilmadi.',
        "text_ru": 'Запрошенные данные клуба не найдены.',
        "text_en": 'The requested club resource was not found.',
    },
    {
        "code": 'clubs.open_hours_required',
        "text_uz": 'Ochiq ish kuni uchun ochilish va yopilish vaqti kerak.',
        "text_ru": 'Для рабочего дня необходимо указать время открытия и закрытия.',
        "text_en": 'Opening and closing times are required for an open day.',
    },
    {
        "code": 'clubs.owner_manager_admin_only',
        "text_uz": 'Bu amal faqat klub egasi, menejeri yoki administrator uchun.',
        "text_ru": 'Это действие доступно только владельцу, менеджеру клуба или администратору.',
        "text_en": 'This action is available only to a club owner, manager, or administrator.',
    },
    {
        "code": 'clubs.permission_denied',
        "text_uz": 'Bu klub resurslarini boshqarish uchun ruxsatingiz yo‘q.',
        "text_ru": 'У вас нет прав для управления ресурсами этого клуба.',
        "text_en": "You do not have permission to manage this club's resources.",
    },
    {
        "code": 'clubs.special_open_hours_required',
        "text_uz": 'Maxsus ochiq kun uchun ochilish va yopilish vaqti kerak.',
        "text_ru": 'Для специального рабочего дня необходимо указать время открытия и закрытия.',
        "text_en": 'Opening and closing times are required for an open special day.',
    },
    # Common
    {
        "code": 'common.error',
        "text_uz": 'Xatolik yuz berdi.',
        "text_ru": 'Произошла ошибка.',
        "text_en": 'An error occurred.',
    },
    {
        "code": 'common.success',
        "text_uz": 'Operatsiya muvaffaqiyatli bajarildi.',
        "text_ru": 'Операция успешно выполнена.',
        "text_en": 'Operation completed successfully.',
    },
    {
        "code": 'common.unknown_error',
        "text_uz": 'Noma’lum xatolik yuz berdi.',
        "text_ru": 'Произошла неизвестная ошибка.',
        "text_en": 'An unknown error occurred.',
    },
    {
        "code": 'common.unsupported_language',
        "text_uz": 'Tanlangan til qo‘llab-quvvatlanmaydi.',
        "text_ru": 'Выбранный язык не поддерживается.',
        "text_en": 'The selected language is not supported.',
    },
    # Payments
    {
        "code": 'payments.active_paid_subscription_required',
        "text_uz": 'Bu amal uchun faol PAID obuna kerak.',
        "text_ru": 'Для этого действия требуется активная подписка PAID.',
        "text_en": 'An active PAID subscription is required for this action.',
    },
    {
        "code": 'payments.cannot_mark_paid',
        "text_uz": 'Bu to‘lovni to‘langan holatiga o‘tkazib bo‘lmaydi.',
        "text_ru": 'Этот платёж нельзя перевести в статус оплаченного.',
        "text_en": 'This payment cannot be marked as paid.',
    },
    {
        "code": 'payments.expiry_before_start',
        "text_uz": 'Obuna tugash vaqti boshlanish vaqtidan keyin bo‘lishi kerak.',
        "text_ru": 'Время окончания подписки должно быть позже времени начала.',
        "text_en": 'The subscription expiry must be later than its start time.',
    },
    {
        "code": 'payments.invalid_status',
        "text_uz": 'To‘lov holati noto‘g‘ri.',
        "text_ru": 'Некорректный статус платежа.',
        "text_en": 'The payment status is invalid.',
    },
    {
        "code": 'payments.invalid_webhook_signature',
        "text_uz": 'To‘lov webhook imzosi noto‘g‘ri.',
        "text_ru": 'Некорректная подпись платёжного webhook.',
        "text_en": 'The payment webhook signature is invalid.',
    },
    {
        "code": 'payments.plan_not_found',
        "text_uz": 'Tanlangan obuna tarifi topilmadi yoki faol emas.',
        "text_ru": 'Выбранный тариф подписки не найден или неактивен.',
        "text_en": 'The selected subscription plan was not found or is inactive.',
    },
    {
        "code": 'payments.provider_id_mismatch',
        "text_uz": 'To‘lov provayder identifikatori mos kelmadi.',
        "text_ru": 'Идентификатор платёжного провайдера не совпадает.',
        "text_en": 'The payment provider identifier does not match.',
    },
    {
        "code": 'payments.provider_invalid_response',
        "text_uz": 'To‘lov provayderi noto‘g‘ri javob qaytardi.',
        "text_ru": 'Платёжный провайдер вернул некорректный ответ.',
        "text_en": 'The payment provider returned an invalid response.',
    },
    {
        "code": 'payments.provider_not_configured',
        "text_uz": 'To‘lov provayderi sozlanmagan.',
        "text_ru": 'Платёжный провайдер не настроен.',
        "text_en": 'The payment provider is not configured.',
    },
    # Reviews
    {
        "code": 'reviews.already_submitted',
        "text_uz": 'Bu bron uchun sharh allaqachon yozilgan.',
        "text_ru": 'Для этого бронирования уже оставлен отзыв.',
        "text_en": 'A review has already been submitted for this booking.',
    },
    {
        "code": 'reviews.booking_immutable',
        "text_uz": 'Sharh biriktirilgan bronni o‘zgartirib bo‘lmaydi.',
        "text_ru": 'Нельзя изменить бронирование, связанное с отзывом.',
        "text_en": 'The booking linked to a review cannot be changed.',
    },
    {
        "code": 'reviews.comment_too_long',
        "text_uz": 'Sharh matni 1000 belgidan oshmasligi kerak.',
        "text_ru": 'Текст отзыва не должен превышать 1000 символов.',
        "text_en": 'The review text must not exceed 1000 characters.',
    },
    {
        "code": 'reviews.invalid_data',
        "text_uz": 'Yuborilgan sharh ma’lumotlari noto‘g‘ri.',
        "text_ru": 'Переданные данные отзыва недействительны.',
        "text_en": 'The submitted review data is invalid.',
    },
    {
        "code": 'reviews.not_found',
        "text_uz": 'So‘ralgan sharh yoki bron topilmadi.',
        "text_ru": 'Запрошенный отзыв или бронирование не найдено.',
        "text_en": 'The requested review or booking was not found.',
    },
    {
        "code": 'reviews.only_completed_booking',
        "text_uz": 'Faqat tugallangan bron uchun sharh yozish mumkin.',
        "text_ru": 'Отзыв можно оставить только для завершённого бронирования.',
        "text_en": 'A review can only be submitted for a completed booking.',
    },
    {
        "code": 'reviews.permission_denied',
        "text_uz": 'Bu bron uchun sharh yozishga ruxsatingiz yo‘q.',
        "text_ru": 'У вас нет прав оставлять отзыв для этого бронирования.',
        "text_en": 'You do not have permission to review this booking.',
    },
    {
        "code": 'reviews.rating_invalid',
        "text_uz": 'Reyting 1 dan 5 gacha bo‘lishi kerak.',
        "text_ru": 'Рейтинг должен быть от 1 до 5.',
        "text_en": 'The rating must be between 1 and 5.',
    },
    # Telegram
    {
        "code": 'telegram.action_cannot_be_completed',
        "text_uz": 'Bu amalni bajarib bo‘lmaydi.',
        "text_ru": 'Это действие невозможно выполнить.',
        "text_en": 'This action cannot be completed.',
    },
    {
        "code": 'telegram.action_completed',
        "text_uz": 'Amal bajarildi.',
        "text_ru": 'Действие выполнено.',
        "text_en": 'The action was completed.',
    },
    {
        "code": 'telegram.bot_connected_to_group',
        "text_uz": '✅ Club Booking bot test guruhiga muvaffaqiyatli ulandi.',
        "text_ru": '✅ Бот Club Booking успешно подключён к тестовой группе.',
        "text_en": '✅ The Club Booking bot was connected to the test group successfully.',
    },
    {
        "code": 'telegram.btn_cancel',
        "text_uz": '❌ Bekor qilish',
        "text_ru": '❌ Отменить',
        "text_en": '❌ Cancel',
    },
    {
        "code": 'telegram.btn_confirm',
        "text_uz": '✅ Tasdiqlash',
        "text_ru": '✅ Подтвердить',
        "text_en": '✅ Confirm',
    },
    {
        "code": 'telegram.group_admin_only',
        "text_uz": 'Bu amal faqat guruh admini uchun.',
        "text_ru": 'Это действие доступно только администратору группы.',
        "text_en": 'This action is available only to a group administrator.',
    },
    {
        "code": 'telegram.group_not_configured',
        "text_uz": 'Bu filial uchun Telegram guruhi sozlanmagan.',
        "text_ru": 'Для этого филиала не настроена Telegram-группа.',
        "text_en": 'A Telegram group is not configured for this branch.',
    },
    {
        "code": 'telegram.invalid_cancel_reason',
        "text_uz": 'Telegram orqali bekor qilish sababi noto‘g‘ri.',
        "text_ru": 'Некорректная причина отмены через Telegram.',
        "text_en": 'The Telegram cancellation reason is invalid.',
    },
]


class Command(BaseCommand):
    help = "Tizim xabarlarini yaratadi yoki yangilaydi (snake_case formatda)."

    @transaction.atomic
    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing system messages in the database",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        # Eski raqamli (legacy numeric) xabar kodlarini tozalash
        deleted_numeric, _ = SystemMessage.objects.filter(code__regex=r"^[0-9]+$").delete()
        if deleted_numeric:
            self.stdout.write(self.style.WARNING(f"Eski raqamli {deleted_numeric} ta SystemMessage olib tashlandi."))

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for message_data in SYSTEM_MESSAGES:
            code = message_data["code"]

            if force:
                _, created = SystemMessage.objects.update_or_create(
                    code=code,
                    defaults={
                        "text_uz": message_data["text_uz"],
                        "text_ru": message_data["text_ru"],
                        "text_en": message_data["text_en"],
                        "is_active": True,
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            else:
                _, created = SystemMessage.objects.get_or_create(
                    code=code,
                    defaults={
                        "text_uz": message_data["text_uz"],
                        "text_ru": message_data["text_ru"],
                        "text_en": message_data["text_en"],
                        "is_active": True,
                    },
                )
                if created:
                    created_count += 1
                else:
                    skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                (
                    "SystemMessage holati: "
                    f"{created_count} ta yaratildi, "
                    f"{updated_count} ta yangilandi, "
                    f"{skipped_count} ta mavjud saqlandi."
                )
            )
        )

