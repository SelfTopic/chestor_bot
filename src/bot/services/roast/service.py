import asyncio
import logging
import random
import re
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.database.models import RoastLog

from ...repositories import PlayerFacts, RoastRepository
from .llm import LlmClient, LlmError
from .prompts import RoastPrompts

logger = logging.getLogger(__name__)

ARGUMENT_WINDOW = 180.0
MAX_TURNS = 15
SILENCE = 1800.0
HISTORY_LIMIT = 3
EXAMPLES_PER_REQUEST = 4
GOOD_EXAMPLES_PER_REQUEST = 2
INSULTS_PER_REQUEST = 4
FACTS_PER_REQUEST = 2
BOT_MESSAGES_KEPT = 5000
LOG_RETENTION = timedelta(days=180)

NAME_CALL = re.compile(r"^\s*(бот|честор)\b", re.IGNORECASE)
# Модель держит запреты не всегда: то, что она пропустила, режется здесь.
BANNED = re.compile(
    r"(?<!на )\bхуй\b|пид[оа]р|пидр|хох[оа]?л|чурк|жид|нигер|негр|хач|\bдаун|аутист|\bгей"
    r"|ебу тво|изнасил|опущ|дыряв|сдохни|убей себя|у\w{0,2}бейся|выпились|вскройся|повесься"
    r"|суицид",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Replied:
    text: str
    addressee: str | None


@dataclass(frozen=True)
class Incoming:
    chat_id: int
    telegram_id: int
    first_name: str
    text: str
    replied: Replied | None


@dataclass(frozen=True)
class RoastOutcome:
    reply: str | None = None
    log_id: int | None = None
    bored: bool = False


@dataclass
class Argument:
    turns: int = 0
    last_at: float = float("-inf")
    last_log_id: int | None = None
    silent_until: float = float("-inf")


def chat_style(text: str) -> str:
    # Пунктуацию модель в споре держит плохо, поэтому стиль чата наводит код.
    text = text.strip().strip("\"'«»<>").lower().replace("—", " ")
    text = re.sub(r"[.,;:«»\"]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def fact_lines(facts: PlayerFacts | None, turns: int) -> list[str]:
    lines: list[str] = []
    if facts is not None:
        lines.append(f"баланс {facts.balance} CheSton")
        lines.append(f"уровень гуля {facts.level}" if facts.level is not None else "гуля у него нет")
        if facts.wins or facts.losses:
            lines.append(f"дуэли: {facts.wins} побед, {facts.losses} поражений")
        if facts.snap_count:
            lines.append(f"ломал пальцы {facts.snap_count} раз")
        if facts.coffee_count:
            lines.append(f"пил кофе {facts.coffee_count} раз")
        if facts.deaths:
            lines.append(f"умирал {facts.deaths} раз")
    # Все факты разом делают ответы однообразными: каждый раз цепляется «уровень N».
    picked = random.sample(lines, min(FACTS_PER_REQUEST, len(lines)))
    if turns >= 2:
        picked.append(f"пишет тебе уже {turns + 1}-е сообщение в этом споре")
    return picked


def render_chat(incoming: Incoming, history: list[RoastLog]) -> str:
    lines: list[str] = []
    for row in history:
        lines.append(f"{row.first_name}: {row.message}")
        lines.append(f"бот → {row.first_name}: {row.reply}")
    replied = incoming.replied
    if replied is not None and not (history and history[-1].reply == replied.text):
        speaker = f"бот → {replied.addressee}" if replied.addressee else "бот"
        lines.append(f"{speaker}: {replied.text}")
    suffix = " [в ответ боту]" if replied is not None else ""
    last = f"{incoming.first_name}{suffix}: {incoming.text}"
    return "Чат:\n" + "\n".join(lines) + f"\n\nПоследнее сообщение — {last}"


class RoastService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        llm: LlmClient,
        prompts: RoastPrompts,
        *,
        enabled: bool,
        model: str,
        classifier_model: str,
        daily_limit: int,
        timeout: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._session_factory = session_factory
        self._llm = llm
        self._prompts = prompts
        self._enabled = enabled
        self._model = model
        self._classifier_model = classifier_model
        self._daily_limit = daily_limit
        self._timeout = timeout
        self._clock = clock
        self.bot_id: int | None = None
        self._arguments: dict[tuple[int, int], Argument] = {}
        self._locks: dict[tuple[int, int], asyncio.Lock] = {}
        # Кому бот отвечал своим сообщением: Telegram не присылает вложенные реплаи.
        self._bot_messages: OrderedDict[tuple[int, int], str] = OrderedDict()
        self._spent_on = date.today()
        self._spent = 0

    def remember_bot_message(self, chat_id: int, message_id: int, addressee: str) -> None:
        self._bot_messages[(chat_id, message_id)] = addressee
        if len(self._bot_messages) > BOT_MESSAGES_KEPT:
            self._bot_messages.popitem(last=False)

    def addressee_of(self, chat_id: int, message_id: int) -> str | None:
        return self._bot_messages.get((chat_id, message_id))

    def is_bot(self, user_id: int) -> bool:
        return self.bot_id is not None and user_id == self.bot_id

    def wants(self, chat_id: int, telegram_id: int, text: str, *, replied_to_bot: bool) -> bool:
        if not self._enabled:
            return False
        argument = self._arguments.get((chat_id, telegram_id))
        now = self._clock()
        if argument is not None and argument.silent_until > now:
            return False
        in_argument = argument is not None and now - argument.last_at < ARGUMENT_WINDOW
        return replied_to_bot or in_argument or NAME_CALL.match(text) is not None

    async def respond(self, incoming: Incoming) -> RoastOutcome:
        key = (incoming.chat_id, incoming.telegram_id)
        # Два быстрых сообщения подряд не должны получить два ответа вперемешку.
        async with self._locks.setdefault(key, asyncio.Lock()):
            return await self._respond(incoming, self._arguments.setdefault(key, Argument()))

    async def _respond(self, incoming: Incoming, argument: Argument) -> RoastOutcome:
        now = self._clock()
        if argument.silent_until > now:
            return RoastOutcome()
        in_argument = now - argument.last_at < ARGUMENT_WINDOW
        if not in_argument:
            argument.turns = 0
            argument.last_log_id = None
        if argument.turns >= MAX_TURNS:
            argument.silent_until = now + SILENCE
            argument.turns = 0
            return RoastOutcome(bored=True)
        if not self._spend():
            return RoastOutcome()

        async with self._session_factory() as session:
            repository = RoastRepository(session)
            if argument.last_log_id is not None:
                await repository.add_followup(argument.last_log_id)
            facts = await repository.player_facts(incoming.telegram_id)
            history = await repository.argument_history(
                incoming.chat_id,
                incoming.telegram_id,
                timedelta(seconds=ARGUMENT_WINDOW),
                HISTORY_LIMIT,
            )
            good = await repository.good_examples(GOOD_EXAMPLES_PER_REQUEST)
            await session.commit()

        chat = render_chat(incoming, history)
        facts_text = "; ".join(fact_lines(facts, argument.turns))
        request = self._request(chat, facts_text, good)

        started = time.monotonic()
        verdict, reply = await self._ask(chat, request)
        if not verdict:
            return RoastOutcome()
        latency_ms = int((time.monotonic() - started) * 1000)

        reply = chat_style(reply) if reply else None
        filtered = reply is not None and BANNED.search(reply) is not None
        async with self._session_factory() as session:
            entry = await RoastRepository(session).add(
                RoastLog(
                    chat_id=incoming.chat_id,
                    telegram_id=incoming.telegram_id,
                    first_name=incoming.first_name,
                    message=incoming.text,
                    context=chat,
                    facts=facts_text,
                    reply=reply,
                    model=self._model,
                    filtered=filtered,
                    latency_ms=latency_ms,
                    followups=0,
                )
            )
            await session.commit()
            log_id = entry.id

        if not reply or filtered:
            return RoastOutcome(log_id=log_id)
        argument.turns += 1
        argument.last_at = self._clock()
        argument.last_log_id = log_id
        return RoastOutcome(reply=reply, log_id=log_id)

    async def sent(self, chat_id: int, message_id: int, addressee: str, log_id: int) -> None:
        self.remember_bot_message(chat_id, message_id, addressee)
        async with self._session_factory() as session:
            await RoastRepository(session).set_bot_message(log_id, message_id)
            await session.commit()

    async def rate(self, chat_id: int, bot_message_id: int, rating: int) -> bool:
        async with self._session_factory() as session:
            rated = await RoastRepository(session).rate(chat_id, bot_message_id, rating)
            await session.commit()
        return rated

    async def cleanup(self) -> None:
        async with self._session_factory() as session:
            await RoastRepository(session).delete_older_than(LOG_RETENTION)
            await session.commit()

    def _spend(self) -> bool:
        today = date.today()
        if today != self._spent_on:
            self._spent_on, self._spent = today, 0
        if self._spent >= self._daily_limit:
            return False
        self._spent += 1
        return True

    def _request(self, chat: str, facts: str, good: list[RoastLog]) -> str:
        examples = self._prompts.examples()
        picked = random.sample(examples, min(EXAMPLES_PER_REQUEST, len(examples)))
        picked += [f"{row.message} → {row.reply}" for row in good]
        insults = self._prompts.insults()
        insults = random.sample(insults, min(INSULTS_PER_REQUEST, len(insults)))
        return (
            self._prompts.request.replace("{examples}", "\n".join(f"- {line}" for line in picked))
            .replace("{insults}", "\n".join(f"- {line}" for line in insults))
            .replace("{chat}", chat)
            .replace("{facts}", f"Что ты знаешь о собеседнике: {facts}" if facts else "")
        )

    async def _ask(self, chat: str, request: str) -> tuple[bool, str | None]:
        # Ответ генерируется одновременно с решением «к боту ли это»: иначе ждать пришлось бы
        # оба запроса подряд. Если сообщение не к боту, генерация отменяется.
        classify = asyncio.create_task(
            self._llm.complete(
                self._classifier_model, self._prompts.classify, chat, max_tokens=3, temperature=0.0
            )
        )
        generate = asyncio.create_task(
            self._llm.complete(
                self._model, self._prompts.persona, request, max_tokens=120, temperature=0.9
            )
        )
        # Результат брошенной задачи никто не заберёт, а её ошибка иначе ушла бы в лог asyncio.
        for task in (classify, generate):
            task.add_done_callback(lambda t: t.cancelled() or t.exception())
        try:
            async with asyncio.timeout(self._timeout):
                try:
                    verdict = await classify
                except LlmError:
                    logger.warning("Классификатор огрызаний не ответил", exc_info=True)
                    return False, None
                if not verdict.lower().startswith("да"):
                    return False, None
                try:
                    return True, await generate
                except LlmError:
                    logger.warning("Модель огрызаний не ответила", exc_info=True)
                    return True, None
        except TimeoutError:
            logger.warning("Огрызание не уложилось в %s с", self._timeout)
            return classify.done() and not classify.cancelled(), None
        finally:
            for task in (classify, generate):
                task.cancel()


__all__ = [
    "Incoming",
    "Replied",
    "RoastOutcome",
    "RoastService",
    "chat_style",
]
