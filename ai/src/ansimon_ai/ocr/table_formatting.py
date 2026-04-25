from __future__ import annotations

from ansimon_ai.ocr.types import OCRResult, OCRSegment, OCRTable, OCRVertex


def render_table_text(table: OCRTable) -> str:
    if not table.cells:
        return table.text.strip()

    max_row = max(cell.row_index for cell in table.cells)
    max_col = max(cell.column_index for cell in table.cells)
    rows = [["" for _ in range(max_col + 1)] for _ in range(max_row + 1)]

    for cell in sorted(table.cells, key=lambda item: (item.row_index, item.column_index)):
        value = cell.text.strip()
        if not value:
            continue

        row_index = max(cell.row_index, 0)
        column_index = max(cell.column_index, 0)
        current = rows[row_index][column_index].strip()
        if current and current != value:
            rows[row_index][column_index] = f"{current} / {value}"
        else:
            rows[row_index][column_index] = value

    rendered_rows: list[str] = []
    for row in rows:
        normalized = [cell.strip() for cell in row]
        if any(normalized):
            rendered_rows.append(" | ".join(normalized))

    return "\n".join(rendered_rows).strip()


def is_tabular_table(table: OCRTable) -> bool:
    if len(table.cells) < 2:
        return False
    distinct_columns = {cell.column_index for cell in table.cells}
    return len(distinct_columns) >= 2


def format_ocr_result_text(result: OCRResult) -> str:
    segment_lines = [segment.text.strip() for segment in result.segments if segment.text.strip()]
    tabular_tables = [table for table in result.tables if is_tabular_table(table)]

    if not tabular_tables:
        return "\n".join(segment_lines).strip() or (result.full_text or "").strip()

    if not segment_lines:
        rendered = [render_table_text(table) for table in tabular_tables if render_table_text(table)]
        return "\n\n".join(rendered).strip() or (result.full_text or "").strip()

    table_ranges = _build_table_ranges(result, tabular_tables)
    if not table_ranges:
        base_text = "\n".join(segment_lines).strip() or (result.full_text or "").strip()
        rendered = [render_table_text(table) for table in tabular_tables if render_table_text(table)]
        if base_text and rendered:
            return f"{base_text}\n\n" + "\n\n".join(rendered)
        return base_text or "\n\n".join(rendered).strip()

    rendered_lines: list[str] = []
    consumed_indexes: set[int] = set()

    for index, segment in enumerate(result.segments):
        if index in consumed_indexes:
            continue

        matched = None
        for table, covered_indexes in table_ranges:
            if covered_indexes and covered_indexes[0] == index:
                matched = (table, covered_indexes)
                break

        if matched is not None:
            table, covered_indexes = matched
            table_text = render_table_text(table)
            if table_text:
                rendered_lines.append(table_text)
            consumed_indexes.update(covered_indexes)
            continue

        text = segment.text.strip()
        if text:
            rendered_lines.append(text)

    return "\n".join(rendered_lines).strip() or "\n".join(segment_lines).strip() or (result.full_text or "").strip()


def _build_table_ranges(result: OCRResult, tables: list[OCRTable]) -> list[tuple[OCRTable, list[int]]]:
    ranges: list[tuple[OCRTable, list[int]]] = []
    for table in tables:
        covered_indexes = [
            index
            for index, segment in enumerate(result.segments)
            if _segment_is_within_table(segment, table)
        ]
        if covered_indexes:
            ranges.append((table, covered_indexes))
    return sorted(ranges, key=lambda item: item[1][0])


def _segment_is_within_table(segment: OCRSegment, table: OCRTable) -> bool:
    table_bounds = _table_bounds(table)
    if (
        segment.min_x is None
        or segment.max_x is None
        or segment.min_y is None
        or segment.max_y is None
        or table_bounds is None
    ):
        return False

    table_min_x, table_max_x, table_min_y, table_max_y = table_bounds
    center_x = segment.center_x
    center_y = segment.center_y
    if center_x is not None and center_y is not None:
        if table_min_x <= center_x <= table_max_x and table_min_y <= center_y <= table_max_y:
            return True

    overlap_width = min(segment.max_x, table_max_x) - max(segment.min_x, table_min_x)
    overlap_height = min(segment.max_y, table_max_y) - max(segment.min_y, table_min_y)
    if overlap_width <= 0 or overlap_height <= 0:
        return False

    segment_area = (segment.max_x - segment.min_x) * (segment.max_y - segment.min_y)
    if segment_area <= 0:
        return False

    overlap_ratio = (overlap_width * overlap_height) / segment_area
    return overlap_ratio >= 0.5


def _table_bounds(table: OCRTable) -> tuple[float, float, float, float] | None:
    vertices: list[OCRVertex] = []
    if table.vertices:
        vertices.extend(table.vertices)
    else:
        for cell in table.cells:
            if cell.vertices:
                vertices.extend(cell.vertices)

    if not vertices:
        return None

    return (
        min(vertex.x for vertex in vertices),
        max(vertex.x for vertex in vertices),
        min(vertex.y for vertex in vertices),
        max(vertex.y for vertex in vertices),
    )
