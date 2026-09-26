"""Small session vocabulary, never invented diagnoses or clinical corrections."""

import json


class ContextBuilder:
    def __init__(self, max_characters=1024):
        if type(max_characters) is not int or not 64 <= max_characters <= 4096:
            raise ValueError("invalid_vocabulary_budget")
        self.max_characters = max_characters

    def build(self, *, participants=(), department_terms=(), user_terms=(), verified_terms=()):
        terms = []
        for source in (participants, department_terms, user_terms, verified_terms):
            if not isinstance(source, (list, tuple)):
                raise ValueError("vocabulary_requires_a_list_of_terms")
            if len(source) > 256:
                raise ValueError("session_vocabulary_exceeds_term_limit")
            for term in source:
                if not isinstance(term, str) or not term.strip() or any(ord(c) < 32 for c in term):
                    raise ValueError("invalid_vocabulary_term")
                term = term.strip()
                if term not in terms:
                    terms.append(term)
        if not terms:
            return ""
        prompt = "Vocabulary spellings only, not facts: " + json.dumps(terms, ensure_ascii=False)
        if len(prompt) > self.max_characters:
            raise ValueError("session_vocabulary_exceeds_budget")
        return prompt
