"""Tiny i18n layer for the site and the bot.

Usage:
    from app.i18n import t
    t("ru", "nav.clients")           -> "Клиенты"
    t(lang, "task.assigned", name=x) -> formatted string

Resolution: requested lang -> ru -> the key itself (so missing keys degrade
gracefully and never crash a page).
"""

LANGUAGES = ["ru", "uz", "en"]

LANGUAGE_NAMES = {"ru": "Русский", "uz": "O‘zbekcha", "en": "English"}

DEFAULT_LANG = "ru"


def normalize_lang(value: str | None) -> str:
    if value and value in LANGUAGES:
        return value
    return DEFAULT_LANG


# Flat key -> {lang: text}. Keep keys grouped by area with dotted names.
TRANSLATIONS: dict[str, dict[str, str]] = {
    # ---- nav ----
    "nav.dashboard": {"ru": "Дашборд", "uz": "Boshqaruv paneli", "en": "Dashboard"},
    "nav.clients": {"ru": "Клиенты", "uz": "Mijozlar", "en": "Clients"},
    "nav.pipeline": {"ru": "Pipeline", "uz": "Pipeline", "en": "Pipeline"},
    "nav.meetings": {"ru": "Встречи", "uz": "Uchrashuvlar", "en": "Meetings"},
    "nav.tasks": {"ru": "Задачи", "uz": "Vazifalar", "en": "Tasks"},
    "nav.settings": {"ru": "Настройки", "uz": "Sozlamalar", "en": "Settings"},
    "nav.logout": {"ru": "Выйти", "uz": "Chiqish", "en": "Log out"},
    # ---- common ----
    "common.save": {"ru": "Сохранить", "uz": "Saqlash", "en": "Save"},
    "common.cancel": {"ru": "Отмена", "uz": "Bekor qilish", "en": "Cancel"},
    "common.delete": {"ru": "Удалить", "uz": "O‘chirish", "en": "Delete"},
    "common.edit": {"ru": "Редактировать", "uz": "Tahrirlash", "en": "Edit"},
    "common.all": {"ru": "Все", "uz": "Hammasi", "en": "All"},
    "common.mine": {"ru": "Мои", "uz": "Mening", "en": "Mine"},
    "common.add": {"ru": "Добавить", "uz": "Qo‘shish", "en": "Add"},
    "common.none": {"ru": "—", "uz": "—", "en": "—"},
    "common.not_assigned": {"ru": "не назначен", "uz": "tayinlanmagan", "en": "unassigned"},
    "common.theme": {"ru": "Тема", "uz": "Mavzu", "en": "Theme"},
    "common.language": {"ru": "Язык", "uz": "Til", "en": "Language"},
    # ---- auth ----
    "auth.login_title": {"ru": "Вход", "uz": "Kirish", "en": "Sign in"},
    "auth.email": {"ru": "Email", "uz": "Email", "en": "Email"},
    "auth.password": {"ru": "Пароль", "uz": "Parol", "en": "Password"},
    "auth.name": {"ru": "Имя", "uz": "Ism", "en": "Name"},
    "auth.sign_in": {"ru": "Войти", "uz": "Kirish", "en": "Sign in"},
    "auth.error": {"ru": "Неверный email или пароль", "uz": "Email yoki parol noto‘g‘ri", "en": "Invalid email or password"},
    "auth.no_account": {"ru": "Нет аккаунта?", "uz": "Hisobingiz yo‘qmi?", "en": "No account?"},
    "auth.register_link": {"ru": "Зарегистрироваться", "uz": "Ro‘yxatdan o‘tish", "en": "Register"},
    "auth.register_title": {"ru": "Регистрация", "uz": "Ro‘yxatdan o‘tish", "en": "Register"},
    "auth.create_account": {"ru": "Создать аккаунт", "uz": "Hisob yaratish", "en": "Create account"},
    "auth.have_account": {"ru": "Уже есть аккаунт?", "uz": "Hisobingiz bormi?", "en": "Already have an account?"},
    "auth.login_link": {"ru": "Войти", "uz": "Kirish", "en": "Sign in"},
    "auth.email_taken": {"ru": "Этот email уже зарегистрирован", "uz": "Bu email allaqachon ro‘yxatdan o‘tgan", "en": "This email is already registered"},
    "auth.reg_disabled": {"ru": "Регистрация отключена", "uz": "Ro‘yxatdan o‘tish o‘chirilgan", "en": "Registration is disabled"},
    # ---- dashboard ----
    "dash.title": {"ru": "Дашборд", "uz": "Boshqaruv paneli", "en": "Dashboard"},
    "dash.clients": {"ru": "Клиентов", "uz": "Mijozlar", "en": "Clients"},
    "dash.upcoming_meetings": {"ru": "Предстоящих встреч", "uz": "Kelgusi uchrashuvlar", "en": "Upcoming meetings"},
    "dash.open_tasks": {"ru": "Открытых задач", "uz": "Ochiq vazifalar", "en": "Open tasks"},
    "dash.pipeline_money": {"ru": "Pipeline (в деньгах)", "uz": "Pipeline (pulda)", "en": "Pipeline value"},
    "stage.lead": {"ru": "Лид", "uz": "Lid", "en": "Lead"},
    "stage.qualified": {"ru": "Квалифицирован", "uz": "Saralangan", "en": "Qualified"},
    "stage.demo": {"ru": "Демо", "uz": "Demo", "en": "Demo"},
    "stage.pilot": {"ru": "Пилот", "uz": "Pilot", "en": "Pilot"},
    "stage.procurement": {"ru": "Закупка", "uz": "Xarid", "en": "Procurement"},
    "stage.contract": {"ru": "Договор", "uz": "Shartnoma", "en": "Contract"},
    "stage.won": {"ru": "Выиграно", "uz": "Yutilgan", "en": "Won"},
    "stage.lost": {"ru": "Проиграно", "uz": "Yutqazilgan", "en": "Lost"},
    "client.address": {"ru": "Адрес", "uz": "Manzil", "en": "Address"},
    "dash.in_work": {"ru": "В работе", "uz": "Ishda", "en": "In progress"},
    "dash.weighted": {"ru": "Взвешенный прогноз", "uz": "Vaznli prognoz", "en": "Weighted forecast"},
    "dash.won": {"ru": "Выиграно", "uz": "Yutilgan", "en": "Won"},
    "dash.upcoming_7d": {"ru": "Ближайшие встречи (7 дней)", "uz": "Yaqin uchrashuvlar (7 kun)", "en": "Upcoming meetings (7 days)"},
    "dash.open_tasks_h": {"ru": "Открытые задачи", "uz": "Ochiq vazifalar", "en": "Open tasks"},
    "dash.recent_activity": {"ru": "Последняя активность", "uz": "So‘nggi faollik", "en": "Recent activity"},
    "dash.no_meetings": {"ru": "Нет запланированных встреч.", "uz": "Rejalashtirilgan uchrashuvlar yo‘q.", "en": "No scheduled meetings."},
    "dash.no_tasks": {"ru": "Открытых задач нет.", "uz": "Ochiq vazifalar yo‘q.", "en": "No open tasks."},
    "dash.no_activity": {"ru": "Пока нет активности.", "uz": "Hozircha faollik yo‘q.", "en": "No activity yet."},
    # ---- clients ----
    "client.title": {"ru": "Клиенты", "uz": "Mijozlar", "en": "Clients"},
    "client.new": {"ru": "Новый клиент", "uz": "Yangi mijoz", "en": "New client"},
    "client.search": {"ru": "Поиск по названию или отрасли…", "uz": "Nomi yoki soha bo‘yicha qidirish…", "en": "Search by name or industry…"},
    "client.name": {"ru": "Название", "uz": "Nomi", "en": "Name"},
    "client.type": {"ru": "Тип", "uz": "Turi", "en": "Type"},
    "client.industry": {"ru": "Отрасль", "uz": "Soha", "en": "Industry"},
    "client.owner": {"ru": "Ответственный", "uz": "Mas’ul", "en": "Owner"},
    "client.bank": {"ru": "Банк", "uz": "Bank", "en": "Bank"},
    "client.company": {"ru": "Компания", "uz": "Kompaniya", "en": "Company"},
    "client.website": {"ru": "Сайт", "uz": "Sayt", "en": "Website"},
    "client.notes": {"ru": "Заметки", "uz": "Eslatmalar", "en": "Notes"},
    "client.none": {"ru": "Клиентов пока нет.", "uz": "Hozircha mijozlar yo‘q.", "en": "No clients yet."},
    "client.edit": {"ru": "Редактирование клиента", "uz": "Mijozni tahrirlash", "en": "Edit client"},
    "client.new_title": {"ru": "Новый клиент", "uz": "Yangi mijoz", "en": "New client"},
    "client.owner_none": {"ru": "— не назначен —", "uz": "— tayinlanmagan —", "en": "— unassigned —"},
    "client.delete_confirm": {"ru": "Удалить клиента и все связанные данные?", "uz": "Mijoz va barcha bog‘liq ma’lumotlar o‘chirilsinmi?", "en": "Delete client and all related data?"},
    # ---- contacts ----
    "contact.h": {"ru": "Контакты", "uz": "Kontaktlar", "en": "Contacts"},
    "contact.none": {"ru": "Контактов нет.", "uz": "Kontaktlar yo‘q.", "en": "No contacts."},
    "contact.name": {"ru": "Имя", "uz": "Ism", "en": "Name"},
    "contact.position": {"ru": "Должность", "uz": "Lavozim", "en": "Position"},
    "contact.email": {"ru": "Email", "uz": "Email", "en": "Email"},
    "contact.phone": {"ru": "Телефон", "uz": "Telefon", "en": "Phone"},
    "contact.add": {"ru": "Добавить контакт", "uz": "Kontakt qo‘shish", "en": "Add contact"},
    "contact.edit": {"ru": "Редактирование контакта", "uz": "Kontaktni tahrirlash", "en": "Edit contact"},
    "contact.delete": {"ru": "Удалить контакт", "uz": "Kontaktni o‘chirish", "en": "Delete contact"},
    "contact.delete_confirm": {"ru": "Удалить контакт?", "uz": "Kontakt o‘chirilsinmi?", "en": "Delete contact?"},
    # ---- deals ----
    "deal.h": {"ru": "Сделки", "uz": "Bitimlar", "en": "Deals"},
    "deal.none": {"ru": "Сделок нет.", "uz": "Bitimlar yo‘q.", "en": "No deals."},
    "deal.title_field": {"ru": "Название сделки", "uz": "Bitim nomi", "en": "Deal title"},
    "deal.stage": {"ru": "Этап", "uz": "Bosqich", "en": "Stage"},
    "deal.amount": {"ru": "Сумма", "uz": "Summa", "en": "Amount"},
    "deal.currency": {"ru": "Валюта", "uz": "Valyuta", "en": "Currency"},
    "deal.probability": {"ru": "Вероятность %", "uz": "Ehtimollik %", "en": "Probability %"},
    "deal.expected_close": {"ru": "Ожидаемое закрытие", "uz": "Kutilayotgan yopilish", "en": "Expected close"},
    "deal.add": {"ru": "Добавить сделку", "uz": "Bitim qo‘shish", "en": "Add deal"},
    "deal.edit": {"ru": "Редактирование сделки", "uz": "Bitimni tahrirlash", "en": "Edit deal"},
    "deal.delete": {"ru": "Удалить сделку", "uz": "Bitimni o‘chirish", "en": "Delete deal"},
    "deal.delete_confirm": {"ru": "Удалить сделку?", "uz": "Bitim o‘chirilsinmi?", "en": "Delete deal?"},
    "deal.pipeline_title": {"ru": "Pipeline", "uz": "Pipeline", "en": "Pipeline"},
    "deal.in_work_total": {"ru": "В работе", "uz": "Ishda", "en": "In progress"},
    "deal.owner": {"ru": "Ответственный", "uz": "Mas’ul", "en": "Owner"},
    # ---- tasks ----
    "task.h": {"ru": "Задачи", "uz": "Vazifalar", "en": "Tasks"},
    "task.none": {"ru": "Задач нет.", "uz": "Vazifalar yo‘q.", "en": "No tasks."},
    "task.new": {"ru": "Новая задача", "uz": "Yangi vazifa", "en": "New task"},
    "task.title_field": {"ru": "Название задачи", "uz": "Vazifa nomi", "en": "Task title"},
    "task.description": {"ru": "Описание", "uz": "Tavsif", "en": "Description"},
    "task.assignee": {"ru": "Исполнитель", "uz": "Ijrochi", "en": "Assignee"},
    "task.due": {"ru": "Срок", "uz": "Muddat", "en": "Due"},
    "task.status": {"ru": "Статус", "uz": "Holat", "en": "Status"},
    "task.client": {"ru": "Клиент", "uz": "Mijoz", "en": "Client"},
    "task.source": {"ru": "Источник", "uz": "Manba", "en": "Source"},
    "task.create": {"ru": "Создать задачу", "uz": "Vazifa yaratish", "en": "Create task"},
    "task.in_linear": {"ru": " в Linear", "uz": " Linear’da", "en": " in Linear"},
    "task.edit": {"ru": "Редактирование задачи", "uz": "Vazifani tahrirlash", "en": "Edit task"},
    "task.delete": {"ru": "Удалить задачу", "uz": "Vazifani o‘chirish", "en": "Delete task"},
    "task.delete_confirm": {"ru": "Удалить задачу?", "uz": "Vazifa o‘chirilsinmi?", "en": "Delete task?"},
    "task.active": {"ru": "Активные", "uz": "Faol", "en": "Active"},
    "task.done": {"ru": "Выполненные", "uz": "Bajarilgan", "en": "Done"},
    "task.all_statuses": {"ru": "Все статусы", "uz": "Barcha holatlar", "en": "All statuses"},
    "task.choose_client": {"ru": "— выберите клиента —", "uz": "— mijozni tanlang —", "en": "— choose client —"},
    "task.no_deal": {"ru": "— нет —", "uz": "— yo‘q —", "en": "— none —"},
    # ---- meetings ----
    "meet.h": {"ru": "Встречи", "uz": "Uchrashuvlar", "en": "Meetings"},
    "meet.none": {"ru": "Встреч нет.", "uz": "Uchrashuvlar yo‘q.", "en": "No meetings."},
    "meet.upcoming": {"ru": "Предстоящие", "uz": "Kelgusi", "en": "Upcoming"},
    "meet.past": {"ru": "Прошедшие", "uz": "O‘tgan", "en": "Past"},
    "meet.new": {"ru": "Новая встреча", "uz": "Yangi uchrashuv", "en": "New meeting"},
    "meet.topic": {"ru": "Тема", "uz": "Mavzu", "en": "Topic"},
    "meet.when": {"ru": "Когда", "uz": "Qachon", "en": "When"},
    "meet.start": {"ru": "Начало", "uz": "Boshlanish", "en": "Start"},
    "meet.end": {"ru": "Конец", "uz": "Tugash", "en": "End"},
    "meet.location": {"ru": "Место / ссылка", "uz": "Joy / havola", "en": "Location / link"},
    "meet.participants": {"ru": "Участники", "uz": "Ishtirokchilar", "en": "Participants"},
    "meet.responsible": {"ru": "Ответственный", "uz": "Mas’ul", "en": "Responsible"},
    "meet.schedule": {"ru": "Запланировать", "uz": "Rejalashtirish", "en": "Schedule"},
    "meet.schedule_meeting": {"ru": "Запланировать встречу", "uz": "Uchrashuv rejalashtirish", "en": "Schedule meeting"},
    "meet.edit": {"ru": "Редактирование встречи", "uz": "Uchrashuvni tahrirlash", "en": "Edit meeting"},
    "meet.delete": {"ru": "Удалить встречу", "uz": "Uchrashuvni o‘chirish", "en": "Delete meeting"},
    "meet.delete_confirm": {"ru": "Удалить встречу?", "uz": "Uchrashuv o‘chirilsinmi?", "en": "Delete meeting?"},
    "meet.upcoming_badge": {"ru": "предстоит", "uz": "kutilmoqda", "en": "upcoming"},
    "meet.client": {"ru": "Клиент", "uz": "Mijoz", "en": "Client"},
    # ---- activity ----
    "act.h": {"ru": "Активность", "uz": "Faollik", "en": "Activity"},
    "act.what": {"ru": "Что произошло…", "uz": "Nima sodir bo‘ldi…", "en": "What happened…"},
    # ---- settings ----
    "set.title": {"ru": "Настройки", "uz": "Sozlamalar", "en": "Settings"},
    "set.profile": {"ru": "Профиль", "uz": "Profil", "en": "Profile"},
    "set.role": {"ru": "Роль", "uz": "Rol", "en": "Role"},
    "set.appearance": {"ru": "Оформление", "uz": "Ko‘rinish", "en": "Appearance"},
    "set.theme_light": {"ru": "Светлая", "uz": "Yorug‘", "en": "Light"},
    "set.theme_dark": {"ru": "Тёмная", "uz": "Qorong‘i", "en": "Dark"},
    "set.tg_notifications": {"ru": "Telegram-уведомления", "uz": "Telegram bildirishnomalari", "en": "Telegram notifications"},
    "set.bot_not_configured": {"ru": "Бот не настроен.", "uz": "Bot sozlanmagan.", "en": "Bot is not configured."},
    "set.tg_connected": {"ru": "Telegram подключён.", "uz": "Telegram ulangan.", "en": "Telegram connected."},
    "set.unlink": {"ru": "Отвязать", "uz": "Uzish", "en": "Unlink"},
    "set.send_command": {"ru": "Откройте бота в Telegram и отправьте команду:", "uz": "Telegram’da botni oching va buyruq yuboring:", "en": "Open the bot in Telegram and send the command:"},
    "set.get_code": {"ru": "Получить код привязки", "uz": "Ulanish kodini olish", "en": "Get linking code"},
    "set.new_code": {"ru": "Сгенерировать новый код", "uz": "Yangi kod yaratish", "en": "Generate new code"},
    "set.notify_all": {"ru": "Уведомлять обо всех активностях клиентов (не только встречи)", "uz": "Mijozlarning barcha faolliklari haqida xabar berish (faqat uchrashuvlar emas)", "en": "Notify about all client activity (not just meetings)"},
    "set.users": {"ru": "Пользователи", "uz": "Foydalanuvchilar", "en": "Users"},
    "set.add_user": {"ru": "Добавить пользователя", "uz": "Foydalanuvchi qo‘shish", "en": "Add user"},
    "set.user_delete_confirm": {"ru": "Удалить пользователя?", "uz": "Foydalanuvchi o‘chirilsinmi?", "en": "Delete user?"},
    # ---- errors ----
    "err.403": {"ru": "Недостаточно прав для этого действия.", "uz": "Bu amal uchun ruxsat yetarli emas.", "en": "You don't have permission for this action."},
    "err.404": {"ru": "Объект не найден.", "uz": "Obyekt topilmadi.", "en": "Not found."},
    "err.back_home": {"ru": "На дашборд", "uz": "Boshqaruv paneliga", "en": "Back to dashboard"},
    # ---- bot ----
    "bot.menu_clients": {"ru": "📇 Клиенты", "uz": "📇 Mijozlar", "en": "📇 Clients"},
    "bot.menu_meetings": {"ru": "📅 Встречи", "uz": "📅 Uchrashuvlar", "en": "📅 Meetings"},
    "bot.menu_tasks": {"ru": "✅ Задачи", "uz": "✅ Vazifalar", "en": "✅ Tasks"},
    "bot.menu_pipeline": {"ru": "📊 Pipeline", "uz": "📊 Pipeline", "en": "📊 Pipeline"},
    "bot.not_linked": {"ru": "Вы не подключены. Откройте «Настройки» в CRM, получите код и отправьте сюда: /start &lt;код&gt;", "uz": "Siz ulanmagansiz. CRM’dagi «Sozlamalar»ni oching, kod oling va bu yerga yuboring: /start &lt;kod&gt;", "en": "You're not linked. Open Settings in the CRM, get a code and send it here: /start &lt;code&gt;"},
    "bot.already_linked": {"ru": "Вы уже подключены как {name}.", "uz": "Siz allaqachon {name} sifatida ulangansiz.", "en": "You're already linked as {name}."},
    "bot.link_hint": {"ru": "Привет! Чтобы подключить уведомления, откройте «Настройки» в CRM, получите код и отправьте сюда:\n/start &lt;код&gt;", "uz": "Salom! Bildirishnomalarni ulash uchun CRM’dagi «Sozlamalar»ni oching, kod oling va yuboring:\n/start &lt;kod&gt;", "en": "Hi! To enable notifications, open Settings in the CRM, get a code and send it here:\n/start &lt;code&gt;"},
    "bot.code_not_found": {"ru": "Код не найден или устарел. Сгенерируйте новый в CRM.", "uz": "Kod topilmadi yoki eskirgan. CRM’da yangisini yarating.", "en": "Code not found or expired. Generate a new one in the CRM."},
    "bot.linked_ok": {"ru": "✅ Готово, {name}! Буду присылать напоминания о встречах.", "uz": "✅ Tayyor, {name}! Uchrashuvlar haqida eslatma yuboraman.", "en": "✅ Done, {name}! I'll send meeting reminders."},
    "bot.commands_hint": {"ru": "Команды: /today, /agenda, /clients, /tasks, /pipeline, /language", "uz": "Buyruqlar: /today, /agenda, /clients, /tasks, /pipeline, /language", "en": "Commands: /today, /agenda, /clients, /tasks, /pipeline, /language"},
    "bot.today": {"ru": "Встречи на сегодня", "uz": "Bugungi uchrashuvlar", "en": "Today's meetings"},
    "bot.agenda": {"ru": "Встречи на 7 дней", "uz": "7 kunlik uchrashuvlar", "en": "Meetings for 7 days"},
    "bot.upcoming_meetings": {"ru": "Предстоящие встречи", "uz": "Kelgusi uchrashuvlar", "en": "Upcoming meetings"},
    "bot.no_meetings": {"ru": "Встреч не найдено.", "uz": "Uchrashuvlar topilmadi.", "en": "No meetings found."},
    "bot.recent_clients": {"ru": "Последние клиенты", "uz": "So‘nggi mijozlar", "en": "Recent clients"},
    "bot.search_hint": {"ru": "Или напишите название для поиска:", "uz": "Yoki qidirish uchun nom yozing:", "en": "Or type a name to search:"},
    "bot.no_clients": {"ru": "Клиентов нет.", "uz": "Mijozlar yo‘q.", "en": "No clients."},
    "bot.open_tasks": {"ru": "Открытые задачи", "uz": "Ochiq vazifalar", "en": "Open tasks"},
    "bot.no_tasks": {"ru": "Открытых задач нет.", "uz": "Ochiq vazifalar yo‘q.", "en": "No open tasks."},
    "bot.pipeline": {"ru": "Pipeline (активные сделки)", "uz": "Pipeline (faol bitimlar)", "en": "Pipeline (active deals)"},
    "bot.total_in_work": {"ru": "Итого в работе", "uz": "Jami ishda", "en": "Total in progress"},
    "bot.deals": {"ru": "Сделки", "uz": "Bitimlar", "en": "Deals"},
    "bot.open_in_crm": {"ru": "🌐 Открыть в CRM", "uz": "🌐 CRM’da ochish", "en": "🌐 Open in CRM"},
    "bot.done": {"ru": "✓ Выполнить", "uz": "✓ Bajarish", "en": "✓ Done"},
    "bot.choose_language": {"ru": "Выберите язык:", "uz": "Tilni tanlang:", "en": "Choose a language:"},
    "bot.language_set": {"ru": "Язык переключён на русский.", "uz": "Til o‘zbekchaga o‘zgartirildi.", "en": "Language switched to English."},
    "bot.welcome_back": {"ru": "С возвращением, {name}! Выберите раздел ниже.", "uz": "Xush kelibsiz, {name}! Quyidan bo‘limni tanlang.", "en": "Welcome back, {name}! Pick a section below."},
    "bot.menu": {"ru": "Меню:", "uz": "Menyu:", "en": "Menu:"},
    "bot.help": {
        "ru": "<b>Команды</b>\n/today — встречи на сегодня\n/agenda — встречи на 7 дней\n/clients — клиенты\n/tasks — открытые задачи\n/deals — воронка\n/language — язык\n/menu — меню\n\n💡 Просто напишите название клиента — найду карточку.",
        "uz": "<b>Buyruqlar</b>\n/today — bugungi uchrashuvlar\n/agenda — 7 kunlik uchrashuvlar\n/clients — mijozlar\n/tasks — ochiq vazifalar\n/deals — voronka\n/language — til\n/menu — menyu\n\n💡 Mijoz nomini yozing — kartochkasini topaman.",
        "en": "<b>Commands</b>\n/today — today's meetings\n/agenda — meetings for 7 days\n/clients — clients\n/tasks — open tasks\n/deals — pipeline\n/language — language\n/menu — menu\n\n💡 Just type a client name to find its card.",
    },
    "bot.note_prompt": {"ru": "📝 Введите текст заметки (или /cancel):", "uz": "📝 Eslatma matnini kiriting (yoki /cancel):", "en": "📝 Enter the note text (or /cancel):"},
    "bot.task_prompt": {"ru": "➕ Введите название задачи (или /cancel):", "uz": "➕ Vazifa nomini kiriting (yoki /cancel):", "en": "➕ Enter the task title (or /cancel):"},
    "bot.canceled": {"ru": "Отменено.", "uz": "Bekor qilindi.", "en": "Canceled."},
    "bot.note_saved": {"ru": "✅ Заметка сохранена.", "uz": "✅ Eslatma saqlandi.", "en": "✅ Note saved."},
    "bot.task_created": {"ru": "✅ Задача создана{linear}.", "uz": "✅ Vazifa yaratildi{linear}.", "en": "✅ Task created{linear}."},
    "bot.in_linear_short": {"ru": " (в Linear ↗)", "uz": " (Linear’da ↗)", "en": " (in Linear ↗)"},
    "bot.back_to_card": {"ru": "← К карточке", "uz": "← Kartochkaga", "en": "← Back to card"},
    "bot.min_chars": {"ru": "Введите минимум 2 символа для поиска.", "uz": "Qidirish uchun kamida 2 ta belgi kiriting.", "en": "Enter at least 2 characters to search."},
    "bot.nothing_found": {"ru": "По запросу «{q}» ничего не найдено.", "uz": "«{q}» bo‘yicha hech narsa topilmadi.", "en": "Nothing found for “{q}”."},
    "bot.found": {"ru": "Найдено: {n}", "uz": "Topildi: {n}", "en": "Found: {n}"},
    "bot.industry": {"ru": "Отрасль", "uz": "Soha", "en": "Industry"},
    "bot.owner": {"ru": "Ответственный", "uz": "Mas’ul", "en": "Owner"},
    "bot.next_meeting": {"ru": "Ближайшая встреча", "uz": "Yaqin uchrashuv", "en": "Next meeting"},
    "bot.contacts_count": {"ru": "Контактов", "uz": "Kontaktlar", "en": "Contacts"},
    "bot.open_tasks_count": {"ru": "Открытых задач", "uz": "Ochiq vazifalar", "en": "Open tasks"},
    "bot.btn_tasks": {"ru": "✅ Задачи", "uz": "✅ Vazifalar", "en": "✅ Tasks"},
    "bot.btn_meetings": {"ru": "📅 Встречи", "uz": "📅 Uchrashuvlar", "en": "📅 Meetings"},
    "bot.btn_note": {"ru": "📝 Заметка", "uz": "📝 Eslatma", "en": "📝 Note"},
    "bot.btn_task": {"ru": "➕ Задача", "uz": "➕ Vazifa", "en": "➕ Task"},
    "bot.btn_done": {"ru": "✓ Выполнено", "uz": "✓ Bajarildi", "en": "✓ Done"},
    "bot.btn_prog": {"ru": "▶ В работе", "uz": "▶ Jarayonda", "en": "▶ In progress"},
    "bot.label_done": {"ru": "выполнена ✓", "uz": "bajarildi ✓", "en": "done ✓"},
    "bot.label_prog": {"ru": "в работе ▶", "uz": "jarayonda ▶", "en": "in progress ▶"},
    "bot.task_status_changed": {"ru": "Задача {label}", "uz": "Vazifa {label}", "en": "Task {label}"},
    "bot.task_not_found": {"ru": "Задача не найдена", "uz": "Vazifa topilmadi", "en": "Task not found"},
    "bot.client_not_found": {"ru": "Клиент не найден", "uz": "Mijoz topilmadi", "en": "Client not found"},
    "bot.no_active_deals": {"ru": "Активных сделок нет.", "uz": "Faol bitimlar yo‘q.", "en": "No active deals."},
    "bot.tasks_done_zero": {"ru": "Открытых задач нет 🎉", "uz": "Ochiq vazifalar yo‘q 🎉", "en": "No open tasks 🎉"},
    "bot.register_prompt": {
        "ru": "Похоже, у вас ещё нет аккаунта. Зарегистрируйтесь на сайте, затем вернитесь сюда для привязки:\n{url}/register",
        "uz": "Sizda hali hisob yo‘qga o‘xshaydi. Saytda ro‘yxatdan o‘ting, so‘ng ulash uchun qayting:\n{url}/register",
        "en": "Looks like you don't have an account yet. Register on the site, then come back here to link:\n{url}/register",
    },
    "bot.open_site": {"ru": "🌐 Открыть сайт", "uz": "🌐 Saytni ochish", "en": "🌐 Open site"},
    # ---- roles ----
    "role.guest": {"ru": "Гость", "uz": "Mehmon", "en": "Guest"},
    "role.member": {"ru": "Участник", "uz": "Ishtirokchi", "en": "Member"},
    "role.admin": {"ru": "Админ", "uz": "Admin", "en": "Admin"},
    # ---- pending approval ----
    "pending.title": {"ru": "Ожидает подтверждения", "uz": "Tasdiqlash kutilmoqda", "en": "Awaiting approval"},
    "pending.text": {"ru": "Ваш аккаунт создан и ждёт подтверждения администратором. После одобрения вы получите доступ к задачам и встречам.", "uz": "Hisobingiz yaratildi va administrator tasdiqini kutmoqda. Tasdiqlangach, vazifalar va uchrashuvlarga kirish ochiladi.", "en": "Your account is created and awaiting an admin's approval. Once approved, you'll get access to tasks and meetings."},
    # ---- settings: roles & telegram link ----
    "set.role_member": {"ru": "Роль", "uz": "Rol", "en": "Role"},
    "set.approve": {"ru": "Подтвердить", "uz": "Tasdiqlash", "en": "Approve"},
    "set.make_admin": {"ru": "Сделать админом", "uz": "Admin qilish", "en": "Make admin"},
    "set.make_member": {"ru": "Сделать участником", "uz": "Ishtirokchi qilish", "en": "Make member"},
    "set.main_admin": {"ru": "главный", "uz": "asosiy", "en": "main"},
    "set.link_tg_button": {"ru": "Привязать Telegram", "uz": "Telegram’ni ulash", "en": "Link Telegram"},
    "set.link_tg_hint": {"ru": "Нажмите кнопку — откроется бот и привяжет аккаунт автоматически.", "uz": "Tugmani bosing — bot ochiladi va hisobni avtomatik ulaydi.", "en": "Tap the button — the bot opens and links your account automatically."},
}


def t(lang: str | None, key: str, **kwargs) -> str:
    entry = TRANSLATIONS.get(key)
    if entry is None:
        text = key
    else:
        text = entry.get(normalize_lang(lang)) or entry.get(DEFAULT_LANG) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
