import asyncio
import getpass
import hashlib
import hmac
import json
import os
import random
import secrets
from hashlib import md5
from ipaddress import IPv6Network, IPv6Address

import websockets
from Crypto.Cipher import AES

SUBNETS = [
    "2a0c:3b85:24::/48"
]


# FunCaptcha encryption modified, because I cba to make my own :joy:
def encrypt(data, key) -> str:
    data = data + chr(16 - len(data) % 16) * (16 - len(data) % 16)

    salt = secrets.token_hex(16).encode()
    salted, dx = b"", b""
    while len(salted) < 48:
        dx = hashlib.md5(dx + key.encode() + salt).digest()
        salted += dx

    key = salted[:32]
    iv = salted[32:48]
    aes = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = {
        "content": aes.encrypt(data.encode()).hex(),
        "iv": iv.hex(),
        "salt": salt.hex()
    }
    return json.dumps(encrypted_data, separators=(',', ':')).encode().hex()


def port_identity() -> int:
    # strip off some data so it cant be de-hashed easily
    _str1_: str = md5(getpass.getuser().encode()).hexdigest()[:28]
    _str2_: str = md5(os.getenv("PATH").encode()).hexdigest()[:28]
    _str3_: str = md5(str(os.cpu_count()).encode()).hexdigest()[:16]
    _int1_: int = len(os.name.encode()) << 4
    _int2_: int = 2048
    for char in _str1_:
        if char:
            _int2_ += ord(char) + _int1_
    for char in _str2_:
        if char:
            _int2_ += ord(char) + _int1_
    for char in _str3_:
        if char:
            _int2_ += ord(char) + _int1_
    return round(min(_int2_, 32768)) + 2


def username_identity() -> str:
    # strip off some data so it cant be de-hashed easily
    _str1_: str = md5(getpass.getuser().encode()).hexdigest()[:28]
    _str2_: str = md5(os.getenv("PATH").encode()).hexdigest()[:28]
    _str3_: str = md5(str(os.cpu_count()).encode()).hexdigest()[:16]
    _int1_: int = len(os.name.encode()) << 4
    _int2_: int = 2048
    for char in _str1_:
        if char:
            _int2_ += ord(char) + _int1_
    for char in _str2_:
        if char:
            _int2_ += ord(char) + _int1_
    for char in _str3_:
        if char:
            _int2_ += ord(char) + _int1_
    return md5(str(_int2_).encode()).hexdigest()[:16].upper()


def password_identity() -> str:
    # strip off some data so it cant be de-hashed easily
    _str1_: str = md5(getpass.getuser().encode()).hexdigest()[:28]
    _str2_: str = md5(os.getenv("PATH").encode()).hexdigest()[:28]
    _str3_: str = md5(str(os.cpu_count()).encode()).hexdigest()[:16]
    _int1_: int = len(os.name.encode()) << 31
    _int2_: int = 2048
    for char in _str1_:
        if char:
            _int2_ += ord(char) + _int1_
    for char in _str2_:
        if char:
            _int2_ += ord(char) + _int1_
    for char in _str3_:
        if char:
            _int2_ += ord(char) + _int1_
    return md5(str(_int2_).encode()).hexdigest()[:16].upper()


PROXY_PORT = port_identity()
PROXY_USER = username_identity()
PROXY_PASSWORD = password_identity()


def random_subnet(length: int) -> str:
    network = IPv6Network(random.choice(SUBNETS))
    address = IPv6Address(network.network_address + random.getrandbits(network.max_prefixlen - network.prefixlen))
    changed_network = IPv6Network(f"{address}/{length}", False)
    return str(changed_network)


def proof_data() -> tuple[str, str]:
    key = secrets.token_bytes(64)
    return key.hex(), hmac.new(key,
                               f"PORT_ID:{PROXY_PORT}|"
                               f"USERNAME_ID:{PROXY_USER}|"
                               f"PASSWORD_ID:{PROXY_PASSWORD}".encode(),
                               digestmod=hashlib.sha512).digest().hex()


async def main() -> None:
    key, hmc = proof_data()
    async with websockets.connect(f"ws://85.202.203.139:41089/?_key={key}&_hmc={hmc}") as websocket:
        while 1:
            subnet = random_subnet(48)
            await websocket.send(encrypt(json.dumps({
                "server-mode": 64,
                "data": {
                    "task": "ip_change",
                    "username": PROXY_USER,
                    "password": PROXY_PASSWORD,
                    "port": PROXY_PORT,
                    "new_subnet": subnet
                }
            }), 'cfd2a8d8610a4e5d939bcb59aa82abc1'))
            await asyncio.sleep(600)


def proxy_url() -> str:
    return f"socks5://{PROXY_USER}:{PROXY_PASSWORD}@85.202.203.139:{PROXY_PORT}"


def start() -> None:
    print("Using credentials:")
    print(f"-> User: {PROXY_USER}")
    print(f"-> Pass: {PROXY_PASSWORD}")
    print(f"-> Port: {PROXY_PORT}")
    print(f"-> SOCKS5: {PROXY_USER}:{PROXY_PASSWORD}@85.202.203.139:{PROXY_PORT}")
    loop = asyncio.new_event_loop()
    loop.create_task(main())
    loop.run_forever()


if __name__ == '__main__':
    start()
