#!/usr/bin/env python3
import argparse
import base64
import hashlib
import time

from azure.identity import DefaultAzureCredential
from azure.keyvault.keys import KeyClient
from azure.keyvault.keys.crypto import CryptographyClient, SignatureAlgorithm

TAG_SIGNATURE = 2
TAG_PUBLIC_KEY = 6
TAG_PUBLIC_SUBKEY = 14

SUBPACKET_CREATION_TIME = 2
SUBPACKET_ISSUER_KEY_ID = 16
SUBPACKET_ISSUER_FINGERPRINT = 33

KEY_VERSION_4 = 4
SIGNATURE_VERSION_4 = 4
SIGNATURE_TYPE_BINARY_DOCUMENT = 0x00
PUBKEY_ALGORITHM_RSA_ENCRYPT_OR_SIGN = 1
HASH_ALGORITHM_SHA512 = 10


def encode_mpi(value: int) -> bytes:
    value_bytes = value.to_bytes((value.bit_length() + 7) // 8 or 1, "big")
    return value.bit_length().to_bytes(2, "big") + value_bytes


def encode_length(length: int) -> bytes:
    if length < 192:
        return bytes([length])
    if length < 8384:
        length -= 192
        return bytes([192 + (length >> 8), length & 0xFF])
    return b"\xff" + length.to_bytes(4, "big")


def encode_packet(tag: int, body: bytes) -> bytes:
    return bytes([0xC0 | tag]) + encode_length(len(body)) + body


def encode_subpacket(subpacket_type: int, data: bytes) -> bytes:
    body = bytes([subpacket_type]) + data
    return encode_length(len(body)) + body


class KeyVaultSigner:
    def __init__(self, vault_name: str, key_name: str, key_version: str = None):
        credential = DefaultAzureCredential()
        vault_url = f"https://{vault_name}.vault.azure.net"
        key = KeyClient(vault_url=vault_url, credential=credential).get_key(key_name, version=key_version)
        if key.key_type not in ("RSA", "RSA-HSM"):
            raise SystemExit(f"key {key_name} is {key.key_type}; only RSA is supported")
        self.key_id = key.id
        self.modulus = int.from_bytes(key.key.n, "big")
        self.public_exponent = int.from_bytes(key.key.e, "big")
        self._crypto = CryptographyClient(key, credential=credential)

    def sign_sha512_digest(self, digest: bytes) -> bytes:
        return self._crypto.sign(SignatureAlgorithm.rs512, digest).signature


def v4_key_fingerprint(key_packet_body: bytes) -> bytes:
    preamble = b"\x99" + len(key_packet_body).to_bytes(2, "big")
    return hashlib.sha1(preamble + key_packet_body).digest()


def take(data: bytes, i: int, count: int) -> bytes:
    if i + count > len(data):
        raise ValueError("truncated packet data")
    return data[i:i + count]


def iter_packets(data: bytes):
    i, end = 0, len(data)
    while i < end:
        header = data[i]
        i += 1
        if not (header & 0x80):
            raise ValueError("bad packet header")
        if header & 0x40:
            tag = header & 0x3F
            first = take(data, i, 1)[0]
            i += 1
            if first < 192:
                length = first
            elif first < 224:
                length = ((first - 192) << 8) + take(data, i, 1)[0] + 192
                i += 1
            elif first == 255:
                length = int.from_bytes(take(data, i, 4), "big")
                i += 4
            else:
                raise ValueError("partial lengths unsupported")
        else:
            tag = (header >> 2) & 0x0F
            length_type = header & 0x03
            if length_type == 0:
                length = take(data, i, 1)[0]
                i += 1
            elif length_type == 1:
                length = int.from_bytes(take(data, i, 2), "big")
                i += 2
            elif length_type == 2:
                length = int.from_bytes(take(data, i, 4), "big")
                i += 4
            else:
                raise ValueError("indeterminate length unsupported")
        yield tag, take(data, i, length)
        i += length


def read_mpi(buf: bytes, i: int):
    header = take(buf, i, 2)
    bit_length = (header[0] << 8) | header[1]
    byte_length = (bit_length + 7) // 8
    i += 2
    return int.from_bytes(take(buf, i, byte_length), "big"), i + byte_length


def find_fingerprint_of_vault_key(keyring_path: str, modulus: int, public_exponent: int) -> bytes:
    with open(keyring_path, "rb") as f:
        keyring = f.read()
    for tag, body in iter_packets(keyring):
        is_key_packet = tag in (TAG_PUBLIC_KEY, TAG_PUBLIC_SUBKEY)
        if not is_key_packet or len(body) < 8:
            continue
        if body[0] != KEY_VERSION_4 or body[5] != PUBKEY_ALGORITHM_RSA_ENCRYPT_OR_SIGN:
            continue
        key_modulus, after_modulus = read_mpi(body, 6)
        key_exponent, after_exponent = read_mpi(body, after_modulus)
        if after_exponent != len(body):
            continue
        if key_modulus == modulus and key_exponent == public_exponent:
            return v4_key_fingerprint(body)
    raise SystemExit("keyring has no signing-capable RSA key matching the Key Vault key material")


def build_detached_signature(signer: KeyVaultSigner, issuer_fingerprint: bytes,
                             signed_data: bytes, creation_time: int) -> bytes:
    hashed_subpackets = encode_subpacket(SUBPACKET_CREATION_TIME, creation_time.to_bytes(4, "big"))
    hashed_subpackets += encode_subpacket(SUBPACKET_ISSUER_FINGERPRINT,
                                          bytes([KEY_VERSION_4]) + issuer_fingerprint)

    signature_fields = (bytes([SIGNATURE_VERSION_4, SIGNATURE_TYPE_BINARY_DOCUMENT,
                               PUBKEY_ALGORITHM_RSA_ENCRYPT_OR_SIGN, HASH_ALGORITHM_SHA512])
                        + len(hashed_subpackets).to_bytes(2, "big") + hashed_subpackets)

    v4_trailer = bytes([SIGNATURE_VERSION_4, 0xFF]) + len(signature_fields).to_bytes(4, "big")
    digest = hashlib.sha512(signed_data + signature_fields + v4_trailer).digest()
    raw_signature = signer.sign_sha512_digest(digest)

    issuer_key_id = issuer_fingerprint[12:]
    unhashed_subpackets = encode_subpacket(SUBPACKET_ISSUER_KEY_ID, issuer_key_id)

    body = (signature_fields
            + len(unhashed_subpackets).to_bytes(2, "big") + unhashed_subpackets
            + digest[:2]
            + encode_mpi(int.from_bytes(raw_signature, "big")))
    return encode_packet(TAG_SIGNATURE, body)


def crc24(data: bytes) -> bytes:
    crc = 0xB704CE
    for byte in data:
        crc ^= byte << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= 0x1864CFB
    return (crc & 0xFFFFFF).to_bytes(3, "big")


def ascii_armor(kind: str, data: bytes) -> str:
    encoded = base64.b64encode(data).decode()
    body = "\n".join(encoded[i:i + 64] for i in range(0, len(encoded), 64))
    checksum = base64.b64encode(crc24(data)).decode()
    return (f"-----BEGIN PGP {kind}-----\n\n{body}\n="
            + checksum
            + f"\n-----END PGP {kind}-----\n")


def cmd_sign(args):
    signer = KeyVaultSigner(args.kv_name, args.key_name, args.key_version)
    issuer_fingerprint = find_fingerprint_of_vault_key(args.keyring, signer.modulus,
                                                       signer.public_exponent)
    if args.expect_fingerprint:
        expected = args.expect_fingerprint.replace(" ", "").upper()
        actual = issuer_fingerprint.hex().upper()
        if actual != expected:
            raise SystemExit(f"issuer fingerprint {actual} does not match expected {expected}")
    with open(args.infile, "rb") as f:
        signed_data = f.read()
    signature_packet = build_detached_signature(signer, issuer_fingerprint,
                                                signed_data, int(time.time()))
    with open(args.out, "w") as f:
        f.write(ascii_armor("SIGNATURE", signature_packet))
    print(f"wrote {args.out} (issuer {issuer_fingerprint.hex().upper()[-16:]}, kv key {signer.key_id})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kv-name", required=True)
    parser.add_argument("--key-name", required=True)
    parser.add_argument("--key-version", default=None)
    subcommands = parser.add_subparsers(dest="cmd", required=True)

    sign = subcommands.add_parser("sign")
    sign.add_argument("--in", dest="infile", required=True)
    sign.add_argument("--out", required=True)
    sign.add_argument("--keyring", required=True)
    sign.add_argument("--expect-fingerprint", default=None)
    sign.set_defaults(func=cmd_sign)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
