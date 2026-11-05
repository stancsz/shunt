"""Inspect explicitly supplied Python file scope; never predict future edits."""
import ast
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=32)
def _line_count(name, source):
    """Cache pure parsing by actual content, never by filesystem timestamps."""
    tree=ast.parse(source,filename=name)
    covered=set()
    for node in tree.body:
        start=min([node.lineno]+[d.lineno for d in getattr(node,'decorator_list',[])])
        covered.update(range(start,node.end_lineno+1))
    return len(covered)


def inspect_scope(paths):
    files=list(dict.fromkeys(str(Path(p).resolve()) for p in paths))
    if not files:
        raise ValueError('At least one scope file is required')
    lines=0
    for name in files:
        path=Path(name)
        if path.suffix != '.py':
            raise ValueError('AST inspection currently supports Python files only')
        if path.stat().st_size>1_000_000:
            raise ValueError('Scope file exceeds one megabyte')
        # Read every request so changed contents cannot reuse stale AST results.
        lines+=_line_count(name,path.read_text(encoding='utf-8-sig'))
    return len(files),lines
