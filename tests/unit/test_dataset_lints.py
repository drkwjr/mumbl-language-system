from mumbl_dataset_builder.lints import lint_tts_manifest

def test_lints_ok():
    rows = [
        {"wav":"clips/a.wav","sample_rate":24000,"duration_s":2.0,"text":"hi"},
        {"wav":"clips/b.wav","sample_rate":24000,"duration_s":3.0,"text":"there"}
    ]
    rep = lint_tts_manifest(rows)
    assert rep.ok
