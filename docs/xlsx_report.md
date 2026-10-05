# xlsx_report reference

Use `ansible_tools.reporting.xlsx_report` to generate an XLSX file on a POSIX host.
Keep application-specific data in your playbook; the module handles workbook
structure and presentation. For one combined report across an inventory,
delegate to localhost and use `run_once: true`.

## Module options

| Option | Type | Default | Meaning |
| --- | --- | --- | --- |
| `path` | path | required | Output file; its parent directory must exist. |
| `overwrite` | boolean | `true` | Permit replacing different existing contents. |
| `properties` | mapping | `{}` | String-valued workbook metadata. |
| `styles` | mapping | `{}` | Named style definitions. |
| `sheets` | list of mappings | required | At least one sheet, in output order. |

Metadata keys: `title`, `subject`, `creator`, `description`, `keywords`, `category`,
`language`, and `last_modified_by`. The default creator is `ansible_tools.reporting`.
Creation and modification timestamps are fixed to `2000-01-01T00:00:00Z` for
reproducible output. They are also ignored when comparing existing reports.

## Sheets and columns

Each sheet requires `name` and a non-empty `columns` list. Names must be valid Excel
sheet names, at most 31 characters, and unique without regard to case. Column
names are non-empty strings and must also be unique within the sheet.

| Sheet option | Meaning |
| --- | --- |
| `rows` | Data rows; defaults to an empty list. Row 1 always contains headers. |
| `header_style` | Named style for all headers, unless overridden per column. |
| `freeze_panes` | First unfrozen cell, such as `A2` or `B2`. `A1` freezes nothing. |
| `auto_filter` | `true` uses table filters when tables exist, otherwise the whole data range; `false` disables the worksheet filter. Also accepts an explicit A1 range. |
| `tables` | Structured tables; defaults to an empty list. |
| `conditional_formatting` | Formatting rules; defaults to an empty list. |

Each column supports `name`, `width` (0.1 through 255), `style` for its data cells,
`header_style`, and `number_format`. An explicit column number format overrides
the chosen named style's number format; a cell's number format overrides both.

Tables always include their own filters. An explicit `auto_filter` range matching
a table uses that table's filter without duplicating it on the worksheet. A range
that partly overlaps a table is rejected; a separate range is allowed. This avoids
Excel repairing the workbook and removing its table.

## Rows and cells

Positional rows must contain exactly one cell per column. Keyed rows use column
names; omitted columns become blank and unknown names are rejected.

```yaml
rows:
  - [server01, SUCCESS, 12]
  - {Server: server02, Status: FAILED, Updates: 3}
  - values: [server03, WARNING, 0]
    styles:
      Status: warning
```

A structured row has `values` and may define `style` for the row and `styles`
for individual columns. The selected cell style has this precedence:
cell object > row `styles` > row `style` > column `style`. Styles replace one
another rather than merging. If every key in a row mapping is a declared column
name, it is treated as a keyed row; otherwise it must be a structured row.

Scalar cells accept strings, finite numbers, booleans, and null. Use strings for
identifiers whose digits must remain exact; Excel numbers use floating point
precision. Native Python
date and datetime values are also accepted by the renderer. ISO strings stay text
unless you use a typed cell. Timezones are not supported in Excel datetime cells.

```yaml
rows:
  - - {value: server01, type: string, style: emphasis}
    - {value: '2026-10-01', type: date, number_format: yyyy-mm-dd}
    - {value: '2026-10-01T14:30:00', type: datetime, number_format: 'yyyy-mm-dd hh:mm'}
    - {value: 0.95, type: number, number_format: '0.0%'}
    - {value: true, type: boolean}
    - {formula: '=SUM(D2:D10)', number_format: '0.0%'}
```

Cell objects define exactly one of `value` or `formula`. `value` accepts an optional
`type` of `string`, `number`, `boolean`, `date`, or `datetime`; the first three
validate the value's type. `formula` requires a string beginning with `=` and
cannot be combined with `type`. Both forms accept `style` and `number_format`.

