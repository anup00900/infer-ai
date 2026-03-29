from forward_testing.runner.question_designer import QuestionDesigner


def test_design_t1():
    qd = QuestionDesigner(["NVDA", "AAPL", "MSFT"])
    prompt = qd.design("t1", "2026-03-29", "some md content")
    assert "T+1" in prompt
    assert "2026-03-30" in prompt
    assert "NVDA" in prompt
    assert "probability" in prompt.lower()


def test_design_t3():
    qd = QuestionDesigner(["NVDA", "AAPL"])
    prompt = qd.design("t3", "2026-03-29", "content")
    assert "T+3" in prompt
    assert "2026-04-01" in prompt


def test_design_t7():
    qd = QuestionDesigner(["NVDA"])
    prompt = qd.design("t7", "2026-03-29", "content")
    assert "T+7" in prompt
    assert "2026-04-05" in prompt


def test_design_invalid_horizon():
    import pytest
    qd = QuestionDesigner(["NVDA"])
    with pytest.raises(ValueError):
        qd.design("t30", "2026-03-29", "content")
