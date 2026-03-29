"""Pair with Dirigera hub to get an access token."""

from dirigera.hub.auth import random_code, send_challenge, get_token, ALPHABET, CODE_LENGTH

HUB_IP = input("Enter your Dirigera hub IP: ").strip()

print(f"Pairing with Dirigera hub at {HUB_IP}...")
code_verifier = random_code(ALPHABET, CODE_LENGTH)
code = send_challenge(HUB_IP, code_verifier)
print("Challenge sent successfully!")
print()
print("Now press the action button on your Dirigera hub.")
print("(It's a small round button on the BOTTOM of the hub)")
print()
input("After pressing it, hit ENTER here... ")
token = get_token(HUB_IP, code, code_verifier)
print()
print("Your token:")
print(token)
