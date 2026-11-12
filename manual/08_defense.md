# 08 — Защита (SLA-очки и не дать себя фармить)

Защита = очки тоже. Правило №1: **патч не должен ломать сервис** (иначе теряешь SLA).
Проверяй `python checker/healthcheck.py` после каждого изменения.

## Первым делом — бэкап (чтобы откатиться)
```bash
sudo cp -a /path/to/service /root/backup_service_$(date +%s)
docker commit <container> backup_service:orig     # если в докере
```

## Найти, что крутится и где код
```bash
ss -tlnp                      # какие порты слушаются и каким процессом
docker ps                     # сервисы в контейнерах
ps aux | grep -iE 'python|php|node|go'
```

## Патчить баг (аккуратно)
- Нашёл дыру (сам или по трафику из файла 07) → закрой её в коде сервиса.
- Самое безопасное: **входная валидация** (отфильтровать `../`, кавычки, спецсимволы),
  добавить проверку прав (IDOR), убрать дефолтные пароли.
- После правки: перезапусти сервис и сразу `healthcheck`.
```bash
docker restart <container>    # или systemctl restart <svc>
python checker/healthcheck.py
```

## Мониторить атаки по себе в реальном времени
```bash
# видеть входящие запросы к сервису
sudo tcpdump -i any -A -l "tcp port PORT" | grep --line-buffered -iE 'union|\.\./|{{|;|flag'
# логи сервиса
tail -f /path/to/service/logs/*.log
docker logs -f <container>
```

## Экстренно: заблокировать конкретного атакующего (осторожно!)
> Блокировать по IP рискованно: можно случайно зарубить чекер жюри и потерять SLA.
> Лучше патчить баг. Если всё же надо — точечно и временно:
```bash
sudo iptables -A INPUT -s IP_АТАКУЮЩЕГО -p tcp --dport PORT -j DROP
sudo iptables -D INPUT -s IP_АТАКУЮЩЕГО -p tcp --dport PORT -j DROP   # снять
```

## Поймать закладки соперников (persistence)
Соперники могли оставить вебшелл/бэкдор. Проверь:
```bash
# свежеизменённые файлы в сервисе
find /path/to/service -mmin -60 -type f
# подозрительные процессы и крон
ps aux --sort=-%cpu | head
crontab -l; ls -la /etc/cron.*
# левые ssh-ключи
cat ~/.ssh/authorized_keys
```

## Главное правило
Сервис `DOWN` после патча → **немедленно откат из бэкапа**. Лучше дырявый живой сервис,
чем мёртвый запатченный — за живой ты хотя бы не теряешь SLA.
