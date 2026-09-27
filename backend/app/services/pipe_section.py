"""管段档案业务规则：状态流转、字段校验、坐标/编号数据质量标注与总览分组口径都收在这里。

数据质量原则：坐标缺失、坐标格式有误、同一管段编号重复出现，都不能静默丢弃，
而是给记录打上 issues 标记进入"待补项"，由前端引导修正。
"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "pipe_section"
# 登记时必填的字段；坐标允许缺失（缺失只标记待补，不拦截建档）
REQUIRED_FIELDS = ["管段编号", "管线类型", "材质规格"]
# 总览工作台与列表必须保留的四个核心字段
CORE_FIELDS = ["管段编号", "管线类型", "材质规格", "埋设深度"]
# 允许通过修正接口修改的字段（状态只能走动作流转，不在这里改）
EDITABLE_FIELDS = [
    "管段编号", "管线类型", "材质规格", "埋设深度", "建设年代", "产权单位",
    "所在道路", "所属管线", "空间位置", "经度", "纬度",
]
STATUS_ORDER = ["在役", "废弃", "封存", "迁改中"]
ACTION_RULES = {"封存管段": "封存", "恢复在役": "在役", "登记迁改": "迁改中", "标记废弃": "废弃"}
# 坐标精度：按 0.01 度网格做"按空间位置"分组
LOCATION_GRID = 0.01


def _to_float(value: Any) -> float | None:
    """把经度/纬度转成数字；空值与无法解析的值都返回 None（由调用方区分原因）。"""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        text = str(value).strip()
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


class PipeSectionService:
    # ---- 读取与数据质量标注 -------------------------------------------------

    def _raw_rows(self) -> list[dict[str, Any]]:
        return store.rows(MODULE)

    def _duplicate_codes(self, rows: list[dict[str, Any]]) -> set[str]:
        """出现两次及以上的管段编号；空编号不参与重复判定。"""
        seen: set[str] = set()
        duplicate: set[str] = set()
        for row in rows:
            code = str(row.get("管段编号") or "").strip()
            if not code:
                continue
            if code in seen:
                duplicate.add(code)
            seen.add(code)
        return duplicate

    def _issues(self, row: dict[str, Any], duplicate_codes: set[str]) -> list[str]:
        """计算一条管段的待补项：坐标问题优先细分缺失/格式错误，重复编号单独标注。"""
        issues: list[str] = []
        lng, lat = _to_float(row.get("经度")), _to_float(row.get("纬度"))
        if lng is None or lat is None:
            raw_lng = str(row.get("经度") or "").strip()
            raw_lat = str(row.get("纬度") or "").strip()
            if raw_lng or raw_lat:
                issues.append("坐标格式有误，待补")
            else:
                issues.append("坐标待补")
        code = str(row.get("管段编号") or "").strip()
        if code and code in duplicate_codes:
            issues.append("管段编号重复，待核实")
        return issues

    def _serialize(self, row: dict[str, Any], duplicate_codes: set[str]) -> dict[str, Any]:
        """统一出口：列表、详情、总览都走这里，保证三处口径一致。"""
        lng, lat = _to_float(row.get("经度")), _to_float(row.get("纬度"))
        issues = self._issues(row, duplicate_codes)
        return {
            "id": row.get("id"),
            "status": row.get("status"),
            "管段状态": row.get("status"),
            "管段编号": row.get("管段编号"),
            "管线类型": row.get("管线类型"),
            "材质规格": row.get("材质规格"),
            "埋设深度": row.get("埋设深度"),
            "建设年代": row.get("建设年代"),
            "产权单位": row.get("产权单位"),
            "所在道路": row.get("所在道路"),
            "所属管线": row.get("所属管线"),
            "空间位置": row.get("空间位置"),
            "经度": lng,
            "纬度": lat,
            "hasCoordinate": lng is not None and lat is not None,
            "duplicate": "管段编号重复，待核实" in issues,
            "issues": issues,
        }

    def _serialize_all(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        duplicate_codes = self._duplicate_codes(rows)
        return [self._serialize(row, duplicate_codes) for row in rows]

    # ---- 列表与详情 ---------------------------------------------------------

    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = self._raw_rows()
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("管段编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        page_rows = rows[start:start + size]
        # 重复判定必须基于全量数据，否则筛选或翻页后会漏标，等于把问题静默藏起来
        duplicate_codes = self._duplicate_codes(self._raw_rows())
        return [self._serialize(row, duplicate_codes) for row in page_rows], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        row = store.find(MODULE, entry_id)
        if row is None:
            return None
        return self._serialize(row, self._duplicate_codes(self._raw_rows()))

    # ---- 总览工作台 ---------------------------------------------------------

    def overview(self, group_by: str = "pipeline") -> dict[str, Any]:
        """按管线或空间位置分组汇总；坐标有问题的管段不参与空间分组，归入"坐标待补"。"""
        items = self._serialize_all(self._raw_rows())

        def group_key(item: dict[str, Any]) -> tuple[str, str]:
            if group_by == "location":
                if item["hasCoordinate"]:
                    lng = round(item["经度"] / LOCATION_GRID) * LOCATION_GRID
                    lat = round(item["纬度"] / LOCATION_GRID) * LOCATION_GRID
                    lng_text = f"{lng:.2f}"
                    lat_text = f"{lat:.2f}"
                    place = str(item.get("空间位置") or "").strip()
                    label = f"{place}（{lng_text}, {lat_text}）" if place else f"网格 {lng_text}, {lat_text}"
                    return f"grid:{lng_text},{lat_text}", label
                return "coord-missing", "坐标待补 / 待修正"
            pipeline = str(item.get("所属管线") or "").strip()
            return (f"line:{pipeline}", pipeline) if pipeline else ("line:none", "未归属管线")

        grouped: dict[str, dict[str, Any]] = {}
        for item in items:
            key, label = group_key(item)
            group = grouped.setdefault(key, {"key": key, "label": label, "counts": {}, "items": []})
            group["counts"][item["status"]] = group["counts"].get(item["status"], 0) + 1
            group["items"].append(item)

        groups = list(grouped.values())
        # 坐标待补组固定排在最后，其余按名称排序，前端切换时顺序稳定
        groups.sort(key=lambda g: (g["key"] == "coord-missing", g["label"]))
        for group in groups:
            group["total"] = len(group["items"])

        counts = {name: 0 for name in STATUS_ORDER}
        for item in items:
            counts[item["status"]] = counts.get(item["status"], 0) + 1
        return {
            "groupBy": group_by,
            "total": len(items),
            "counts": counts,
            "pendingCoord": sum(1 for item in items if not item["hasCoordinate"]),
            "duplicate": sum(1 for item in items if item["duplicate"]),
            "groups": groups,
        }

    # ---- 写入：登记、状态动作、修正 ----------------------------------------

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        lng_error = self._coordinate_error(values)
        if lng_error:
            return None, [lng_error]
        rows = self._raw_rows()
        entry: dict[str, Any] = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        for field in EDITABLE_FIELDS:
            if field in ("经度", "纬度"):
                entry[field] = _to_float(values.get(field))
            elif field in values:
                entry[field] = values.get(field)
        entry["status"] = STATUS_ORDER[0]
        entry["管段状态"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return self._serialize(entry, self._duplicate_codes(rows)), []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"管段 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于管段档案可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        # 管段状态展示字段与状态机字段同步，避免列表与详情口径不一
        entry["管段状态"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = target == "废弃"
        return self._serialize(entry, self._duplicate_codes(self._raw_rows())), f"管段已{action}"

    def update_entry(
        self, entry_id: int, values: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str]:
        """修正管段档案字段；只接受白名单字段，必填项与坐标格式不通过时说明原因，不做部分写入。"""
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"管段 {entry_id} 不存在或已归档"
        changes = {key: values[key] for key in EDITABLE_FIELDS if key in values}
        if not changes:
            return None, "没有可修正的字段"
        merged = {**entry, **changes}
        missing = [
            field for field in REQUIRED_FIELDS if not str(merged.get(field) or "").strip()
        ]
        if missing:
            return None, f"必填字段不能为空：{'、'.join(missing)}"
        coord_error = self._coordinate_error(changes)
        if coord_error:
            return None, coord_error
        for field, value in changes.items():
            if field in ("经度", "纬度"):
                entry[field] = _to_float(value)
            else:
                entry[field] = value
        # 编号、坐标修正后，重复/待补标记由 _serialize 即时重算，不保留陈旧标记
        return self._serialize(entry, self._duplicate_codes(self._raw_rows())), "管段档案已修正"

    def _coordinate_error(self, values: dict[str, Any]) -> str | None:
        """坐标只要给了值就必须成对且可解析；想清空请显式传空字符串。"""
        if "经度" not in values and "纬度" not in values:
            return None
        parts: list[float | None] = []
        for field in ("经度", "纬度"):
            if field in values and str(values.get(field) or "").strip():
                parsed = _to_float(values.get(field))
                if parsed is None:
                    return f"{field}格式不正确，请输入数字坐标"
                parts.append(parsed)
        if parts and len(parts) == 1:
            return "经度与纬度需要同时填写，只填一项时无法定位"
        return None
