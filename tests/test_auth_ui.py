from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_public_pages_do_not_expose_demo_credentials():
    landing = (ROOT / "app" / "templates" / "landing.html").read_text(encoding="utf-8")
    login = (ROOT / "app" / "templates" / "login.html").read_text(encoding="utf-8")

    assert "demo credentials" not in landing.lower()
    assert "demo" not in login.lower()


def test_default_admin_password_is_not_hardcoded():
    init_file = (ROOT / "app" / "__init__.py").read_text(encoding="utf-8")

    assert "admin123" not in init_file
    assert "Default admin created" not in init_file
