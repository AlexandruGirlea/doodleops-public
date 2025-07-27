# Contributing to DoodleOps

Thank you for helping improve **DoodleOps**!  Because this project is released
under the Business Source License 1.1 (BSL) *and* also offered under a
commercial licence, we need to ensure that all incoming contributions can be
re-licensed in the future.  By submitting any pull request, patch, or
documentation update, **you agree to the Contributor License Agreement (CLA)
below**.

---

## 📄 Contributor License Agreement (CLA)

By contributing to this repository you **irrevocably confirm** that:

1. **Copyright assignment** – You assign joint copyright in your
   contribution to *Alexandru Girlea* (the “Maintainer”).  This allows the
   Maintainer to re-license, sub-license, and commercially distribute your
   work without further permission or payment.  You retain the right to use
   your contribution for any purpose.

2. **Patent grant** – You grant a perpetual, worldwide, royalty-free patent
   licence for any patent claims you control that would be infringed by the
   contribution or its combination with DoodleOps.

3. **Original work** – Your contribution is original (or you have permission
   to submit it) and does not include third-party code that is incompatible
   with the project’s licensing roadmap (BSL 1.1 → future Apache-2.0).

4. **Moral rights waiver** – To the fullest extent permitted by law, you waive
   any moral or similar rights so the Maintainer may adapt, publish, or
   sublicense your contribution.

5. **One-time action** – Agreeing to this CLA once covers all future
   contributions you make.

By submitting code, you confirm that you have the authority to agree to
these terms on behalf of yourself and any entity you represent.  If you are
contributing on behalf of an organization, you confirm that you have the
authority to bind that organization to this CLA.

If you **cannot** agree to these terms, do **not** submit code.  Instead,
open an issue describing your idea.

---

## 🛠 Development workflow

1. **Fork** → **feature branch**.  
2. Run `make precommit` (lint + tests).  
3. **Open a PR** against `main`.  
4. A maintainer reviews; feedback within *five working days*.

---

## 🔧 Code style & CI

| Language / stack | Formatter & linter | Tests |
|------------------|--------------------|-------|
| Python           | Black · Ruff       | Pytest |
| Terraform        | terraform fmt · tflint | `checkov` |
| Docs / Markdown  | Markdownlint       | – |

All checks must pass in GitHub Actions before merge.

---

## 🚀 Thank you!

Your time and expertise keep DoodleOps moving forward.  Accepted contributors
are listed in **AUTHORS.md** and get early access to the next release.