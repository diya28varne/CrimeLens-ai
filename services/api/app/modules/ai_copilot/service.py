"""Grounded AI copilot — deterministic tool routing (Gemini optional later)."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.shared.errors import NotFoundError

from app.infra.db.models import AiConversationModel, AiMessageModel, MessageRole
from app.modules.ai_copilot.schemas import (
    AiChatSyncResponseData,
    Citation,
    ConversationDetail,
    ConversationSummary,
    MessageOut,
    ToolTraceSummary,
)
from app.modules.network.service import NetworkService
from app.modules.predictions.service import PredictionService


class AiCopilotService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._predictions = PredictionService(session)
        self._network = NetworkService(session)

    async def list_conversations(self, ctx: AuthContext) -> list[ConversationSummary]:
        rows = (
            await self._session.execute(
                select(AiConversationModel)
                .where(
                    AiConversationModel.user_id == ctx.user_id,
                    AiConversationModel.deleted_at.is_(None),
                )
                .order_by(AiConversationModel.updated_at.desc())
                .limit(50)
            )
        ).scalars().all()
        return [
            ConversationSummary(
                id=r.id,
                title=r.title,
                updated_at=r.updated_at,
                district_id=r.district_id,
            )
            for r in rows
        ]

    async def get_conversation(self, ctx: AuthContext, conversation_id: UUID) -> ConversationDetail:
        conv = await self._session.get(AiConversationModel, conversation_id)
        if conv is None or conv.deleted_at is not None or conv.user_id != ctx.user_id:
            raise NotFoundError("Conversation not found")
        messages = (
            await self._session.execute(
                select(AiMessageModel)
                .where(AiMessageModel.conversation_id == conversation_id)
                .order_by(AiMessageModel.created_at.asc())
            )
        ).scalars().all()
        return ConversationDetail(
            conversation=ConversationSummary(
                id=conv.id,
                title=conv.title,
                updated_at=conv.updated_at,
                district_id=conv.district_id,
            ),
            messages=[
                MessageOut(
                    id=m.id,
                    role=m.role.value,
                    content=m.content,
                    citations=[Citation(**c) for c in (m.citations or [])],
                    created_at=m.created_at,
                )
                for m in messages
            ],
        )

    async def delete_conversation(self, ctx: AuthContext, conversation_id: UUID) -> None:
        conv = await self._session.get(AiConversationModel, conversation_id)
        if conv is None or conv.user_id != ctx.user_id:
            raise NotFoundError("Conversation not found")
        conv.deleted_at = datetime.now(UTC)
        await self._session.commit()

    async def chat_sync(
        self,
        ctx: AuthContext,
        *,
        message: str,
        conversation_id: UUID | None = None,
        district_id: UUID | None = None,
    ) -> AiChatSyncResponseData:
        if conversation_id:
            conv = await self._session.get(AiConversationModel, conversation_id)
            if conv is None or conv.deleted_at is not None or conv.user_id != ctx.user_id:
                raise NotFoundError("Conversation not found")
        else:
            title = message.strip()[:60] or "New conversation"
            conv = AiConversationModel(
                id=uuid.uuid4(),
                user_id=ctx.user_id,
                title=title,
                district_id=district_id,
            )
            self._session.add(conv)
            await self._session.flush()

        user_msg = AiMessageModel(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role=MessageRole.user,
            content=message,
            citations=[],
            tool_traces=[],
        )
        self._session.add(user_msg)

        content, citations, traces = await self._grounded_answer(ctx, message)
        assistant_msg = AiMessageModel(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role=MessageRole.assistant,
            content=content,
            citations=[c.model_dump() for c in citations],
            tool_traces=[t.model_dump() for t in traces],
        )
        self._session.add(assistant_msg)
        conv.updated_at = datetime.now(UTC)
        await self._session.commit()

        return AiChatSyncResponseData(
            conversation_id=conv.id,
            message_id=assistant_msg.id,
            content=content,
            citations=citations,
            tool_traces=traces,
        )

    async def _grounded_answer(
        self, ctx: AuthContext, message: str
    ) -> tuple[str, list[Citation], list[ToolTraceSummary]]:
        text = message.lower()
        citations: list[Citation] = []
        traces: list[ToolTraceSummary] = []

        if any(k in text for k in ("hotspot", "cluster", "heat")):
            t0 = time.perf_counter()
            data = await self._predictions.hotspots_current(ctx, limit=5)
            traces.append(
                ToolTraceSummary(
                    tool_name="get_hotspots_current",
                    status="ok",
                    latency_ms=int((time.perf_counter() - t0) * 1000),
                )
            )
            if not data.features:
                return (
                    "No current hotspot run is published yet. Run prediction seed after migrations.",
                    citations,
                    traces,
                )
            lines = [
                f"Current hotspot run ({data.run.method if data.run else 'n/a'}) highlights:"
            ]
            for f in data.features:
                label = (f.properties or {}).get("label", f"rank-{f.rank}")
                lines.append(
                    f"- #{f.rank} {label}: score {f.score:.2f}, incidents {f.incident_count}"
                )
                citations.append(
                    Citation(
                        type="hotspot",
                        id=str(f.id),
                        label=str(label),
                        href="/map",
                    )
                )
            lines.append("Use as patrol focus candidates — human review required.")
            return "\n".join(lines), citations, traces

        if any(k in text for k in ("risk", "predict", "forecast", "shap", "explain")):
            t0 = time.perf_counter()
            data = await self._predictions.current(ctx, top_n=5)
            traces.append(
                ToolTraceSummary(
                    tool_name="get_current_predictions",
                    status="ok",
                    latency_ms=int((time.perf_counter() - t0) * 1000),
                )
            )
            if not data.run or not data.values:
                return "No current risk prediction run found.", citations, traces
            lines = [
                f"Model {data.run.model_code}@{data.run.model_version} "
                f"({data.run.status_banner}) — top station risk scores:"
            ]
            for v in data.values:
                name = (v.properties or {}).get("station_name", str(v.scope.get("station_id")))
                lines.append(f"- {name}: {v.value:.3f}")
                citations.append(
                    Citation(
                        type="prediction",
                        id=str(v.id),
                        label=str(name),
                        href="/prediction",
                    )
                )
            top = data.values[0]
            try:
                expl = await self._predictions.explanation(ctx, top.id)
                traces.append(
                    ToolTraceSummary(tool_name="get_prediction_explanation", status="ok", latency_ms=0)
                )
                if expl.summary_text:
                    lines.append("")
                    lines.append(f"SHAP note for top station: {expl.summary_text}")
            except Exception:
                traces.append(
                    ToolTraceSummary(
                        tool_name="get_prediction_explanation", status="error", latency_ms=0
                    )
                )
            return "\n".join(lines), citations, traces

        if any(k in text for k in ("network", "repeat", "offender", "link", "gang")):
            t0 = time.perf_counter()
            repeats = await self._network.repeat_offenders(ctx, limit=5)
            graph = await self._network.graph(ctx, limit_nodes=20)
            traces.append(
                ToolTraceSummary(
                    tool_name="get_network_graph",
                    status="ok",
                    latency_ms=int((time.perf_counter() - t0) * 1000),
                )
            )
            lines = [
                f"Network snapshot: {graph.meta.node_count} persons, {graph.meta.edge_count} links.",
                "Repeat offenders (demo):",
            ]
            for r in repeats:
                lines.append(f"- {r.full_name}: score {r.score:.2f}, incidents {r.incident_count}")
                citations.append(
                    Citation(
                        type="incident",
                        id=str(r.person_id),
                        label=r.full_name,
                        href="/network",
                    )
                )
            return "\n".join(lines), citations, traces

        # default briefing
        t0 = time.perf_counter()
        preds = await self._predictions.current(ctx, top_n=3)
        hotspots = await self._predictions.hotspots_current(ctx, limit=3)
        traces.append(
            ToolTraceSummary(
                tool_name="command_brief_tools",
                status="ok",
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )
        )
        lines = [
            "CrimeLens grounded brief (deterministic tools — Gemini can replace this later):",
            "",
            f"Risk run: {preds.run.model_code + '@' + preds.run.model_version if preds.run else 'none'}",
        ]
        for v in preds.values[:3]:
            name = (v.properties or {}).get("station_name", "station")
            lines.append(f"  • {name}: risk {v.value:.3f}")
            citations.append(
                Citation(type="prediction", id=str(v.id), label=str(name), href="/prediction")
            )
        lines.append(
            f"Hotspots: {len(hotspots.features)} active features"
            + (f" via {hotspots.run.method}" if hotspots.run else "")
        )
        for f in hotspots.features[:3]:
            label = (f.properties or {}).get("label", f"#{f.rank}")
            lines.append(f"  • {label}: {f.score:.2f}")
            citations.append(
                Citation(type="hotspot", id=str(f.id), label=str(label), href="/map")
            )
        lines.append("")
        lines.append(
            "Ask about 'risk', 'hotspots', or 'network' for focused tool retrieval."
        )
        return "\n".join(lines), citations, traces
