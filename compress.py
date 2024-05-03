from dataclasses import dataclass
from collections import defaultdict
from typing import Iterable
import struct

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

class StringCompressor:
	def __init__(self):
		# One byte, so that index `0` is never used for a different prefix.
		self.prefix_trie_bytes = bytearray([0])
		self.prefixes: dict[bytes, int] = {b'': 0}

		self.occured = set()
		self.unique_edges = defaultdict(int)

	def register(self, entry: bytes) -> int:
		if entry == b"": return

		if entry not in self.occured:
			self.occured.add(entry)
			self.unique_edges[entry[:-1]] += 1

		self.register(entry[:-1])

	def insert_common_prefixes(self):
		pass

	def compress(self, entry: bytes) -> int:
		if (existing := self.prefixes.get(entry)) is not None:
			return existing

		if len(entry) == 0:
			return 0

		chunk_size = 1

		prefix_index = self.compress(entry[:-1])
		suffix = entry[-1:]

		inserted_index = len(self.prefix_trie_bytes)

		self.prefix_trie_bytes.extend(encode_varint(inserted_index - prefix_index))
		self.prefix_trie_bytes.extend(encode_var_ascii(suffix))

		self.prefixes[entry] = inserted_index

		return inserted_index

	def estimate_size(self):
		return len(self.prefix_trie_bytes)
