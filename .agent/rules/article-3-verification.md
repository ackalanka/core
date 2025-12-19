---
trigger: always_on
---

<metadata>
description: "Governs security, testing, error handling, and self-correction. The final filter."
globs: ["*/"]
alwaysApply: true
priority: high
</metadata>

# ARTICLE 3: THE PROTOCOL OF VERIFICATION & EVOLUTION

## 1.0 SECURITY BY DESIGN (NON-NEGOTIABLE)

- **Input Validation:** All external inputs (API params, user forms) must be validated and sanitized. Trust nothing.   
- **Secrets Management:** NEVER hardcode API keys, passwords, or tokens. Use environment variables (`process.env`, `os.environ`).
- **Injection Prevention:** Use parameterized queries for SQL. Use safe DOM methods for HTML.
- **Dependency Audit:** Do not recommend deprecated or insecure libraries.

## 2.0 THE TESTING COVENANT

- **Test Generation:** For every functional change, you must generate or update the corresponding unit test.   
- **Coverage:** Aim for edge-case coverage, not just "happy path" testing.   
- **Test Frameworks:** Use the project's existing framework (Jest, PyTest, etc.). Do not introduce new frameworks without permission.

## 3.0 ERROR HANDLING & ROBUSTNESS

- **No Silent Failures:** Try/Catch blocks must handle errors explicitly. Logging the error is the minimum requirement; swallowing errors is prohibited.   
- **User Feedback:** Error messages exposed to the UI must be user-friendly, while backend logs must be detailed for debugging.

## 4.0 THE SELF-CORRECTION LOOP

- **Reflexion:** If code generation fails (syntax error, test failure), you must:
    1. Read the error message.
    2. Analyze _why_ it failed in the `<thinking>` block.
    3. Propose a fix.
    4. Verify the fix against the constraint that failed.   
- **Double Check:** Before outputting the final response, review your code against `article-2-implementation.md`. Did you use `any`? Did you leave a magic number? Fix it before the user sees it.

## 5.0 EVOLUTION & DOCUMENTATION

- **Documentation Update:** If your code changes the behavior of the system, you must update the `README.md` or `docs/` folder.   
- **Rule Improvement:** If you encounter a recurring issue that these Articles did not prevent, suggest a new rule to the user to update the Constitution.