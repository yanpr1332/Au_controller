"""Bounded, read-only media candidate search. Never relinks ambiguous matches."""
from pathlib import Path
import os


class AuditionMediaSearch:
    @classmethod
    def search_session_media(cls, source, roots, *, expected_hashes=None, max_files=20000):
        src, tree, root, tracks = cls._native_tree(source)
        if not isinstance(roots, list) or not 1 <= len(roots) <= 12 or type(max_files) is not int or not 1 <= max_files <= 200000:
            raise ValueError('1..12 search roots and file budget 1..200000 required')
        folders = [Path(p).resolve() for p in roots]
        if any(not p.is_dir() for p in folders):
            raise ValueError('Search roots must be existing directories')
        hashes = expected_hashes or {}
        if not isinstance(hashes, dict): raise ValueError('Expected hashes must be a file-ID mapping')
        media = root.findall('./files/file')+root.findall('./session/files/file')
        missing = []
        for node in media:
            absolute, relative = node.get('absolutePath'), node.get('relativePath')
            valid = bool(absolute and Path(absolute).is_file()) or bool(relative and (src.parent/relative).is_file())
            if not valid:
                name = Path(absolute or relative or '').name
                missing.append(dict(file_id=node.get('id'), name=name, candidates=[]))
        names = {m['name'].casefold() for m in missing if m['name']}
        seen = set(); scanned = 0; truncated = False
        candidates = {}
        for folder in folders:
            if truncated: break
            for parent, dirs, files in os.walk(folder, followlinks=False):
                dirs[:] = sorted(d for d in dirs if not (Path(parent)/d).is_symlink())
                for name in sorted(files):
                    path = (Path(parent)/name).resolve()
                    if path in seen or folder not in path.parents: continue
                    if scanned >= max_files:
                        truncated = True; break
                    seen.add(path); scanned += 1
                    if name.casefold() in names and path.is_file():
                        if sum(map(len,candidates.values())) >= 512:
                            truncated = True; break
                        candidates.setdefault(name.casefold(), []).append(dict(path=str(path), bytes=path.stat().st_size, sha256=cls._hash_file(path)))
                if truncated: break
        for item in missing:
            expected = hashes.get(item['file_id'])
            item['candidates'] = [c for c in candidates.get(item['name'].casefold(), []) if expected is None or c['sha256'] == expected]
            item['ambiguous'] = len(item['candidates']) > 1
            item['selection_required'] = True
        return dict(source=str(src), scanned_files=scanned, truncated=truncated, missing_media=missing,
                    source_modified=False, automatic_relink=False)
