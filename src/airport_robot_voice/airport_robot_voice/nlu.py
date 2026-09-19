#!/usr/bin/env python3
"""
nlu.py — Lõi hiểu ngôn ngữ, THUẦN PYTHON, KHÔNG phụ thuộc thư viện ngoài.

Vì sao không dùng rapidfuzz/difflib để so khớp cả câu?
--------------------------------------------------------
So khớp "cả câu" theo độ giống ký tự/token cho ra điểm số RẤT khác nhau
tuỳ máy có cài được thư viện đó hay không (đây là nguyên nhân chính khiến
kết quả test dao động mạnh giữa các máy). Engine này dùng SO KHỚP TỪ KHOÁ
CÓ TRỌNG SỐ tự viết (kiểu TF-IDF thu nhỏ), không phụ thuộc thư viện ngoài
nên chạy giống hệt nhau trên mọi máy.

Hai tầng xử lý dấu tiếng Việt
--------------------------------------------------------
Tiếng Việt có 2 loại dấu khác nhau về bản chất:
  1. Dấu THANH ĐIỆU (sắc, huyền, hỏi, ngã, nặng) — STT hay nghe sai/rớt.
  2. Dấu tạo NGUYÊN ÂM GỐC (ô, ơ, ê, ư, ă) — đây là CHỮ CÁI riêng, không
     phải dấu phụ. Xoá cả loại 2 sẽ gộp nhầm các từ khác nghĩa hoàn toàn,
     ví dụ "đói" (hungry) và "đổi" (exchange) đều thành "doi", hay
     "cổng" (gate) và "công" (effort) đều thành "cong".

Vì vậy:
  - `clean()`  — chỉ xoá dấu thanh điệu, GIỮ ô/ơ/ê/ư/ă. Dùng để CHẤM ĐIỂM
    Ý ĐỊNH (nơi độ chính xác quan trọng nhất, tránh gộp nhầm từ).
  - `clean_ascii()` — xoá TOÀN BỘ dấu. Dùng để DÒ SỐ CỔNG / SỐ CHUYẾN BAY /
    TÊN ĐỊA ĐIỂM (nơi cần dung sai cao, chấp nhận cả input gõ tay không dấu
    hoặc STT nghe mất dấu hoàn toàn).
"""

import difflib
import json
import math
import re
import time
import unicodedata

# 5 dấu thanh điệu (huyền, sắc, ngã, hỏi, nặng) trong bảng mã Unicode tổ hợp.
_TONE_MARKS = {0x0300, 0x0301, 0x0303, 0x0309, 0x0323}


def strip_tones(text: str) -> str:
    """Chỉ xoá dấu THANH ĐIỆU, giữ nguyên ô/ơ/ê/ư/ă. VD: 'đổi' -> 'dôi'."""
    text = text.replace('đ', 'd').replace('Đ', 'D')
    nfd = unicodedata.normalize('NFD', text)
    kept = ''.join(c for c in nfd if ord(c) not in _TONE_MARKS)
    return unicodedata.normalize('NFC', kept)


def strip_all(text: str) -> str:
    """Xoá TOÀN BỘ dấu (kể cả ô/ơ/ê/ư/ă). VD: 'đổi' -> 'doi'."""
    text = text.replace('đ', 'd').replace('Đ', 'D')
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', ' ', text, flags=re.UNICODE)
    return re.sub(r'\s+', ' ', text).strip()


def is_accented(text: str) -> bool:
    """True nếu câu có ít nhất 1 ký tự tiếng Việt có dấu. Dùng để chọn
    tầng xử lý dấu phù hợp: câu CÓ dấu -> tin tưởng dấu, giữ nguyên âm
    gốc (chính xác cao); câu KHÔNG dấu (gõ tay/STT mất dấu hoàn toàn)
    -> chuyển sang so khớp bỏ dấu hoàn toàn."""
    return any(ord(c) > 127 for c in normalize(text))


def clean(text: str) -> str:
    """Dùng để CHẤM ĐIỂM Ý ĐỊNH — giữ nguyên âm gốc để tránh gộp nhầm từ."""
    return strip_tones(normalize(text))


def clean_ascii(text: str) -> str:
    """Dùng để DÒ SLOT / TÊN ĐỊA ĐIỂM — dung sai cao, bỏ dấu hoàn toàn."""
    return strip_all(normalize(text))


