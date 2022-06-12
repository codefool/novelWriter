"""
novelWriter – GUI Novel Tree
============================
GUI classe for the main window novel tree

File History:
Created: 2020-12-20 [1.1a0]

This file is a part of novelWriter
Copyright 2018–2020, Veronica Berglyd Olsen

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

import logging
import novelwriter

from time import time

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import (
    QAbstractItemView, QFrame, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget
)

from novelwriter.common import checkInt
from novelwriter.constants import nwKeyWords

logger = logging.getLogger(__name__)


class GuiNovelView(QWidget):

    def __init__(self, mainGui):
        QWidget.__init__(self, mainGui)

        self.mainGui = mainGui

        # Build GUI
        self.novelTree = GuiNovelTree(self)
        self.novelBar = GuiNovelToolBar(self)

        # Assemble
        self.outerBox = QVBoxLayout()
        self.outerBox.addWidget(self.novelBar, 0)
        self.outerBox.addWidget(self.novelTree, 1)
        self.outerBox.setContentsMargins(0, 0, 0, 0)
        self.outerBox.setSpacing(0)

        self.setLayout(self.outerBox)

        # Function Mappings
        self.refreshTree = self.novelTree.refreshTree
        self.updateWordCounts = self.novelTree.updateWordCounts
        self.getSelectedHandle = self.novelTree.getSelectedHandle

        return

    ##
    #  Methods
    ##

    def initSettings(self):
        self.novelTree.initSettings()
        return

    def clearProject(self):
        self.novelTree.clearTree()
        return

    def setFocus(self):
        """Forward the set focus call to the tree widget.
        """
        self.novelTree.setFocus()
        return

    def treeFocus(self):
        """Check if the novel tree has focus.
        """
        return self.novelTree.hasFocus()

# END Class GuiNovelView


class GuiNovelToolBar(QWidget):

    def __init__(self, novelView):
        QTreeWidget.__init__(self, novelView)

        self.mainConf  = novelwriter.CONFIG
        self.novelView = novelView

        return

# END Class GuiNovelToolBar


class GuiNovelTree(QTreeWidget):

    C_TITLE = 0
    C_WORDS = 1
    C_POV   = 2

    def __init__(self, novelView):
        QTreeWidget.__init__(self, novelView)

        logger.debug("Initialising GuiNovelTree ...")

        self.mainConf   = novelwriter.CONFIG
        self.novelView  = novelView
        self.mainGui    = novelView.mainGui
        self.mainTheme  = novelView.mainGui.mainTheme
        self.theProject = novelView.mainGui.theProject

        # Internal Variables
        self._treeMap   = {}
        self._lastBuild = 0

        # Build GUI
        iPx = self.mainTheme.baseIconSize
        self.setFrameStyle(QFrame.NoFrame)
        self.setIconSize(QSize(iPx, iPx))
        self.setIndentation(iPx)
        self.setColumnCount(3)
        self.setHeaderLabels([
            self.tr("Novel Outline"),
            self.tr("Words"),
            self.tr("POV")
        ])
        self.itemDoubleClicked.connect(self._treeDoubleClick)
        self.itemSelectionChanged.connect(self._itemSelected)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setExpandsOnDoubleClick(False)
        self.setDragEnabled(False)

        treeHeadItem = self.headerItem()
        treeHeadItem.setTextAlignment(self.C_WORDS, Qt.AlignRight)
        treeHeadItem.setToolTip(self.C_TITLE, self.tr("Section title"))
        treeHeadItem.setToolTip(self.C_WORDS, self.tr("Word count"))
        treeHeadItem.setToolTip(self.C_POV,   self.tr("Point-of-view character"))

        treeHeader = self.header()
        treeHeader.setStretchLastSection(True)
        treeHeader.setMinimumSectionSize(iPx + 6)

        # Get user's column width preferences for NAME and COUNT
        treeColWidth = self.mainConf.getNovelColWidths()
        if len(treeColWidth) <= 3:
            for colN, colW in enumerate(treeColWidth):
                self.setColumnWidth(colN, colW)

        # The last column should just auto-scale
        self.resizeColumnToContents(self.C_POV)

        # Set custom settings
        self.initSettings()

        logger.debug("GuiNovelTree initialisation complete")

        return

    def initSettings(self):
        """Set or update tree widget settings.
        """
        # Scroll bars
        if self.mainConf.hideVScroll:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        if self.mainConf.hideHScroll:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        return

    ##
    #  Class Methods
    ##

    def clearTree(self):
        """Clear the GUI content and the related maps.
        """
        self.clear()
        self._treeMap = {}
        self._lastBuild = 0
        return

    def refreshTree(self, overRide=False):
        """Called whenever the Novel tab is activated.
        """
        logger.verbose("Requesting refresh of the novel tree")
        treeChanged = self.mainGui.projView.changedSince(self._lastBuild)
        indexChanged = self.theProject.index.indexChangedSince(self._lastBuild)
        if not (treeChanged or indexChanged or overRide):
            logger.verbose("No changes have been made to the novel index")
            return

        selItem = self.selectedItems()
        titleKey = None
        if selItem:
            titleKey = selItem[0].data(self.C_TITLE, Qt.UserRole)[2]

        self._populateTree()

        if titleKey is not None and titleKey in self._treeMap:
            self._treeMap[titleKey].setSelected(True)

        return

    def updateWordCounts(self, tHandle):
        """Update the word count for a given handle.
        """
        tHeaders = self.theProject.index.getHandleWordCounts(tHandle)
        for titleKey, wCount in tHeaders:
            if titleKey in self._treeMap:
                self._treeMap[titleKey].setText(self.C_WORDS, f"{wCount:n}")
        return

    def getSelectedHandle(self):
        """Get the currently selected handle. If multiple items are
        selected, return the first.
        """
        selItem = self.selectedItems()
        tHandle = None
        tLine = 0
        if selItem:
            tHandle = selItem[0].data(self.C_TITLE, Qt.UserRole)[0]
            tLine = checkInt(selItem[0].data(self.C_TITLE, Qt.UserRole)[1], 1) - 1

        return tHandle, tLine

    ##
    #  Events
    ##

    def mousePressEvent(self, theEvent):
        """Overload mousePressEvent to clear selection if clicking the
        mouse in a blank area of the tree view, and to load a document
        for viewing if the user middle-clicked.
        """
        QTreeWidget.mousePressEvent(self, theEvent)

        if theEvent.button() == Qt.LeftButton:
            selItem = self.indexAt(theEvent.pos())
            if not selItem.isValid():
                self.clearSelection()

        elif theEvent.button() == Qt.MiddleButton:
            selItem = self.itemAt(theEvent.pos())
            if not isinstance(selItem, QTreeWidgetItem):
                return

            tHandle, _ = self.getSelectedHandle()
            if tHandle is None:
                return

            self.mainGui.viewDocument(tHandle)

        return

    ##
    #  Slots
    ##

    def _treeDoubleClick(self, tItem, tCol):
        """Extract the handle and line number of the title double-
        clicked, and send it to the main gui class for opening in the
        document editor.
        """
        tHandle, tLine = self.getSelectedHandle()
        self.mainGui.openDocument(tHandle, tLine=tLine-1, doScroll=True)
        return

    def _itemSelected(self):
        """Extract the handle and line number of the currently selected
        title, and send it to the tree meta panel.
        """
        selItems = self.selectedItems()
        if selItems:
            tHandle = selItems[0].data(self.C_TITLE, Qt.UserRole)[0]
            self.mainGui.itemDetails.updateViewBox(tHandle)

        return

    ##
    #  Internal Functions
    ##

    def _populateTree(self):
        """Build the tree based on the project index.
        """
        self.clearTree()

        currTitle = None
        currChapter = None
        currScene = None

        for tKey, tHandle, sTitle, novIdx in self.theProject.index.novelStructure(skipExcl=True):

            tItem = self._createTreeItem(tHandle, sTitle, tKey, novIdx)
            self._treeMap[tKey] = tItem

            tLevel = novIdx.level
            if tLevel == "H1":
                self.addTopLevelItem(tItem)
                currTitle = tItem
                currChapter = None
                currScene = None

            elif tLevel == "H2":
                if currTitle is None:
                    self.addTopLevelItem(tItem)
                else:
                    currTitle.addChild(tItem)
                currChapter = tItem
                currScene = None

            elif tLevel == "H3":
                if currChapter is None:
                    if currTitle is None:
                        self.addTopLevelItem(tItem)
                    else:
                        currTitle.addChild(tItem)
                else:
                    currChapter.addChild(tItem)
                currScene = tItem

            elif tLevel == "H4":
                if currScene is None:
                    if currChapter is None:
                        if currTitle is None:
                            self.addTopLevelItem(tItem)
                        else:
                            currTitle.addChild(tItem)
                    else:
                        currChapter.addChild(tItem)
                else:
                    currScene.addChild(tItem)

            tItem.setExpanded(True)

        self._lastBuild = time()

        return

    def _createTreeItem(self, tHandle, sTitle, titleKey, novIdx):
        """Populate a tree item with all the column values.
        """
        newItem = QTreeWidgetItem()
        hIcon   = "doc_%s" % novIdx.level.lower()
        theData = (tHandle, sTitle[1:].lstrip("0"), titleKey)

        wC = int(novIdx.wordCount)

        newItem.setText(self.C_TITLE, novIdx.title)
        newItem.setData(self.C_TITLE, Qt.UserRole, theData)
        newItem.setIcon(self.C_TITLE, self.mainTheme.getIcon(hIcon))
        newItem.setText(self.C_WORDS, f"{wC:n}")
        newItem.setTextAlignment(self.C_WORDS, Qt.AlignRight)

        theRefs = self.theProject.index.getReferences(tHandle, sTitle)
        newItem.setText(self.C_POV, ", ".join(theRefs[nwKeyWords.POV_KEY]))

        return newItem

# END Class GuiNovelTree
