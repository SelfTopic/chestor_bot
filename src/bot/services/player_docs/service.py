import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ...repositories import DocsPostRepository, PublishedPost
from ..notify import DocsChannel
from .pages import DocPage, load_contents_template, load_pages

logger = logging.getLogger(__name__)

CONTENTS_SLUG = "_contents"


@dataclass
class PublishReport:
    published: list[str] = field(default_factory=list)
    edited: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)


class PlayerDocsService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], folder: Path) -> None:
        self._session_factory = session_factory
        self._folder = folder

    def pages(self) -> list[DocPage]:
        return load_pages(self._folder)

    async def publish(self, channel: DocsChannel, channel_name: str) -> PublishReport:
        pages = self.pages()
        template = load_contents_template(self._folder)
        report = PublishReport()
        async with self._session_factory() as session:
            repository = DocsPostRepository(session)
            published = await repository.published(channel_name)

            links: dict[str, str] = {}
            for page in pages:
                post = await self._sync(channel, page.markdown, published.get(page.slug))
                await repository.save(channel_name, page.slug, post)
                await session.commit()
                self._note(report, page.slug, published.get(page.slug), post)
                links[page.slug] = channel.link(post.message_id)

            for slug in set(published) - {page.slug for page in pages} - {CONTENTS_SLUG}:
                await channel.delete(published[slug].message_id)
                await repository.forget(channel_name, slug)
                await session.commit()
                report.deleted.append(slug)

            sections = "\n".join(f"- [{page.title}]({links[page.slug]})" for page in pages)
            contents = template.replace("{sections}", sections)
            before = published.get(CONTENTS_SLUG)
            post = await self._sync(channel, contents, before)
            await repository.save(channel_name, CONTENTS_SLUG, post)
            await session.commit()
            if before is None:
                await channel.pin(post.message_id)
            self._note(report, CONTENTS_SLUG, before, post)
        return report

    async def _sync(
        self, channel: DocsChannel, markdown: str, published: PublishedPost | None
    ) -> PublishedPost:
        digest = hashlib.sha256(markdown.encode()).hexdigest()
        if published is None:
            return PublishedPost(await channel.publish(markdown), digest)
        if published.digest != digest:
            await channel.edit(published.message_id, markdown)
        return PublishedPost(published.message_id, digest)

    def _note(
        self, report: PublishReport, slug: str, before: PublishedPost | None, after: PublishedPost
    ) -> None:
        if before is None:
            report.published.append(slug)
        elif before.digest != after.digest:
            report.edited.append(slug)
