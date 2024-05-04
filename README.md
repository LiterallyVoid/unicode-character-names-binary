This project compiles Unicode data in the format described by <https://www.unicode.org/reports/tr42/> to a compact binary file, storing character names and ages (when a character was first introducted to Unicode).

The header consists of a magic, a version, and the locations and sizes of three separate chunks. All integers in the header are unsigned 32-bit little-endian integers.

  * Magic: always "UCDNAMES"
  * Version (always `2`)

  * Nametable location (always aligned to 4 bytes)
  * Nametable size (in bytes)

  * Unique age table (always aligned to 4 bytes)
  * Unique age table size (in bytes)

  * Range list (always aligned to 4 bytes)
  * Range list size (in bytes)

To look up a character, find the Range containing that codepoint. Each Range is two 32-bit unsigned integers.

The first integer is a packed representation of:
  * The first character in the range (24 bits)
  * This range's class
    * `0`: reserved
    * `1`: noncharacter
    * `2`: surrogate
    * `3`: character
  * This range's age, index into the unique age table.

The second integer is a byte index into the nametable.

The nametable is a packed prefix tree. Each tree node contains a *prefix* and a *suffix*.

To read a tree node by its byte index:

* Read a single `varint`, which is the offset from this tree node's index to the index of its prefix,
* Read a `var_ascii` string of this tree node's suffix.

If the offset points at byte zero of the prefix table, then this node does not have a prefix. The nametable is guaranteed to never have a valid node at byte offset `0`.

For example, if one tree node starts at index `150`, it could have:
  * A two-byte `varint` of `130`, pointing at the tree node to its prefix at byte index `20` in the nametable.
  * A three-byte suffix, making this tree node five bytes long in the file.

The age table is a list of `var_ascii` strings.

A `varint` is an unsigned LEB128 integer.

A `var_ascii` string is a self-terminated ASCII string. Its last byte, and no other bytes, has the 8th bit set. There is no way to encode an empty `var_ascii` string.

I chose to set the high bit on only the last byte, instead of on all bytes except the last byte (like `LEB128`), so that these ASCII strings are viewable in hexdumps.
