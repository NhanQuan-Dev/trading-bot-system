# Debugging Rules & Protocol

This document outlines the **mandatory** process for debugging and fixing issues in this project.

## 1. Startup & Environment
- **Start Command**: Always use `@[run-all.sh]` to start both Backend and Frontend.
  ```bash
  ./run-all.sh
  ```
- **Prerequisites**: Ensure the user is in the `docker` group to verify containers without password prompts.

## 2. Tooling & MCP
Leverage the available MCP servers configured in `@[.vscode/mcp.json]`:
- **Postgres**: Use for direct database inspection and query verification.
- **Filesystem**: For file operations (default).
- **HTTP**: For making API requests (`curl` is also fine).
- **Playwright**: For end-to-end browser testing and UI verification.

## 3. Pre-Fix Protocol
**Before** attempting any fix:
1.  **Consult Experience**: Read `@[docs/debugging-experience.md]` to check for known patterns, similar existing bugs, or best practices.
2.  **Reproduction**: Create a reproduction script or clearly identified steps to reproduce the issue.
3.  **No Assumptions**: Do not skip over small errors, warnings, or "noise" in logs. They often indicate the root cause.
4.  **Analyze**: Understand the root cause fully before touching code.

## 4. Post-Fix Protocol
**After** implementing a fix:
1.  **Mandatory Agent Testing**: You (the agent) MUST verify the fix yourself.
    - Use `curl` for API endpoints.
    - Use Python scripts for logic verification.
    - Use the Browser tool for UI verification.
    - **NEVER** ask the user to test before you have verified it yourself.
2.  **Documentation**: Update `@[docs/debugging-experience.md]` with:
    - **Symptom**: What was observed?
    - **Root Cause**: What specifically failed (include code snippets)?
    - **Fix Pattern**: How it was resolved (include "BAD" vs "GOOD" examples).
    - **Related Files**: Where did this happen?

## 5. Mindset
- **Zero Assumptions**: Verify every hypothesis.
- **Precision**: Fix small issues; do not leave "technical debt" or ignore "minor" console errors.
- **User Experience**: The user should only see verified solutions.

## 6. Test Credentials
- **Account**: `trinhan@gmail.com`
- **Password**: `Qwe12345`
- **Purpose**: Use this account to obtain authentication tokens for testing API endpoints and protected routes.
