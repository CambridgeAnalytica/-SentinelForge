"""
Agent Testing API endpoints.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user
from models import User
from schemas import AgentTestRequest, AgentTestResponse
from services.agent_service import run_agent_test, list_tests, get_test

router = APIRouter()
logger = logging.getLogger("sentinelforge.agent")


@router.post("/test", response_model=AgentTestResponse)
async def launch_agent_test(
    request: AgentTestRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Launch an agent safety test against the specified endpoint."""
    logger.info(f"Agent test requested: {request.endpoint} by {user.username}")
    test = await run_agent_test(
        db=db,
        endpoint=request.endpoint,
        allowed_tools=request.allowed_tools,
        forbidden_actions=request.forbidden_actions,
        test_scenarios=request.test_scenarios,
        user_id=user.id,
    )
    # Dispatch webhook notification
    background_tasks.add_task(
        _dispatch_webhook,
        "agent.test.completed",
        {
            "test_id": test.id,
            "endpoint": test.endpoint,
            "status": test.status.value,
            "risk_level": test.risk_level,
        },
    )

    return AgentTestResponse(
        id=test.id,
        endpoint=test.endpoint,
        status=test.status.value,
        risk_level=test.risk_level,
        findings_count=test.findings_count,
        results=test.results or {},
        created_at=test.created_at,
        completed_at=test.completed_at,
    )


@router.get("/tests")
async def list_agent_tests(
    endpoint: str = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List agent tests."""
    tests = await list_tests(db, endpoint=endpoint)
    return [
        {
            "id": t.id,
            "endpoint": t.endpoint,
            "status": t.status.value,
            "risk_level": t.risk_level,
            "findings_count": t.findings_count,
            "created_at": t.created_at.isoformat(),
        }
        for t in tests
    ]


@router.get("/tests/{test_id}", response_model=AgentTestResponse)
async def get_agent_test(
    test_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific agent test."""
    test = await get_test(db, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Agent test not found")

    return AgentTestResponse(
        id=test.id,
        endpoint=test.endpoint,
        status=test.status.value,
        risk_level=test.risk_level,
        findings_count=test.findings_count,
        results=test.results or {},
        created_at=test.created_at,
        completed_at=test.completed_at,
    )


async def _dispatch_webhook(event_type: str, payload: dict) -> None:
    """Background task: dispatch webhook event."""
    try:
        from services.webhook_service import dispatch_webhook_event

        await dispatch_webhook_event(event_type, payload)
    except Exception as e:
        logger.error(f"Webhook dispatch error: {e}")
