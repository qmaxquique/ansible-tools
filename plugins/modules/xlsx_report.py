#!/usr/bin/python
"""Ansible entry point for declarative XLSX reports."""

DOCUMENTATION = r"""
---
module: xlsx_report
short_description: Generate a styled XLSX workbook from declarative data
version_added: '0.1.0'
description:
  - Generate complete XLSX workbooks with multiple worksheets using openpyxl.
  - Support named styles, typed cells, formulas, tables, filters, and conditional formatting.
  - Compare workbook contents to provide idempotency and check mode.
  - The workbook is regenerated from the definition; existing workbooks are not edited in place.
author:
  - ansible-tools contributors
requirements:
  - Python >= 3.9 on the host running the module
  - openpyxl >= 3.1, < 4 on the host running the module
options:
  path:
    description:
      - Destination file on the host executing the module.
      - The parent directory must already exist. The destination cannot be a symlink.
    required: true
    type: path
  overwrite:
    description:
      - Allow replacing an existing file whose content differs from the definition.
      - An identical workbook remains unchanged even when this is false.
    type: bool
    default: true
  properties:
    description:
      - Workbook metadata as strings.
      - Supported keys are title, subject, creator, description, keywords, category,
        language, and last_modified_by.
    type: dict
    default: {}
  styles:
    description:
      - Mapping from style names to font, fill, border, alignment, and number_format definitions.
      - Colors accept six-digit RGB or eight-digit ARGB hexadecimal strings.
      - Use a fill mapping with color, or the background shorthand, for solid fills.
    type: dict
    default: {}
  sheets:
    description:
      - Non-empty list of worksheet definitions, in workbook order.
      - Each sheet requires name and columns. Columns are mappings with name and optional
        width, style, header_style, and number_format.
      - Each sheet may define rows, header_style, freeze_panes, auto_filter, tables,
        and conditional_formatting.
      - Rows accept positional lists, mappings keyed by column name, or objects with
        values and optional style and styles keyed by column name.
      - Cells accept scalar values or objects with value, optional type, style, and number_format.
      - Typed date and datetime values use ISO strings. Datetimes must have no timezone.
      - Use a cell object with formula for an Excel formula beginning with an equals sign.
      - Plain strings are always literal text, including strings beginning with an equals sign.
      - Tables require a workbook-unique name and accept ref, style, and stripe options.
        Table ranges must begin in header row 1 and fit within the declared data.
      - Tables include filters. When tables exist, auto_filter=true uses their filters.
        An explicit matching range uses the table filter; other overlapping ranges are rejected.
      - Conditional formatting requires column or range, equals or formula, and a
        named style or background or font_color.
    required: true
    type: list
    elements: dict
attributes:
  check_mode:
    support: full
    description: Render and compare the workbook without creating or changing the output file.
  diff_mode:
    support: none
  platform:
    platforms: posix
notes:
  - For reports generated in an Execution Environment, delegate to localhost and use run_once.
  - Formulas and conditional formatting are stored for Excel to evaluate.
  - The module does not calculate formula results.
  - Only ZIP metadata and core creation and modification timestamps are ignored during comparison.
  - Generated timestamps are fixed for reproducibility. All other workbook content is compared.
  - Charts, images, merged cells, and editing existing workbooks are outside the initial scope.
"""

EXAMPLES = r"""
- name: Generate a report on the controller
  ansible_tools.reporting.xlsx_report:
    path: /tmp/report.xlsx
    properties:
      title: Inventory report
    styles:
      header:
        font: {bold: true, color: 'FFFFFF'}
        fill: {color: '1F4E78'}
        alignment: {horizontal: center}
      success:
        background: 'C6EFCE'
        font: {color: '006100'}
    sheets:
      - name: Summary
        header_style: header
        freeze_panes: A2
        auto_filter: true
        columns:
          - {name: Server, width: 25}
          - {name: Status, width: 15}
          - {name: Updates, width: 12, number_format: '0'}
        rows:
          - ['server01', SUCCESS, 12]
          - ['server02', FAILED, 3]
        tables:
          - {name: Inventory, style: TableStyleMedium2}
        conditional_formatting:
          - {column: Status, equals: SUCCESS, style: success}
      - name: Totals
        columns:
          - {name: Metric, width: 25}
          - {name: Value, width: 20}
        rows:
          - ['Total updates', {formula: '=SUM(Summary!C2:C3)'}]
          - ['Report date', {value: '2026-10-01', type: date, number_format: 'yyyy-mm-dd'}]
  delegate_to: localhost
  run_once: true
"""

RETURN = r"""
path:
  description: Absolute destination path.
  returned: success
  type: str
  sample: /tmp/report.xlsx
checksum:
  description: SHA-256 of normalized workbook contents.
  returned: success
  type: str
  sample: 5916125098c39d39d0bdca8b121b93fd315c639755ae73e65e8a3d798981833d
sheets:
  description: Worksheet names in workbook order.
  returned: success
  type: list
  elements: str
  sample: [Summary, Totals]
sheet_count:
  description: Number of worksheets.
  returned: success
  type: int
  sample: 2
row_count:
  description: Total data rows across all sheets, excluding column headers.
  returned: success
  type: int
  sample: 4
"""

import os
import tempfile

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.ansible_tools.reporting.plugins.module_utils.xlsx_report import (
    HAS_OPENPYXL,
    ReportError,
    normalize_report,
    render_workbook,
    workbook_checksum,
)


def run_module():
    module = AnsibleModule(
        argument_spec={
            "path": {"type": "path", "required": True},
            "overwrite": {"type": "bool", "default": True},
            "properties": {"type": "dict", "default": {}},
            "styles": {"type": "dict", "default": {}},
            "sheets": {"type": "list", "elements": "dict", "required": True},
        },
        supports_check_mode=True,
    )
    if not HAS_OPENPYXL:
        module.fail_json(msg=missing_required_lib("openpyxl>=3.1,<4"))
    temporary_path = None
    try:
        if not module.params["path"] or not module.params["path"].strip():
            raise ReportError("path must be a non-empty destination filename")
        path = os.path.abspath(os.path.expanduser(module.params["path"]))
        if not os.path.isdir(os.path.dirname(path)):
            raise ReportError("the parent directory of path must already exist")
        if os.path.islink(path) or (os.path.exists(path) and not os.path.isfile(path)):
            raise ReportError("path must be a regular file and cannot be a symlink")
        spec = normalize_report(
            module.params["sheets"], module.params["styles"], module.params["properties"]
        )
        data = render_workbook(spec)
        checksum = workbook_checksum(data)
        exists = os.path.exists(path)
        previous_checksum = None
        if exists:
            with open(path, "rb") as existing:
                previous_checksum = workbook_checksum(existing.read())
        changed = previous_checksum != checksum
        if changed and exists and not module.params["overwrite"]:
            raise ReportError("path exists with different contents and overwrite is false")
        if changed and not module.check_mode:
            descriptor, temporary_path = tempfile.mkstemp(
                prefix=".xlsx-report-", dir=os.path.dirname(path)
            )
            module.add_cleanup_file(temporary_path)
            with os.fdopen(descriptor, "wb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            module.atomic_move(temporary_path, path)
        result = {
            "changed": changed,
            "path": path,
            "checksum": checksum,
            "sheets": [sheet.name for sheet in spec.sheets],
            "sheet_count": len(spec.sheets),
            "row_count": sum(len(sheet.rows) for sheet in spec.sheets),
        }
    except (ReportError, OSError, ValueError, TypeError, OverflowError) as exc:
        module.fail_json(msg=str(exc))
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
