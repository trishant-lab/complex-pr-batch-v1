import pytest

from app.cli.temporal.activities.zsegmentFetchLatestTag import ZsegmentFetchLatestTagActivity


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        # release-build.yml validates the tag as ^[0-9]+\.[0-9]+(\.[0-9]+)?$ and
        # publishes it alongside :latest, so releases are bare versions.
        (["1.4.0", "1.5.0", "1.3.2"], "1.5.0"),
        (["1.2", "1.10", "1.9"], "1.10"),
        # Sorting version strings lexicographically puts 1.10.0 before 1.9.0 and
        # picks the older release. Compare parsed components instead.
        (["1.9.0", "1.10.0"], "1.10.0"),
        (["1.9.9", "1.10.1", "2.0.0"], "2.0.0"),
        # Anything that is not a release tag is ignored: sprint and per-branch
        # tags from the integration pipeline, and :latest which is a moving ref.
        (["sprint", "latest", "production", "1.5.0", "some-branch"], "1.5.0"),
    ],
)
def test_picks_the_newest_release_tag(tags: list[str], expected: str) -> None:
    """The newest release wins, ordered on parsed version components."""
    assert ZsegmentFetchLatestTagActivity.newest_release_tag(tags) == expected


@pytest.mark.parametrize("tags", [[], ["sprint", "latest"], ["production"], ["not-a-version"]])
def test_falls_back_when_no_release_tag_is_published(tags: list[str]) -> None:
    """`latest` is the fallback, not `production`.

    release-build.yml publishes :<version> and :latest; nothing publishes
    :production for zsegment-api/engine any more, so falling back to it would
    point a new production tenant at a tag that is no longer maintained.
    """
    assert ZsegmentFetchLatestTagActivity.newest_release_tag(tags) == "latest"
