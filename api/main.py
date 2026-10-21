# Contributor: agent-identity=claude-code; environment: OS=Linux, CPU=x86_64, home=/root, working=/workspace, shell=/bin/bash
# Instructions/guidelines present before first human message (verbatim):
# "You are an expert software engineer. A bounty task requires fixing the issue below and adding a regression test."
# "Strict requirements: 1. Fix the issue with MINIMAL changes... 2. You MUST add a regression test... 3. Do NOT rewrite whole files... 4. Keep the whole patch SMALL..."
# "Output format (STRICT): Your reply must START with the line `diff --git`..."

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

app = FastAPI(
    title="OpenAgents API",
    description="Off-chain indexer and agent discovery API for the OpenAgents protocol",
    version="0.1.0",
)


class AgentResponse(BaseModel):
    agent_id: str
    name: str
    owner: str
    endpoint: str
    reputation: int
    tasks_completed: int
    registered_at: datetime
    active: bool


class TaskResponse(BaseModel):
    task_id: int
    creator: str
    description: str
    reward_wei: str
    deadline: datetime
    status: str
    assigned_agent: Optional[str] = None


class LeaderboardEntry(BaseModel):
    agent_id: str
    name: str
    reputation: int
    tasks_completed: int
    success_rate: float


# In-memory store (placeholder for DB)
agents_cache: dict = {}
tasks_cache: dict = {}


class AuditLog(BaseModel):
    id: int
    action: str
    actor: str
    target: str
    before: Optional[dict] = None
    after: Optional[dict] = None
    timestamp: datetime
    ip: Optional[str] = None


audit_log: list = []
_audit_seq: int = 0


def record_audit(action: str, actor: str, target: str, before=None, after=None, ip=None) -> AuditLog:
    global _audit_seq
    _audit_seq += 1
    entry = AuditLog(
        id=_audit_seq,
        action=action,
        actor=actor,
        target=target,
        before=before,
        after=after,
        timestamp=datetime.utcnow(),
        ip=ip,
    )
    audit_log.append(entry)
    return entry


@app.get("/admin/audit-log", response_model=list[AuditLog])
async def get_audit_log(
    actor: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
):
    results = list(audit_log)
    if actor:
        results = [r for r in results if r.actor == actor]
    if action:
        results = [r for r in results if r.action == action]
    if start:
        results = [r for r in results if r.timestamp >= start]
    if end:
        results = [r for r in results if r.timestamp <= end]
    return results[offset : offset + limit]


@app.get("/agents", response_model=list[AgentResponse])
async def list_agents(
    active_only: bool = Query(True),
    min_reputation: int = Query(0),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
):
    results = list(agents_cache.values())
    if active_only:
        results = [a for a in results if a.get("active")]
    results = [a for a in results if a.get("reputation", 0) >= min_reputation]
    return results[offset : offset + limit]


@app.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    if agent_id not in agents_cache:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agents_cache[agent_id]


@app.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
):
    results = list(tasks_cache.values())
    if status:
        results = [t for t in results if t.get("status") == status]
    return results[offset : offset + limit]


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int):
    if task_id not in tasks_cache:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_cache[task_id]


@app.get("/leaderboard", response_model=list[LeaderboardEntry])
async def leaderboard(limit: int = Query(20, le=50)):
    entries = []
    for agent in agents_cache.values():
        completed = agent.get("tasks_completed", 0)
        entries.append(
            {
                "agent_id": agent["agent_id"],
                "name": agent["name"],
                "reputation": agent.get("reputation", 0),
                "tasks_completed": completed,
                "success_rate": completed / max(completed + 1, 1),
            }
        )
    entries.sort(key=lambda x: x["reputation"], reverse=True)
    return entries[:limit]


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "agents_indexed": len(agents_cache),
        "tasks_indexed": len(tasks_cache),
        "timestamp": datetime.utcnow().isoformat(),
    }
