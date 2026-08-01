import json, re, unicodedata
data = json.load(open(r'I:\GitHub\statsfut\statsfut\media\videos\temp\kaggle_timeline_478821.json', encoding='utf-8'))
aw = data['words']

def remove_accents(s): return ''.join([c for c in unicodedata.normalize('NFD', s) if not unicodedata.combining(c)]) if s else ''

# Over 2.5 text:
text_after = "Seguindo as estatísticas de Over 2.5, para over dois vírgula cinco gols, a estatística aponta sessenta e três por cento de chance."
text_after = text_after.replace('.5', ' ponto 5')
stopwords = {'mercado', 'over', 'ponto', 'cinco', 'para', 'como', 'mais', 'menos', 'estatisticas', 'probabilidade', 'cento', 'isso', 'esse', 'essa', 'sugere', 'indica'}
words_after = [remove_accents(w) for w in re.sub(r'[^\w\s]', '', text_after.lower()).split() if len(w) > 3 and remove_accents(w) not in stopwords]
anchor_words = words_after[:12]
target_anchors = anchor_words[:6]

clean_roteiro_text = "..." # Too long, I will hardcode the estimated idx
# Over 1.5 was at 15.78s (idx=45 roughly)
# search_start_idx = 46

bs = 0
bi = -1
for j in range(46, 448):
    c = []
    for k in range(15):
        if j+k < len(aw):
            w = re.sub(r'[^\w\s]', '', remove_accents(aw[j+k]['text'].lower()))
            if w: c.append(w)
    s = 0
    for a in target_anchors:
        for w in c:
            if a==w or (len(a)>3 and len(w)>3 and (a in w or w in a)): s+=1; break
    for idx, w in enumerate(c[:4]):
        if target_anchors and (target_anchors[0]==w or (len(target_anchors[0])>3 and target_anchors[0] in w)): s+=3; break
        if len(target_anchors)>1 and (target_anchors[1]==w or (len(target_anchors[1])>3 and target_anchors[1] in w)): s+=1.5; break
    
    # print(f"j={j}, s={s}, time={aw[j]['start']}")
    if s > bs:
        bs = s
        bi = j

print(f"best_idx={bi}, score={bs}, time={aw[bi]['start']}")
