import app as app_module


def test_create_and_view_linkbox_page():
    app_module.app.config.update(TESTING=True, LINKBOX_DB_PATH=":memory:")
    app_module.init_db(app_module.app.config["LINKBOX_DB_PATH"])

    with app_module.app.test_client() as client:
        response = client.post(
            "/linkbox/create",
            data={
                "title": "Launch Page",
                "description": "A simple launch page",
                "notes": "Welcome",
                "link_title": "Docs",
                "link_url": "https://example.com",
                "theme_color": "#6d5dfc",
                "accent_color": "#4f46e5",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        pages = app_module.get_linkbox_pages(app_module.app.config["LINKBOX_DB_PATH"])
        assert len(pages) == 1
        assert pages[0]["title"] == "Launch Page"

        response = client.get(f"/page/{pages[0]['slug']}")
        assert response.status_code == 200
        assert b"Launch Page" in response.data
