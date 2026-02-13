from datetime import date
from app.database import get_db
import structlog

logger = structlog.get_logger()

# Pricing per 1M tokens (USD) - update as providers change rates
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.0},
    "gemini-3-pro-image-preview": {"input": 0.0, "output": 120.0},
    "gemini-2.5-flash-image": {"input": 0.0, "output": 30.0},
    "claude-haiku-4-5-20251001": {"input": 0.8, "output": 4.0},
}


class CostTracker:
    """Records and queries API cost data by date and model."""

    async def record_usage(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        images_generated: int = 0,
    ) -> None:
        db = await get_db()
        today = date.today().isoformat()
        estimated_cost = self._estimate_cost(
            model, input_tokens, output_tokens
        )

        # UPSERT: increment counters if row exists, insert if not
        await db.execute(
            """INSERT INTO cost_tracking (date, model, request_count, input_tokens, output_tokens, images_generated, estimated_cost_usd)
               VALUES (?, ?, 1, ?, ?, ?, ?)
               ON CONFLICT(date, model) DO UPDATE SET
                   request_count = request_count + 1,
                   input_tokens = input_tokens + excluded.input_tokens,
                   output_tokens = output_tokens + excluded.output_tokens,
                   images_generated = images_generated + excluded.images_generated,
                   estimated_cost_usd = estimated_cost_usd + excluded.estimated_cost_usd""",
            (today, model, input_tokens, output_tokens, images_generated, estimated_cost),
        )
        await db.commit()

    async def get_daily_costs(self, target_date: str | None = None) -> list[dict]:
        db = await get_db()
        target = target_date or date.today().isoformat()
        cursor = await db.execute(
            "SELECT * FROM cost_tracking WHERE date = ? ORDER BY model",
            (target,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_cost_summary(self, days: int = 30) -> dict:
        db = await get_db()
        cursor = await db.execute(
            """SELECT
                   SUM(request_count) as total_requests,
                   SUM(input_tokens) as total_input_tokens,
                   SUM(output_tokens) as total_output_tokens,
                   SUM(images_generated) as total_images,
                   SUM(estimated_cost_usd) as total_cost_usd
               FROM cost_tracking
               WHERE date >= date('now', ? || ' days')""",
            (f"-{days}",),
        )
        row = await cursor.fetchone()
        return dict(row) if row else {}

    async def get_cost_by_model(self, days: int = 30) -> list[dict]:
        db = await get_db()
        cursor = await db.execute(
            """SELECT model,
                   SUM(request_count) as total_requests,
                   SUM(input_tokens) as total_input_tokens,
                   SUM(output_tokens) as total_output_tokens,
                   SUM(images_generated) as total_images,
                   SUM(estimated_cost_usd) as total_cost_usd
               FROM cost_tracking
               WHERE date >= date('now', ? || ' days')
               GROUP BY model
               ORDER BY total_cost_usd DESC""",
            (f"-{days}",),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    def _estimate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        pricing = MODEL_PRICING.get(model)
        if not pricing:
            return 0.0
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)


cost_tracker = CostTracker()
