# 05 — Crypto (криптографические сервисы)

Нужен исходник сервиса — без него крипту почти не сломать. Нашёл исходник → скинь мне.
Ниже — что искать и типовые быстрые поломки.

## На что смотреть в коде
- Как генерят ключ/IV/nonce — **переиспользуют?** (главная дыра A/D-крипты).
- Режим шифра: **ECB** (одинаковые блоки → одинаковый шифртекст), **CBC** с
  предсказуемым IV.
- RSA: маленькая `e` (=3), общий модуль, близкие простые.
- Генератор случайных: `random` вместо `secrets`, seed от времени.

## Частые быстрые поломки
```text
ECB            → одинаковые блоки открытого текста = одинаковые блоки шифра.
                 Cut-and-paste блоков, byte-at-a-time если есть оракул.
Reused IV/nonce (CTR/GCM) → XOR двух шифртекстов убирает keystream.
RSA e=3        → если m^3 < n, флаг = целочисленный кубический корень из c.
RSA общий n    → два ключа с общим модулем → факторизация.
LCG / weak PRNG→ восстановить состояние по нескольким выводам, предсказать дальше.
Padding oracle → сервер отвечает по-разному на плохой паддинг → расшифровка по байту.
Hash length ext→ подделать подпись MAC = hash(secret‖data) через hashpybuddy/hlextend.
```

## Инструменты
```bash
# RSA — автоатака по частым дырам
python3 -m pip install owiener         # атака Винера (малый d)
# RsaCtfTool:
git clone https://github.com/RsaCtfTool/RsaCtfTool && cd RsaCtfTool
python3 RsaCtfTool.py --publickey key.pub --uncipher c

# факторизация модуля
# http://factordb.com  (вставить n)  или:
python3 -c "from sympy import factorint; print(factorint(N))"

# быстрый кубический корень (RSA e=3, m^3<n)
python3 -c "from gmpy2 import iroot; print(iroot(C,3))"
```

## Скелет (exploits/crypto_svc.py)
```python
#!/usr/bin/env python3
import sys
from pwn import remote, context
context.log_level="error"
io = remote(sys.argv[1], 10001)          # TODO порт
# io.recvuntil(b"n = "); n=int(io.recvline())
# ... твоя математика ...
io.sendline(b"getflag")
print(io.recvall(timeout=4).decode(errors="replace"))
```
