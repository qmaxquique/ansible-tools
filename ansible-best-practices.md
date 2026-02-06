# Ansible Best Practices

Purpose: produce **repeatable, idempotent, secure, lintable** Ansible that is easy to review and operate. Optimize for **clarity**: short tasks, strict naming, minimal noise.

---

## 1) Non-negotiable rules

* **Idempotency**: every task MUST be safe to run repeatedly without unintended changes.
* **Declarative modules first**: prefer built-in modules over `shell`/`command`.
* **No hidden side effects**: tasks MUST not modify unrelated state.
* **Fail fast**: validate inputs early; use `assert` for required vars and invariants.
* **Least privilege**: default to unprivileged; elevate with `become: true` only where needed.
* **Deterministic**: pin versions (collections/roles), avoid time-dependent logic.
* **Structured output**: use `changed_when` and `failed_when` only when necessary and correct.
* **FQMN / FQCN usage**: always use fully qualified module names (e.g., `ansible.builtin.package`).

---

## 2) Project layout

Prefer a standard role-first structure:

```
ansible/
  ansible.cfg
  playbooks/
    site.yml
  roles/
    <role_name>/
      defaults/main.yml
      vars/main.yml
      tasks/main.yml
      templates/
      files/
      meta/main.yml
  collections/requirements.yml
  roles/requirements.yml
```

* `playbooks/` should be **thin** (orchestration only).
* `roles/` contain implementation and MUST be reusable.

---

## 3) Inventory and vars discipline

### 3.1 Where vars go

* Use `defaults/` for safe defaults (lowest precedence).
* Use `vars/` only for role-internal constants (higher precedence).
* Use `group_vars/` and `host_vars/` for environment-specific data.
* Avoid `set_fact` unless you must derive a value at runtime.

### 3.2 Naming

* Role vars MUST be prefixed: `<role>_...` (e.g., `nginx_worker_processes`).
* Avoid ambiguous names (`path`, `user`, `name`).

### 3.3 Secrets

* Never commit secrets. Use Ansible Vault or an external secrets manager.
* For vault: store only the secret values, keep structure minimal.

---

## 4) Task writing standards

### 4.1 Task naming

* Every task MUST have a meaningful `name:` describing the desired state.
* Prefer “Ensure …” / “Configure …” / “Install …” patterns.

### 4.2 Module choice order

1. Specific module (e.g., `ansible.builtin.package`, `user`, `service`, `template`)
2. `ansible.builtin.command` (only when module not available)
3. `ansible.builtin.shell` (last resort; requires justification)

If using `shell`/`command`:

* MUST set `creates:` or `removes:` when possible.
* MUST set `changed_when:` and `failed_when:` correctly.
* MUST avoid piping when possible; if needed, use `shell` with `set -euo pipefail` (and `executable: /bin/bash`).

### 4.3 Idempotency patterns

* Use modules that implement desired state (`state: present/absent`, `lineinfile`, `blockinfile`, `ini_file`, etc.).
* Avoid “run command then parse output” unless no alternative.

### 4.4 Conditions and safety

* Prefer `when:` over complex Jinja in parameters.
* Use `assert` for required inputs:

```yaml
- name: Validate required vars
  ansible.builtin.assert:
    that:
      - myrole_target_dir is defined
      - myrole_target_dir | length > 0
    fail_msg: "myrole_target_dir must be set"
```

### 4.5 Loops

* Prefer `loop:` over legacy `with_items`.
* Use `loop_control.label` for readable output.

### 4.6 Files and templates

* Templates MUST be stable and minimize diffs (sorted keys, consistent whitespace).
* Prefer `template` over `copy` if any interpolation is needed.
* Always set ownership and permissions explicitly when security-relevant.

### 4.7 Facts

* Disable fact gathering unless needed: `gather_facts: false`.
* If needed, keep fact usage local; do not rely on obscure fact fields without checks.

---

## 5) Error handling and “changed” semantics

* Avoid blanket `ignore_errors: true`. If you must, pair with:

  * explicit `failed_when: false` and
  * follow-up validation and messaging.
* `changed_when:` is allowed only to correct module limitations or interpret commands.
* Prefer `check_mode:` compatibility; modules should support it by default.

---

## 6) Handlers policy

Default: **avoid handlers unless they provide clear operational value**.

Preferred patterns to reduce handler usage:

* Use idempotent modules that restart only when necessary (some modules do this).
* Use explicit conditional restarts tied to registered changes:

```yaml
- name: Render config
  ansible.builtin.template:
    src: app.conf.j2
    dest: /etc/app/app.conf
  register: app_conf

- name: Restart service if config changed
  ansible.builtin.service:
    name: app
    state: restarted
  when: app_conf.changed
```

If using handlers:

* MUST name them clearly and notify only from tasks that truly require it.

---

## 7) Performance and scaling

* Use `strategy: free` only when safe; default strategy is fine.
* Batch changes with `serial:` for risky operations.
* Use `async` + `poll` only when long-running tasks are unavoidable.
* Minimize remote calls:

  * combine related tasks
  * avoid repeated `stat`/`command` checks when module provides `state`.

---

## 8) OS portability

* Prefer `ansible_facts['os_family']` / `ansible_facts['distribution']` gating.
* Use `package` for common installs; use distro-specific modules only when needed.
* Keep paths and service names abstracted via vars.

---

## 9) Linting, formatting, and CI

* YAML: 2 spaces indent, no tabs.
* Keep lines reasonably short; break long Jinja expressions.
* Recommended checks:

  * `ansible-lint`
  * `yamllint`
  * `ansible-playbook --check --diff` in CI for core playbooks
* Pin collections/roles:
  * `collections/requirements.yml`
  * `roles/requirements.yml`

---

## 10) Playbook standards

* Plays should declare:

  * `hosts:`
  * `become:` (explicit true/false)
  * `gather_facts:` (explicit)
  * `vars_files:` only when necessary
* Prefer `pre_tasks` for validation and environment prep.
* Keep role ordering explicit and stable.

Example minimal play:

```yaml
- name: Site
  hosts: all
  become: false
  gather_facts: false
  roles:
    - role: myrole
```

---

## 11) Testing expectations

* Role MUST be runnable on a clean host with only documented prerequisites.
* Include a small “smoke” playbook or Molecule scenario when feasible.
* Validate outcomes (file exists, service running, port open) using idempotent checks:

  * `stat`, `service_facts`, `uri`, `wait_for`.

---

## 12) General authoring guidelines

When writing or modifying Ansible content:

1. **Start with invariants**: define required vars, supported OSes, and privilege needs.
2. **Choose the narrowest module** that expresses desired state.
3. **Write small tasks**; each task changes one thing.
4. **Register changes** only when needed for follow-up logic.
5. **Avoid noisy debug**; use `debug` only for actionable troubleshooting.
6. **Document intent** in role README or comments only when non-obvious.

---

### Definition of "done" for Ansible content:

* `ansible-lint` clean (or explicitly justified exceptions),
* idempotent (2nd run shows zero changes),
* no plaintext secrets,
* minimal use of `shell/command`,
* variables and role naming consistent.
