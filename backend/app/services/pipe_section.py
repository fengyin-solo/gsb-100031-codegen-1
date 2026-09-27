"""管段档案业务规则：状态流转、字段校验、待补项识别与总览分组都收在这里。

工作台支持两种分组口径（view）：
- line：按管线类型分组；
- location：按空间位置分组，没有空间位置的管段进「空间位置待补」组，不丢弃。

待补项（issues）在读取时动态计算，修正后无需额外清洗即自动消失：
- 坐标缺失 / 坐标格式有误；
- 空间位置缺失；
- 管段编号重复（同一编号出现两次及以上，涉及的每条都标记）。
"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "pipe_section"
REQUIRED_FIELDS = ["管段编号", "管线类型", "材质规格", "埋设深度"]
OPTIONAL_FIELDS = ["空间位置", "坐标", "建设年代", "产权单位", "所在道路"]
CORRECTABLE_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS
STATUS_ORDER = ["在役", "废弃", "封存", "迁改中"]
ACTION_RULES = {"恢复在役": "在役", "标记废弃": "废弃", "封存管段": "封存", "登记迁改": "迁改中"}

ISSUE_MISSING_COORDINATE = "坐标缺失"
ISSUE_INVALID_COORDINATE = "坐标格式有误"
ISSUE_MISSING_LOCATION = "空间位置缺失"
ISSUE_DUPLICATE_CODE = "管段编号重复"

VIEW_LINE = "line"
VIEW_LOCATION = "location"
PENDING_LOCATION_GROUP = "空间位置待补"
MISSING_TYPE_GROUP = "管线类型待补"


def _coordinate_issue(value: Any) -> str | None:
    """坐标按「经度,纬度」校验；空值算缺失，解析失败或越界算格式有误。"""
    text = str(value or "").strip()
    if not text:
        return ISSUE_MISSING_COORDINATE
    parts = text.replace("，", ",").split(",")
    if len(parts) != 2:
        return ISSUE_INVALID_COORDINATE
    try:
        longitude = float(parts[0].strip())
        latitude = float(parts[1].strip())
    except ValueError:
        return ISSUE_INVALID_COORDINATE
    if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
        return ISSUE_INVALID_COORDINATE
    return None


def _canonical_coordinate(text: str) -> str:
    """合法坐标统一成不带多余空格的「经度,纬度」，避免同一坐标写出多种样子。"""
    longitude, latitude = (part.strip() for part in text.replace("，", ",").split(","))
    return f"{float(longitude)},{float(latitude)}"


class PipeSectionService:
    # ---- 读取与待补项识别 -------------------------------------------------

    def _snapshot(self) -> tuple[list[dict[str, Any]], set[str]]:
        """取全量管段，并算出当前重复的管段编号集合。"""
        rows = store.rows(MODULE)
        code_counts: dict[str, int] = {}
        for row in rows:
            code = str(row.get("管段编号") or "").strip()
            if code:
                code_counts[code] = code_counts.get(code, 0) + 1
        duplicates = {code for code, count in code_counts.items() if count > 1}
        return rows, duplicates

    def _decorate(self, row: dict[str, Any], duplicates: set[str]) -> dict[str, Any]:
        """给单条记录挂上 issues 与可直接展示的管段状态，不改写库存数据本身。"""
        entry = dict(row)
        issues: list[str] = []
        coordinate_issue = _coordinate_issue(entry.get("坐标"))
        if coordinate_issue:
            issues.append(coordinate_issue)
        if not str(entry.get("空间位置") or "").strip():
            issues.append(ISSUE_MISSING_LOCATION)
        code = str(entry.get("管段编号") or "").strip()
        if code and code in duplicates:
            issues.append(ISSUE_DUPLICATE_CODE)
        entry["issues"] = issues
        entry["has_issue"] = bool(issues)
        entry["管段状态"] = entry.get("status")
        return entry

    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        issue: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows, duplicates = self._snapshot()
        entries = [self._decorate(row, duplicates) for row in rows]
        if keyword:
            entries = [row for row in entries if keyword in str(row.get("管段编号", ""))]
        if status:
            entries = [row for row in entries if row.get("status") == status]
        if issue:
            entries = [row for row in entries if issue in row["issues"]]
        total = len(entries)
        start = max(page - 1, 0) * size
        return entries[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        _, duplicates = self._snapshot()
        entry = store.find(MODULE, entry_id)
        return self._decorate(entry, duplicates) if entry is not None else None

    # ---- 总览工作台 -------------------------------------------------------

    def workbench(self, view: str) -> dict[str, Any]:
        """按管线或空间位置聚合，组内再按在役/废弃等状态分桶，数量逐桶统计。"""
        rows, duplicates = self._snapshot()
        entries = [self._decorate(row, duplicates) for row in rows]

        grouped: dict[str, list[dict[str, Any]]] = {}
        order: list[str] = []
        for entry in entries:
            if view == VIEW_LOCATION:
                raw = str(entry.get("空间位置") or "").strip()
                key = raw or PENDING_LOCATION_GROUP
            else:
                raw = str(entry.get("管线类型") or "").strip()
                key = raw or MISSING_TYPE_GROUP
            if key not in grouped:
                grouped[key] = []
                order.append(key)
            grouped[key].append(entry)

        groups: list[dict[str, Any]] = []
        totals = {status: 0 for status in STATUS_ORDER}
        for key in order:
            members = grouped[key]
            buckets: dict[str, list[dict[str, Any]]] = {status: [] for status in STATUS_ORDER}
            unknown: list[dict[str, Any]] = []
            for entry in members:
                status = str(entry.get("status") or "")
                if status in buckets:
                    buckets[status].append(entry)
                else:
                    # 状态不在约定序列里也不丢弃，单独挂出来供修正
                    unknown.append(entry)
            counts = {status: len(buckets[status]) for status in STATUS_ORDER}
            counts["total"] = len(members)
            counts["pending"] = sum(1 for entry in members if entry["has_issue"])
            for status in STATUS_ORDER:
                totals[status] += counts[status]
            groups.append({
                "key": key,
                "label": key,
                "missing_location": key == PENDING_LOCATION_GROUP,
                "buckets": buckets,
                "unknown": unknown,
                "counts": counts,
            })

        totals["total"] = len(entries)
        pending_entries = [entry for entry in entries if entry["has_issue"]]
        return {
            "view": view,
            "groups": groups,
            "counts": totals,
            "issues": pending_entries,
            "issue_count": len(pending_entries),
        }

    # ---- 写入：登记 / 修正 / 状态流转 ------------------------------------

    def create_entry(
        self, values: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, list[str], str]:
        """登记管段。返回 (记录, 缺失字段, 警告)；坐标非法时记录不入库。"""
        missing = [
            field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()
        ]
        if missing:
            return None, missing, ""

        coordinate = str(values.get("坐标") or "").strip()
        if coordinate and _coordinate_issue(coordinate) == ISSUE_INVALID_COORDINATE:
            return None, [], "坐标格式应为「经度,纬度」，例如 120.102,30.286，管段未登记"

        rows = store.rows(MODULE)
        code = str(values.get("管段编号")).strip()
        duplicate = any(str(row.get("管段编号") or "").strip() == code for row in rows)

        entry: dict[str, Any] = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry[REQUIRED_FIELDS[0]] = code
        for field in REQUIRED_FIELDS[1:]:
            entry[field] = str(values.get(field) or "").strip()
        for field in OPTIONAL_FIELDS:
            entry[field] = str(values.get(field) or "").strip()
        if coordinate:
            entry["坐标"] = _canonical_coordinate(coordinate)
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)

        warning = ""
        if duplicate:
            warning = "管段编号与已有档案重复，已标记为「管段编号重复」待核，未做静默丢弃"
        _, duplicates = self._snapshot()
        return self._decorate(entry, duplicates), [], warning

    def correct_entry(
        self, entry_id: int, values: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str]:
        """修正档案字段；只接受可修正字段，坐标要过格式校验，保存后重算待补项。"""
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"管段 {entry_id} 不存在或已归档"

        updates = {key: value for key, value in values.items() if key in CORRECTABLE_FIELDS}
        if not updates:
            return None, "没有可修正的字段"

        code_update = updates.get("管段编号")
        if code_update is not None and not str(code_update).strip():
            return None, "管段编号不能为空，重复编号请改成正确的唯一编号"

        if updates.get("坐标") is not None:
            coordinate_issue = _coordinate_issue(updates["坐标"])
            if coordinate_issue == ISSUE_INVALID_COORDINATE:
                return None, "坐标格式应为「经度,纬度」，例如 120.102,30.286"

        for key, value in updates.items():
            text = str(value or "").strip()
            if key == "坐标" and text:
                text = _canonical_coordinate(text)
            entry[key] = text

        _, duplicates = self._snapshot()
        decorated = self._decorate(entry, duplicates)
        remaining = len(decorated["issues"])
        message = "管段信息已修正，待补项已清零" if not remaining else f"已保存，该管段仍有 {remaining} 项待补"
        return decorated, message

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"管段 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于管段档案可执行范围"
        target = ACTION_RULES[action]
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = target == "废弃"
        _, duplicates = self._snapshot()
        return self._decorate(entry, duplicates), f"管段已{action}"
