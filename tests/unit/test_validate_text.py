from mumbl_format_guardians.validate_text import validate_text_jsonl

def test_validate_text_ok():
    data = '{"text":"Hi","lang":"en","labels":{"is_dialogue":true,"topic":"g","register":"i","code_switch_spans":[]},"source_ref":{"doc_id":"SRC","start":0,"end":2}}\n'
    rep = validate_text_jsonl(data.splitlines())
    assert rep.ok
    assert rep.checked == 1
