from typing import Tuple

# Encode ASCII bytes from `s` into an array of bytes, with the high bit of the last byte set.
# If `s` is zero bytes long this will instead encode a single NUL character, because the encoding of an empty string is not well-formed.
# I chose to set the high bit of the last byte instead of clearing it (contrary to `encode_varint`) to make it easier to parse these delimited strings in hexdumps and such.
def encode_var_ascii(s: bytes) -> bytes:
	arr = bytearray()
	for byte in s:
		assert (byte & 0x80) == 0
		arr.append(byte)

	if len(arr) == 0:
		arr.append(0)

	arr[-1] |= 0x80

	return bytes(arr)

def encode_varint(i: int) -> bytes:
	arr = bytearray()
	while len(arr) == 0 or i != 0:
		arr.append((i % 128) | 0x80)
		i //= 128

	arr.reverse()
	arr[-1] &= ~0x80

	return bytes(arr)

def decode_var_ascii(raw: bytes) -> str:
	array = bytearray()
	i = 0
	while raw[i] & 0x80 == 0:
		array.append(raw[i])
		i += 1

	array.append(raw[i] & ~0x80)

	if len(array) == 1 and array[0] == 0x00:
		return ""

	return bytes(array).decode("ascii")

# decode a varint from the bytes in `raw`.
# Returns the decoded integer, and additionally how long that integer was.
def decode_varint(raw: bytes) -> Tuple[int, int]:
	value = 0

	i = 0
	while True:
		value *= 128
		value += raw[i] & 0x7F

		if raw[i] & 0x80 == 0:
			i += 1
			break

		i += 1

	return value, i

assert decode_varint(b"\x23") == (0x23, 1)
assert decode_varint(b"\x8F\x04") == (0x0F * 128 + 0x04, 2)