NUMBER_WORDS = {
    'khong': '0', 'mot': '1', 'hai': '2', 'ba': '3', 'bon': '4', 'tu': '4',
    'nam': '5', 'lam': '5', 'sau': '6', 'bay': '7', 'tam': '8', 'chin': '9',
    'muoi': '10', 'be': 'b', 'xe': 'c', 'de': 'd',
}


def words_to_digits(text: str) -> str:
    return ' '.join(NUMBER_WORDS.get(w, w) for w in text.split())


# Từ đệm tiếng Việt hay gặp trong câu hỏi — không mang tính phân biệt intent
# nên bị loại khỏi bước tính điểm từ khoá. (KHÔNG ảnh hưởng boost_keywords,
# vì boost khớp trên cả câu, không qua bước lọc từ đệm này.)
_STOPWORDS_RAW = """
ơi anh chị em à ạ nhé nhỉ ha hả cho hỏi là gì có không được chưa
bạn tôi mình này đó kia thế nào đâu ở vậy giúp làm ơn xin một chút
đây thì và hay hoặc đến từ của với về các những rất quá ấy như nếu
sẽ đã đang rồi muốn cần nên phải luôn chỉ cũng cả mọi tất cả tớ
nha nè vâng dạ ừ trước sau ra vào lên xuống đi tới nơi chỗ cứ
"""
STOPWORDS = set(clean(w) for w in _STOPWORDS_RAW.split())
STOPWORDS_ASCII = set(clean_ascii(w) for w in _STOPWORDS_RAW.split())


def tokenize(text: str):
    return [w for w in clean(text).split() if w]


def tokenize_ascii(text: str):
    return [w for w in clean_ascii(text).split() if w]


def content_words(text: str):
    """Từ mang nội dung (giữ nguyên âm gốc) — dùng khi input có dấu đầy đủ."""
    return [w for w in tokenize(text) if w not in STOPWORDS]


def content_words_ascii(text: str):
    """Từ mang nội dung (bỏ dấu hoàn toàn) — dùng khi input gõ tay/STT mất
    dấu hoàn toàn, ví dụ 've' thay vì 'vệ'. Chạy song song với bản giữ
    nguyên âm gốc, lấy điểm cao hơn, để không mode nào bị thiệt."""
    return [w for w in tokenize_ascii(text) if w not in STOPWORDS_ASCII]


