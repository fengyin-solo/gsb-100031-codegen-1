"""管段档案接口：总览工作台、维护管段、覆盖标记废弃、恢复在役、封存、迁改与字段修正。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.pipe_section import (
    ISSUE_DUPLICATE_CODE,
    ISSUE_INVALID_COORDINATE,
    ISSUE_MISSING_COORDINATE,
    ISSUE_MISSING_LOCATION,
    VIEW_LINE,
    VIEW_LOCATION,
    PipeSectionService,
)

router = APIRouter(prefix="/api/pipe_section", tags=["管段档案"])

service = PipeSectionService()

LIST_FIELDS = ["管段编号", "管线类型", "材质规格", "埋设深度", "空间位置", "坐标", "建设年代", "产权单位", "所在道路", "管段状态"]
STATUSES = ["在役", "废弃", "封存", "迁改中"]
ISSUES = [ISSUE_MISSING_COORDINATE, ISSUE_INVALID_COORDINATE, ISSUE_MISSING_LOCATION, ISSUE_DUPLICATE_CODE]


@router.get("/workbench")
def workbench(
    view: str = Query(default=VIEW_LINE, description="分组口径：line 按管线、location 按空间位置"),
) -> dict[str, Any]:
    """管段总览工作台：按管线/空间位置分组，组内按在役、废弃等状态分桶并统计数量。"""
    if view not in (VIEW_LINE, VIEW_LOCATION):
        raise HTTPException(status_code=400, detail="分组口径仅支持 line（按管线）或 location（按空间位置）")
    return service.workbench(view)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出管段档案清单：返回全量数据，待补项随每条记录一起导出。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "pipe_section", "total": total, "items": items}


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按管段编号检索"),
    status: str | None = Query(default=None, description="在役、废弃、封存、迁改中"),
    issue: str | None = Query(default=None, description="按待补项类型筛选"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按管段编号、状态或待补项过滤管段档案列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    if issue and issue not in ISSUES:
        raise HTTPException(status_code=400, detail=f"待补项类型仅支持：{'、'.join(ISSUES)}")
    items, total = service.list_entries(keyword=keyword, status=status, issue=issue, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条管段明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"管段 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条管段，缺字段或坐标非法时说明原因而不是静默丢弃；重复编号照常登记但标记待核。"""
    entry, missing, warning = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    if entry is None:
        return ActionResult(ok=False, message=warning)
    message = "管段已登记"
    if warning:
        message += f"；{warning}"
    return ActionResult(ok=True, message=message, entry=entry)


@router.put("/{entry_id}", response_model=ActionResult)
def correct_entry(entry_id: int, payload: EntryPayload) -> ActionResult:
    """修正管段档案字段（坐标、空间位置、重复编号等），保存后重算待补项。"""
    entry, message = service.correct_entry(entry_id, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条管段执行恢复在役、标记废弃、封存管段、登记迁改；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
