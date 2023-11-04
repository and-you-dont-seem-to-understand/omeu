from base64 import b64decode, b64encode
from bs4 import BeautifulSoup
from Crypto.Cipher import ChaCha20_Poly1305
from discord_webhook import DiscordWebhook
from dotenv import load_dotenv
from json import loads, dumps
from os import getenv
from os.path import exists
from requests import get, post
from unicodedata import normalize

load_dotenv()

URL = getenv("URL")
TARGET_CLASS = getenv("TARGET_CLASS")
START_TEXT = getenv("START_TEXT")
WEBHOOK = getenv("WEBHOOK")

KEY = b64decode(getenv("KEY"))
NONCE = b64decode(getenv("NONCE"))

saved_data = []
saved_data_path = "./data.txt"


def get_data():
    soup = BeautifulSoup(get(URL).content, "html.parser")
    content = soup.select_one(TARGET_CLASS)

    lines = []
    update_start = False
    for line in content.text.splitlines():
        if update_start == True:
            text = normalize("NFKD", line.strip())
            if text != "":
                lines.append(text)
        if line.strip() == START_TEXT:
            update_start = True

    return lines[:-2]


def write_to_data(data: list):
    with open(saved_data_path, "w", encoding="utf-8") as f:
        json_str = dumps(data).encode("utf-8")
        CIPHER = ChaCha20_Poly1305.new(key=KEY, nonce=NONCE)
        ciphertext, tag = CIPHER.encrypt_and_digest(json_str)
        f.write(
            b64encode(ciphertext).decode("utf-8")
            + "\n"
            + b64encode(tag).decode("utf-8")
        )


if exists(saved_data_path):
    with open(saved_data_path, "r") as f:
        ciphertext, tag = f.read().split("\n")
        CIPHER = ChaCha20_Poly1305.new(key=KEY, nonce=NONCE)
        json_data = CIPHER.decrypt_and_verify(b64decode(ciphertext), b64decode(tag))
        saved_data = loads(json_data.decode("utf-8"))

    new_data = get_data()
    new_update = set(new_data) - set(saved_data)

    print(f"NEW: {len(new_update)}")

    if len(new_update) != 0:
        message = "```\n" + "\n".join(sorted(list(new_update), reverse=True)) + "\n```"
        webhook = DiscordWebhook(url=WEBHOOK, content=message)
        response = webhook.execute()
        print(response.status_code)
        write_to_data(new_data)

else:
    data = get_data()
    write_to_data(data)
