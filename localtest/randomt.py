from cryptography.fernet import Fernet
from base64 import urlsafe_b64decode


def add_base64_padding(unpadded: str):
    while len(unpadded) % 4 != 0:
        unpadded += "="
    return unpadded

private = add_base64_padding("qmUHHM-Em05PGvaeWDY4JnWu_pZDos8ki9o3RrZVJow")

x = "gAAAAABh0InmXBSEJII-1Jog3VXJztRBMfFlC2C0ILeFOqaMvPDW6eB9olyPW2opsqqz2CUTQeL-r1JLLHT5Rth8YSVJakF8J5RBcQtMzGvkifZhC8ARKEoXHeiY9sxYIvKuAmDv79z3DAygo_q9WKcbyjOmwvBA4A=="
yy = add_base64_padding(x)
print(yy)
print(len(urlsafe_b64decode(yy)))

fern = Fernet(private)
z = fern.encrypt(b"id2famOaxY54iaD8W7YoA_4ZSilg")
print(z.decode('utf-8'))
