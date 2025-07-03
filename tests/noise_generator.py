import os
import random

secrets = [
    "8466-fHCvVxCEc44KLOTQw4MBWV9VKA1Ds1JzqE5abV7o",
    "EAACEdEose0cBAZdG9ylLmNoJNaoNxkwa86o9Vn5LD",
    "AIzaEXkq-hiYSt3Lvu5d95jqrYHCx3nEHIelYl4",
    "8573491-G7h2Jk_5Lm9P0QrS8tUv6WxYz1AbCdEf.apps.googleusercontent.com",
    "sk_live_0xvzezi4c46esfzxfkxm5ry9vfif9ii0",
    "sk_live_LFwqDdw3FyKqb0t66I5Szfdn",
    "rk_live_3WbnveStCKoFzmZIBmHvCSbN",
    "sq0atp-dr6vf6ksfqtyP5ez332tbh",
    "sq0csp-Fds2Mpkdr_ujbnD9aBlpPOYQ_9h2dmS-WDtyr7rLWKU",
    "access_token$production$cj9go1au32dsndbx$1347b1b71f0b314a739a2f8a55087ec4",
    "amzn.mws.0c6ee0be-f81a-0326-076a-ca115435318f",
    "SKEDcFBB7AB713C5fa3F4E4C8AE55b376c",
    "key-jPDW9qYKpQKv1qPCVxF5rpzxRlXbAbIv",
    "b1b42a2917ba283e417fdadef15e5c80-us97",
    "AKIA2DS13A7NFX15DKY0",
]


def single_big_file():
    filename = "dump/noise.txt"
    total_size = 10 * 1024 * 1024 * 1024  # 10 GB
    chunk_size = 10 * 1024 * 1024  # 10 MB per write

    secret_chunk = 782
    example_secret = "EAACEdEose0cBAz"

    with open(filename, "wb+") as f:
        for i in range(total_size // chunk_size):
            if not i % 50:
                print(i)
            if i == secret_chunk:
                print(
                    f"got to chunk {i}, placing secret {example_secret} (encoded as {example_secret.encode()})"
                )
            f.write(example_secret.encode())
            f.write(os.urandom(chunk_size))


def many_small_files():
    output_dir = "tests/dump"
    os.makedirs(output_dir, exist_ok=True)

    file_count = 10000  # 10,000 files
    file_size = 10 * 1024  # 10 KB

    files_with_secrets = random.sample(range(file_count), len(secrets))
    secret_positions = random.sample(range(file_size), len(secrets))

    for i in range(file_count):
        filename = os.path.join(output_dir, f"file_{i:05}.bin")
        with open(filename, "wb") as f:
            if i not in files_with_secrets:
                f.write(os.urandom(file_size))
                continue
            secret_index = files_with_secrets.index(i)
            secret, secret_position = (
                secrets[secret_index],
                secret_positions[secret_index],
            )
            f.write(os.urandom(secret_position))
            f.write(bytes(secret, "utf-8"))
            f.write(os.urandom(file_size - secret_position - len(secret)))
