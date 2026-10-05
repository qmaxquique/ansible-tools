# ansible_tools.reporting

An Ansible collection for generating declarative XLSX reports with `openpyxl`.
The first module is `ansible_tools.reporting.xlsx_report`.

It supports multiple sheets, named styles and colors, column widths and number
formats, dates, explicit formulas, freeze panes, filters, structured Excel tables,
and equality or formula-based conditional formatting. The renderer is independent
of Ansible and covered by unit tests.

## Install and run

Use an Ansible controller with `ansible-core>=2.16`. The Python interpreter on the
host executing the module needs Python 3.9 or newer and `openpyxl>=3.1,<4`.
Install `requirements.txt` into that interpreter, including your Execution
Environment when delegating report generation to localhost.

```sh
python -m pip install -r requirements.txt
ansible-galaxy collection build --output-path /tmp
ansible-galaxy collection install /tmp/ansible_tools-reporting-0.1.0.tar.gz
ansible-playbook examples/report.yml
```

The example writes `/tmp/ansible-report.xlsx`; set `report_path` to choose another
destination. The parent directory must exist.

```sh
ansible-playbook examples/report.yml -e report_path=/tmp/my-report.xlsx --check
```

Identical definitions return `changed: false` and preserve the existing file and
its modification time. Check mode renders and compares in memory without writing
the report. Changed output is written atomically. `overwrite: false` protects an
existing file with different contents.

See [the module reference](docs/xlsx_report.md) for the schema and behavior, and
[the example playbook](examples/report.yml) for a complete report with two sheets.
Run `ansible-doc ansible_tools.reporting.xlsx_report` after installing the collection.

## Develop

Python 3.12 is a suitable controller environment for the development tools.

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

CI runs this suite and the Ansible integration playbook against the minimum
dependency versions (`ansible-core 2.16.0`, `openpyxl 3.1.0`) and the latest versions
allowed by the dependency ranges.

To exercise real Ansible module packaging and execution without publishing:

```sh
.venv/bin/ansible-galaxy collection build --output-path /tmp --force
.venv/bin/ansible-galaxy collection install /tmp/ansible_tools-reporting-0.1.0.tar.gz \
  --collections-path .test-collections --force
ANSIBLE_COLLECTIONS_PATH="$PWD/.test-collections" \
  .venv/bin/ansible-playbook tests/integration/report.yml
```

The integration playbook creates its own temporary directory and removes it when
finished. The collection uses the initial local namespace `ansible_tools.reporting`.

## Initial scope

The module generates an entire workbook from the provided definition. Charts,
images, merged cells, and editing existing templates are deferred. Excel evaluates
formulas and conditional formatting when opening the file; the module stores the
definitions and does not calculate formula results.

Architecture and dependency choices follow the
[shared module design](https://chatgpt.com/share/e/6abeb240-fa98-8009-b533-73323c7ba4fe),
the [Ansible collection structure](https://docs.ansible.com/projects/ansible/latest/dev_guide/developing_collections_structure.html),
and the official `openpyxl` documentation for
[styles](https://openpyxl.readthedocs.io/en/stable/styles.html),
[tables](https://openpyxl.readthedocs.io/en/stable/worksheet_tables.html), and
[conditional formatting](https://openpyxl.readthedocs.io/en/stable/formatting.html).
