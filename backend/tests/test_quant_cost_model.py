from app.quant.cost_model import CostModel, apply_slippage


def test_default_cost_model_is_alpaca_style():
    c = CostModel()
    assert c.commission == 0.0
    assert c.slippage_bps == 5.0
    assert c.allow_short is False


def test_apply_slippage_buy_pushes_price_up():
    px = apply_slippage(100.0, side="buy", slippage_bps=5)
    # 5 bps = 0.05% = +0.05 on 100.00
    assert px == 100.05


def test_apply_slippage_sell_pushes_price_down():
    px = apply_slippage(100.0, side="sell", slippage_bps=5)
    assert px == 99.95


def test_apply_slippage_short_is_like_sell():
    assert apply_slippage(100.0, side="short", slippage_bps=10) == 99.9


def test_apply_slippage_cover_is_like_buy():
    assert apply_slippage(100.0, side="cover", slippage_bps=10) == 100.1


def test_apply_slippage_zero_bps_returns_input():
    assert apply_slippage(123.45, side="buy", slippage_bps=0) == 123.45


def test_cost_model_serializes_to_dict():
    c = CostModel(commission=0.0, slippage_bps=5.0, allow_short=True)
    assert c.to_dict() == {"commission": 0.0, "slippage_bps": 5.0, "allow_short": True}


def test_target_qty_from_weight_positive():
    from app.quant.cost_model import target_qty_from_weight
    assert target_qty_from_weight(weight=1.0, equity=100_000, price=200.0) == 500


def test_target_qty_from_weight_negative_is_short():
    from app.quant.cost_model import target_qty_from_weight
    assert target_qty_from_weight(weight=-0.5, equity=100_000, price=200.0) == -250


def test_target_qty_from_weight_zero_price_returns_zero():
    from app.quant.cost_model import target_qty_from_weight
    assert target_qty_from_weight(weight=0.5, equity=100_000, price=0.0) == 0


def test_target_qty_from_weight_floors_to_int():
    from app.quant.cost_model import target_qty_from_weight
    assert target_qty_from_weight(weight=0.33, equity=100_000, price=199.5) == 165
