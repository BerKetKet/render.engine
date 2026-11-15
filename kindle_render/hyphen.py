"""
Liang's Hyphenation Algorithm (Frank Liang, 1983).
Unified Trie-based syllabification engine supporting both Kindle compiled
binary hyphenation tries (`hyph_*.bin`) and standard TeX/Libhyphen `.dic` files.
"""
import os
import struct
from typing import List, Tuple, Dict, Optional


class TrieNode:
    __slots__ = ('children', 'values')
    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}
        self.values: Optional[List[Tuple[int, int]]] = None


class LiangHyphenator:
    _CACHE: Dict[Tuple[str, int, int, int], 'LiangHyphenator'] = {}

    @classmethod
    def get_cached(cls, dic_path: str, left_min: int = 2, right_min: int = 3, min_word_len: int = 5) -> 'LiangHyphenator':
        key = (os.path.abspath(dic_path) if dic_path else "", left_min, right_min, min_word_len)
        if key not in cls._CACHE:
            cls._CACHE[key] = cls(dic_path, left_min, right_min, min_word_len)
        return cls._CACHE[key]

    def __init__(self, dic_path: Optional[str] = None, left_min: int = 2, right_min: int = 3, min_word_len: int = 5):
        self.dic_path = dic_path or ""
        self.left_min = left_min
        self.right_min = right_min
        self.min_word_len = min_word_len
        self.root = TrieNode()
        self.pattern_count = 0
        self._bin_mode = False
        self._bin_states: List[Tuple[str, int, int, int]] = []
        self._bin_trans: Dict[Tuple[int, int], int] = {}
        if dic_path and os.path.isfile(dic_path):
            if dic_path.lower().endswith(".bin"):
                self.load_bin(dic_path)
            else:
                self.load_dic(dic_path)

    def load_bin(self, bin_path: str):
        """Parses a compiled Kindle/libhyphen binary hyphenation dictionary (.bin)."""
        with open(bin_path, "rb") as f:
            p = f.read()
        if len(p) < 40:
            return
        _, _, ntrans1, pool1, _, nstates1 = struct.unpack_from("<HHIIHH", p, 0)
        lh1, rh1, _, crh1 = struct.unpack_from("<BBBB", p, 36)
        self.left_min = max(self.left_min, lh1)
        self.right_min = max(self.right_min, rh1)
        off = 40 + nstates1 * 8 + ntrans1 * 4 + pool1
        if crh1 & 0x80 and off + 36 <= len(p):
            ntrans2, pool2, _, nstates2 = struct.unpack_from("<IIHH", p, off)
            lh2, rh2, _, _ = struct.unpack_from("<BBBB", p, off + 32)
            self.left_min = max(self.left_min, lh2)
            self.right_min = max(1, rh2)
            states_off = off + 36
            trans_off = states_off + nstates2 * 8
            pool_off = trans_off + ntrans2 * 4
        else:
            nstates2, ntrans2, pool2 = nstates1, ntrans1, pool1
            states_off = 40
            trans_off = states_off + nstates2 * 8
            pool_off = trans_off + ntrans2 * 4

        pool = p[pool_off:pool_off + pool2]
        states: List[Tuple[str, int, int, int]] = []
        trans_map: Dict[Tuple[int, int], int] = {}
        t_cursor = 0
        pat_count = 0
        for i in range(nstates2):
            m_off, fb, num_t, _ = struct.unpack_from("<IhBB", p, states_off + i * 8)
            pat = ""
            if m_off != 0:
                end = pool.find(b"\x00", m_off)
                if end != -1:
                    pat = pool[m_off:end].decode("utf-8", "replace")
                    if pat:
                        pat_count += 1
            states.append((pat, fb, num_t, t_cursor))
            for k in range(t_cursor, t_cursor + num_t):
                ns, ch, _ = struct.unpack_from("<HBB", p, trans_off + k * 4)
                trans_map[(i, ch)] = ns
            t_cursor += num_t

        self._bin_mode = True
        self._bin_states = states
        self._bin_trans = trans_map
        self.pattern_count = pat_count

    def load_dic(self, dic_path: str):
        """Parses a standard TeX/Libhyphen dictionary and builds the pattern trie."""
        encoding = "utf-8"
        with open(dic_path, "rb") as f:
            header = f.read(256)
            if b"ISO8859" in header or b"ISO-8859" in header:
                encoding = "latin1"

        with open(dic_path, "r", encoding=encoding, errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(("%", "#")):
                    continue
                if line.startswith("UTF-8"):
                    encoding = "utf-8"
                elif line.startswith("ISO8859") or line.startswith("ISO-8859"):
                    encoding = "latin1"
                elif line.startswith("LEFTHYPHENMIN"):
                    try:
                        self.left_min = max(1, int(line.split()[1]))
                    except (IndexError, ValueError):
                        pass
                elif line.startswith("RIGHTHYPHENMIN"):
                    try:
                        self.right_min = max(1, int(line.split()[1]))
                    except (IndexError, ValueError):
                        pass
                elif not line.startswith(("COMPOUND", "NEXTLEVEL")):
                    self._add_pattern(line)

    def _add_pattern(self, pat: str):
        chars = []
        digits = []
        curr = 0
        for ch in pat:
            if ch.isdigit():
                digits.append((curr, int(ch)))
            else:
                chars.append(ch)
                curr += 1
        node = self.root
        for c in chars:
            if c not in node.children:
                node.children[c] = TrieNode()
            node = node.children[c]
        if digits:
            if node.values is None:
                node.values = digits
            else:
                merged = dict(node.values)
                for off, val in digits:
                    if val > merged.get(off, 0):
                        merged[off] = val
                node.values = sorted(merged.items())
        self.pattern_count += 1

    def _hyphenate_word_bin(self, word: str) -> List[str]:
        low = word.lower()
        char_bytes = [c.encode("utf-8") for c in low]
        # Build byte stream for '.' + low + '.' and map byte boundaries to char positions
        wb = bytearray(b".")
        # byte_to_char_boundary[byte_pos] = char_idx (0..len(word)) for boundaries inside word
        byte_to_char: Dict[int, int] = {}
        for ci, cb in enumerate(char_bytes):
            if ci > 0:
                byte_to_char[len(wb)] = ci
            wb.extend(cb)
        wb.extend(b".")

        scores = [0] * (len(wb) + 1)
        state = 0
        states = self._bin_states
        trans = self._bin_trans
        for idx, b in enumerate(wb):
            while state != -1:
                ns = trans.get((state, b))
                if ns is not None:
                    state = ns
                    break
                state = states[state][1]
            if state == -1:
                state = 0
            cur = state
            while cur != -1:
                pat, fb, _, _ = states[cur]
                if pat:
                    base = idx + 2 - len(pat)
                    for j, ch in enumerate(pat):
                        if ch.isdigit():
                            pos = base + j
                            if 0 <= pos < len(scores):
                                v = ord(ch) - 48
                                if v > scores[pos]:
                                    scores[pos] = v
                cur = fb

        word_len = len(word)
        cuts = []
        for bpos, ci in byte_to_char.items():
            if ci >= self.left_min and (word_len - ci) >= self.right_min and scores[bpos] % 2 == 1:
                cuts.append(ci)
        if not cuts:
            return [word]
        parts = []
        last = 0
        for c in cuts:
            parts.append(word[last:c])
            last = c
        parts.append(word[last:])
        return parts

    def hyphenate_word(self, word: str) -> List[str]:
        """
        Applies Liang's scoring vector to a single word.
        Returns syllabic segments: e.g. 'telecommunications' -> ['tele', 'com', 'mu', 'ni', 'ca', 'tions'].
        """
        if len(word) < self.min_word_len or not word.isalpha():
            return [word]
        if self._bin_mode:
            return self._hyphenate_word_bin(word)

        w = '.' + word.lower() + '.'
        n = len(w)
        scores = [0] * (n + 1)

        for i in range(n):
            node = self.root
            j = i
            while j < n and w[j] in node.children:
                node = node.children[w[j]]
                if node.values:
                    for off, val in node.values:
                        pos = i + off
                        if pos < len(scores) and val > scores[pos]:
                            scores[pos] = val
                j += 1

        word_len = len(word)
        cuts = []
        for i in range(word_len):
            slot = i + 2
            left_len = i + 1
            right_len = word_len - left_len
            if slot < len(scores) and scores[slot] % 2 == 1 and left_len >= self.left_min and right_len >= self.right_min:
                cuts.append(left_len)

        if not cuts:
            return [word]

        parts = []
        last = 0
        for c in cuts:
            parts.append(word[last:c])
            last = c
        parts.append(word[last:])
        return parts
