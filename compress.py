from dataclasses import dataclass
from collections import defaultdict
from typing import Iterable
import struct

from util import encode_var_ascii, encode_varint

class StringCompressor:
	def __init__(self) -> None:
		# One byte, so that index `0` is never used for a different prefix.
		self.prefix_trie_bytes = bytearray([0])
		self.prefixes: dict[bytes, int] = {b'': 0}

		self.occured: set[bytes] = set()
		self.unique_edges: defaultdict[bytes, int] = defaultdict(int)

	def register(self, entry: bytes) -> None:
		if entry == b"": return
		if entry in self.occured:
			return

		self.occured.add(entry)
		self.unique_edges[entry[:-1]] += 1

		self.register(entry[:-1])

	# Always returns True if prefix is `b''`
	def should_use_prefix(self, prefix: bytes) -> bool:
		return prefix == b"" or self.unique_edges[prefix] > 1

	def compress(self, entry: bytes) -> int:
		if (existing := self.prefixes.get(entry)) is not None:
			return existing

		if len(entry) == 0:
			return 0

		chunk_size = 1

		while not self.should_use_prefix(entry[:-chunk_size]):
			chunk_size += 1

		prefix_index = self.compress(entry[:-chunk_size])
		suffix = entry[-chunk_size:]

		inserted_index = len(self.prefix_trie_bytes)

		self.prefix_trie_bytes.extend(encode_varint(inserted_index - prefix_index))
		self.prefix_trie_bytes.extend(encode_var_ascii(suffix))

		self.prefixes[entry] = inserted_index

		return inserted_index
