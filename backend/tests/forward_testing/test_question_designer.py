from forward_testing.runner.question_designer import QuestionDesigner, _add_trading_days
from datetime import datetime


def test_design_t1():
    qd = QuestionDesigner(["NVDA", "AAPL", "MSFT"])
    prompt = qd.design("t1", "2026-03-29", "some md content")  # Sunday
    assert "T+1" in prompt
    assert "2026-03-30" in prompt  # Monday (1 trading day)
    assert "NVDA" in prompt
    assert "probability" in prompt.lower()


def test_design_t3():
    qd = QuestionDesigner(["NVDA", "AAPL"])
    prompt = qd.design("t3", "2026-03-29", "content")  # Sunday
    assert "T+3" in prompt
    assert "2026-04-01" in prompt  # Wednesday (3 trading days from Sunday)


def test_design_t7():
    qd = QuestionDesigner(["NVDA"])
    prompt = qd.design("t7", "2026-03-29", "content")  # Sunday
    assert "T+7" in prompt
    assert "2026-04-07" in prompt  # Tuesday (7 trading days from Sunday, skips 2 weekends)


def test_design_invalid_horizon():
    import pytest
    qd = QuestionDesigner(["NVDA"])
    with pytest.raises(ValueError):
        qd.design("t30", "2026-03-29", "content")


def test_add_trading_days_skips_weekends():
    # Friday March 27
    fri = datetime(2026, 3, 27)
    assert _add_trading_days(fri, 1).strftime("%Y-%m-%d") == "2026-03-30"  # Monday
    assert _add_trading_days(fri, 3).strftime("%Y-%m-%d") == "2026-04-01"  # Wednesday


def test_add_trading_days_from_wednesday():
    # Wednesday April 1
    wed = datetime(2026, 4, 1)
    assert _add_trading_days(wed, 1).strftime("%Y-%m-%d") == "2026-04-02"  # Thursday
    assert _add_trading_days(wed, 3).strftime("%Y-%m-%d") == "2026-04-06"  # Monday (skips weekend)
