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

At startup ScoreSight picks the language in this order:

1. the language chosen in **File > Language** (saved as the `language` setting),
2. the system's UI languages and locale: an exact match such as `de_DE`, or else another region of the same language (`de_AT` gets `de_DE`, `fr_CA` gets `fr_FR`, `pt_AO` gets `pt_PT`; the language's "home" region is preferred),
3. `en_US`.

## Workflow

### 1. Extract new strings

After you add or change user-visible text in `src/*.ui` or in Python code (wrapped in `QCoreApplication.translate(...)` / `self.tr(...)`), update all `.ts` files from the repository root, with the dev environment active:

```bash
python scripts/update_translations.py
```

It updates every `translations/*.ts` file from the sources in `src/` only, so your virtual environment and build folders aren't scanned. Without the script, the equivalent is:

```bash
for ts in translations/*.ts; do pyside6-lupdate src -ts "$ts"; done
```

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

{: .note }
Connection values in the `.ui` files (the vMix host, port and input, the UNO URL and Essentials overlay ID, the template text) are marked as not translatable, so switching the language never resets them. Keep it that way for any field whose default text is a value rather than a label.

## Adding a language

1. Create the new `.ts` file with lupdate, for example `pyside6-lupdate src -ts translations/scoresight_sv_SE.ts`.
2. Translate it and compile the `.qm` file (steps 2–3 above).
3. Add a menu entry in `MainWindow.__init__` in `src/mainwindow.py`, next to the other `addLanguageOption(...)` lines:

   ```python
   self.addLanguageOption(languageMenu, "Swedish", "sv_SE")
   ```

4. The packaged app bundles every `translations/*.qm` file through the `DATA_GLOBS` list in `scoresight.spec`, so nothing needs to change there. `tests/test_packaging.py` checks it.
5. Add the language to the lists in `README.md` and in this documentation (FAQ and Keyboard & Mouse pages).

## Tips

- Keep translations short. Many labels sit in narrow side panels.
- Don't translate placeholders, product names (OBS, vMix, NDI, UNO) or technical values such as `{% raw %}{{template}}{% endraw %}`, `mm:ss` or `.Text`.
- If you only want to improve one language, a pull request that changes just that `.ts`/`.qm` pair is welcome.
