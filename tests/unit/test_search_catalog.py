from sqlmodel import Session, SQLModel, create_engine

from apps.api.commerce.catalog import search_catalog
from apps.api.models import Product


def make_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )

    SQLModel.metadata.create_all(engine)

    session = Session(engine)

    products = [
        Product(
            id="GAME-001",
            name="Genshin Impact - Digital Edition",
            category="Games",
            price_paise=0,
            currency="INR",
            in_stock=True,
            description="Open-world action RPG from HoYoverse.",
        ),
        Product(
            id="GAME-002",
            name="EA Sports FC 24",
            category="Games",
            price_paise=449900,
            currency="INR",
            in_stock=True,
            description="Football game.",
        ),
        Product(
            id="PER-001",
            name="DualSense Wireless Controller",
            category="Controllers / Peripherals",
            price_paise=599000,
            currency="INR",
            in_stock=True,
            description="Wireless PlayStation controller.",
        ),
    ]

    session.add_all(products)
    session.commit()

    return session


def test_search_catalog_finds_matching_product():
    session = make_session()

    result = search_catalog(session, "Genshin Impact")

    assert len(result["matches"]) == 1
    assert result["matches"][0]["product_id"] == "GAME-001"


def test_search_catalog_respects_category_hint():
    session = make_session()

    result = search_catalog(
        session,
        "controller",
        category_hint="Controllers / Peripherals",
    )

    assert len(result["matches"]) == 1
    assert result["matches"][0]["product_id"] == "PER-001"


def test_search_catalog_caps_results_at_five():
    session = make_session()

    for i in range(10):
        session.add(
            Product(
                id=f"TEST-{i:03d}",
                name=f"Gaming Controller {i}",
                category="Controllers / Peripherals",
                price_paise=100000,
                currency="INR",
                in_stock=True,
                description="Gaming controller.",
            )
        )

    session.commit()

    result = search_catalog(session, "controller")

    assert len(result["matches"]) == 5


def test_search_catalog_rejects_empty_query():
    session = make_session()

    try:
        search_catalog(session, "   ")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert str(exc) == "query must not be empty"


def test_search_catalog_ranks_name_match_above_description_match():
    session = make_session()

    session.add(
        Product(
            id="TEST-001",
            name="Football Gaming Accessory",
            category="Accessories",
            price_paise=100000,
            currency="INR",
            in_stock=True,
            description="Useful for EA Sports FC players.",
        )
    )

    session.commit()

    result = search_catalog(session, "EA Sports FC")

    assert result["matches"][0]["product_id"] == "GAME-002"


def test_search_catalog_category_hint_affects_ranking():
    session = make_session()

    session.add(
        Product(
            id="TEST-002",
            name="Gaming Controller",
            category="Accessories",
            price_paise=100000,
            currency="INR",
            in_stock=True,
            description="A gaming controller accessory.",
        )
    )

    session.commit()

    result = search_catalog(
        session,
        "gaming controller",
        category_hint="Controllers / Peripherals",
    )

    assert result["matches"][0]["product_id"] == "PER-001"


def test_search_catalog_prefers_in_stock_when_scores_tie():
    session = make_session()

    session.add(
        Product(
            id="TEST-003",
            name="Controller Pro",
            category="Accessories",
            price_paise=100000,
            currency="INR",
            in_stock=False,
            description="Gaming controller.",
        )
    )

    session.add(
        Product(
            id="TEST-004",
            name="Controller Pro Plus",
            category="Accessories",
            price_paise=100000,
            currency="INR",
            in_stock=True,
            description="Gaming controller.",
        )
    )

    session.commit()

    result = search_catalog(session, "controller")

    ids = [match["product_id"] for match in result["matches"]]

    assert ids.index("TEST-004") < ids.index("TEST-003")