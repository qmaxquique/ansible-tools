# td-paas Naming Conventions

This document defines naming conventions for repositories, roles, variables, tags, and files.

## 1) Repository naming
All repos MUST start with:
- `td-paas-`

Recommended pattern:
- `td-paas-<domain>-<component>[-<type>]`

Allowed:
- lowercase letters, digits, hyphens

Avoid:
- underscores in repo names
- ambiguous repo names without a `-role/-collection/-playbooks` suffix when unclear

## 2) Ansible role naming
Role ID (internal):
- `td-paas-<domain>-<component>`

Example:
- repo: `td-paas-linux-patch-role`
- role: `td-paas-linux-patch`

## 3) Collection naming
Namespace:
- `tdp`
Collection:
- `paas`

## 4) Variable naming
### General
- role defaults: `defaults/main.yml`
- role vars: `vars/main.yml` (use sparingly; defaults preferred)
- prefix all role vars with role ID:
  - `td-paas-linux-patch-*`

### Boolean
- use `true/false` (YAML booleans), not "yes/no" strings

### Lists and dicts
- plural for lists: `*_packages`, `*_users`
- dicts for structured config: `*_config`

## 5) Tags
Standard tags (recommended):
- `td-paas`
- `<domain>` (e.g. `linux`, `aap`, `sec`)
- `<component>` (e.g. `patch`, `repo_mount`)

Special tags:
- `never` MUST only be used for tasks that are dangerous by default
- `always` MUST be avoided unless strictly necessary

## 6) Files and task includes
- task include files: `tasks/<topic>.yml`
- handler includes: `handlers/<topic>.yml` (optional)

## 7) Inventory group naming
- lowercase, underscores allowed (`web_servers`, `db_primary`)
- avoid hyphens in group names (Ansible group vars mapping is cleaner)
