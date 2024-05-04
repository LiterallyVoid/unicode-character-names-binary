#! /usr/bin/env python3

import sys, argparse, time, struct, typing
from collections import defaultdict
from compress import StringCompressor, encode_varint, encode_var_ascii

from dataclasses import dataclass
from enum import StrEnum

import xml.etree.ElementTree as ET

class TaskStatusReporter:
	def __init__(self, name):
		self.name = name
		self.start_time = time.time()

	def complete(self):
		duration_seconds = time.time() - self.start_time
		print(f"done in {duration_seconds:.3}s", file = sys.stderr)

	def __enter__(self):
		print(self.name + "...", file = sys.stderr, end = "")
		sys.stderr.flush()

	def __exit__(self, _type, _value, _traceback):
		self.complete()

class StatusReporter:
	def __init__(self):
		pass

	def start(self, name: str) -> TaskStatusReporter:
		return TaskStatusReporter(name)

UCD_NAMESPACE = "http://www.unicode.org/ns/2003/ucd/1.0"

# Returns a range of [first, last], retrieved either from the node's `ucd:cp` attribute or its `ucd:first-cp` and `ucd:last-cp` attributes.
def get_range(et: ET.Element) -> list[int]:
	if (codepoint_string := et.get("cp")) is not None:
		codepoint = int(codepoint_string, 16)
		return [codepoint, codepoint]

	first_string = et.get("first-cp")
	last_string = et.get("last-cp")

	assert first_string is not None and last_string is not None

	first = int(first_string, 16)
	last = int(last_string, 16)

	return [first, last]

class RangeClass(StrEnum):
	reserved = "reserved"
	noncharacter = "noncharacter"
	surrogate = "surrogate"
	character = "char"

class Range:
	def __init__(self, first: int, last: int, class_: RangeClass, name, age):
		self.first = first
		self.last = last
		self.class_ = class_
		self.name = name
		self.age = age

def read_ranges(ucd: ET.Element) -> list[Range]:
	ns = {"ucd": UCD_NAMESPACE}

	repertoire = ucd.find("ucd:repertoire", ns)
	assert repertoire is not None

	total_characters = 0
	total_noncharacters = 0
	total_reserved = 0
	total_surrogate = 0

	all_ranges: list[Range] = []

	for class_ in RangeClass:
		for range_element in repertoire.findall(".//{*}" + class_):
			range = get_range(range_element)

			name = range_element.get("na")
			if name == "":
				first_alias = range_element.find("ucd:name-alias", ns)
				if first_alias is not None:
					name = first_alias.get("alias")

			age = range_element.get("age")

			all_ranges.append(Range(range[0], range[1], class_, name, age))

	return all_ranges

def parse_args():
	parser = argparse.ArgumentParser(
		prog = 'compile-unicode',
		description = "Compile codepoint names from a Unicode XML Data file into a binary blob",
	)
	parser.add_argument(
		'filename',
		type = argparse.FileType('r'),
	)
	parser.add_argument(
		'-o', '--out',
		required = True,
		type = argparse.FileType('wb'),
	)

	return parser.parse_args()

def align_file_to_u32(file: typing.BinaryIO):
	location = file.tell()

	for i in range(location % 4):
		file.write(b"\x00")

def main():
	reporter = StatusReporter()

	args = parse_args()

	with reporter.start("Parsing XML"):
		tree = ET.parse(args.filename)
	
	with reporter.start("Reading ranges"):
		ranges = read_ranges(tree.getroot())


	with reporter.start("Checking that ranges are complete and non-overlapping"):
		ranges.sort(key = lambda range: range.first)

		index = 0

		for range in ranges:
			assert range.first == index
			index = range.last + 1

		assert index == 0x10FFFF + 1

	ages: dict[str, int] = {}

	with reporter.start("Writing to file"):
		compressor = StringCompressor()

		for range in ranges:
			compressor.register(range.name.encode("ascii"))

		header_format = "<8sIIIIIII"
		# Overwritten later with correct data.
		args.out.write(struct.pack(header_format,
			# Magic
			b"",

			# Version
			0,

			# Prefix trie location
			0,

			# Prefix trie size
			0,

			# Unique age (introduced unicode version) strings location
			0,

			# Age list size
			0,

			# Range list location
			0,

			# Range list size
			0,
		))

		align_file_to_u32(args.out)
		range_list_location = args.out.tell()
		range_list_size = 0
		for range in ranges:
			range_start = range.first
			range_start |= {
				RangeClass.reserved: 0,
				RangeClass.noncharacter: 1,
				RangeClass.surrogate: 2,
				RangeClass.character: 3,
			}[range.class_] << 24
			
			age_index = ages.get(range.age)
			if age_index is None:
				age_index = len(ages)
				ages[range.age] = age_index

			range_start |= age_index << 26

			args.out.write(struct.pack('<I', range_start))
			args.out.write(struct.pack('<I', compressor.compress(range.name.encode("ascii"))))
			range_list_size += 8

		align_file_to_u32(args.out)
		trie_location = args.out.tell()
		trie_size = len(compressor.prefix_trie_bytes)
		args.out.write(compressor.prefix_trie_bytes)

		align_file_to_u32(args.out)
		ages_location = args.out.tell()
		ages_size = 0
		for age in ages.keys():
			encoded = encode_var_ascii(age.encode("ascii"))
			args.out.write(encoded)
			ages_size += len(encoded)

		align_file_to_u32(args.out)

		args.out.seek(0)
		args.out.write(struct.pack(header_format,
			# Magic
			b"UCDNAMES",

			# Version
			1,

			trie_location,
			trie_size,

			ages_location,
			ages_size,

			range_list_location,
			range_list_size,
		))

		args.out.seek(0, 2) # whence 2: offset from end of file
		print(args.out.tell() / 1024, "KiB")

if __name__ == "__main__":
	main()