# ----------------------------------------------------------------------
class NluEngine:
    def __init__(self, intents_file, places_file):
        with open(intents_file, encoding='utf-8') as f:
            self.cfg = json.load(f)
        with open(places_file, encoding='utf-8') as f:
            db = json.load(f)

        self.places = db.get('places', {})
        self.flights = db.get('flights', {})
        self.threshold = float(self.cfg.get('threshold', 40))
        self.priority_margin = float(self.cfg.get('priority_margin', 15))
        self.fallback = self.cfg['fallback_response']
        self.pending = None
        self.ctx_timeout = 15.0

        self._build_vocab()
        self._build_alias_map()

    # ------------------------------------------------------------------
    def _build_vocab(self):
        """Với mỗi intent: gom từ nội dung từ examples + boost_keywords
        thành 'từ điển' riêng. Đồng thời tính idf (độ hiếm) cho mỗi từ
        trên toàn bộ tập intent để tự động hạ trọng số từ đệm/phổ biến."""
        intents = self.cfg['intents']
        n = len(intents)

        for it in intents:
            vocab, vocab_ascii = set(), set()
            for ex in it['examples']:
                vocab.update(content_words(ex))
                vocab_ascii.update(content_words_ascii(ex))
            for kw in it.get('boost_keywords', []):
                vocab.update(content_words(kw))
                vocab_ascii.update(content_words_ascii(kw))
            it['_vocab'] = vocab
            it['_vocab_ascii'] = vocab_ascii
            it['_boost_norm'] = [clean(k) for k in it.get('boost_keywords', [])]
            it['_boost_ascii'] = [clean_ascii(k) for k in it.get('boost_keywords', [])]

        # document frequency: từ này xuất hiện trong bao nhiêu intent
        df, df_ascii = {}, {}
        for it in intents:
            for w in it['_vocab']:
                df[w] = df.get(w, 0) + 1
            for w in it['_vocab_ascii']:
                df_ascii[w] = df_ascii.get(w, 0) + 1

        self.idf = {w: math.log((1 + n) / (1 + d)) + 1.0 for w, d in df.items()}
        self.idf_ascii = {w: math.log((1 + n) / (1 + d)) + 1.0 for w, d in df_ascii.items()}

    def _build_alias_map(self):
        """Dùng clean_ascii (bỏ dấu hoàn toàn) để dò tên địa điểm — chấp
        nhận cả input gõ tay không dấu lẫn STT nghe mất dấu."""
        self.alias_map = {}
        for key, p in self.places.items():
            for name in [key, p.get('name', '')] + p.get('aliases', []):
                name = clean_ascii(str(name))
                if name:
                    self.alias_map[name] = key

    # ------------------------------------------------------------------
    def _word_weight(self, w, ascii_mode=False):
        table = self.idf_ascii if ascii_mode else self.idf
        return table.get(w, 1.0)   # từ lạ (không có trong vocab nào) -> trọng số nền

    def _in_vocab(self, word, vocab):
        """True nếu word khớp thẳng, hoặc khớp gần đúng (dung sai lỗi chính
        tả) với một từ trong vocab. So khớp TỪNG TỪ bằng difflib -> ổn định,
        không phụ thuộc thư viện ngoài."""
        if word in vocab:
            return True
        if len(word) < 5:                     # từ ngắn: không dò lỗi chính tả, tránh khớp nhầm
            return False
        for v in vocab:
            if len(v) < 5 or abs(len(v) - len(word)) > 2:
                continue
            if difflib.SequenceMatcher(None, word, v).ratio() >= 0.88:
                return True
        return False

    # ------------------------------------------------------------------
    # Trích slot (số cổng, số hiệu chuyến bay, tên địa điểm)
    # Dùng clean_ascii (bỏ dấu hoàn toàn) vì đây là các mã/tên riêng,
    # dung sai cao quan trọng hơn là tránh gộp nhầm nghĩa.
    # ------------------------------------------------------------------
    def extract_slots(self, raw):
        slots = {}
        norm = clean_ascii(raw)
        digit = words_to_digits(norm)

        m = re.search(r'\b(vn|vj|qh|bl|vu)\s*-?\s*(\d{2,4})\b', digit)
        if m:
            slots['flight'] = (m.group(1) + m.group(2)).upper()

        m = re.search(r'(?:cong|cua|gate)\s+([a-z])?\s*(\d{1,2})', digit)
        if m:
            letter = (m.group(1) or '')
            num = m.group(2)
            slots['gate'] = f'{letter.upper()}{num}'
            slots['place_key'] = f'gate_{letter}{num}' if letter else f'gate_{num}'

        for alias in sorted(self.alias_map, key=len, reverse=True):
            if len(alias) >= 3 and alias in norm:
                slots.setdefault('place_key', self.alias_map[alias])
                break
        return slots

    # ------------------------------------------------------------------
    # Chấm điểm intent: % trọng số từ khoá của câu hỏi có mặt trong
    # từ điển intent, cộng bonus nếu khớp nguyên cụm boost_keywords.
    # ------------------------------------------------------------------
    def _score_one(self, query_words, vocab, ascii_mode):
        if not query_words:
            return 0.0
        matched = sum(self._word_weight(w, ascii_mode) for w in query_words
                     if self._in_vocab(w, vocab))
        total = sum(self._word_weight(w, ascii_mode) for w in query_words)
        return 100.0 * matched / total if total else 0.0

    def score_intent(self, words, norm_query, it, ascii_mode):
        """Chấm 1 tầng dấu duy nhất (chọn sẵn theo is_accented() của câu
        gốc) — KHÔNG trộn lẫn 2 tầng, vì tầng bỏ dấu hoàn toàn có thể gộp
        nhầm các từ khác nghĩa (đói/đổi) và sẽ chen điểm sai vào nếu trộn."""
        vocab = it['_vocab_ascii'] if ascii_mode else it['_vocab']
        boost = it['_boost_ascii'] if ascii_mode else it['_boost_norm']

        base = self._score_one(words, vocab, ascii_mode)
        if any(kw and kw in norm_query for kw in boost):
            base = max(base, 95.0)
        return base

    def match_intent(self, raw):
        ascii_mode = not is_accented(raw)
        norm = clean_ascii(raw) if ascii_mode else clean(raw)
        words = content_words_ascii(raw) if ascii_mode else content_words(raw)

        scored = [(it, self.score_intent(words, norm, it, ascii_mode))
                 for it in self.cfg['intents']]

        passed = [(it, s) for it, s in scored if s >= self.threshold]
        pool = passed if passed else scored

        pool_sorted = sorted(pool, key=lambda p: p[1], reverse=True)
        best, best_score = pool_sorted[0]

        # Priority chỉ dùng để phá thế hoà GIỮA các intent có điểm GẦN
        # BẰNG intent tốt nhất (thực sự đang "ăn tranh" nhau) — ví dụ
        # "dẫn tôi đến nhà vệ sinh" thì guide_me (95, nhờ boost) và
        # ask_toilet (100, khớp từ khoá) đang cạnh tranh sít sao, lúc đó
        # guide_me (priority cao hơn, vì là HÀNH ĐỘNG) mới được ưu tiên.
        # Nếu một intent priority cao chỉ tình cờ có vài từ trùng lặp và
        # điểm THẤP HƠN NHIỀU (như "robot" xuất hiện rải rác ở nhiều
        # intent), nó KHÔNG được phép thắng chỉ vì priority.
        close = [(it, s) for it, s in pool_sorted
                if best_score - s <= self.priority_margin]
        if len(close) > 1:
            best, best_score = max(close, key=lambda p: (int(p[0].get('priority', 1)), p[1]))

        return best, best_score

    # ------------------------------------------------------------------
    # Sinh câu trả lời
    # ------------------------------------------------------------------
    def build_response(self, intent, slots):
        place_key = slots.get('place_key') or intent.get('place')
        place = self.places.get(place_key, {}) if place_key else {}

        need = intent.get('slot_required')
        if need and need not in slots and not place:
            self.pending = {'intent': intent['name'], 'time': time.time()}
            return intent['responses'][-1], None, None

        if intent.get('action') == 'query_flight':
            code = slots.get('flight')
            f = self.flights.get(code) if code else None
            if f:
                return (f'Chuyến bay {code} đi {f["route"]}, khởi hành lúc {f["time"]}, '
                        f'{f["gate"]}, tình trạng: {f["status"]}.'), None, None
            if code:
                return (f'Tôi không tìm thấy chuyến bay {code}. '
                        'Bạn vui lòng kiểm tra lại số hiệu.'), None, None

        text = intent['responses'][0]
        for k, v in (('{gate}', slots.get('gate', '')),
                     ('{flight}', slots.get('flight', '')),
                     ('{place_name}', place.get('name', 'nơi bạn cần')),
                     ('{place_desc}', place.get('desc', 'phía trước, theo biển chỉ dẫn')),
                     ('{time}', time.strftime('%H giờ %M'))):
            text = text.replace(k, v)
        text = re.sub(r'\s+', ' ', text).strip()

        action = intent.get('action')
        target = place_key if action == 'navigate' else None
        if action == 'navigate' and not target:
            return 'Bạn muốn tôi dẫn tới đâu ạ?', None, None
        return text, action, target

    # ------------------------------------------------------------------
    def process(self, raw):
        """Trả về dict: {text, intent, score, slots, action, target}"""
        raw = raw.strip()
        if not raw:
            return None

        slots = self.extract_slots(raw)
        intent, score = self.match_intent(raw)

        if self.pending and (time.time() - self.pending['time'] < self.ctx_timeout):
            if score < self.threshold and any(
                    slots.get(k) for k in ('gate', 'flight', 'place_key')):
                intent = next(i for i in self.cfg['intents']
                              if i['name'] == self.pending['intent'])
                score = 100.0
        self.pending = None

        if intent is None or score < self.threshold:
            return {'text': self.fallback, 'intent': 'unknown', 'score': score,
                    'slots': slots, 'action': None, 'target': None}

        text, action, target = self.build_response(intent, slots)
        return {'text': text, 'intent': intent['name'], 'score': score,
                'slots': slots, 'action': action, 'target': target}
