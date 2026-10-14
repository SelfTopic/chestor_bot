# Тестовый стенд: автодеплой

Стенд сам ставит **последнюю запушенную ветку**, но только если CI на её последнем коммите
зелёный, и пишет в Telegram, что вышло. Прод обновляется руками, как раньше.

Как это работает: на сервере таймер systemd раз в минуту запускает `deploy/stand/deploy.sh`.
Скрипт делает `git fetch`, берёт ветку с самым свежим коммитом и смотрит check runs этого
коммита на GitHub:

- CI ещё идёт — ждёт следующей минуты;
- CI красный — пишет «❌ CI красный» и этот коммит больше не трогает;
- CI зелёный — `git checkout` коммита в папке стенда и
  `docker compose -p chestor_test up -d --build bot`, затем «✅ На стенде <ветка>» или
  «❌ Стенд не поднялся» с последними строками лога сборки.

Сервер сам забирает обновления: у GitHub нет ключей от сервера.

## Установка (один раз, на сервере)

Нужны `git`, `docker compose`, `curl`, `python3`, `flock` (есть почти везде).

1. Папка стенда — отдельный клон репозитория со своим `.env` (токен **тестового** бота).
   Если стенд уже есть, подойдёт он. Если нет:
   ```sh
   git clone https://github.com/SelfTopic/chestor_bot.git /root/chestor_test
   cp /путь/к/.env.стенда /root/chestor_test/.env
   ```
   В эту папку руками ничего не править: скрипт делает `git checkout --force`.

2. Скрипт и юниты:
   ```sh
   cd /root/chestor_test
   install -m 755 deploy/stand/deploy.sh /usr/local/bin/chestor-stand-deploy
   install -m 644 deploy/stand/chestor-stand.service deploy/stand/chestor-stand.timer /etc/systemd/system/
   install -m 600 deploy/stand/chestor-stand.env.example /etc/chestor-stand.env
   nano /etc/chestor-stand.env   # STAND_DIR, NOTIFY_CHAT_ID, при желании STAND_SERVICES
   systemctl daemon-reload
   systemctl enable --now chestor-stand.timer
   ```
   Скрипт копируется в `/usr/local/bin`, а не запускается из клона: иначе ветка, которую он
   ставит, могла бы сломать сам деплой. Изменился `deploy.sh` в репозитории — повторить
   `install` для него.

3. Проверить: `systemctl start chestor-stand.service` и `journalctl -u chestor-stand -n 50`.
   Через минуту-другую после зелёного CI придёт сообщение от тестового бота.

## Если что-то не так

- Сообщений нет — `journalctl -u chestor-stand -n 50`. Частые причины: тестовому боту не
  написали `/start` (он не может начать диалог сам), неверный `NOTIFY_CHAT_ID`.
- Поставить коммит заново (например, после ручной починки): удалить в папке стенда
  `.stand_deployed` и `.stand_rejected`.
- Остановить автодеплой: `systemctl disable --now chestor-stand.timer`.
- Лимит API GitHub без токена — 60 запросов в час с IP; скрипт ходит в API только пока ждёт
  CI нового коммита. Если упрётся — `GITHUB_TOKEN` (без прав) в `/etc/chestor-stand.env`.
