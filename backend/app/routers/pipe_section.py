"""管段档案接口：维护管段，覆盖总览工作台、封存管段、恢复在役、登记迁改、标记废弃与档案修正。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.pipe_section import PipeSectionService

router = APIRouter(prefix="/api/pipe_section", tags=["管段档案"])

service = PipeSectionService()

LIST_FIELDS = ["管段编号", "管线类型", "材质规格", "埋设深度", "建设年代", "产权单位", "所在道路", "管段状态"]
STATUSES = ["在役", "废弃", "封存", "迁改中"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按管段编号检索"),
    status: str | None = Query(default=None, description="在役、废弃、封存、迁改中"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按管段编号与状态过滤管段档案列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/overview")
def overview(
    group_by: str = Query(default="pipeline", description="pipeline 按管线分组，location 按空间位置分组"),
) -> dict[str, Any]:
    """总览工作台：按管线或空间位置分组，保留在役/废弃等状态分组与待补项统计。"""
    if group_by not in ("pipeline", "location"):
        raise HTTPException(status_code=400, detail="分组方式仅支持 pipeline（按管线）或 location（按空间位置）")
    return service.overview(group_by=group_by)


# 静态路径必须声明在 /{entry_id} 之前，否则会被当成管段 id 匹配
@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出管段档案清单：返回全量数据，包含坐标缺失与编号重复标记，不静默剔除。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "pipe_section", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条管段明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"管段 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条管段，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段或字段不合法：{'、'.join(missing)}")
    return ActionResult(ok=True, message="管段已登记", entry=entry)


@router.patch("/{entry_id}", response_model=ActionResult)
def update_entry(entry_id: int, payload: EntryPayload) -> ActionResult:
    """修正管段档案：补齐坐标、核实重复编号等；校验不通过时整体不写入。"""
    entry, message = service.update_entry(entry_id, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条管段执行封存管段、恢复在役、登记迁改、标记废弃；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