Plain strings beginning with `=` are written as literal text. Explicit formula
objects make it possible to include reports containing arbitrary input text.
No formula evaluation or cached results are produced.

## Styles

```yaml
styles:
  header:
    font: {name: Calibri, size: 11, bold: true, color: 'FFFFFF'}
    fill: {color: '1F4E78'}
    alignment: {horizontal: center, vertical: center, wrap_text: true}
    border:
      bottom: {style: thin, color: 'FFFFFF'}
  warning:
    background: 'FFEB9C'
    font: {color: '9C6500', bold: true}
  percent:
    number_format: '0.0%'
```

Colors accept RGB (`RRGGBB`) or ARGB (`AARRGGBB`), with an optional leading `#`.
Quote colors in YAML. `fill.color` and `background` are interchangeable solid-fill
forms and cannot be used together. The built-in `Normal` name is reserved.
Style names must be unique without regard to case.

Font keys: `name`, `size`, `bold`, `italic`, `color`, `underline`, `strike`.
Underline values: `none`, `single`, `double`, `singleAccounting`, `doubleAccounting`.
Alignment keys: `horizontal`, `vertical`, `wrap_text`, `shrink_to_fit`,
`text_rotation` (integer 0–180), and `indent` (integer 0–250). A string alignment
is shorthand for `horizontal`. Border sides `left`, `right`, `top`, and `bottom`
accept `style` and optional `color`; use Excel border names such as `thin`,
`medium`, `thick`, `dashed`, `dotted`, and `double`.

## Tables

```yaml
tables:
  - name: Inventory
    ref: A1:C4
    style: TableStyleMedium2
    show_row_stripes: true
```

`name` must be an Excel table name, unique across the workbook without regard to
case. Use letters, digits, underscores, or periods, starting with a letter or
underscore. Cell references and the reserved names `R` and `C` are rejected.

The default `ref` covers all headers and data. Explicit table ranges must start
in row 1, fit within the sheet's declared data, and not overlap another table.
Header-only tables are supported. Built-in styles are `TableStyleLight1` through
`21`, `TableStyleMedium1` through `28`, and `TableStyleDark1` through `11`.
`show_row_stripes` defaults to true; `show_column_stripes`, `show_first_column`,
and `show_last_column` default to false.

## Conditional formatting

```yaml
conditional_formatting:
  - column: Status
    equals: FAILED
    background: 'FFC7CE'
    font_color: '9C0006'
    stop_if_true: true
  - range: A2:C4
    formula: '$B2="WARNING"'
    style: warning
```

Each rule defines exactly one of `column` or `range`, and exactly one of `equals`
or `formula`. `column` targets only its data cells; on an empty sheet, these rules
are validated and omitted. An explicit range must fit within the sheet's data.
`equals` accepts a string, number, or boolean. An expression formula can include
or omit a leading `=` and is evaluated relative to the range's first cell.

Provide a named `style`, `background`, `font_color`, or a combination. The direct
color options override those parts of the named style. `stop_if_true` defaults
to false. Rule order follows the input list.

## File behavior and results

The module compares normalized ZIP entries, including values, formulas, styles,
sheet order, tables, and metadata. ZIP container timestamps and core creation and
modification timestamps do not trigger changes. Other manually edited content
is replaced when overwrite is enabled. This comparison does not attempt to
treat arbitrary Excel rewrites of equivalent XML as identical.

An identical report is left untouched. A different report fails with
`overwrite: false`, including in check mode. Invalid or corrupt existing XLSX
files are replaced only when overwrite is enabled. Destination directories and
symlinks are rejected. Existing file permissions and ownership are preserved
using Ansible's atomic move; new files use the executing process's umask.

Successful results include `changed`, absolute `path`, a normalized SHA-256
`checksum`, ordered `sheets`, `sheet_count`, and `row_count` excluding headers.
The renderer holds the workbook and XLSX bytes in memory; size your report data
to the available memory. Concurrent writers to the same path are not coordinated.
