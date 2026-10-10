---
title: Translations
parent: Developer Guide
nav_order: 4
description: "Update, translate and compile ScoreSight's Qt translation files, and add a new language."
---

# Translations
{: .no_toc }

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

ScoreSight's interface is translated with Qt's translation system. Every language has a source file `translations/scoresight_<locale>.ts` (XML, edited by translators) and a compiled file `translations/scoresight_<locale>.qm` (loaded by the app). Both are committed.

Available locales: `en_US`, `de_DE`, `es_ES`, `fr_FR`, `it_IT`, `ja_JP`, `ko_KR`, `nl_NL`, `pl_PL`, `pt_BR`, `pt_PT`, `ru_RU` and `zh_CN`.

At startup ScoreSight loads the `.qm` file that matches the system locale (falling back to `en_US`). Users can switch languages with **File > Language**.

## Workflow

### 1. Extract new strings

After you add or change user-visible text in `src/*.ui` or in Python code (wrapped in `QCoreApplication.translate(...)` / `self.tr(...)`), update all `.ts` files:

```bash
# from the repository root, with the dev environment active
for ts in translations/*.ts; do pyside6-lupdate src -ts "$ts"; done
```

On Windows you can run `scripts/update_translations.ps1`, which does the same for every `.ts` file. Make sure the scan covers only `src/`, not your virtual environment.

### 2. Translate

Open a `.ts` file in **Qt Linguist** (`pyside6-linguist translations/scoresight_de_DE.ts`), translate the unfinished entries and mark them as done.

Translators who prefer PO-file tools (Poedit, Weblate and similar) can convert with `ts2po` from the [Translate Toolkit](https://toolkit.translatehouse.org/) (`scripts/ts2po.ps1` converts every file), and convert back with `po2ts` afterwards.

### 3. Compile

```bash
for ts in translations/*.ts; do pyside6-lrelease "$ts" -qm "${ts%.ts}.qm"; done
```

On Windows: `scripts/compile_translations.ps1`.

### 4. Test and commit

Start ScoreSight, choose the language in **File > Language** and check the main window and dialogs for truncated or untranslated text. Commit both the `.ts` and the `.qm` files.

## Adding a language

1. Create the new `.ts` file with lupdate, for example `pyside6-lupdate src -ts translations/scoresight_sv_SE.ts`.
2. Translate it and compile the `.qm` file (steps 2–3 above).
3. Add a menu entry in `MainWindow.__init__` in `src/mainwindow.py`, next to the other `addLanguageOption(...)` lines:

   ```python
   self.addLanguageOption(languageMenu, "Swedish", "sv_SE")
   ```

4. Make sure the new `.qm` file is bundled by `scoresight.spec` (check its translations entries) so it ships in the packaged app.
5. Add the language to the lists in `README.md` and in this documentation (FAQ and Keyboard & Mouse pages).

## Tips

- Keep translations short. Many labels sit in narrow side panels.
- Don't translate placeholders, product names (OBS, vMix, NDI, UNO) or technical values such as `{% raw %}{{template}}{% endraw %}`, `mm:ss` or `.Text`.
- If you only want to improve one language, a pull request that changes just that `.ts`/`.qm` pair is welcome.
