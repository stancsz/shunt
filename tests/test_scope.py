from pathlib import Path
import pytest
from shunt.scope import inspect_scope


def test_python_scope(tmp_path):
    a=tmp_path/'a.py'; a.write_text('# comment\n\ndef f():\n    return 1\n')
    b=tmp_path/'b.py'; b.write_text('x = 1\n')
    assert inspect_scope([a,a])==(1,2)
    assert inspect_scope([a,b])==(2,3)


def test_decorators(tmp_path):
    p=tmp_path/'decorated.py'; p.write_text('@decorate\ndef f():\n    pass\n')
    assert inspect_scope([p])==(1,3)


def test_invalid_scope(tmp_path):
    with pytest.raises(ValueError): inspect_scope([])
    p=tmp_path/'x.js'; p.write_text('x=1')
    with pytest.raises(ValueError): inspect_scope([p])
    p=tmp_path/'bad.py'; p.write_text('def!')
    with pytest.raises(SyntaxError): inspect_scope([p])
    with pytest.raises(FileNotFoundError): inspect_scope([tmp_path/'missing.py'])


def test_cache_uses_content_not_timestamp(tmp_path):
    import os
    p=tmp_path/'changed.py'; p.write_text('x=1\ny=2\n')
    previous=p.stat()
    assert inspect_scope([p])==(1,2)
    p.write_text('x=1;y=2\n')
    os.utime(p,ns=(previous.st_atime_ns,previous.st_mtime_ns))
    assert inspect_scope([p])==(1,1)
    p.write_text('invalid syntax !')
    with pytest.raises(SyntaxError): inspect_scope([p])
