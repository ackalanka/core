---
trigger: always_on
---

<metadata>
description: "Governs syntax, naming, architecture, and code style. Applied during code generation."
globs: ["*/.{ts,js,py,go,rs,java,c,cpp,h,hpp,cs}"]
alwaysApply: true
priority: high
</metadata>

# ARTICLE 2: THE CODEX OF IMPLEMENTATION & CRAFT

## 1.0 THE LAW OF CLEAN CODE

All code generated must adhere to strict software craftsmanship principles.

### 1.1 Core Principles

- **DRY (Don't Repeat Yourself):** Never duplicate logic. Extract shared logic into utility functions or base classes.   
- **KISS (Keep It Simple, Stupid):** Prefer simple, readable solutions over complex, clever abstractions unless performance mandates otherwise.   
- **SOLID:** Adhere to Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion.   

### 1.2 The "No-Lazy" Mandate

- **Verbatim Output:** When refactoring, you MUST output the **entire** modified function or file.
- **Prohibited Placeholders:** NEVER use comments like `//... rest of code remains same` or `//... existing logic`. You must rewrite the full context to ensure integration continuity. The user pays for tokens; you deliver code.

## 2.0 NAMING & SYNTAX CONVENTIONS

- **Variables:** `camelCase` (JS/TS/Go), `snake_case` (Python/Ruby). Names must be descriptive (`isUserAuthenticated` vs `auth`).
- **Constants:** `UPPER_SNAKE_CASE` for global constants. Magic numbers are strictly prohibited; extract them to named constants.   
- **Functions:** Verb-noun pairs (`getUser`, `calculateTotal`).
- **Types:** explicit typing is mandatory in typed languages. usage of `any` (TS) or `interface{}` (Go) is prohibited unless absolutely necessary and documented.

## 3.0 MODULARITY & STRUCTURE

- **File Limits:** Files should not exceed 300 lines. If a file grows larger, propose a refactor to split it.   
- **Function Limits:** Functions should be atomized. If a function exceeds 30 lines, breaks it into sub-routines.
- **Imports:** Group imports: Standard Lib -> 3rd Party Libs -> Internal Modules. Remove unused imports immediately.

## 4.0 DOCUMENTATION STANDARDS

- **Self-Documenting Code:** Code structure should explain itself. Use comments _only_ to explain "Why", not "What".   
- **JSDoc/Docstrings:** Public APIs must have documentation strings defining parameters, return types, and exceptions.
- **Commit Messages:** If asked to generate git commits, follow the Conventional Commits specification (e.g., `feat: add user login`).