from sqlmodel import Session, SQLModel, create_engine

from apps.api.commerce.catalog import get_upsell_candidates
from apps.api.models import CompatibilityMap, Product


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
            description="Open-world action RPG.",
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
            id="MER-001",
            name="Genshin Impact Paimon Plush (30cm)",
            category="Gaming Merchandise",
            price_paise=249900,
            currency="INR",
            in_stock=True,
            description="Genshin Impact Paimon plush.",
        ),
    ]

    mappings = [
        CompatibilityMap(
            product_id="GAME-001",
            upsell_product_id="MER-002",
            reason_code="frequently_bought_with",
            max_autonomous=True,
        ),
        CompatibilityMap(
            product_id="GAME-001",
            upsell_product_id="MER-001",
            reason_code="frequently_bought_with",
            max_autonomous=False,
        ),
    ]

    session.add_all(products)
    session.add_all(mappings)
    session.commit()

    return session


def test_get_upsell_candidates_returns_mapped_products():
    session = make_session()

    result = get_upsell_candidates(session, "GAME-001")

    assert len(result["candidates"]) == 2

    ids = {
        candidate["product_id"]
        for candidate in result["candidates"]
    }

    assert ids == {"MER-001", "MER-002"}


def test_get_upsell_candidates_returns_required_fields():
    session = make_session()

    result = get_upsell_candidates(session, "GAME-001")

    for candidate in result["candidates"]:
        assert set(candidate.keys()) == {
            "product_id",
            "name",
            "price_paise",
            "reason_code",
            "max_autonomous",
        }


def test_get_upsell_candidates_preserves_mapping_metadata():
    session = make_session()

    result = get_upsell_candidates(session, "GAME-001")

    candidates = {
        candidate["product_id"]: candidate
        for candidate in result["candidates"]
    }

    assert candidates["MER-002"]["reason_code"] == "frequently_bought_with"
    assert candidates["MER-002"]["max_autonomous"] is True

    assert candidates["MER-001"]["reason_code"] == "frequently_bought_with"
    assert candidates["MER-001"]["max_autonomous"] is False


def test_get_upsell_candidates_returns_empty_for_unknown_product():
    session = make_session()

    result = get_upsell_candidates(session, "DOES-NOT-EXIST")

    assert result == {"candidates": []}


def test_get_upsell_candidates_does_not_return_unmapped_products():
    session = make_session()

    session.add(
        Product(
            id="UNMAPPED-001",
            name="Unmapped Gaming Product",
            category="Accessories",
            price_paise=100000,
            currency="INR",
            in_stock=True,
            description="Not part of the compatibility graph.",
        )
    )

    session.commit()

    result = get_upsell_candidates(session, "GAME-001")

    ids = {
        candidate["product_id"]
        for candidate in result["candidates"]
    }

    assert "UNMAPPED-001" not in ids