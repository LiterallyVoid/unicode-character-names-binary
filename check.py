#! /usr/bin/env python3

import argparse, struct

from util import decode_var_ascii, decode_varint
from typing import TextIO

def parse_args():
	parser = argparse.ArgumentParser(
		prog = 'check-bin',
		description = "Parse a unicode data binary file, that's in the format that `compile.py` uses.",
	)
	parser.add_argument(
		'filename',
		type = argparse.FileType('rb'),
	)

	return parser.parse_args()

def main() -> None:
	args = parse_args()

	file = args.filename
	data = file.read()

	magic, version, trie, trie_size, ages, ages_size, ranges, ranges_size = struct.unpack("<8sIIIIIII", data[0:36])

	unique_ages = []
	i = 0
	while i < ages_size:
		age = decode_var_ascii(data[ages + i:ages + ages_size])
		i += len(age)

		unique_ages.append(age)

	assert magic == b"UCDNAMES"
	assert version == 2

	def read_name(index: int) -> str:
		if index == 0:
			return ""

		name_data = data[trie + index:trie + index + 100]

		prefix_offset, prefix_len = decode_varint(name_data)
		prefix = index - prefix_offset

		suffix = decode_var_ascii(name_data[prefix_len:])

		return read_name(prefix) + suffix

	for i in range(0, ranges_size, 8):
		bits, name = struct.unpack("<II", data[ranges + i:ranges + i + 8])
		name = read_name(name)

		range_first = bits & 0x00FF_FFFF
		range_class_index = (bits >> 24) & 0b11
		range_age = (bits >> 26)

		range_class = [
			"reserved",
			"noncharacter",
			"surrogate",
			"character",
		][range_class_index]

		age = unique_ages[range_age]

		print(f"U+{range_first:04X} {name!r} (cls: {range_class}, first introduced: {age})")

if __name__ == '__main__':
	main()
