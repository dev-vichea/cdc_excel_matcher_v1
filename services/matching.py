"""Conservative candidate ranking. Suggestions are NEVER approved stock transactions."""
import json
import re
import unicodedata
from rapidfuzz import fuzz

TRANSLATIONS = {
    '堆垛架': 'stacking rack',
    '周转车': 'material handling trolley',
    '工业缝纫机': 'industrial sewing machine',
    '布料架': 'fabric rack',
    '自动模板机': 'automatic template sewing machine',
    '裁剪台': 'cutting table',
    '缝纫机': 'sewing machine',
    '货架': 'storage rack',
}

STOP={'the','a','an','of','for','and','with','in','machine','equipment'}

def normalize(s):
    s=unicodedata.normalize('NFKC',str(s or '')).lower()
    s=re.sub(r'[^\w\s]+',' ',s)
    return ' '.join(s.split())

def translate(chinese, provided='', online=False, glossary=None):
    zh=str(chinese or '').strip()
    saved=(glossary or {}).get(zh,'')
    if saved:return saved,'saved translation'
    local=TRANSLATIONS.get(zh,'')
    if local:return local,'local dictionary'
    if online and zh and re.search(r'[\u3400-\u9fff]',zh):
        try:
            from deep_translator import GoogleTranslator
            value=GoogleTranslator(source='zh-CN',target='en').translate(zh)
            if value:return value,'online translation'
        except Exception:pass
    if provided:return provided,'invoice English description'
    if zh and not re.search(r'[\u3400-\u9fff]',zh):return zh,'source English'
    return '', 'translation unavailable'


def signature(text):
    return {t for t in normalize(text).split() if t not in STOP}


def convert_unit_quantity(qty: float, from_unit: str, to_unit: str):
    """Convert quantity when invoice unit differs from CDC unit.
    Returns (converted_qty, is_converted).
    Formula for m/meters/yd/pcs to Gross: int(qty // 144).
    """
    if qty is None or not from_unit or not to_unit:
        return qty, False
    f = str(from_unit).strip().lower()
    t = str(to_unit).strip().lower()
    if f == t:
        return qty, False
    # m / meter / yd / pcs to Gross: formula = qty // 144
    if f in ['m', 'meter', 'meters', 'yd', 'yard', 'yards', 'pcs', 'pc'] and t == 'gross':
        return int(float(qty) // 144), True
    # Doz to Gross: formula = qty // 12
    if f in ['doz', 'dz', 'dozen'] and t == 'gross':
        return int(float(qty) // 12), True
    # Pcs to Doz: formula = qty // 12
    if f in ['pcs', 'pc', 'piece', 'pieces'] and t in ['doz', 'dz', 'dozen']:
        return int(float(qty) // 12), True
    return qty, False


def candidate_score(source, target):
    a,b=normalize(source),normalize(target)
    if not a or not b:return 0
    ratio=fuzz.ratio(a,b)
    token=fuzz.token_set_ratio(a,b)
    x,y=signature(a),signature(b)
    overlap=100*len(x&y)/max(len(x|y),1)
    # Prevent generic 'machine' alone from implying a good match
    score=.35*ratio+.4*token+.25*overlap
    # Category cues: a rack should rank against racks, not against fabric rolls.
    if "rack" in x and "rack" in y:score=max(score,62)
    if "trolley" in x and "trolley" in y:score=max(score,62)
    return round(score,1)


def load_mappings(path):
    try:
        with open(path,encoding='utf-8') as f:return json.load(f)
    except (OSError,ValueError):return {}


def build_results(shipping, cdc, mappings=None, online=False, glossary=None, overrides=None):
    mappings=mappings or {}
    overrides=overrides or {}
    results=[]
    for ship in shipping:
        override=overrides.get((ship['sheet'],ship['row']))
        if override:
            translated,method=override,'reviewer correction'
        else:
            translated,method=translate(ship['chinese'],ship['english_provided'],online,glossary)
        # A reviewed term takes priority over supplier English; otherwise use
        # both the supplier description and the automatic translation.
        query=translated if method in ('saved translation','reviewer correction') else ship['english_provided'] or translated
        key=normalize(ship['chinese'])
        candidates=[]
        for item in cdc:
            # Evaluate shipper English and Chinese translation separately; concatenating
            # them can mis-rank unrelated fabric entries.
            score=max(candidate_score(q,item['description']) for q in [query,translated] if q) if (query or translated) else 0
            unit_ok=normalize(ship['unit'])==normalize(item['unit']) or convert_unit_quantity(ship.get('qty'), ship.get('unit'), item['unit'])[1]
            candidates.append({**item,'score':score,'unit_compatible':unit_ok})
        candidates.sort(key=lambda c:c['score'],reverse=True)
        known=mappings.get(key)
        if isinstance(known,dict):
            known_id=(known.get('sheet'),known.get('row'))
            for i,c in enumerate(candidates):
                if (c['sheet'],c['row'])==known_id:
                    candidates.insert(0,candidates.pop(i));method+=' + saved mapping';break
        # No auto-confirm; all suggestions have to be reviewed, especially different companies.
        top=candidates[0] if candidates else None
        status='POSSIBLE MATCH — REVIEW' if top and top['score']>=60 else 'UNMATCHED'
        if not query:status='TRANSLATION NEEDED'
        results.append({**ship,'translated':translated,'translation_method':method,'query':query,
                        'candidates':candidates[:5],'suggestion':top,'status':status})
    return results
