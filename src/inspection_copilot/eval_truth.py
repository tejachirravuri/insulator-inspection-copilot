"""Ground truth for the data questions of the answer-quality evaluation.

Computed with plain SQL at evaluation time, independently of the service layer the agent's
tools use, so a bug in the tools cannot make a wrong answer look right. Because it is computed
live, the expected answers stay correct when inspections are added.

Each function returns (expected numbers, human-readable statement).
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

LATEST_RUN = """
    SELECT DISTINCT ON (image_id) id, image_id, mode, escalated, inference_ms
    FROM detection_runs ORDER BY image_id, id DESC
"""


async def _scalar(session: AsyncSession, sql: str):
    return (await session.execute(text(sql))).scalar()


async def n_images(session):
    n = await _scalar(session, "SELECT count(*) FROM images")
    return [n], f"{n} inspections"


async def n_flagged(session):
    # Detections whose most recent review asks for a human.
    n = await _scalar(
        session,
        """
        SELECT count(*) FROM (
            SELECT DISTINCT ON (detection_id) needs_human_review
            FROM detection_reviews ORDER BY detection_id, id DESC
        ) latest WHERE needs_human_review
        """,
    )
    return [n], f"{n} detections flagged for human review"


async def max_detections(session):
    """All inspections sharing the maximum (ties included) and the count."""
    rows = (
        await session.execute(
            text(
                f"""
                WITH counts AS (
                    SELECT r.image_id, count(d.id) AS n FROM ({LATEST_RUN}) r
                    JOIN detections d ON d.run_id = r.id GROUP BY r.image_id
                )
                SELECT image_id, n FROM counts WHERE n = (SELECT max(n) FROM counts)
                ORDER BY image_id
                """
            )
        )
    ).all()
    ids = [r.image_id for r in rows]
    n = rows[0].n
    return [*ids, n], f"inspection(s) {', '.join(map(str, ids))} with {n} insulators each"


async def avg_escalated_ms(session):
    avg = await _scalar(
        session, f"SELECT avg(inference_ms) FROM ({LATEST_RUN}) r WHERE r.escalated"
    )
    return [round(float(avg))], f"about {float(avg):.0f} ms on average"


async def n_fast_only(session):
    n = await _scalar(
        session, f"SELECT count(*) FROM ({LATEST_RUN}) r WHERE r.mode = 'fast' AND NOT r.escalated"
    )
    return [n], f"{n} inspections handled by the fast model alone"


async def max_conf_image3(session):
    value = await _scalar(
        session,
        f"""
        SELECT max(d.confidence) FROM ({LATEST_RUN}) r JOIN detections d ON d.run_id = r.id
        WHERE r.image_id = 3
        """,
    )
    return [round(float(value), 2)], f"highest confidence {float(value):.2f}"


async def not_insulator_image15(session):
    n = await _scalar(
        session,
        f"""
        SELECT count(*) FROM ({LATEST_RUN}) r
        JOIN detections d ON d.run_id = r.id
        JOIN LATERAL (
            SELECT agrees_with_detector FROM detection_reviews v
            WHERE v.detection_id = d.id ORDER BY v.id DESC LIMIT 1
        ) last_review ON true
        WHERE r.image_id = 15 AND NOT last_review.agrees_with_detector
        """,
    )
    return [n], f"{n} detections judged not to be insulators"


async def per_type(session):
    rows = (
        await session.execute(
            text("SELECT insulator_type, count(*) FROM images GROUP BY 1 ORDER BY 1")
        )
    ).all()
    return [n for _, n in rows], ", ".join(f"{t}: {n}" for t, n in rows)


TRUTH = {
    f.__name__: f
    for f in (
        n_images,
        n_flagged,
        max_detections,
        avg_escalated_ms,
        n_fast_only,
        max_conf_image3,
        not_insulator_image15,
        per_type,
    )
}
