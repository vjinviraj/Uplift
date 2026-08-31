from sqlmodel import Session, SQLModel, create_engine

from apps.api.commerce.catalog import price_order
from apps.api.models import Product


def make_session() -> Session:
    engine = create_engine("sqlite://")

    SQLModel.metadata.create_all(engine)

    session = Session(engine)

    session.add_all(
        [
            Product(
                id="GAME-003",
                name="Grand Theft Auto V",
                category="Games",
                price_paise=249900,
                currency="INR",
                in_stock=True,
                description="Open-world action game.",
            ),
            Product(
                id="MER-002",
                name="Genshin Impact Vision Keychain - Pyro Edition",
                category="Gaming Merchandise",
                price_paise=89900,
                currency="INR",
                in_stock=True,
                description="Genshin Impact themed keychain.",
            ),
            Product(
                id="OUT-OF-STOCK",
                name="Out of Stock Product",
                category="Accessories",
                price_paise=100000,
                currency="INR",
                in_stock=False,
                description="Unavailable product.",
            ),
        ]
    )

    session.commit()

    return session


def test_price_order_calculates_authoritative_total():
    session = make_session()

    result = price_order(
        session,
        [
            {"product_id": "GAME-003", "qty": 1},
            {"product_id": "MER-002", "qty": 1},
        ],
    )

    assert result["amount_paise"] == 339800
    assert result["currency"] == "INR"


def test_price_order_supports_multiple_quantities():
    session = make_session()

    result = price_order(
        session,
        [
            {"product_id": "MER-002", "qty": 2},
        ],
    )

    assert result["amount_paise"] == 179800


def test_price_order_returns_breakdown():
    session = make_session()

    result = price_order(
        session,
        [
            {"product_id": "GAME-003", "qty": 2},
        ],
    )

    assert result["breakdown"] == [
        {
            "product_id": "GAME-003",
            "name": "Grand Theft Auto V",
            "qty": 2,
            "unit_price_paise": 249900,
            "line_total_paise": 499800,
        }
    ]


def test_price_order_rejects_unknown_product():
    session = make_session()

    try:
        price_order(
            session,
            [{"product_id": "DOES-NOT-EXIST", "qty": 1}],
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Product not found" in str(exc)


def test_price_order_rejects_out_of_stock_product():
    session = make_session()

    try:
        price_order(
            session,
            [{"product_id": "OUT-OF-STOCK", "qty": 1}],
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "out of stock" in str(exc).lower()


def test_price_order_rejects_invalid_quantity():
    session = make_session()

    for quantity in (0, -1):
        try:
            price_order(
                session,
                [{"product_id": "GAME-003", "qty": quantity}],
            )
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert "quantity" in str(exc).lower()


def test_price_order_rejects_empty_line_items():
    session = make_session()

    try:
        price_order(session, [])
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "line_items" in str(exc).lower()

def test_price_order_ignores_caller_supplied_price():
    session = make_session()

    result = price_order(
        session,
        [
            {
                "product_id": "GAME-003",
                "qty": 1,
                "price_paise": 1,
            }
        ],
    )

    assert result["amount_paise"] == 249900