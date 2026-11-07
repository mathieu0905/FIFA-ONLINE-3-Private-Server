"""Apply probability authoring support to the isolated candidate, never to live data."""
from pathlib import Path
import shutil
R = Path(__file__).resolve().parent
S = Path(r'D:\FO3ID\server')
P = R / 'sandbox/server'

def replace(source, old, new):
    assert source.count(old) == 1, old[:100]
    return source.replace(old, new, 1)

h = (R/'http_config.py').read_text(encoding='utf8')
h = replace(h, '    n = PACKS[itemid][1].get("grade", 1)', '''    if 'probability_mode' in PACKS[itemid][1]:
        from pack_probability import grades
        return grades(PACKS[itemid][1])
    n = PACKS[itemid][1].get("grade", 1)''')
h = replace(h, '("top", "ovr", "grade", "pos", "league") if v.get(k)', '("top", "ovr", "grade", "min_grade", "probability_mode", "probability_formula", "grade_probabilities", "pos", "league") if v.get(k)')
h = replace(h, '("top", "ovr", "grade", "pos", "league")}}', '("top", "ovr", "grade", "min_grade", "probability_mode", "probability_formula", "grade_probabilities", "pos", "league")}}')
(R/'http_config.py').write_text(h,encoding='utf8')
a=(S/'admin.py').read_text(encoding='utf8')
a=replace(a, '@api("shop")', '''def probability_frozen(itemid):
    catalogue = getattr(hc, 'pack_catalogue', {}).get('items', {})
    cadence = getattr(hc, 'pack_cadence', None)
    products = getattr(hc, 'product_packs', {})
    return (str(itemid) in catalogue or
            cadence is not None and (itemid in cadence.items or itemid in cadence.legacy) or
            str(itemid) in products.get('risk_packs', {}) or str(itemid) in products.get('strength_packs', {}))


def probability_definition(itemid, entry):
    definition = hc.pack_to(entry)
    if probability_frozen(itemid):
        rows = [(g, w) for g, w in hc.pack_grades(itemid) if w > 0]
        low, high = min(g for g,w in rows), max(g for g,w in rows)
        weights = dict(rows); total = sum(weights.values())
        definition.update(min_grade=low, grade=high, probability_mode='manual', probability_locked=True,
                          grade_probabilities=[weights.get(g, 0)*100/total for g in range(low, high+1)])
    return definition


@api("shop")''')
a=replace(a, '"def": to(entry)})', '"def": probability_definition(i, entry) if kind == "packs" else to(entry)})')
a=replace(a, '        return {"name": name, "icon": icon_of(d.get("icon"), False),', '''        from pack_probability import clean
        try:
            probability = clean({**d, 'min_grade': d.get('min_grade') or 1,
                                 'grade': d.get('grade') or 1,
                                 'probability_mode': d.get('probability_mode') or 'legacy'}, hc.MAX_GRADE)
        except ValueError as error:
            raise AdminError(str(error))
        return {**probability, "name": name, "icon": icon_of(d.get("icon"), False),''')
# Do not let the existing nullable grade field replace the validated high bound.
a=replace(a, '"grade": opt("grade", 1, hc.MAX_GRADE, ("f_grade",)), "pos": pos or None,', '"grade": probability["grade"], "pos": pos or None,')
a=replace(a, '    cfg.setdefault(kind, {})[str(itemid)] = check_def(kind, p.get("def") or {}, itemid)', '''    definition = check_def(kind, p.get("def") or {}, itemid)
    if kind == 'packs' and probability_frozen(itemid):
        from pack_probability import grades
        actual = [(g,w) for g,w in hc.pack_grades(itemid) if w > 0]
        submitted = [(g,w) for g,w in grades(definition) if w > 0]
        total = sum(w for g,w in actual)
        if len(actual) != len(submitted) or any(g != a or abs(w*100/total-b) > 0.00001 for (g,w),(a,b) in zip(actual,submitted)):
            raise AdminError('已发行卡包的概率已冻结；请按此新建卡包后调整')
    cfg.setdefault(kind, {})[str(itemid)] = definition''')
anchor='@api("shop_save")'
a=replace(a,anchor,'''@api("pack_probability_preview")
def pack_probability_preview(p):
    from pack_probability import clean
    try:
        return clean(p, hc.MAX_GRADE)
    except ValueError as error:
        raise AdminError(str(error))


'''+anchor)
(R/'admin.py').write_text(a,encoding='utf8')
ui=(S/'admin/index.html').read_text(encoding='utf8')
ui=replace(ui, '.grid2 { display: grid;', '.grid2 { align-items: start; display: grid;')
ui=replace(ui,'ovr: null, grade: null, pos:', 'ovr: null, grade: 11, min_grade: 6, probability_mode: "formula", pos:')
ui=replace(ui, 't(p ? "edit_kind" : "new_kind",', 't(p?.itemid ? "edit_kind" : "new_kind",')
ui=replace(ui, 'p ? `itemid ${p.itemid}` : "";', 'p?.itemid ? `itemid ${p.itemid}` : "";')
ui=replace(ui,'${field(t("f_grade"), num("grade", d.grade, 1, MAX_GRADE))}', '''<div class="grid2" style="grid-column:1/-1">${field("最低强化", num("min_grade", d.min_grade ?? 1, 1, MAX_GRADE))}
      ${field("最高强化", num("grade", d.grade ?? 1, 1, MAX_GRADE))}
      ${field("强化概率模式", `<select data-k="probability_mode"><option value="formula" ${(d.probability_mode === 'formula') ? 'selected' : ''}>统一公式（自动计算）</option><option value="manual" ${d.probability_mode === 'manual' ? 'selected' : ''}>自定义概率</option><option value="legacy" ${!d.probability_mode || d.probability_mode === 'legacy' ? 'selected' : ''}>保留旧版递减概率</option></select>`)}
      </div><div class="f" style="grid-column:1/-1"><span>各强化档概率（%）</span><div id="gradeProbabilityRows" style="display:flex;flex-wrap:wrap;gap:6px"></div><small id="gradeProbabilitySummary"></small><button type="button" class="b small" id="resetGradeFormula">按公式重算</button></div>''')
