"""Fixed five enhancement sets with a six-starter threshold; work artifacts only."""
from pathlib import Path
import ast, hashlib, json
R=Path(__file__).resolve().parent;S=Path(r'D:\FO3ID\server')
ROOT=R;SERVER=S
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def transform(source):
    newline='\r\n' if '\r\n' in source else '\n'
    source=source.replace('\r\n','\n')
    tree=ast.parse(source)
    is_grade=lambda n:isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TC_GRADE' for t in n.targets) or isinstance(n,ast.AugAssign) and isinstance(n.target,ast.Name) and n.target.id=='TC_GRADE'
    definitions=[n for n in tree.body if is_grade(n)]
    if not definitions:raise RuntimeError('Current TC_GRADE declaration absent')
    first,last=definitions[0],definitions[-1]
    between=[n for n in tree.body if first.lineno<=n.lineno<=last.end_lineno]
    if not all(is_grade(n) for n in between):raise RuntimeError('Other executable code interleaves grade declarations')
    new='''# Fixed enhancement sets: >=6 eligible starters unlock each threshold.
# Counts 6..11 have the same bonus; each player gets only the best grade
# threshold they meet. Supersedes all former range and single-grade colors.
TC_GRADE = tuple((10100 + g, g, f"强化+{g}套装", _tc_groups((6, 11, bonus)))
                 for g, bonus in ((5, 3), (9, 5), (12, 7), (16, 9), (20, 12)))
'''
    lines=source.splitlines(keepends=True)
    result=''.join(lines[:first.lineno-1])+new+''.join(lines[last.end_lineno:]);compile(result,'http_config.py','exec')
    a,b=ast.parse(source),ast.parse(result)
    # Constants only: all handlers, membership, grade fit and best-of logic exact.
    f=lambda t:{n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,ast.FunctionDef)}
    assert f(a)==f(b)
    return result.replace('\n',newline)
def main():
    old=(S/'http_config.py').read_bytes();new=transform(old.decode('utf8')).encode('utf8')
    (R/'http_config.before.py').write_bytes(old);(R/'http_config.prepared.py').write_bytes(new)
    report=dict(status='PREPARED_NOT_INSTALLED',revision='grade-five-six-v2',scope='Replaces every prior grade color with only five tiers; 6 starters unlock fixed bonus; IM stats/feature, client resources and assets unchanged',
        source=str(S/'http_config.py'),before_sha256=hashlib.sha256(old).hexdigest(),after_sha256=hashlib.sha256(new).hexdigest(),
        tiers={g:[[6,11,bonus]] for g,bonus in ((5,3),(9,5),(12,7),(16,9),(20,12))},formal_files_written=False,services_restarted=False)
    (R/'prepared.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(report,ensure_ascii=True))
if __name__=='__main__':main()
