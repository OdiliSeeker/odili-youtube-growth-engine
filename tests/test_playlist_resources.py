"""Playlist Resources: service behavior + stored-XSS regression on /resources."""

from app.services import playlist_resource_service as prs
from app.routes.playlist_resources import _json_for_script


def test_seed_is_idempotent(db):
    prs.seed_default_resources(db)
    first = len(prs.list_resources(db))
    assert first == 19
    prs.seed_default_resources(db)
    assert len(prs.list_resources(db)) == first


def test_seed_category_distribution(db):
    prs.seed_default_resources(db)
    counts = {slug: len(prs.list_resources(db, category=slug)) for slug in prs.SECTIONS}
    assert counts == {
        "papal-history": 5,
        "heresies-councils": 5,
        "trials-of-the-church": 3,
        "church-fathers": 3,
        "playlist-resources": 3,
    }
    assert all(r["link"] for r in prs.list_resources(db))


def test_verified_upgrade_runs_once(db):
    prs.seed_default_resources(db)
    prs.apply_verified_source_upgrade(db)
    assert len(prs.list_resources(db)) == 19
    # Second call must be a no-op: admin edits after the upgrade survive.
    edited = prs.list_resources(db)[0]
    prs.update_resource(db, edited["id"], {"title": "Admin Edited"})
    prs.apply_verified_source_upgrade(db)
    assert prs.get_resource(db, edited["id"])["title"] == "Admin Edited"
    assert len(prs.list_resources(db)) == 19


def test_unsafe_urls_and_tags_rejected(db):
    item = prs.create_resource(
        db,
        title="T",
        category="church-fathers",
        link="javascript:alert(1)",
        video_url="data:text/html,x",
        tags=["fathers", "not-a-real-tag"],
    )
    assert item["link"] is None
    assert item["video_url"] is None
    assert item["tags"] == ["fathers"]
    assert item["seo_title"] and item["seo_keywords"]


def test_update_refreshes_seo_meta(db):
    item = prs.create_resource(db, title="Old", category="papal-history")
    updated = prs.update_resource(db, item["id"], {"title": "New Title"})
    assert updated["title"] == "New Title"
    assert "New Title" in updated["seo_title"]


def test_json_for_script_blocks_script_breakout():
    payload = {"title": "</script><script>alert(1)</script>", "u2028": "a\u2028b"}
    out = _json_for_script(payload)
    assert "</script" not in out
    assert "<\\/script" in out
    assert "\u2028" not in out


def test_resources_page_does_not_leak_script_tag(db, monkeypatch):
    """A stored </script> in a resource must never appear unescaped in /resources."""
    import asyncio

    prs.create_resource(
        db,
        title="Evil</script><script>alert(1)</script>",
        category="church-fathers",
        description="desc</script><img src=x onerror=alert(1)>",
        relevance="rel",
    )
    from app.routes import playlist_resources as route

    html_resp = asyncio.run(route.resources_page(db=db))
    body = html_resp.body.decode()
    # Only the two legitimate script blocks may close a script tag.
    assert body.count("</script>") == 1
    assert "<script>alert(1)</script>" not in body