ui=replace(ui,'  if (kind === "items") { editing.itemDef = d;', '  if (kind === "packs") { editing.probabilityDef = d; renderGradeProbabilities(); }\n  if (kind === "items") { editing.itemDef = d;')
ui=replace(ui,'  $("#editor").showModal();', '''  if (kind === 'packs' && d.probability_locked) {
    $('[data-k="min_grade"]').disabled = true;
    $('[data-k="grade"]').disabled = true;
    $('[data-k="probability_mode"]').disabled = true;
    $('#resetGradeFormula').disabled = true;
    $('#gradeProbabilityRows').insertAdjacentHTML('beforebegin', '<p>已发行概率固定。<button type="button" class="b small" id="clonePack">用此强化概率新建</button></p>');
  }
  $("#editor").showModal();''')
ui=replace(ui,'grade: optNum("grade"), pos:', '''grade: optNum("grade"), min_grade: optNum("min_grade"), probability_mode: v("probability_mode"),
    grade_probabilities: $$("[data-grade-probability]", f).map(e => Number(e.value)), pos:''')
ui=replace(ui,'  if (tg.id === "edIconBtn")', '''  if (tg.id === 'clonePack') {
    const d = readEditor(); Object.assign(d, {probability_locked:false, name:'', seasons:[], top:null, ovr:null, pos:null, league:null});
    $('#editor').close(); openEditor('packs', {itemid: null, def:d}); return;
  }
  if (tg.id === "resetGradeFormula") {
    $('[data-k="probability_mode"]').value = 'formula'; renderGradeProbabilities(); return;
  }
  if (tg.id === "edIconBtn")''')
ui=replace(ui,'  if (e.target.dataset.k === "type")', '''  if (['grade', 'min_grade', 'probability_mode'].includes(e.target.dataset.k)) renderGradeProbabilities();
  if (e.target.dataset.k === "type")''')
ui=replace(ui,'function renderTypeFields(type) {', '''let probabilityRequest = 0;
async function renderGradeProbabilities() {
  const request = ++probabilityRequest;
  const low = Number($('[data-k="min_grade"]').value), high = Number($('[data-k="grade"]').value);
  const mode = $('[data-k="probability_mode"]').value;
  const box = $('#gradeProbabilityRows'), summary = $('#gradeProbabilitySummary');
  $('[data-k="min_grade"]').setCustomValidity(low > high ? '最低强化不能高于最高强化' : '');
  if (!Number.isInteger(low) || !Number.isInteger(high) || low < 1 || high > MAX_GRADE || low > high) {
    box.innerHTML = ''; summary.textContent = '最低强化不能高于最高强化，范围1～' + MAX_GRADE; return;
  }
  try {
    // The server computes the preview using the same function that draws cards.
    const result = await api('pack_probability_preview', {min_grade: low, grade: high, probability_mode: mode === 'legacy' ? 'legacy' : 'formula'});
    if (request !== probabilityRequest || !editing || editing.kind !== 'packs') return;
    const old = editing.probabilityDef;
    const saved = mode === 'manual' && old.min_grade === low && old.grade === high && old.grade_probabilities?.length === high-low+1;
    const values = saved ? old.grade_probabilities : result.grade_probabilities;
    box.innerHTML = values.map((p,i) => `<label style="display:inline-flex;align-items:center;gap:3px;white-space:nowrap;margin:4px">+${low+i} <input aria-label="+${low+i}概率" type="number" data-grade-probability="${low+i}" min="0" max="100" step="any" value="${p}" style="width:85px" ${mode !== 'manual' || old.probability_locked ? 'readonly' : ''}>%</label>`).join('');
    updateProbabilityTotal();
  } catch (error) { summary.textContent = error.message; }
}
function updateProbabilityTotal() {
  const sum = $$('[data-grade-probability]').reduce((s,e) => s + Number(e.value), 0);
  const valid = Number.isFinite(sum) && Math.abs(sum - 100) < 0.00001;
  const first = $('[data-grade-probability]');
  if (first) first.setCustomValidity(valid ? '' : '各档概率合计必须为100%');
  $('#gradeProbabilitySummary').style.color = valid ? '' : '#ffb6a8';
  $('#gradeProbabilitySummary').textContent = '合计 ' + Number(sum.toFixed(6)) + '%；自定义必须为100%。公式：六档锚点30/28/25/10/6/1，按强化范围插值并归一化。';
}
$('#editorBody').addEventListener('input', e => {
  if (e.target.hasAttribute('data-grade-probability')) {
    editing.probabilityDef = {...readEditor()}; updateProbabilityTotal();
  }
});
function renderTypeFields(type) {''')
(R/'admin').mkdir(exist_ok=True)
(R/'admin/index.html').write_text(ui,encoding='utf8')
for name in ('http_config.py','admin.py','pack_probability.py','admin/index.html'):
    shutil.copyfile(R/name,P/name)
print('Probability editor and shared formula built in isolated candidate')
