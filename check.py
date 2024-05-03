#! /usr/bin/env python3

import argparse, struct

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

def unpack_from_file(format, file):
	size = struct.calcsize(format)
	return struct.unpack(format, file.read(size))

def unpack_var_ascii(raw) -> bytes:
	array = bytearray()
	i = 0
	while raw[i] & 0x80 == 0:
		array.append(raw[i])
		i += 1

	array.append(raw[i] & ~0x80)

	if len(array) == 1 and array[0] == 0x00:
		return ""

	return bytes(array).decode("ascii")

def unpack_varint(raw) -> int:
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

assert unpack_varint(b"\x23") == (0x23, 1)
assert unpack_varint(b"\x8F\x04") == (0x0F * 128 + 0x04, 2)

def main():
	args = parse_args()

	file = args.filename
	data = file.read()

	magic, version, trie, trie_size, ages, ages_size, ranges, ranges_size = struct.unpack("<8sIIIIIII", data[0:36])

	unique_ages = []
	i = 0
	while i < ages_size:
		age = unpack_var_ascii(data[ages + i:ages + ages_size])
		i += len(age)

		unique_ages.append(age)

	assert magic == b"UCDNAMES"
	assert version == 1

	def read_name(index):
		if index == 0:
			return ""

		name_data = data[trie + index:trie + index + 100]

		prefix_offset, prefix_len = unpack_varint(name_data)
		prefix = index - prefix_offset

		suffix = unpack_var_ascii(name_data[prefix_len:])

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
