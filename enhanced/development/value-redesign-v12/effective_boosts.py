"""Read the installed boost assignments without importing HTTP or running hooks."""
from pathlib import Path
import ast,types
S=Path('D:/FO3ID/server')
def grade_boosts():
 tree=ast.parse((S/'http_config.py').read_text('utf8'));assign=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='GRADE_BOOST' for t in n.targets));scope={'MAX_GRADE':20}
 exec(compile(ast.Module(body=[assign],type_ignores=[]),'installed_base_boost_assignment','exec'),scope)
 host=types.SimpleNamespace(MAX_GRADE=20,GRADE_BOOST=scope['GRADE_BOOST'])
 extension=ast.parse((S/'enhancement20.py').read_text('utf8'));override=next(n for f in extension.body if isinstance(f,ast.FunctionDef) and f.name=='install' for n in f.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=='GRADE_BOOST' for t in n.targets))
 exec(compile(ast.Module(body=[override],type_ignores=[]),'installed_progression_boost_assignment','exec'),{'hc':host})
 return host.GRADE_BOOST
