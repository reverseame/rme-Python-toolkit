import hashlib

import ijson


def read_json_chunks(path, chunk_size):
    with open(path, encoding="latin-1") as f:
        parser = ijson.items(f, "item")
        chunk = []
        for item in parser:
            chunk.append(item)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

def file_sha256(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()
