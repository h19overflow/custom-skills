---
name: windows-secure-env-handoff
description: Safely copy a dotenv secret into Windows User environment variables for new OMP or CLI processes without exposing the value.
---

## Procedure

1. Create a temporary PowerShell script outside versioned source. Read the dotenv line with `Get-Content`; parse the value and strip matching quotes.
2. Validate the value is non-empty.
3. Persist it with:
   ```powershell
   [Environment]::SetEnvironmentVariable('NAME', $value, 'User')
   ```
4. Print only a confirmation; never print the value.
5. Delete the temporary script after execution.
6. Verify with `[Environment]::GetEnvironmentVariable('NAME', 'User')`, reporting only presence and length.
7. Start a fresh child process and explicitly load the User value into its process environment before launching the target CLI.
8. Verify the target application through a harmless shadow-mode operation or log entry. Existing processes must be restarted to inherit the new variable.

Do not use `setx NAME <secret>` or pass the secret as a command-line argument: both can leak through process history, logs, or shell output.
