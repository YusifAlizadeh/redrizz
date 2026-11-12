# 01 — Рекон (разведка)

Цель: узнать IP всех команд, какие порты открыты, что за сервисы, и где лежат флаги.

## Список команд
Обычно сеть вида `10.60.<id>.1` на команду. Сгенерить список:
```bash
# команды с 1 по 20, подставь свой диапазон
for i in $(seq 1 20); do echo "10.60.$i.1"; done > teams.txt
cat teams.txt
```
Либо через наш хелпер (он уже исключает нашу команду):
```bash
python utils/targets.py > teams.txt
```

## Кто живой (быстрый ping-свип)
```bash
# fping быстрее; если нет — обычный ping в цикле
fping -a -g 10.60.0.0/16 2>/dev/null         # все живые хосты
# или:
for ip in $(cat teams.txt); do ping -c1 -W1 $ip >/dev/null && echo "UP $ip"; done
```

## Сканирование портов (nmap)
```bash
# быстрый скан одного хоста
nmap -Pn -T4 TEAM

# самые частые порты сервисов + версии
nmap -Pn -sV -T4 -p1-20000 TEAM

# один конкретный порт по всем командам сразу (найти, у кого сервис поднят)
nmap -Pn -p PORT -iL teams.txt --open

# очень быстрый массовый скан (masscan, нужен root)
sudo masscan -p1-20000 --rate 5000 -iL teams.txt
```

## Что это за сервис (снять баннер)
```bash
# TCP-сервис — просто подключиться и посмотреть, что отвечает
nc TEAM PORT
# или с таймаутом:
timeout 3 nc TEAM PORT

# HTTP — заголовки и тело
curl -s -i http://TEAM:PORT/
curl -s http://TEAM:PORT/ | head -50

# что за бинарь по порту (иногда даёт версию)
nmap -Pn -sV --script=banner -p PORT TEAM
```

## Веб: найти страницы и эндпоинты
```bash
# директории (поставь wordlist свой)
ffuf -u http://TEAM:PORT/FUZZ -w /usr/share/wordlists/dirb/common.txt -mc 200,301,302,403
gobuster dir -u http://TEAM:PORT/ -w /usr/share/wordlists/dirb/common.txt

# посмотреть, какие технологии
whatweb http://TEAM:PORT/
```

## Исходники сервиса — ГЛАВНОЕ
На A/D организаторы почти всегда дают **исходный код сервисов** (в архиве/репозитории
на vulnbox, часто в `/home/<service>/` или в выданном архиве). Найди их:
```bash
# на своей vulnbox поищи код сервисов
ls -la /home /opt /srv 2>/dev/null
find / -name '*.py' -o -name '*.php' -o -name '*.go' 2>/dev/null | grep -iv proc | head
docker ps                     # сервисы часто в контейнерах
docker inspect <container>     # где смонтирован код
```
> Нашёл исходник → скинь его мне (Claude), я найду баг и напишу эксплойт.
