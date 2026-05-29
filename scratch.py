import base64

def _chunks(text: str, size: int = 73) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)]

encoded = "HelloWorld1234567890"
packed = encoded[::-1]
parts = _chunks(packed)
table = [(index * 7 + 3, part) for index, part in enumerate(parts)]

# Runtime simulation:
assembled = ''.join(_9 for _8,_9 in sorted(table,key=lambda _a:_a[0]))
_7 = assembled[::-1]

print("encoded:", encoded)
print("packed:", packed)
print("_7:", _7)
print("Is _7 equal to packed?", _7 == packed)
print("Is _7 equal to packed[::-1]?", _7 == packed[::-1])
print("Is _7 equal to encoded?", _7 == encoded)
