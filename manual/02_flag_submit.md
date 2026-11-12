# 02 — Сдать флаг РУКАМИ (самое важное)

Пока не умеешь сдать хотя бы один флаг — всё остальное бесполезно. Сначала
разберись с этим на первом же пойманном флаге.

Формат и адрес сдачи — из правил. Обычно один из двух вариантов.

## Вариант A — HTTP (современные движки: ForcAD и т.п.)
```bash
TOKEN="ваш_токен"
URL="http://СЕРВЕР_СДАЧИ/flags"

# чаще всего: массив флагов в JSON + токен в заголовке
curl -s -X PUT "$URL" \
  -H "X-Team-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '["FLAG1=","FLAG2="]'

# иногда токен и флаги в JSON-полях
curl -s -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"$TOKEN\",\"flags\":[\"FLAG1=\"]}"

# иногда просто текст, один флаг на строку
printf 'FLAG1=\nFLAG2=\n' | curl -s -X PUT "$URL" -H "X-Team-Token: $TOKEN" --data-binary @-
```
Смотри, что сервер отвечает: `accepted` / `invalid` / `too old` / `own flag`. Это
подскажет, правильно ли ты сдаёшь.

## Вариант B — TCP / netcat (старые движки: RuCTF, Hackerdom)
```bash
# подключаешься, (иногда) шлёшь токен первой строкой, потом флаги по строке
{ echo "$TOKEN"; echo "FLAG1="; echo "FLAG2="; sleep 1; } | nc СЕРВЕР_СДАЧИ ПОРТ

# если сервер шлёт приветствие и ждёт флаги:
nc СЕРВЕР_СДАЧИ ПОРТ
# дальше вручную вставляешь флаги строками
```

## Сдать МНОГО флагов из файла
```bash
# flags.txt — по одному флагу на строку
# HTTP построчно:
while read f; do
  curl -s -X PUT "$URL" -H "X-Team-Token: $TOKEN" -H 'Content-Type: application/json' -d "[\"$f\"]"
  echo
done < flags.txt

# TCP разом:
cat flags.txt | nc СЕРВЕР_СДАЧИ ПОРТ
```

## Как только сдача руками заработала
Перенеси ровно эти параметры в `config.py` (`SUBMIT_*`, `ACCEPT_WORDS/REJECT_WORDS`) —
и ферма будет сдавать автоматически. Руками — только аварийный режим.
