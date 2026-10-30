# Windows 0.25.19 reset recovery

Task: Keep reset and repair usable after a partial runtime removal.

The user reports that a second full reset fails with a Python path error. The exact Windows error was not retained. These changes fix tested failure classes; they do not establish the exact PC root cause.

- Check that the private Python interpreter can run. An executable file alone is not readiness evidence. Cache the bounded check against the executable, environment configuration and base-file signatures.
- Repair an existing but unusable Windows venv without clearing downloaded models or installed packages.
- Keep native full reset available before Python setup and after Python damage.
- Complete ordinary backend requests before reviewing cleanup. Stop new backend requests after deferred reset is confirmed. Own Windows RPC descendants so exit releases their handles.
- Hold one launcher storage lock across extraction, the app session and deferred cleanup. A new launcher waits for an active cleanup before it reads or extracts packages. An open app retains the existing single-instance rule.
- Save cleanup and interpreter errors locally. Include both in normal and emergency support export.

Mac binaries stay at 0.25.17. Conversion policies, source clocks, model choices and user media are unchanged. Native helper, isolated child, UI fixture and package tests do not replace actual Windows reset and deployment acceptance.
