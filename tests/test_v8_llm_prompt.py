from tradeshield.services.llm_client import build_case_prompt, build_trade_finance_system_prompt


def test_llm_system_prompt_has_guardrails():
    prompt = build_trade_finance_system_prompt()
    assert "decision support" in prompt
    assert "Do not invent" in prompt


def test_case_prompt_contains_question_and_context():
    prompt = build_case_prompt({"case": {"case_ref": "TS-1"}}, "Should we approve?")
    assert "TS-1" in prompt
    assert "Should we approve?" in prompt
    assert "Evidence used" in prompt
