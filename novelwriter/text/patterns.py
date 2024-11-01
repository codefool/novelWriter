"""
novelWriter – Text Pattern Functions
====================================

File History:
Created: 2024-06-01 [2.5ec1]

This file is a part of novelWriter
Copyright 2018–2024, Veronica Berglyd Olsen

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
from __future__ import annotations

import re

from novelwriter import CONFIG
from novelwriter.constants import nwRegEx


class RegExPatterns:

    # Static RegExes
    _rxUrl     = re.compile(nwRegEx.URL, re.ASCII)
    _rxWords   = re.compile(nwRegEx.WORDS, re.UNICODE)
    _rxBreak   = re.compile(nwRegEx.BREAK, re.UNICODE)
    _rxItalic  = re.compile(nwRegEx.FMT_EI, re.UNICODE)
    _rxBold    = re.compile(nwRegEx.FMT_EB, re.UNICODE)
    _rxStrike  = re.compile(nwRegEx.FMT_ST, re.UNICODE)
    _rxSCPlain = re.compile(nwRegEx.FMT_SC, re.UNICODE)
    _rxSCValue = re.compile(nwRegEx.FMT_SV, re.UNICODE)

    @property
    def url(self) -> re.Pattern:
        """Find URLs."""
        return self._rxUrl

    @property
    def wordSplit(self) -> re.Pattern:
        """Split text into words."""
        return self._rxWords

    @property
    def lineBreak(self) -> re.Pattern:
        """Find forced line break."""
        return self._rxBreak

    @property
    def markdownItalic(self) -> re.Pattern:
        """Markdown italic style."""
        return self._rxItalic

    @property
    def markdownBold(self) -> re.Pattern:
        """Markdown bold style."""
        return self._rxBold

    @property
    def markdownStrike(self) -> re.Pattern:
        """Markdown strikethrough style."""
        return self._rxStrike

    @property
    def shortcodePlain(self) -> re.Pattern:
        """Plain shortcode style."""
        return self._rxSCPlain

    @property
    def shortcodeValue(self) -> re.Pattern:
        """Plain shortcode style."""
        return self._rxSCValue

    @property
    def dialogStyle(self) -> re.Pattern | None:
        """Dialogue detection rule based on user settings."""
        if CONFIG.dialogStyle > 0:
            symO = ""
            symC = ""
            if CONFIG.dialogStyle in (1, 3):
                symO += CONFIG.fmtSQuoteOpen
                symC += CONFIG.fmtSQuoteClose
            if CONFIG.dialogStyle in (2, 3):
                symO += CONFIG.fmtDQuoteOpen
                symC += CONFIG.fmtDQuoteClose

            rxEnd = "|$" if CONFIG.allowOpenDial else ""
            return re.compile(f"\\B[{symO}].*?(?:[{symC}]\\B{rxEnd})", re.UNICODE)
        return None

    @property
    def altDialogStyle(self) -> re.Pattern | None:
        """Dialogue alternative rule based on user settings."""
        if CONFIG.altDialogOpen and CONFIG.altDialogClose:
            symO = re.escape(CONFIG.altDialogOpen)
            symC = re.escape(CONFIG.altDialogClose)
            return re.compile(f"\\B{symO}.*?{symC}\\B", re.UNICODE)
        return None


REGEX_PATTERNS = RegExPatterns()


class DialogParser:

    __slots__ = ("_quotes", "_dialog", "_narrator", "_break", "_enabled")

    def __init__(self) -> None:
        self._quotes = None
        self._dialog = ""
        self._narrator = ""
        self._break = re.compile("")
        self._enabled = False
        return

    @property
    def enabled(self) -> bool:
        """Return True if there are any settings to parse."""
        return self._enabled

    def initParser(self) -> None:
        """Init parser settings. Must be called when config changes."""
        punct = re.escape("!?.,:;")
        self._quotes = REGEX_PATTERNS.dialogStyle
        self._dialog = CONFIG.dialogLine
        self._narrator = CONFIG.narratorBreak.strip()[:1]
        self._break = re.compile(
            f"({self._narrator}\\s?.*?\\s?(?:{self._narrator}[{punct}]?|$))", re.UNICODE
        )
        self._enabled = bool(self._quotes or self._dialog or self._narrator)
        return

    def __call__(self, text: str) -> list[tuple[int, int]]:
        """Caller wrapper for dialogue processing."""
        temp: list[int] = []
        if text:
            plain = True
            if self._dialog and text[0] in self._dialog:
                plain = False
                temp.append(0)
                temp.append(len(text))
                if self._narrator:
                    for res in self._break.finditer(text, 1):
                        temp.append(res.start(0))
                        temp.append(res.end(0))
            elif self._quotes:
                for res in self._quotes.finditer(text):
                    plain = False
                    temp.append(res.start(0))
                    temp.append(res.end(0))
                    if self._narrator:
                        for sub in self._break.finditer(text, res.start(0), res.end(0)):
                            temp.append(sub.start(0))
                            temp.append(sub.end(0))

            if plain and self._narrator:
                pos = 0
                for num, bit in enumerate(text.split(self._narrator)):
                    length = len(bit) + int(num > 0)
                    if num%2:
                        temp.append(pos)
                        temp.append(pos + length)
                    pos += length

        start = None
        result = []
        for pos in sorted(set(temp)):
            if start is None:
                start = pos
            else:
                result.append((start, pos))
                start = None

        # print("-"*80)
        # print(f"'{text}'")
        # print(temp)
        # print(result)

        return result
