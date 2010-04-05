#!/usr/bin/env python
# -*- coding: utf-8 -*-

## @package LFM_GUI
# LFM GUI
#
# @author Turbo Data Laboratories, Inc.
# @date 2010/02/20

import sys
import codecs
import os
import decimal
import ConfigParser
import re

import threading
import Queue
import time

# wxPython
import wx
import wx.grid
import wx.grid as gridlib
import wx.xrc as xrc
import wx.aui as aui
import wx.wizard as wiz

# LFM
from LFM_Grid import *
from LFM_Macro import *
from LFM_TextWizard import *


# ##################################################################################################
#
#         PyFIT スタンドアローンバージョン
#
# ##################################################################################################

# バージョン情報
ABOUT_NAME      = "PyFIT"
ABOUT_VERSION   = "1.5.5"
ABOUT_COPYRIGHT = "(C)2009-2010 Turbo Data Laboratories, Inc.  "

# メインフレームアイコン
ICON_MAIN_FRAME = "icons/lifit/exefile_MainIcon_LIFIT.gif"

# 文字コード ---------------------------------------------------------------------------------------
ENC_DEFAULT = "UTF8"         # デフォルト文字コード
ENC_OS      = "MS932"        # OS文字コード
ENC_DB      = "MS932"        # DB文字コード
#ENC_DB     = "UTF8"

# 標準入出力文字コード設定 -------------------------------------------------------------------------
sys.stdin  = codecs.getreader(ENC_OS)(sys.stdin)
sys.stdout = codecs.getwriter(ENC_OS)(sys.stdout)
sys.stderr = codecs.getwriter(ENC_OS)(sys.stderr)

# デバッグ用 ---------------------------------------------------------------------------------------
DEBUG_MSG = True    # デバッグメッセージ出力
#DEBUG_MSG = False  # デバッグメッセージ出力

# XRCファイル --------------------------------------------------------------------------------------
XRC_FILE = "LFM_GUI.xrc"

# LFM設定ファイル ----------------------------------------------------------------------------------
CONFIG_FILE = "LFM_GUI.ini"

# タイトルフォーマット -----------------------------------------------------------------------------
FORMAT_TITLE_TABLE = "%s [ID:%d,Row:%d]"    # テーブル
FORMAT_TITLE_SET   = "Set:%d [Row:%d]%s"    # セット 
FORMAT_TITLE_PAGE  = "%s [Set:%d]"          # タブページ

# リストヘッダ -------------------------------------------------------------------------------------
TITLE_ID           = "ID"
TITLE_TYPE         = "Type"
TITLE_FILTER_NAME  = "Filter Name"
TITLE_FUNCTION     = "Function"

# 項目なし（Unionダイアログ用）---------------------------------------------------------------------
FILTER_TYPE_NONE_ID       = 0
FILTER_TYPE_NONE_TYPE     = -1
FILTER_TYPE_NONE_TYPE_STR = "(None)"
FILTER_TYPE_NONE_NAME     = ""

# クリップボード -----------------------------------------------------------------------------------
CB_SEP_CHAR = '\t'  # 区切り文字

# グリッド -----------------------------------------------------------------------------------------
OFFSET_COL_RN  = 1  # RecNo列分オフセット
OFFSET_COL_RN2 = 2  # RecNo+RecNo2列分オフセット

# Global -------------------------------------------------------------------------------------------
g_CurPath = "."     # カレントパス
g_WSInfo  = None    # ワークスペース
g_WSTree  = None    # ワークスペースツリー
g_WSFrame = None    # ワークスペースフレーム
g_App     = ""

#---------------------------------------------------------------------------------------------------
## 計算用関数
LIST_CALC_FUNC_STR = (r'$&(,)', r'$UPPER()', r'$Extract(,,)', r'$IF(,,)', r'$NumericToStr()', r'$FloatToStr()', r'$IntToStr()' \
                    , r'EQ(,)', r'NEQ(,)', r'LT(,)', r'GT(,)', r'LEQ(,)', r'GEQ(,)', r'LEN()', r'POS(,)' \
                    , r'StrToNumeric()', r'StrToFloat()', r'StrToInt()')
LIST_CALC_FUNC_NUM = (r'+(,)', r'-(,)', r'*(,)', r'/(,)', r'=(,)', r'<>(,)', r'<(,)', r'>(,)', r'<=(,)', r'>=(,)' \
                    , r'AND(,)', r'OR(,)', r'NOT()', r'IF(,,)', r'CEIL()', r'ROUND()', r'FLOOR()')
LIST_CALC_FUNC_CMP = (r'EQ(,)', r'NEQ(,)', r'LT(,)', r'GT(,)', r'LEQ(,)', r'GEQ(,)' \
                    , r'=(,)', r'<>(,)', r'<(,)', r'>(,)', r'<=(,)', r'>=(,)')
LIST_CALC_FUNC_SP  = (r'ISNULL()', r'NVL(,)', r'RecNo', r'RowNo', r'$""')
LIST_CALC_FUNC_ALL = LIST_CALC_FUNC_STR + LIST_CALC_FUNC_NUM + LIST_CALC_FUNC_SP

# 最大次元数
MAX_DIM = 32

#---------------------------------------------------------------------------------------------------
## ワークスペースツリー管理クラス
class WSTree():
    def __init__(self, Frame, WSInfo):
        self.frame    = Frame
        self.treeCtrl = Frame.wstree
        self.dataTab  = Frame.datatab
        self.WSInfo   = WSInfo

        self.itemRoot = self.treeCtrl.AddRoot("Workspace")
        self.itemReal = self.treeCtrl.AppendItem(self.itemRoot, "REAL Table")
        self.itemJoin = self.treeCtrl.AppendItem(self.itemRoot, "JOIN Table")

        self.mapItem    = {}    # (テーブルID,セットID)とツリーアイテムのマップ
        self.mapGrid    = {}    # (テーブルID,セットID)とグリッドのマップ
        self.listGrid   = []    # グリッドリスト

        self.currentTab = -1
        self.init()
        
        return

    ## 初期化共通 ----------------------------------------------------------------------------------
    def init(self):
        self.mapItem.clear()
        self.mapGrid.clear()
        del self.listGrid[:]

        self.curTID = -1    # カレントテーブルID
        self.curSID = -1    # カレントセットID
        self.srchId   = -1  # 検索ID 

        self.treeCtrl.Expand(self.itemRoot)
        return

    ## ワークスペースクリア ------------------------------------------------------------------------
    def clear(self):
        self.treeCtrl.DeleteChildren(self.itemReal)
        self.treeCtrl.DeleteChildren(self.itemJoin)

        # データタブ内グリッド全削除
        for i in range(len(self.listGrid)):
            self.dataTab.DeletePage(0)

        self.init()
        return

    ## テーブル追加 --------------------------------------------------------------------------------
    def appendTable(self, tid):
        # REALとJOIN振り分け
        if self.WSInfo.isJoinTable(tid):
            itemParent = self.itemJoin
        else:
            itemParent = self.itemReal

        tableName = self.WSInfo.getTableName(tid)
        tableRow  = self.WSInfo.getCountRow(tid)
        itemTable = self.treeCtrl.AppendItem(itemParent, FORMAT_TITLE_TABLE % (tableName, tid, tableRow))
        self.mapItem[(tid, 0)] = itemTable
        self.treeCtrl.Expand(itemParent)
        return

    ## テーブルサイズ更新 --------------------------------------------------------------------------
    def updateTableSize(self, tid):
        # テーブル情報
        itemTable = self.mapItem[(tid, 0)]
        tableName = self.WSInfo.getTableName(tid)
        tableRow  = self.WSInfo.getCountRow(tid)
        self.treeCtrl.SetItemText(itemTable, FORMAT_TITLE_TABLE % (tableName, tid, tableRow))
        return

    ## グリッド追加 --------------------------------------------------------------------------------
    def appendGrid(self, tid, sid, grid):
        self.mapGrid[(tid, sid)] = grid
        self.listGrid.append(grid)
        return
        
    def replaceGrid(self, tid, sid, grid):
        ogrid = self.mapGrid[(tid, sid)]
        self.listGrid[self.listGrid.index(ogrid)]=grid
        self.mapGrid[(tid, sid)] = grid 
        
    def getGrid(self, tid, sid):
        grid = self.mapGrid[(tid, sid)] 
        return  grid

    def isGridOpen(self):
        if len(g_WSTree.mapGrid) > 0:
            return True
        else:
            return False

    ## グリッドから(テーブルID,セットID)を取得 -----------------------------------------------------
    def getTidSidFromGrid(self, grid):
        retval = None
        for (tid, sid), v in self.mapGrid.iteritems():
            if v == grid: # found
                retval = (tid, sid)
                break
        return retval

    ## 指定テーブル内にオープン済みセットが存在すればその(セットID,グリッド,インデックス)を返す（１つのみ）
    def getOpenGridInTable(self, TID):
        retval = (-1, None, -1)
        for (tid, sid), page in self.mapGrid.iteritems():
            if tid == TID:
                retval = (sid, page, self.listGrid.index(page))
                break
        return retval

    ## セット追加 ----------------------------------------------------------------------------------
    def appendSet(self, tid, sid):
        itemTable = self.mapItem[(tid, 0)]
        setSize = g_WSInfo.getSetSize(tid, sid)
        scom = g_WSInfo.getComment(tid, sid) # セットコメント
        if len(scom) == 0:
            scom = ""
        else:
            scom = " [%s]" % scom
        itemSet = self.treeCtrl.AppendItem(itemTable, FORMAT_TITLE_SET % (sid, setSize, scom))
        self.mapItem[(tid, sid)] = itemSet
        self.treeCtrl.Expand(itemTable)
        return

    ## セットサイズ更新 ----------------------------------------------------------------------------
    def updateSetSize(self, tid, sid):
        # テーブル情報
        self.updateTableSize(tid)

        # セット情報
        itemSet = self.mapItem[(tid, sid)]
        self.updateSetSizeSub(tid, sid, itemSet)
        return

    ## 全セットサイズ更新 --------------------------------------------------------------------------
    # 同一テーブル内の全セット更新
    def updateSetSizeAll(self, tid):
        # テーブル情報
        self.updateTableSize(tid)

        # セット情報
        for (tableId, sid), itemSet in self.mapItem.iteritems():
            if (tableId != tid) or (sid == 0):
                continue
            self.updateSetSizeSub(tid, sid, itemSet)
        return

    def updateSetSizeSub(self, tid, sid, itemSet):
        ret = g_WSInfo.updateSetSize(tid, sid)
        self.frame.outputLog(ret)
        if ret.retCode < 0: # エラー
            return
        setSize = ret.retCode
        scom = g_WSInfo.getComment(tid, sid) # セットコメント
        if len(scom) == 0:
            scom = ""
        else:
            scom = " [%s]" % scom
        self.treeCtrl.SetItemText(itemSet, FORMAT_TITLE_SET % (sid, setSize, scom))
        return

    ## セット選択 ----------------------------------------------------------------------------------
    def selectSet(self, tid, sid):
        itemSet = self.mapItem[(tid, sid)]
        self.treeCtrl.SelectItem(itemSet)
        itemTable = self.mapItem[(tid, 0)]
        self.treeCtrl.Expand(itemTable)
        return

    ## セットグリッド選択 --------------------------------------------------------------------------
    def selectSetGrid(self, tid, sid):
        page = self.mapGrid[(tid, sid)]
        idxPage = self.listGrid.index(page)
        self.dataTab.SetSelection(idxPage)
        return

    ## セットクローズ ------------------------------------------------------------------------------
    def closeSet(self):
        idxPage = self.dataTab.GetSelection() # 現在のタブインデックス
        if idxPage < 0:
            return

        # データタブから削除
        page = self.listGrid[idxPage]
        for (tid, sid), v in self.mapGrid.iteritems():
            if v == page:
                self.WSInfo.closeSet(tid, sid)
                del self.mapGrid[(tid, sid)]
                break
        del self.listGrid[idxPage]
        self.dataTab.DeletePage(idxPage)

        return

    # グリッドマップのキー変更 ---------------------------------------------------------------------
    def changeKeyMapGrid(self, oldKey, newKey):
        grid = self.mapGrid[oldKey]
        del self.mapGrid[oldKey]
        self.mapGrid[newKey] = grid
        return

    ## テーブル削除 --------------------------------------------------------------------------------
    def deleteTable(self, tid):
        # テーブル内セット削除
        for sid in self.WSInfo.getSetList(tid):
            self.deleteSet(tid, sid)

        self.treeCtrl.Delete(self.mapItem[(tid, 0)])
        del self.mapItem[(tid, 0)]
        return

    ## セット削除 ----------------------------------------------------------------------------------
    def deleteSet(self, tid, sid):
        # グリッドタブページタイトル
        #(openSid, openGrid, idxPage) = g_WSTree.getOpenGridInTable(tid)
        #g_WSTree.curTID=tid
        #g_WSTree.curSID=1
        #g_WSFrame.openSet()
        
        if (tid, sid) in self.mapGrid:
            # 対応グリッド削除
            page = self.mapGrid[(tid, sid)]
            idxPage = self.listGrid.index(page)
            del self.mapGrid[(tid, sid)]
            del self.listGrid[idxPage]
            self.dataTab.DeletePage(idxPage)
        
        self.treeCtrl.Delete(self.mapItem[(tid, sid)])
        del self.mapItem[(tid, sid)]
        
        return

    ## テーブル名変更 ------------------------------------------------------------------------------
    def renameTable(self, tid, name):
        # WSツリーアイテム
        itemTable = self.mapItem[(tid, 0)]
        tableRow  = self.WSInfo.getCountRow(tid)
        self.treeCtrl.SetItemText(itemTable, FORMAT_TITLE_TABLE % (name, tid, tableRow))
    
        # グリッドタブページタイトル
        (openSid, openGrid, idxPage) = self.getOpenGridInTable(tid)
        if openGrid != None: # テーブル内で開いているセットあり
            self.dataTab.SetPageText(idxPage, FORMAT_TITLE_PAGE % (name, openSid))
        return


#---------------------------------------------------------------------------------------------------
class MyApp(wx.App):
    def OnInit(self):
        self.res = xrc.XmlResource(XRC_FILE)
        self.frame = MyFrame(self)
        global g_WSFrame
        g_WSFrame  = self.frame
        self.frame.Show()
        return True


#---------------------------------------------------------------------------------------------------
class MyFrame(wx.Frame):
    def __init__(self, app):
        
        self.app = app
        self.listThread = []        # 子スレッドリスト
        global g_WSFrame
        g_WSFrame = self 
        pre = wx.PreFrame()
        app.res.LoadOnFrame(pre, None, "MainFrame")
        self.PostCreate(pre)
        self._mgr = aui.AuiManager(self)

        self.exitflag  = False      # 終了確認フラグ
        self.inProcess = False      # リサイズ中フラグ
        self.selectAll = False      # すべて選択フラグ

        # アイコン設定
        self.SetIcon(wx.Icon(ICON_MAIN_FRAME, wx.BITMAP_TYPE_GIF))

        self.menubar = self.GetMenuBar()
        self.statusbar = self.GetStatusBar()
        self.toolbar = self.GetToolBar()

        # 配置
        self.logtab = xrc.XRCCTRL(self, "LogTab")
        self._mgr.AddPane(self.logtab, aui.AuiPaneInfo().Name("LogTab").Caption(u"ログ").
                            Bottom().Layer(0).Position(0).
                            CloseButton(False).MaximizeButton(True).MinimizeButton(True))
        self.logmacro = xrc.XRCCTRL(self, "MacroLog")
        self.logapi = xrc.XRCCTRL(self, "APILog")

        self.wstree = xrc.XRCCTRL(self, "WSTree")
        self._mgr.AddPane(self.wstree, aui.AuiPaneInfo().Name("WSTree").Caption(u"ワークスペース").
                            Left().Layer(0).Position(0).
                            CloseButton(False).MaximizeButton(True).MinimizeButton(True))

        self.datatab = xrc.XRCCTRL(self, "DataTab")
        self._mgr.AddPane(self.datatab, aui.AuiPaneInfo().Name("DataTab").Caption(u"データ").
                            Center().
                            CloseButton(False).MaximizeButton(True).MinimizeButton(True))

        perspective_default = self._mgr.SavePerspective()

        # イベントBind
        self.bindEvents()

        # ログ出力スレッド
        self.queueLogM = Queue.Queue()
        self.threadLogM = OutputLogThread(self.logmacro, self.queueLogM)
        self.threadLogM.start()
        self.listThread.append(self.threadLogM)

        self.queueLogA = Queue.Queue()
        self.threadLogA = OutputLogThread(self.logapi, self.queueLogA)
        self.threadLogA.start()
        self.listThread.append(self.threadLogA)

        # エンジン初期化
        self.initEngine()

        self._mgr.Update()
        license = getLicense()
	ret = lfmtblpy.RD5SetPassword(license)

        return

    ## イベントBind --------------------------------------------------------------------------------
    def bindEvents(self):
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        # MenuFile
        self.Bind(wx.EVT_MENU, self.OnExit, id=xrc.XRCID("MenuItemExit"))

        self.Bind(wx.EVT_MENU, self.OnMenuItemOpen, id=xrc.XRCID("MenuItemOpen"))
        self.Bind(wx.EVT_TOOL, self.OnMenuItemOpen, id=xrc.XRCID("openFile"))

        self.Bind(wx.EVT_MENU, self.OnMenuItemSaveWS, id=xrc.XRCID("MenuItemSaveWS"))
        self.Bind(wx.EVT_TOOL, self.OnMenuItemSaveWS, id=xrc.XRCID("save"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemSaveTable, id=xrc.XRCID("MenuItemSaveTable"))

        self.Bind(wx.EVT_MENU, self.OnMenuItemImportCatalog, id=xrc.XRCID("MenuItemImportCatalog"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemImportWizard, id=xrc.XRCID("MenuItemImportWizard"))

        self.Bind(wx.EVT_MENU, self.OnMenuItemExport, id=xrc.XRCID("MenuItemExport"))

        self.Bind(wx.EVT_MENU, self.OnMenuItemDBCode, id=xrc.XRCID("MenuItemDBCodeUTF8"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemDBCode, id=xrc.XRCID("MenuItemDBCodeMS932"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemDBCode, id=xrc.XRCID("MenuItemDBCodeEUC_JP"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemDBCode, id=xrc.XRCID("MenuItemDBCodeShift_JIS"))

        # MenuEdit
        self.Bind(wx.EVT_MENU, self.OnMenuItemCopy, id=xrc.XRCID("MenuItemCopy"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemCopy, id=xrc.XRCID("MenuItemCopyWithName"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemPaste, id=xrc.XRCID("MenuItemPaste"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemPaste, id=xrc.XRCID("MenuItemClearData"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemDeleteTable, id=xrc.XRCID("MenuItemDeleteTable"))
        #self.Bind(wx.EVT_MENU, self.OnMenuItemSelectAll, id=xrc.XRCID("MenuItemSelectAll"))

        self.Bind(wx.EVT_MENU, self.OnMenuItemFind, id=xrc.XRCID("MenuItemFind"))
        self.Bind(wx.EVT_TOOL, self.OnMenuItemFind, id=xrc.XRCID("jump"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemPrevNext, id=xrc.XRCID("MenuItemPrev"))
        self.Bind(wx.EVT_TOOL, self.OnMenuItemPrevNext, id=xrc.XRCID("jumpPrevious"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemPrevNext, id=xrc.XRCID("MenuItemNext"))
        self.Bind(wx.EVT_TOOL, self.OnMenuItemPrevNext, id=xrc.XRCID("jumpNext"))

        self.Bind(wx.EVT_MENU, self.OnMenuItemChangeName, id=xrc.XRCID("MenuItemChangeName"))

        # MenuView
        self.Bind(wx.EVT_MENU, self.OnMenuItemShowWS, id=xrc.XRCID("MenuItemShowWS"))

        # MenuWS
        self.Bind(wx.EVT_MENU, self.OnMenuItemNewWS, id=xrc.XRCID("MenuItemNewWS"))

        # MenuTable
        self.Bind(wx.EVT_MENU, self.OnMenuItemNewTable, id=xrc.XRCID("MenuItemNewTable"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemOpenTable, id=xrc.XRCID("MenuItemOpenTable"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemCloseTable, id=xrc.XRCID("MenuItemCloseTable"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemCopyAsRealTable, id=xrc.XRCID("MenuItemCopyAsRealTable"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemJoinTable, id=xrc.XRCID("MenuItemJoinTable"))
        self.Bind(wx.EVT_TOOL, self.OnMenuItemJoinTable, id=xrc.XRCID("join"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemUnionTable, id=xrc.XRCID("MenuItemUnionTable"))
        self.Bind(wx.EVT_TOOL, self.OnMenuItemUnionTable, id=xrc.XRCID("union"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemSummaryTable, id=xrc.XRCID("MenuItemSummaryTable"))
        self.Bind(wx.EVT_TOOL, self.OnMenuItemSummaryTable, id=xrc.XRCID("aggregate"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemTransferFilter, id=xrc.XRCID("MenuItemTransferFilter"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemExtractInOut, id=xrc.XRCID("MenuItemExtractInOut"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemPropertyTable, id=xrc.XRCID("MenuItemPropertyTable"))

        # MenuData
        self.Bind(wx.EVT_MENU, self.OnMenuItemPaste, id=xrc.XRCID("MenuItemEditData"))
        self.Bind(wx.EVT_MENU, self.OnMenuSort, id=xrc.XRCID("MenuItemSortAscend"))
        self.Bind(wx.EVT_MENU, self.OnMenuSort, id=xrc.XRCID("MenuItemSortDescend"))
        self.Bind(wx.EVT_MENU, self.OnMenuSort, id=xrc.XRCID("MenuItemSortSpecify"))
        self.Bind(wx.EVT_TOOL, self.OnMenuSort, id=xrc.XRCID("sort"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemSearch, id=xrc.XRCID("MenuItemSearch"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemCalc, id=xrc.XRCID("MenuItemCalc"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemExUnique, id=xrc.XRCID("MenuItemExUnique"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemSetOp, id=xrc.XRCID("MenuItemSetOp"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemInsertRow, id=xrc.XRCID("MenuItemInsertRow"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemInsertRow, id=xrc.XRCID("MenuItemAppendRow"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemDeleteRow, id=xrc.XRCID("MenuItemDeleteRow"))
        #self.Bind(wx.EVT_MENU, self.OnMenuItemColumnWidth, id=xrc.XRCID("MenuItemColumnWidth"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemMoveColumn, id=xrc.XRCID("MenuItemMoveColumn"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemCopyColumn, id=xrc.XRCID("MenuItemCopyColumn"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemConvTypeColumn, id=xrc.XRCID("MenuItemConvTypeColumn"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemInsertColumn, id=xrc.XRCID("MenuItemInsertColumn"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemInsertColumn, id=xrc.XRCID("MenuItemAppendColumn"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemDeleteColumn, id=xrc.XRCID("MenuItemDeleteColumn"))

        # MenuTool
        self.Bind(wx.EVT_MENU, self.OnMenuItemCondense, id=xrc.XRCID("MenuItemCondense"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemCondenseAll, id=xrc.XRCID("MenuItemCondenseAll"))
	
        # MenuHelp
        self.Bind(wx.EVT_MENU, self.OnMenuItemAbout, id=xrc.XRCID("MenuItemAbout"))
        self.Bind(wx.EVT_MENU, self.OnMenuItemLicenseUpdate, id=xrc.XRCID("MenuItemLicenseUpdate"))

        # WSTree
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnWSSelChanged, self.wstree)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnWSItemActivated, self.wstree)
        self.wstree.Bind(wx.EVT_CONTEXT_MENU, self.OnWSTreePopup)
        self.wstree.Bind(wx.EVT_MENU, self.OnWSTreePopupSelect)

        # Datatab
        self.datatab.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnDataTabPageChanged)
        self.datatab.Bind(wx.EVT_CONTEXT_MENU, self.OnDataTabPopup)
        self.datatab.Bind(wx.EVT_MENU, self.OnDataTabPopupSelect)
        
        self.datatab.Bind(wx.EVT_SIZE, self.OnDataTabResize)
        
        #self.grid.Bind(wx.EVT_CONTEXT_MENU, self.OnDataTabPopup)
        #self.datatab.Bind(wx.EVT_MENU, self.OnDataTabPopupSelect)

        # Log
        self.logmacro.Bind(wx.EVT_CONTEXT_MENU, self.OnLogPopup)
        self.logmacro.Bind(wx.EVT_MENU, self.OnLogPopupSelect)
        self.logapi.Bind(wx.EVT_CONTEXT_MENU, self.OnLogPopup)
        self.logapi.Bind(wx.EVT_MENU, self.OnLogPopupSelect)

        return

    ## 終了イベント --------------------------------------------------------------------------------
    def OnExit(self, event):
        # 終了確認
        if len(g_WSInfo.listTable) > 0:
            Dlg = wx.MessageDialog(self, u"終了します。\n更新後、保存していないテーブルは破棄されます。\nよろしいですか ?", \
                  u"終了確認", wx.YES_NO | wx.ICON_QUESTION)
            AnsBtn = Dlg.ShowModal()
            if AnsBtn != wx.ID_YES:   # キャンセル
                return
        self.exitflag = True
        self.Close(True)
        return

    ## クローズイベント ----------------------------------------------------------------------------
    def OnClose(self, event):
        # 終了確認
        if self.exitflag == False and len(g_WSInfo.listTable) > 0:
            Dlg = wx.MessageDialog(self, u"終了します。\n更新後、保存していないテーブルは破棄されます。\nよろしいですか ?", \
              u"終了確認", wx.YES_NO | wx.ICON_QUESTION)
            AnsBtn = Dlg.ShowModal()
            Dlg.Destroy()
            if AnsBtn != wx.ID_YES:   # キャンセル
                self.exitflag = False
                return
        # 子スレッド終了
        for th in self.listThread:
            th.stop()
        for th in self.listThread:
            th.join()
        self._mgr.UnInit()
        del self._mgr
        self.Destroy()
        return

    ## ログ出力 ------------------------------------------------------------------------------------
    def outputLog(self, retObj):
        # API
        if (retObj.retMsgsA != None) and (len(retObj.retMsgsA) > 0):
            self.queueLogA.put(retObj.retMsgsA)

        # Macro
        if (retObj.retMsgsM != None) and (len(retObj.retMsgsM) > 0):
            self.statusbar.SetStatusText(retObj.retMsgsM[-1], 0)
            self.queueLogM.put(retObj.retMsgsM)

        return

    ## LFMエンジン初期化 ---------------------------------------------------------------------------
    def initEngine(self):
        # マクロの戻り値をオブジェクトで取得モードへ
        MSetRetObj(True) 

        ret = MClearWS()
        self.outputLog(ret)

        ret = MDBCodeSet(ENC_DB)
        self.outputLog(ret)

        # DBコード メニュー選択初期値Check
        self.menubar.Check(xrc.XRCID("MenuItemDBCode" + ENC_DB), True)

        # ワークスペース情報
        global g_WSInfo
        g_WSInfo = WSInfo()

        # ワークスペースView
        global g_WSTree
        g_WSTree = WSTree(self, g_WSInfo)

        # 使用メモリ
        self.updateUsedMemory()

        # DBコード
        self.updateDBCode()

        return

    ## ステータスバーのワークスペース使用メモリ量表示更新 ------------------------------------------
    def updateUsedMemory(self):
        ret = g_WSInfo.getTotalMemorySize()
        self.outputLog(ret)
        if ret.retCode < 0:
            return
        self.statusbar.SetStatusText(u"ワークスペース 使用メモリ: %s bytes" % str(ret.retData), 1)
        return

    ## ステータスバーのＤＢ文字コード表示更新 ------------------------------------------------------
    def updateDBCode(self):
        self.statusbar.SetStatusText(ENC_DB, 2)
        return

    ## テーブル関連ポップアップ有効／無効化 --------------------------------------------------------
    def enableWSPMenuTable(self, menu, bFlag):
        menu.Enable(xrc.XRCID("PMenuItemWsTreeOpenTable"), bFlag)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeRenameTable"), bFlag)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeDeleteTable"), bFlag)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeDuplTable"), bFlag)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeJoinTable"), bFlag)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeUnionTable"), bFlag)
        menu.Enable(xrc.XRCID("PMenuItemSummaryTable"), bFlag)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeExtractInOut"), bFlag)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeProperty"), bFlag)
        return

    ## テーブル関連ポップアップ有効／無効化（REAL/JOIN区別）----------------------------------------
    def enableWSPMenuTableRJ(self, menu, bJoin, bIN):
        bReal = not bJoin
        menu.Enable(xrc.XRCID("PMenuItemWsTreeOpenTable"), True)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeRenameTable"), True)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeDeleteTable"), True)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeDuplTable"), bReal)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeJoinTable"), bReal)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeUnionTable"), bReal)
        menu.Enable(xrc.XRCID("PMenuItemSummaryTable"), True)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeExtractInOut"), bIN)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeProperty"), True)
        return

    ## セット関連ポップアップ有効／無効化 ----------------------------------------------------------
    def enableWSPMenuSet(self, menu, bFlag):
        menu.Enable(xrc.XRCID("PMenuItemWsTreeExUnique"), bFlag)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeSetOp"), bFlag)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeCopyAsRealTable"), bFlag)
        return

    ## セット関連ポップアップ有効／無効化（REAL/JOIN区別）------------------------------------------
    def enableWSPMenuSetRJ(self, menu, bJoin):
        bReal = not bJoin
        menu.Enable(xrc.XRCID("PMenuItemWsTreeExUnique"), bReal)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeSetOp"), bReal)
        menu.Enable(xrc.XRCID("PMenuItemWsTreeCopyAsRealTable"), bJoin)
        return

    ## ツリーポップアップ --------------------------------------------------------------------------
    def OnWSTreePopup(self, event):
        menu = self.app.res.LoadMenu("PMenuWsTree")
        if g_WSTree.curTID < 1:
            self.enableWSPMenuTable(menu, False)
        else:
            bJoin = g_WSInfo.isJoinTable(g_WSTree.curTID)
            if bJoin:
                bIN = not g_WSInfo.isOuterJoinTable(g_WSTree.curTID)
            else:
                bIN = False
            self.enableWSPMenuTableRJ(menu, bJoin, bIN)

        if g_WSTree.curSID < 1:
            self.enableWSPMenuSet(menu, False)
        else:
            self.enableWSPMenuSetRJ(menu, g_WSInfo.isJoinTable(g_WSTree.curTID))

        self.wstree.PopupMenu(menu)
        return

    ## ツリーポップアップ選択 ----------------------------------------------------------------------
    def OnWSTreePopupSelect(self, event):
        eventId = event.GetId()
        if   eventId == xrc.XRCID("PMenuItemWsTreeNewTable"):
            self.OnMenuItemNewTable(event)
        elif eventId == xrc.XRCID("PMenuItemWsTreeOpenTable"):
            self.OnMenuItemOpenTable(event)
        elif eventId == xrc.XRCID("PMenuItemWsTreeRenameTable"):
            self.OnMenuItemChangeName(event)
        elif eventId == xrc.XRCID("PMenuItemWsTreeDeleteTable"):
            self.OnMenuItemDeleteTable(event)
        elif eventId == xrc.XRCID("PMenuItemWsTreeDuplTable"):
            self.OnMenuItemDuplTable(event)
        elif eventId == xrc.XRCID("PMenuItemWsTreeJoinTable"):
            self.OnMenuItemJoinTable(event)
        elif eventId == xrc.XRCID("PMenuItemWsTreeUnionTable"):
            self.OnMenuItemUnionTable(event)
        elif eventId == xrc.XRCID("PMenuItemSummaryTable"):
            self.OnMenuItemSummaryTable(event)
        elif eventId == xrc.XRCID("PMenuItemWsTreeExtractInOut"):
            self.OnMenuItemExtractInOut(event)
        elif eventId == xrc.XRCID("PMenuItemWsTreeProperty"):
            self.OnMenuItemPropertyTable(event)

        elif eventId == xrc.XRCID("PMenuItemWsTreeSetOp"):
            self.OnMenuItemSetOp(event)
        elif eventId == xrc.XRCID("PMenuItemWsTreeExUnique"):
            self.OnMenuItemExUnique(event)
        elif eventId == xrc.XRCID("PMenuItemWsTreeCopyAsRealTable"):
            self.OnMenuItemCopyAsRealTable(event)
        return

    ## データタブポップアップ ----------------------------------------------------------------------
    def OnDataTabPopup(self, event):
        menu = self.app.res.LoadMenu("PMenuDataTab")
        self.datatab.PopupMenu(menu)
        return

    ## データタブポップアップ選択 ------------------------------------------------------------------
    def OnDataTabPopupSelect(self, event):
        eventId = event.GetId()
        if eventId == xrc.XRCID("PMenuItemDataTabClose"):
            self.OnMenuItemCloseTable(event)
        if eventId == xrc.XRCID("PMenuItemDataTabResize"):
            self.OnDataTabResize(event)
        return

    ## ログポップアップ ----------------------------------------------------------------------------
    def OnLogPopup(self, event):
        menu = self.app.res.LoadMenu("PMenuLog")
        menu.ctrl = event.GetEventObject()
        menu.ctrl.SetFocus()
        menu.Enable(xrc.XRCID("PMenuItemLogCopy"), menu.ctrl.CanCopy())
        menu.ctrl.PopupMenu(menu)
        return

    ## ログポップアップ選択 ------------------------------------------------------------------------
    def OnLogPopupSelect(self, event):
        menu = event.GetEventObject()
        eventId = event.GetId()
        if   eventId == xrc.XRCID("PMenuItemLogCopy"):
            menu.ctrl.Copy()
        elif eventId == xrc.XRCID("PMenuItemLogClear"):
            menu.ctrl.Clear()
        elif eventId == xrc.XRCID("PMenuItemLogAll"):
            menu.ctrl.SetSelection(-1, -1)
        return

    ## WSツリーアイテム：シングルクリック ----------------------------------------------------------
    def OnWSSelChanged(self, event):
        itemSel = self.wstree.GetSelection()
        for (tid, sid), item in g_WSTree.mapItem.iteritems():
            if item == itemSel: # found
                g_WSTree.curTID = tid
                g_WSTree.curSID = sid
                return
        g_WSTree.curTID = -1
        g_WSTree.curSID = -1
        return

    ## WSツリーアイテム：ダブルクリック ------------------------------------------------------------
    def OnWSItemActivated(self, event):
        self.OnMenuItemOpenTable(event)
        return

    ## データタブ：ページ変更 ----------------------------------------------------------------------
    def OnDataTabPageChanged(self, event):
        event.Skip()
        idxPage = event.GetSelection()
        try:
            page = g_WSTree.listGrid[idxPage]
            bFound = True
        except:
            bFound = False
        if bFound:
            ret = g_WSTree.getTidSidFromGrid(page)
            if ret:
                (tid, sid) = ret
                g_WSTree.selectSet(tid, sid) # WSツリーセット選択
                #if g_WSTree.currentTab != idxPage:
                #    g_WSTree.currentTab = idxPage
                self.datatab.AddPendingEvent(wx.SizeEvent())
        return

    ## データタブ：リサイズ ------------------------------------------------------------------------
    def OnDataTabResize(self, event):
        event.Skip() 
        if self.inProcess == True:
            return
        self.inProcess = True
        try:
            if g_WSTree.isGridOpen() == True:
                #self.ResetView()
                (openSid, openGrid, idxPage) = g_WSTree.getOpenGridInTable( g_WSTree.curTID )
                openGrid.ResetGridView()
            self.inProcess = False
            return
        except:
            self.inProcess = False
            return

    ## データグリッド作成 --------------------------------------------------------------------------
    def createGrid(self, tid, sid, openGrid, idxPage):
        if openGrid == None: # 再利用グリッドなし
            # 新規グリッド作成して追加
            grid = VirtualGrid(self.datatab, tid, sid, g_WSInfo, g_WSFrame, g_App)
            self.datatab.AddPage(grid, FORMAT_TITLE_PAGE % (g_WSInfo.getTableName(tid), sid), select=True)
            g_WSTree.appendGrid(tid, sid, grid)
        else: # グリッドの情報を書き換え再利用
            openGrid.tid = tid
            openGrid.sid = sid
            self.datatab.SetPageText(idxPage, FORMAT_TITLE_PAGE % (g_WSInfo.getTableName(tid), sid))
            g_WSInfo.setCountRow(tid, openGrid.rows)
            openGrid.ResetGridView()
        return

    ## データグリッド再表示-------------------------------------------------------------------------
    def ResetView(self):
        saveCurTid = g_WSTree.curTID
        saveCurSid = g_WSTree.curSID
        g_WSTree.closeSet()
        g_WSTree.curTID = saveCurTid
        g_WSTree.curSID = saveCurSid
        self.openSet()
        return

    ## DBコード設定 ---------------------------------------------------------------------------------
    def setDBCode(self, DBcode):
        global ENC_DB
        ret = MDBCodeSet(DBcode)
        self.outputLog(ret)
        if ret.retCode >= 0: # 正常
            ENC_DB = DBcode
        self.menubar.Check(xrc.XRCID("MenuItemDBCode" + ENC_DB), True)
        self.updateDBCode()
        return ret.retCode

    ## DBコード選択 --------------------------------------------------------------------------------
    def OnMenuItemDBCode(self, event):
        if len(g_WSInfo.listTable) > 0:
            Dlg = wx.MessageDialog(self, u"ワークスペースが作成済みです。DBコードは変更できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        DBcode = str(self.menubar.GetLabel(event.GetId()))
        self.setDBCode(DBcode)
        return

    ## ワークスペース表示 --------------------------------------------------------------------------
    def OnMenuItemShowWS(self, event):
        #TODO 消えないので削除？
        print self._mgr.GetPane("WSTree").Hide()
        return

    ## 開く ----------------------------------------------------------------------------------------
    def OnMenuItemOpen(self, event):
        global g_CurPath
        Dlg = wx.FileDialog(self, message=u"ファイル選択", defaultDir=g_CurPath, defaultFile="",
                            wildcard = "D5D File (*.D5D)|*.d5d|D5T File (*.D5T)|*.d5t|All (*.*)|*.*")
        AnsBtn = Dlg.ShowModal()
        AnsFilename = Dlg.GetFilename()
        AnsFilePath = Dlg.GetPath()
        AnsDirPath = Dlg.GetDirectory()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        g_CurPath = AnsDirPath

        # ファイル拡張子別処理
        ext = os.path.splitext(AnsFilename)[1].upper() # 拡張子
        if ext == FILE_EXT_WS:    # ワークスペース
            if len(g_WSInfo.listTable) > 0:
                Dlg = wx.MessageDialog(self, u"ワークスペースは既に作成済みです。\n現在のワークスペースはクリアされます。\nよろしいですか ?", \
                      u"WSロード確認",  wx.YES_NO | wx.ICON_QUESTION)
                AnsBtn = Dlg.ShowModal()
                Dlg.Destroy()
                if AnsBtn != wx.ID_YES:   # キャンセル
                    return
        
            g_WSTree.clear() # ワークスペースツリークリア

            # WSファイル(D5D)情報取得
            ret = g_WSInfo.getInfoWSFile(AnsDirPath, AnsFilename)
            self.outputLog(ret)
            if ret.retCode < 0: # エラー
                return
            DBcode = ret.retData.DBCharCode.split('\0')[0]
            if DBcode == lfmtblpy.D5_DBCODE_UNKNOWN: # DBコード情報なし
                DBcode = ENC_OS
            if DBcode != ENC_DB: # 現在のDBコード設定と異なる
                ret = MClearWS()
                self.outputLog(ret)
                if ret.retCode < 0: # エラー
                    return

                ret = self.setDBCode(DBcode) # DBコード設定
                #if ret < 0: # エラー
                #    return

            ret = MDBLoad(AnsDirPath, AnsFilename)
            self.outputLog(ret)
            if ret.retCode < 0: # エラー
                if ret.retCode == lfmtblpy.D5_ROW_SIZE_OVERFLOW:
                    Dlg = wx.MessageDialog(self, u"テーブル行数がライセンスの上限を超えました。", u"エラー", wx.OK | wx.ICON_ERROR)
                    Dlg.ShowModal()
                    return
                elif ret.retCode == lfmtblpy.D5_ERROR_MEMORY_LIMIT_OVERFLOW:
                    Dlg = wx.MessageDialog(self, u"メモリ使用量がライセンスの上限を超えました。", u"エラー", wx.OK | wx.ICON_ERROR)
                    Dlg.ShowModal()
                    return
                else:
                    Dlg = wx.MessageDialog(self, u"処理中にエラーが発生しました。\nログにエラーコードが出力されています。", u"エラー", wx.OK | wx.ICON_ERROR)
                    Dlg.ShowModal()
                    return

            # ワークスペース情報取得
            ret = g_WSInfo.update()
            self.outputLog(ret)

            # ワークスペースツリー更新
            for tid in g_WSInfo.getTableList():
                g_WSTree.appendTable(tid)
            self.wstree.SelectItem(g_WSTree.itemRoot)

        elif ext == FILE_EXT_TABLE: # テーブル
            if g_WSInfo.getCountTable() == 0: # WSにテーブルなし
                # テーブルファイル(D5T)情報取得
                ret = g_WSInfo.getInfoTableFile(AnsDirPath, AnsFilename)
                self.outputLog(ret)
                if ret.retCode < 0: # エラー
                    return
                DBcode = ret.retData.DBCharCode.split('\0')[0]
                if DBcode == lfmtblpy.D5_DBCODE_UNKNOWN: # DBコード情報なし
                    DBcode = ENC_OS
                if DBcode != ENC_DB: # 現在のDBコード設定と異なる
                    ret = self.setDBCode(DBcode) # DBコード設定
                    #if ret < 0: # エラー
                    #    return

            ret = MLoad(AnsDirPath, AnsFilename)
            self.outputLog(ret)
            if ret.retCode < 0: # エラー
                if ret.retCode == lfmtblpy.D5_ROW_SIZE_OVERFLOW:
                    Dlg = wx.MessageDialog(self, u"テーブル行数がライセンスの上限を超えました。", u"エラー", wx.OK | wx.ICON_ERROR)
                    Dlg.ShowModal()
                    return
                elif ret.retCode == lfmtblpy.D5_ERROR_MEMORY_LIMIT_OVERFLOW:
                    Dlg = wx.MessageDialog(self, u"メモリ使用量がライセンスの上限を超えました。", u"エラー", wx.OK | wx.ICON_ERROR)
                    Dlg.ShowModal()
                    return
                else:
                    Dlg = wx.MessageDialog(self, u"処理中にエラーが発生しました。\nログにエラーコードが出力されています。", u"エラー", wx.OK | wx.ICON_ERROR)
                    Dlg.ShowModal()
                    return

            tid = ret.retCode

            # ワークスペースに追加
            g_WSInfo.appendTable(tid)
            g_WSTree.appendTable(tid)

        # 使用メモリ
        self.updateUsedMemory()

        return

    ## ワークスペース保存 --------------------------------------------------------------------------
    def OnMenuItemSaveWS(self, event):
        global g_CurPath
        Dlg = wx.FileDialog(self, message=u"ワークスペース保存ファイル選択", defaultDir=g_CurPath, defaultFile="",
                            wildcard = "D5D File (*.D5D)|*.D5D")
        AnsBtn = Dlg.ShowModal()
        AnsFilename = Dlg.GetFilename()
        AnsFilePath = Dlg.GetPath()
        AnsDirPath = Dlg.GetDirectory()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        g_CurPath = AnsDirPath

        if os.path.exists(AnsFilePath): # 
            Dlg = wx.MessageDialog(self, u"同名のファイルが存在します。上書きしますか？", caption=u"ワークスペース保存") # 
            AnsBtn = Dlg.ShowModal()
            Dlg.Destroy()
            if AnsBtn != wx.ID_OK: # cancel
                return

        name = os.path.splitext(AnsFilename)[0] # 拡張子除去

        ret = MDBSave(AnsDirPath, name)
        self.outputLog(ret)
        return

    ## テーブル保存 --------------------------------------------------------------------------------
    def OnMenuItemSaveTable(self, event):
        tid = g_WSTree.curTID
        # 操作対象テーブルチェック
        if tid <= 0:
            Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        if g_WSInfo.isJoinTable(tid):
            Dlg = wx.MessageDialog(self, u"Joinテーブルは保存できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        tableName = g_WSInfo.getTableName(tid)

        global g_CurPath
        Dlg = wx.FileDialog(self, message=u"テーブル保存ファイル選択", defaultDir=g_CurPath, defaultFile=(tableName + FILE_EXT_TABLE),
                            wildcard = "All (*.*)|*.*")
        AnsBtn = Dlg.ShowModal()
        AnsFilename = Dlg.GetFilename()
        AnsFilePath = Dlg.GetPath()
        AnsDirPath = Dlg.GetDirectory()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        g_CurPath = AnsDirPath

        if os.path.exists(AnsFilePath): # 
            Dlg = wx.MessageDialog(self, u"同名のファイルが存在します。上書きしますか？", caption=u"テーブル保存") # 
            AnsBtn = Dlg.ShowModal()
            Dlg.Destroy()
            if AnsBtn != wx.ID_OK: # cancel
                return

        name = os.path.splitext(AnsFilename)[0] # 拡張子除去
        if tableName != name: # テーブル名が異なる
            ret = MRename(tableName, name) # テーブル名変更
            self.outputLog(ret)
            if ret.retCode < 0: # エラー
                return
            name = ret.retData # 実際に付けられた新しいテーブル名
            g_WSInfo.renameTable(tableName, name)
            g_WSTree.renameTable(tid, name)

        ret = MSave(AnsDirPath, name)
        self.outputLog(ret)
        return

    ## インポート（カタログ）-----------------------------------------------------------------------
    def OnMenuItemImportCatalog(self, event):
        global g_CurPath
        Dlg = wx.FileDialog(self, message=u"インポートカタログファイル選択", defaultDir=g_CurPath, defaultFile="",
                            wildcard = "All (*.*)|*.*")
        AnsBtn = Dlg.ShowModal()
        AnsFilename = Dlg.GetFilename()
        AnsFilePath = Dlg.GetPath()
        AnsDirPath = Dlg.GetDirectory()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        g_CurPath = AnsDirPath

        ret = MCatalog(AnsDirPath, AnsFilename)
        self.outputLog(ret)
        if ret.retCode < 0: # エラー
            if ret.retCode == lfmtblpy.D5_ROW_SIZE_OVERFLOW:
                Dlg = wx.MessageDialog(self, u"テーブル行数がライセンスの上限を超えました。", u"エラー", wx.OK | wx.ICON_ERROR)
                Dlg.ShowModal()
                return
            elif ret == lfmtblpy.D5_ERROR_MEMORY_LIMIT_OVERFLOW:
                Dlg = wx.MessageDialog(self, u"メモリ使用量がライセンスの上限を超えました。", u"エラー", wx.OK | wx.ICON_ERROR)
                Dlg.ShowModal()
                return
            else:
                Dlg = wx.MessageDialog(self, u"処理中にエラーが発生しました。\nログにエラーコードが出力されています。", u"エラー", wx.OK | wx.ICON_ERROR)
                Dlg.ShowModal()
                return

        tid = ret.retCode

        # ワークスペースに追加
        g_WSInfo.appendTable(tid)
        g_WSTree.appendTable(tid)

        # 使用メモリ
        self.updateUsedMemory()

        return

    ## インポート（ウイザード）---------------------------------------------------------------------
    def OnMenuItemImportWizard(self, event):
        global g_CurPath

        wizard = TextImportWizard(self.app, g_WSInfo, g_WSTree, g_WSFrame)
        page1 = xrc.XRCCTRL(wizard.frame, "TxWzFileSelect")
        page2 = xrc.XRCCTRL(wizard.frame, "TxWzSettingPage")
        page3 = xrc.XRCCTRL(wizard.frame, "TxWzDisplayPage")
        wx.wizard.WizardPageSimple_Chain(page1, page2)
        wx.wizard.WizardPageSimple_Chain(page2, page3)
        wizard.frame.FitToPage(page1)
        wizard.frame.RunWizard(page1)
        wizard.frame.Destroy()
        
        return

    ## エクスポート --------------------------------------------------------------------------------
    def OnMenuItemExport(self, event):
        tid = g_WSTree.curTID
        sid = g_WSTree.curSID

        # 操作対象テーブルチェック
        if (tid <= 0) or g_WSInfo.isJoinTable(tid):
            Dlg = wx.MessageDialog(self, u"Joinテーブルはエクスポートできません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        tableName = g_WSInfo.getTableName(tid)

        global g_CurPath
        Dlg = wx.FileDialog(self, message=u"エクスポートファイル選択", defaultDir=g_CurPath, defaultFile=(tableName + ".csv"),
                            wildcard = "All (*.*)|*.*")
        AnsBtn = Dlg.ShowModal()
        AnsFilename = Dlg.GetFilename()
        AnsFilePath = Dlg.GetPath()
        AnsDirPath = Dlg.GetDirectory()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        g_CurPath = AnsDirPath
        if os.path.exists(AnsFilePath): # 
            Dlg = wx.MessageDialog(self, u"同名のファイルが存在します。上書きしますか？", caption=u"エクスポート") # 
            AnsBtn = Dlg.ShowModal()
            Dlg.Destroy()
            if AnsBtn != wx.ID_OK: # cancel
                return

        ret = MTxtWrite(tableName, ",", AnsDirPath, AnsFilename, "1", "*", "1", "*", "N", sid)
        self.outputLog(ret)
        return

    ## クリアＤＢ ----------------------------------------------------------------------------------
    def OnMenuItemNewWS(self, event):
        # クリア確認
        Dlg = wx.MessageDialog(self, u"ワークスペースをクリアします。\n更新後、保存していないテーブルは破棄されます。\nよろしいですか ?", \
              u"クリア確認",  wx.YES_NO | wx.ICON_QUESTION)
        AnsBtn = Dlg.ShowModal()
        Dlg.Destroy()
        if AnsBtn == wx.ID_OK:   # キャンセル
            return

        ret = MClearWS()
        self.outputLog(ret)

        ret = g_WSInfo.clear()
        self.outputLog(ret)

        g_WSTree.clear()

        # 使用メモリ
        self.updateUsedMemory()

        return

    ## グリッドデータコピー ------------------------------------------------------------------------
    def OnMenuItemCopy(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)

        # 選択範囲取得
        setSize = g_WSInfo.getSetSize(tid, sid)
        rowcol = grid.GetExSelectedRowsCols()
        cols = grid.GetSelectedCols()

        if self.selectAll == True:
            self.selectAll = False
            startRow = 1
            endRow   = grid.GetSelectionAllBottomRow()
            topLeft  = grid.GetSelectionBlockTopLeft()
            bottomRight = grid.GetSelectionBlockBottomRight()
            startCol = topLeft[0][1]
            endCol   = bottomRight[0][1]
        else:
            startRow = rowcol[0]
            endRow   = rowcol[1]
            startCol = rowcol[2]
            endCol   = rowcol[3]
        rowCnt = endRow - startRow + 1

        buf = ""
        eventId = event.GetId()
        if eventId in (xrc.XRCID("MenuItemCopyWithName"), xrc.XRCID("PMenuItemCopyWithName")): # 項目名付き
            # 列ラベル
            for col in cols:
                buf +=  grid.GetColLabelValue(col)
                if col == cols[-1]: # 最終列
                    buf += os.linesep
                else:
                    buf += CB_SEP_CHAR

        # セルデータ
        startRow = startRow - 1
        for idxRow in range(rowCnt):
            row = startRow + idxRow
            for col in cols:
                buf +=  grid.GetValue(row, col)
                if col == cols[-1]: # 最終列
                    buf += os.linesep
                else:
                    buf += CB_SEP_CHAR

        # クリップボードへ書き込み
        if not wx.TheClipboard.Open(): # error
            print >>sys.stderr, "[MyFrame.OnMenuItemCopy] wx.TheClipboard.Open() failed."
            return
        data = wx.TextDataObject(buf)
        wx.TheClipboard.SetData(data)
        wx.TheClipboard.Close()
        return

    ## グリッドデータペースト，クリア，Fill --------------------------------------------------------
    def OnMenuItemPaste(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)
        
        # JOINチェック
        if g_WSInfo.getCountJoinRef(tid) > 0:
            Dlg = wx.MessageDialog(self, u"このテーブルはJoinで参照されています。\n操作の対象にできません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        if g_WSInfo.isJoinTable(tid):
            Dlg = wx.MessageDialog(self, u"Joinテーブルは操作の対象にできません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        # 選択範囲取得
        setSize = g_WSInfo.getSetSize(tid, sid)
        rowcol = grid.GetExSelectedRowsCols()
        cols = grid.GetSelectedCols()

        if self.selectAll == True:
            self.selectAll = False
            startRow = 1
            endRow   = grid.GetSelectionAllBottomRow()
            topLeft  = grid.GetSelectionBlockTopLeft()
            bottomRight = grid.GetSelectionBlockBottomRight()
            startCol = topLeft[0][1]
            endCol   = bottomRight[0][1]
        else:
            startRow = rowcol[0]
            endRow   = rowcol[1]
            startCol = rowcol[2]
            endCol   = rowcol[3]
        rowCnt = endRow - startRow + 1

        # テーブル更新
        listFilter = g_WSInfo.getFilterList(tid)
        bPaste = False
        eventId = event.GetId()
        if eventId in (xrc.XRCID("MenuItemPaste"), xrc.XRCID("PMenuItemPaste")): # ペースト
            bPaste = True
            # クリップボードから読み込み
            if not wx.TheClipboard.Open(): # error
                print >>sys.stderr, "[MyFrame.OnMenuItemPaste] wx.TheClipboard.Open() failed."
                return
            data = wx.TextDataObject()
            wx.TheClipboard.GetData(data)
            wx.TheClipboard.Close()
            buf = data.GetText()
            
            # 列(項目)単位のデータリスト作成
            listData = []
            lines = buf.splitlines()
            for idxRows, line in enumerate(lines):
                dataCols = line.split(CB_SEP_CHAR)
                if idxRows == 0:
                    for i in range(len(dataCols)): # 列数分の空リスト追加
                        listData.append([])
                for idxCol, d in enumerate(dataCols):
                    listData[idxCol].append(d)
            if len(listData) == 0:
                return

            # 更新範囲算出
            lenDataCols = len(dataCols)
            lenDataRows = len(listData[0])
            nFilter = len(listFilter)
            if lenDataCols > nFilter:
                nCol = nFilter 
            else:
                nCol = lenDataCols
            if lenDataRows > setSize:
                nRow = setSize 
            else:
                nRow = lenDataRows

        else: # 同一データで埋める
            nRow = rowCnt
            nCol = len(cols)
            if eventId in (xrc.XRCID("MenuItemClearData"), xrc.XRCID("PMenuItemClearData")): # クリア
                data1 = ""
            else: # Fill
                Dlg = wx.TextEntryDialog(self, u"データ：", u"データ入力", defaultValue="")
                AnsBtn = Dlg.ShowModal()
                data1 = Dlg.GetValue()
                Dlg.Destroy()
                if AnsBtn != wx.ID_OK:
                    return
            listDataFill = [data1 for i in range(nRow)]

        # DB書込
        tableName = g_WSInfo.getTableName(tid)
        pos=0
        for i in cols:
            idxCol = i
            pos+=1
            if idxCol == 0: # RecNo列
                continue
            fltName = grid.GetColLabelValue(idxCol)
            if bPaste:
                listDataArg = listData[pos-1]
            else:
                listDataArg = listDataFill
            ret = MFillEx(tableName, fltName, startRow, nRow, listDataArg, sid, RECONO_MARK_NO)
            self.outputLog(ret)
            if ret.retCode < 0: # error
                continue # 処理を続ける

        grid.ResetCurrentView()
        
        # 使用メモリ
        self.updateUsedMemory()
        return

    ## グリッド直接セルデータ変更（Fill）-----------------------------------------------------------
    def OnGridCellChange(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)
        
        # JOINチェック
        if g_WSInfo.getCountJoinRef(tid) > 0:
            Dlg = wx.MessageDialog(self, u"このテーブルはJoinで参照されています。\n操作の対象にできません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        if g_WSInfo.isJoinTable(tid):
            Dlg = wx.MessageDialog(self, u"Joinテーブルは操作の対象にできません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        # 選択範囲取得
        setSize = g_WSInfo.getSetSize(tid, sid)
        rowcol = grid.GetExSelectedRowsCols()
        cols = grid.GetSelectedCols()

        startRow = rowcol[0]
        endRow   = rowcol[1]
        startCol = rowcol[2]
        endCol   = rowcol[3]
        rowCnt = endRow - startRow + 1

        # テーブル更新
        listFilter = g_WSInfo.getFilterList(tid)

        nRow = rowCnt
        nCol = len(cols)
        data1 = grid.grid.GetCellValue(event.GetRow(), event.GetCol())
        listDataFill = [data1 for i in range(nRow)]

        # DB書込
        tableName = g_WSInfo.getTableName(tid)
        pos=0
        for i in cols:
            idxCol = i
            pos+=1
            if idxCol == 0: # RecNo列
                continue
            fltName = grid.GetColLabelValue(idxCol)
            listDataArg = listDataFill
            ret = MFillEx(tableName, fltName, startRow, nRow, listDataArg, sid, RECONO_MARK_NO)
            self.outputLog(ret)
            if ret.retCode < 0: # error
                continue # 処理を続ける

        grid.ResetCurrentView()
        
        # 使用メモリ
        self.updateUsedMemory()
        return

    ## テーブル削除 --------------------------------------------------------------------------------
    def OnMenuItemDeleteTable(self, event):
        tid = g_WSTree.curTID
        if tid <= 0:
            Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        # JOINチェック
        if g_WSInfo.getCountJoinRef(tid) > 0:
            Dlg = wx.MessageDialog(self, u"このテーブルはJoinで参照されています。\n削除できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        if g_WSTree.curSID <= 0:
            sid = 0
        else:
            sid = g_WSTree.curSID

        tableName = g_WSInfo.getTableName(tid)
        if (sid == 0) and (g_WSInfo.getCountJoinRef(tid) == 0): # 未参照テーブル
            ret = MDrop(tableName)
            self.outputLog(ret)
            if ret.retCode >= 0: # 正常
                g_WSTree.curTID = -1
                g_WSTree.curSID = -1
                g_WSTree.deleteTable(tid)
                g_WSInfo.deleteTable(tid)
        elif sid > 1: # 非ルートセット
            ret = MSetDelete(tableName, sid)
            self.outputLog(ret)
            if ret.retCode >= 0: # 正常
                g_WSTree.curTID = -1
                g_WSTree.curSID = -1
                g_WSTree.deleteSet(tid, sid)
                g_WSInfo.deleteSet(tid, sid)

                # カレントセットID更新
                ret = g_WSInfo.updateCurSetId(tid)
                self.outputLog(ret)
                if ret.retCode >= 0: # 正常
                    sid = ret.retData # 最新カレントセットID
                    g_WSTree.selectSet(tid, sid)

        # 使用メモリ
        self.updateUsedMemory()

        return

    ## 全選択 --------------------------------------------------------------------------------------
    def OnMenuItemSelectAll(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = self.datatab.GetPage(idxPage)
        grid.grid.SelectAll()
        self.selectAll = True
        return

    ## 行番号ジャンプ ------------------------------------------------------------------------------
    def OnMenuItemJump(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)

        col = grid.GetGridCursorCol()
        row = grid.GetGridCursorRow()
        Dlg = wx.TextEntryDialog(self, u"行番号：", u"行ジャンプ", defaultValue=str(row + 1)) 
        AnsBtn = Dlg.ShowModal()
        lineNoStr = Dlg.GetValue()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return
        try:
            lineNo = int(lineNoStr)
        except:
            return
        setSize = g_WSInfo.getSetSize(tid, sid)
        if lineNo < 1:
            lineNo = 1
        elif lineNo > setSize:
            lineNo = setSize
        cols = grid.GetSelectedCols()
        if len(cols) > 0: 
            col = cols[0]

        # カーソル移動
        grid.SetGridCursor(lineNo-1, col)
        
        return

    ## 検索ジャンプ ----------------------------------------------------------------------------------
    def OnMenuItemFind(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)

        # JOINチェック
        if g_WSInfo.isJoinTable(tid):
            Dlg = wx.MessageDialog(self, u"Joinテーブルは操作の対象にできません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        cols = grid.GetSelectedCols()
        sz = len(cols)
        if sz < 1: # 列が選択されていない
            col = grid.GetGridCursorCol()
            row = grid.GetGridCursorRow()
        else:
            col = min(cols)
            row = 0
        grid.grid.SetFocus()
        grid.grid.SelectBlock(row, col, row, col)

        tableName = g_WSInfo.getTableName(tid)
        listFilter = g_WSInfo.getFilterList(tid)
        fid = listFilter[col-1]
        fltName = g_WSInfo.getFilterName(tid, fid)
        fltType = g_WSInfo.getFilterType(tid, fid)

        Dlg = MyDialogSearch(self, fltName, fltType)
        Dlg.SetLabel(u"検索") # ウィンドウラベル変更
        AnsBtn = Dlg.ShowModal()

        opeType = Dlg.getOpeType()
        val1 = Dlg.getVal1()
        val2 = Dlg.getVal2()

        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        ret = g_WSInfo.openFind(tid, fid, opeType, val1, val2)
        self.outputLog(ret)
        if ret.retCode < 0:
            return

        g_WSTree.srchId = ret.retCode
        ret = g_WSInfo.getNextHit(tid, g_WSTree.srchId, sid, row + 1, 0)
        self.outputLog(ret)
        if ret.retCode <= 0:
            return
        (fltID, nextPos) = ret.retData

        # グリッドカーソル移動
        grid.SetGridCursor(nextPos - 1, col)

        # 使用メモリ
        self.updateUsedMemory()

        return

    ## 値ジャンプ Prev/Next ------------------------------------------------------------------------
    def OnMenuItemPrevNext(self, event):
        if g_WSTree.srchId < 0: # 検索ID未設定
            Dlg = wx.MessageDialog(self, u"検索IDが設定されていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)

        eventId = event.GetId()
        if eventId in (xrc.XRCID("MenuItemPrev"), xrc.XRCID("PMenuItemPrev"), xrc.XRCID("jumpPrevious")):
            dir = 1
        else:
            dir = 0

        row = grid.GetGridCursorRow()
        listFilter = g_WSInfo.getFilterList(tid)
        ret = g_WSInfo.getNextHit(tid, g_WSTree.srchId, sid, row + 1, dir)
        self.outputLog(ret)
        if ret.retCode < 0: # error
            g_WSTree.srchId = -1
            return
        elif ret.retCode == 0: # not found
            return
        (fltID, nextPos) = ret.retData

        # グリッドカーソル移動
        col = listFilter.index(fltID) + 1
        grid.SetGridCursor(nextPos - 1, col)

        return

    ## 名前変更 ------------------------------------------------------------------------------------
    def OnMenuItemChangeName(self, event):
        focus = wx.Window.FindFocus()
        if focus == g_WSTree.treeCtrl: # WSツリーにフォーカス
        #dummy =0
        #if dummy != 0: # WSツリーにフォーカス
            # テーブル名変更
            if g_WSTree.curTID < 1:
                Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
                Dlg.ShowModal()
                return

            tableName = g_WSInfo.getTableName(g_WSTree.curTID)
            Dlg = wx.TextEntryDialog(self, u"テーブル名：", u"テーブル名入力", defaultValue=tableName)
            AnsBtn = Dlg.ShowModal()
            name = Dlg.GetValue()
            Dlg.Destroy()
            if AnsBtn != wx.ID_OK:
                return

            ret = MRename(tableName, name)
            self.outputLog(ret)
            if ret.retCode < 0:
                return
            newName = ret.retData # 実際に付けられた新しいテーブル名
            g_WSInfo.renameTable(tableName, newName)
            g_WSTree.renameTable(g_WSTree.curTID, newName)

        else:
            # 項目名変更
            if self.datatab.GetPageCount() < 1: # グリッドなし
                Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
                Dlg.ShowModal()
                return

            idxPage = self.datatab.GetSelection()
            grid = g_WSTree.listGrid[idxPage]
            (tid, sid) = g_WSTree.getTidSidFromGrid(grid)

            cols = grid.GetSelectedCols()
            if 0 in cols:
                cols.remove(0) # RecNo列除外
            if len(cols) < 1: # 列が選択されていない
                return

            name = grid.GetColLabelValue(min(cols)) # 一番左のラベル名→入力初期値
            Dlg = wx.TextEntryDialog(self, u"項目名：", u"項目名入力", defaultValue=name)
            AnsBtn = Dlg.ShowModal()
            name = Dlg.GetValue()
            Dlg.Destroy()
            if AnsBtn != wx.ID_OK:
                return

            # 選択されている全ての列に適用
            tableName = g_WSInfo.getTableName(tid)
            for col in cols:
                oldName = grid.GetColLabelValue(col)
                ret = MRenameFilter(tableName, oldName, name)
                self.outputLog(ret)
                if ret.retCode < 0:
                    return
                newName = ret.retData # 実際に付けられた新しい項目名
                g_WSInfo.renameFilter(tid, oldName, newName)
                grid.listFilterName[col-1] = newName
    
        self.ResetView()
        return

    ## テーブルオープン ----------------------------------------------------------------------------
    def OnMenuItemOpenTable(self, event):
        if g_WSTree.curTID < 1:
            return
        if g_WSTree.curSID < 1: # テーブル
            ret = self.checkOpenTable(g_WSTree.curTID) # テーブルが開いていなかったら開く
            if ret < 0:
                return
            g_WSTree.curSID = g_WSInfo.getCurSetId(g_WSTree.curTID)
            g_WSTree.selectSet(g_WSTree.curTID, g_WSTree.curSID)
        # セットを開く
        self.openSet()
        return

    ## セットオープン ----------------------------------------------------------------------------
    def openSet(self):
        if g_WSInfo.isOpenSet(g_WSTree.curTID, g_WSTree.curSID): # オープン済セット
            g_WSTree.selectSetGrid(g_WSTree.curTID, g_WSTree.curSID) # 対応グリッド表示
        else: # 未オープンセット
            ret = g_WSInfo.openSet(g_WSTree.curTID, g_WSTree.curSID)
            self.outputLog(ret)
            if ret.retCode < 0:
                return

            # グリッドデータ処理
            # 同一テーブル内の他のオープン済みセットが存在？
            (openSid, openGrid, idxPage) = g_WSTree.getOpenGridInTable(g_WSTree.curTID)
            if openGrid != None: # 存在する
                # オープン済みセットを閉じてグリッド再利用
                g_WSInfo.closeSet(g_WSTree.curTID, openSid)
                g_WSTree.changeKeyMapGrid((g_WSTree.curTID, openSid), (g_WSTree.curTID, g_WSTree.curSID))
            self.createGrid(g_WSTree.curTID, g_WSTree.curSID, openGrid, idxPage)

        # エンジン内カレントセットID更新
        if g_WSTree.curSID != g_WSInfo.getCurSetId(g_WSTree.curTID):
            ret = MSetCurMove(g_WSInfo.getTableName(g_WSTree.curTID), g_WSTree.curSID)
            self.outputLog(ret)
            if ret.retCode >= 0:
                g_WSInfo.setCurSetId(g_WSTree.curTID, g_WSTree.curSID)
                g_WSTree.selectSet(g_WSTree.curTID, g_WSTree.curSID)

        return

    ## テーブル作成 --------------------------------------------------------------------------------
    def OnMenuItemNewTable(self, event):
        Dlg = MyDialogTableCreate(self)
        ctrlRow = xrc.XRCCTRL(self, "TextCtrlTableCreateRow")
        ctrlRow.SetValue("0")
        ctrlName = xrc.XRCCTRL(self, "TextCtrlTableCreateName")
        ctrlName.SetValue("NewTable")   # テーブル名
        ctrlName.SetFocus()
        ctrlName.SetSelection(-1, -1)   # 全テキスト選択

        AnsBtn = Dlg.ShowModal()
        AnsName = ctrlName.GetValue()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        try:
            nRow = int(ctrlRow.GetValue())
            if nRow < 0:
                Dlg = wx.MessageDialog(self, u"テーブル行数が不正です。", u"エラー", wx.OK | wx.ICON_ERROR)
                Dlg.ShowModal()
                return
        except:
            Dlg = wx.MessageDialog(self, u"テーブル行数は数字を入力してください。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        # テーブル作成
        ret = MCreateTbl(nRow, AnsName)
        self.outputLog(ret)
        if ret.retCode < 0:
            if ret.retCode == lfmtblpy.D5_ERROR_TOO_LARGE_ROW_SIZE:
                Dlg = wx.MessageDialog(self, u"テーブル行数がライセンスの上限を超えています。", u"エラー", wx.OK | wx.ICON_ERROR)
                Dlg.ShowModal()
                return
            else:
                Dlg = wx.MessageDialog(self, u"処理中にエラーが発生しました。\nログにエラーコードが出力されています。", u"エラー", wx.OK | wx.ICON_ERROR)
                Dlg.ShowModal()
                return
        tid = ret.retCode

        # ワークスペースに追加
        g_WSInfo.appendTable(tid)
        g_WSTree.appendTable(tid)

        # 使用メモリ
        self.updateUsedMemory()

        return

    ## テーブル複製 --------------------------------------------------------------------------------
    def OnMenuItemDuplTable(self, event):
        # 操作対象テーブルチェック
        if g_WSTree.curTID < 1:
            Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        if g_WSInfo.isJoinTable(g_WSTree.curTID):
            Dlg = wx.MessageDialog(self, u"Joinテーブルは操作の対象にできません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        tblName = g_WSInfo.getTableName(g_WSTree.curTID)
        ret = MTableDupl(tblName)
        self.outputLog(ret)
        if ret.retCode < 0: # エラー
            return
        tid = ret.retCode

        # ワークスペースに追加
        g_WSInfo.appendTable(tid)
        g_WSTree.appendTable(tid)

        # 使用メモリ
        self.updateUsedMemory()

        return

    ## テーブルクローズ ----------------------------------------------------------------------------
    def OnMenuItemCloseTable(self, event):
        g_WSTree.closeSet()
        return

    ## JOINテーブルをREALテーブルに変換 ------------------------------------------------------------
    def OnMenuItemCopyAsRealTable(self, event):
        # 操作対象テーブルチェック
        if (g_WSTree.curTID < 1) or (g_WSTree.curSID < 1):
            Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        if not g_WSInfo.isJoinTable(g_WSTree.curTID):
            Dlg = wx.MessageDialog(self, u"Joinテーブルではありません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        tableNameJoin = g_WSInfo.getTableName(g_WSTree.curTID)
        listSet = g_WSInfo.getSetList(g_WSTree.curTID)
        listFilterName = g_WSInfo.getFilterNameList(g_WSTree.curTID)

        # REALテーブル名生成
        ret = g_WSInfo.generateTableName(tableNameJoin)
        self.outputLog(ret)
        if ret.retCode == 0: # 正常
            tableName = ret.retData
        else:
            tableName = tableNameJoin

        Dlg = MyDialogJoinRealize(self, tableName, g_WSTree.curSID, listSet, listFilterName)
        AnsBtn = Dlg.ShowModal()
        tableName = Dlg.getTableName()
        sid = Dlg.getSetId()
        bMaster = Dlg.isMaster()
        bSlave = Dlg.isSlave()
        listSelectFilterName = Dlg.getSelectFilterNameList()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        ret = MJoinRealize(tableNameJoin, tableName, sid, MAP_YN[bMaster], MAP_YN[bSlave], listSelectFilterName)
        self.outputLog(ret)
        if ret.retCode < 0:
            return
        tid = ret.retCode

        # ワークスペースに追加
        g_WSInfo.appendTable(tid)
        g_WSTree.appendTable(tid)

        # 使用メモリ
        self.updateUsedMemory()

        return

    ## JOIN ----------------------------------------------------------------------------------------
    def OnMenuItemJoinTable(self, event):
        # 操作対象テーブルチェック
        if g_WSTree.curTID < 1 :
            Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        if g_WSInfo.isJoinTable(g_WSTree.curTID):
            Dlg = wx.MessageDialog(self, u"Joinテーブルは指定できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        tableName = g_WSInfo.getTableName(g_WSTree.curTID)

        # JOINテーブル名生成
        ret = g_WSInfo.generateTableName(tableName)
        self.outputLog(ret)
        if ret.retCode == 0: # 正常
            tableNameJoin = ret.retData
        else:
            tableNameJoin = tableName

        Dlg = MyDialogJoin(self, g_WSTree.curTID, tableNameJoin, g_WSTree)
        AnsBtn = Dlg.ShowModal()

        tableNameJoin = Dlg.getNewTableName()
        (tableNameMaster, tableNameSlave) = Dlg.getTableNames()
        bOuter = Dlg.isOuter()
        (sidMaster, sidSlave) = Dlg.getSetIds()
        (listFilterNameMaster, listFilterNameSlave) = Dlg.getKeyLists()

        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        if (len(listFilterNameMaster) == 0) or (len(listFilterNameSlave) == 0): # JOINキー設定なし
            return

        ret = MCreateJoin(tableNameJoin, tableNameMaster, tableNameSlave, sidMaster, sidSlave \
                        , listFilterNameMaster, listFilterNameSlave, MAP_YN[bOuter])
        self.outputLog(ret)
        if ret.retCode < 0:
            return
        tid = ret.retCode

        # ワークスペースに追加
        g_WSInfo.appendTable(tid)
        g_WSTree.appendTable(tid)

        # 使用メモリ
        self.updateUsedMemory()

        return

    ## Union ---------------------------------------------------------------------------------------
    def OnMenuItemUnionTable(self, event):
        # 操作対象テーブルチェック
        if g_WSTree.curTID < 1:
            Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        if g_WSInfo.isJoinTable(g_WSTree.curTID):
            Dlg = wx.MessageDialog(self, u"Joinテーブルは指定できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        tableName = g_WSInfo.getTableName(g_WSTree.curTID)

        # Unionテーブル名生成
        ret = g_WSInfo.generateTableName(tableName)
        self.outputLog(ret)
        if ret.retCode == 0: # 正常
            tableNameUnion = ret.retData
        else:
            tableNameUnion = tableName

        Dlg = MyDialogUnion(self, g_WSTree.curTID, tableNameUnion, g_WSTree)
        AnsBtn = Dlg.ShowModal()

        tableNameUnion = Dlg.getNewTableName()
        (tableNameMaster, tableNameSlave) = Dlg.getTableNames()
        bTableId = Dlg.isTableId()
        bRecNo = Dlg.isRecNo()
        bDeleteTable = Dlg.isDeleteTable()
        (sidMaster, sidSlave) = Dlg.getSetIds()
        (listFilterNameMaster, listFilterNameSlave) = Dlg.getKeyLists()

        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        if (len(listFilterNameMaster) == 0) or (len(listFilterNameSlave) == 0): # Unionキー設定なし
            return

        ret = MUnion(tableNameUnion, tableNameMaster, tableNameSlave, sidMaster, sidSlave \
                    , listFilterNameMaster, listFilterNameSlave, MAP_YN[bTableId], MAP_YN[bRecNo], MAP_YN[bDeleteTable])
        self.outputLog(ret)
        if ret.retCode < 0:
            if ret.retCode == lfmtblpy.D5_ERROR_TOO_LARGE_ROW_SIZE:
                Dlg = wx.MessageDialog(self, u"テーブル行数がライセンスの上限を超えました。", u"エラー", wx.OK | wx.ICON_ERROR)
                Dlg.ShowModal()
                return
            else:
                Dlg = wx.MessageDialog(self, u"処理中にエラーが発生しました。\nログにエラーコードが出力されています。", u"エラー", wx.OK | wx.ICON_ERROR)
                Dlg.ShowModal()
                return

        tid = ret.retCode

        # 元テーブル削除
        if bDeleteTable:
            for tableName in (tableNameMaster, tableNameSlave):
                tableId = g_WSInfo.getTableId(tableName)
                g_WSTree.deleteTable(tableId)
                g_WSInfo.deleteTable(tableId)
                if tableNameMaster == tableNameSlave:
                    break

        # ワークスペースに追加
        g_WSInfo.appendTable(tid)
        g_WSTree.appendTable(tid)

        # 使用メモリ
        self.updateUsedMemory()

        return

    ## 集計 ----------------------------------------------------------------------------------------
    def OnMenuItemSummaryTable(self, event):
        # 操作対象テーブルチェック
        if g_WSTree.curTID < 1:
            Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        Dlg = MyDialogSum(self, g_WSTree.curTID, g_WSInfo)
        AnsBtn = Dlg.ShowModal()

        sid = Dlg.getSetId()
        listDim = Dlg.getDimList()
        listMsrs = Dlg.getMsrsList()

        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        tableName = g_WSInfo.getTableName(g_WSTree.curTID)
        ret = MXSum(tableName, sid, listDim, listMsrs)
        self.outputLog(ret)
        if ret.retCode < 0:
            return
        tid = ret.retCode

        # ワークスペースに追加
        g_WSInfo.appendTable(tid)
        g_WSTree.appendTable(tid)

        # 使用メモリ
        self.updateUsedMemory()

        return

    ## 項目転送 ------------------------------------------------------------------------------------
    def OnMenuItemTransferFilter(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)

        # 操作対象テーブルチェック
        if not g_WSInfo.isJoinTable(tid): # JOINテーブルでない
            Dlg = wx.MessageDialog(self, u"転送元はJoinテーブルではありません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        cols = grid.GetSelectedCols()
        if 0 in cols:
            cols.remove(0) # RecNo列除外
        eventId = event.GetId()
        sz = len(cols)
        if sz < 1: # 列が選択されていない
            return
        
        # 複数項目列選択サポート
        fids = []
        errRet =  False
        for col in cols:
            name = grid.GetColLabelValue(col)
            ret = MFltTransfer(g_WSInfo.getTableName(tid), name)
            self.outputLog(ret)
            if ret.retCode < 0:
                errRet = True
                break
            fids.append( ret.retCode )
        
        if errRet == True:
            return
        
        g_WSTree.curTID = g_WSInfo.getMasterTableId(tid)
        retOpenTable = self.checkOpenTable(g_WSTree.curTID)
        if retOpenTable < 0:
            return
        g_WSTree.curSID = g_WSInfo.getCurSetId(g_WSTree.curTID)
        g_WSTree.selectSet(g_WSTree.curTID, g_WSTree.curSID)
        if retOpenTable == 1:
            for fid in fids:
                ret = g_WSInfo.appendFilter(g_WSTree.curTID, fid, -1)  # 末尾に新項目追加
                self.outputLog(ret)

        (openSid, openGrid, masidxPage) = g_WSTree.getOpenGridInTable(g_WSTree.curTID)
        self.datatab.SetSelection(masidxPage)
        
        self.ResetView()
        # 使用メモリ
        self.updateUsedMemory()
        return

    ## Extract Join In/Out -------------------------------------------------------------------------
    def OnMenuItemExtractInOut(self, event):
        if g_WSTree.curTID < 1:
            Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        if not g_WSInfo.isJoinTable(g_WSTree.curTID):
            Dlg = wx.MessageDialog(self, u"このテーブルはJoinテーブルではありません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        if g_WSInfo.isOuterJoinTable(g_WSTree.curTID):
            Dlg = wx.MessageDialog(self, u"このテーブルはアウターJoinテーブルです。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        Dlg = MyDialogExtractInOut(self)
        AnsBtn = Dlg.ShowModal()

        bSlave = Dlg.isSlave()
        bIN = Dlg.isIN()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        ret = MINOUT(g_WSInfo.getTableName(g_WSTree.curTID), MAP_YN[bSlave], MAP_YN[bIN])
        self.outputLog(ret)
        if ret.retCode < 0:
            return
        (g_WSTree.curTID, g_WSTree.curSID) = ret.retData

        # ワークスペースに追加
        g_WSInfo.appendSet(g_WSTree.curTID, g_WSTree.curSID)
        ret = self.checkOpenTable(g_WSTree.curTID) # テーブルが開いていなかったら開く
        if ret < 0: # エラー
            return
        elif ret == 1: # オープン済みだった
            g_WSTree.appendSet(g_WSTree.curTID, g_WSTree.curSID)

        # セットを開く
        self.openSet()
        g_WSTree.selectSet(g_WSTree.curTID, g_WSTree.curSID)

        # 使用メモリ
        self.updateUsedMemory()
        return

    ## テーブルが開いているかチェックし、開いていなかったら開く ------------------------------------
    # @param[in]    tid テーブルID
    # @retval   0       正常オープン
    # @retval   1       既にオープンしていた
    # @retval   -1      エラー
    def checkOpenTable(self, tid):
        retval = -1
        if not g_WSInfo.isOpenTable(tid): # テーブル未オープン
            # テーブルを開く
            ret = g_WSInfo.openTable(tid)
            self.outputLog(ret)
            if ret.retCode < 0:
                return retval

            # セット情報→ツリー登録
            for sid in g_WSInfo.getSetList(tid):
                g_WSTree.appendSet(tid, sid)
            retval = 0
        else: # オープン済み
            retval = 1
        return retval

    ## テーブルプロパティ --------------------------------------------------------------------------
    def OnMenuItemPropertyTable(self, event):
        tid = g_WSTree.curTID

        # 操作対象テーブルチェック
        if tid < 1:
            Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        self.checkOpenTable(tid)
        tableName = g_WSInfo.getTableName(tid)
        bJoin = g_WSInfo.isJoinTable(tid)
        propertyText = u"===== テーブル情報 ==========\n"
        if bJoin:
            tableKind = "JOIN"
        else:
            tableKind = "REAL"
        propertyText += u"テーブル種別： %s\n" % tableKind
        propertyText += u"ID： %d\n" % tid
        propertyText += u"項目数： %d\n" % g_WSInfo.getCountFilter(tid)
        propertyText += u"セット数： %d\n" % g_WSInfo.getCountSet(tid)
        propertyText += "\n"

        if bJoin:
            propertyText += u"=== ジョインテーブル情報 =====\n\n"
            propertyText += u"=== マスターテーブル情報 =====\n"
            tidM = g_WSInfo.getMasterTableId(tid)
            self.checkOpenTable(tidM)
            propertyText += u"テーブル名： %s\n" % g_WSInfo.getTableName(tidM)
            propertyText += u"項目数　： %d\n" % g_WSInfo.getCountFilter(tidM)
            propertyText += u"セット数： %d\n" % g_WSInfo.getCountSet(tidM)
            sidM = g_WSInfo.getMasterSetId(tid)
            propertyText += u" JOINセットID： %d\n" % sidM
            propertyText += u" JOINセットサイズ： %d\n" % g_WSInfo.getSetSize(tidM, sidM)
            propertyText += "\n"
            propertyText += u"=== スレーブテーブル情報 ====\n"
            tidS = g_WSInfo.getSlaveTableId(tid)
            self.checkOpenTable(tidS)
            propertyText += u"テーブル名： %s\n" % g_WSInfo.getTableName(tidS)
            propertyText += u"項目数： %d\n" % g_WSInfo.getCountFilter(tidS)
            propertyText += u"セット数： %d\n" % g_WSInfo.getCountSet(tidS)
            sidS = g_WSInfo.getSlaveSetId(tid)
            propertyText += u" JOINセットID： %d\n" % sidS
            propertyText += u" JOINセットサイズ： %d\n" % g_WSInfo.getSetSize(tidS, sidS)
            propertyText += "\n"
            propertyText += u"=== ジョインキー情報 =====\n"
            if g_WSInfo.isOuterJoinTable(tid):
                joinKind = "Outer"
            else:
                joinKind = "Inner"
            propertyText += u"ジョイン種別： %s JOIN\n" % joinKind
            propertyText += u"ジョインキー数： %d\n" % g_WSInfo.getCountJoinKey(tid)
            propertyText += "\n"
            propertyText += u"= 主ジョインキー ==\n"
            listJoinKeyM = g_WSInfo.getMasterJoinKeyList(tid)
            for i, id in enumerate(listJoinKeyM):
                type = g_WSInfo.getFilterType(tidM, id)
                name = g_WSInfo.getFilterName(tidM, id)
                propertyText += "No.%d/ ID=%d/ TYPE=%s/ NAME= %s\n" % (i+1, id, MAP_DATA_TYPE_NC[type], name)
            propertyText += "\n"
            propertyText += u"= 副ジョインキー ==\n"
            listJoinKeyS = g_WSInfo.getSlaveJoinKeyList(tid)
            for i, id in enumerate(listJoinKeyS):
                type = g_WSInfo.getFilterType(tidS, id)
                name = g_WSInfo.getFilterName(tidS, id)
                propertyText += "No.%d/ ID=%d/ TYPE=%s/ NAME= %s\n" % (i+1, id, MAP_DATA_TYPE_NC[type], name)
            propertyText += "\n"
            propertyText += "\n"

        propertyText += u"=== 項目情報 =============\n"
        listFilter = g_WSInfo.getFilterList(tid)
        listFilterType = g_WSInfo.getFilterTypeList(tid)
        listFilterName = g_WSInfo.getFilterNameList(tid)
        for i, (id, type, name) in enumerate(zip(listFilter, listFilterType, listFilterName)):
            propertyText += "No.%d/ ID=%d/ TYPE=%s/ NAME= %s\n" % (i+1, id, MAP_DATA_TYPE_NC[type], name)
        propertyText += "\n"

        propertyText += u"=== セット情報 ===========\n"
        listSet = g_WSInfo.getSetList(tid)
        for i, sid in enumerate(listSet):
            propertyText += "No.%d/ ID=%d/ SIZE= %d\n" % (i+1, sid, g_WSInfo.getSetSize(tid, sid))
        propertyText += "\n"

        if not bJoin:
            propertyText += u"=== ジョインテーブル ===\n"
            listJoinRef = g_WSInfo.getJoinRefList(tid)
            for i, id in enumerate(listJoinRef):
                propertyText += "%d. ID=%d Name=%s\n" % (i+1, id, g_WSInfo.getTableName(id))
            propertyText += "\n"

        Dlg = MyDialogProperty(self, tableName, propertyText)
        AnsBtn = Dlg.ShowModal()
        return

    ## ソート --------------------------------------------------------------------------------------
    def OnMenuSort(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)
        cols = grid.GetSelectedCols()
        eventId = event.GetId()
        sz = len(cols)
        if sz < 1: # 列が選択されていない
            return
        elif eventId in (xrc.XRCID("MenuItemSortSpecify"), xrc.XRCID("PMenuItemSortSpecify"), xrc.XRCID("sort")):
            # 指定順
            # TODO 指定順未対応
            return
        else: # 1項目
            if eventId in (xrc.XRCID("MenuItemSortDescend"), xrc.XRCID("PMenuItemSortDescend")):
                sortType = SORT_TYPE_DSC # 降順
            else:
                sortType = SORT_TYPE_ASC # 昇順
            col=min(cols)
            name = grid.GetColLabelValue(min(cols)) # 一番左のラベル名
            if col == 0:
                #TODO macro 
                if sortType == SORT_TYPE_ASC:
                    type = 0
                else:
                    type = 1
                rc = lfmtblpy.RD5SortByRowNo(tid, 0, sid, type)
                retVal = RetVal()
                retVal.appendLogM("RD5SortByRowNo")
                ret = retVal.makeRetVal(rc)
            else:
                ret = MSort(g_WSInfo.getTableName(tid), name, sid, sortType)

        self.outputLog(ret)
        if ret.retCode < 0:
            return
        g_WSTree.curSID = ret.retCode
        g_WSTree.curTID = tid

        # セットコメント設定
        tableName = g_WSInfo.getTableName(tid)
        scom = "Sort Set:%d [%s:%s]" % (sid, name, sortType)
        ret = MSetComment(tableName, g_WSTree.curSID, scom)
        self.outputLog(ret)

        # ワークスペースに追加
        g_WSInfo.appendSet(g_WSTree.curTID, g_WSTree.curSID)
        g_WSTree.appendSet(g_WSTree.curTID, g_WSTree.curSID)

        # セットを開く
        self.openSet()

        # 使用メモリ
        self.updateUsedMemory()
        return

    ## サーチ --------------------------------------------------------------------------------------
    def OnMenuItemSearch(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        # 操作対象テーブルチェック
        if g_WSTree.curTID < 1:
            Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)

        cols = grid.GetSelectedCols()
        if 0 in cols:
            cols.remove(0) # RecNo列除外
        sz = len(cols)
        if sz < 1: # 列が選択されていない
            return
        col = min(cols)

        tableName = g_WSInfo.getTableName(tid)
        listFilter = g_WSInfo.getFilterList(tid)
        fid = listFilter[col-1]
        fltName = g_WSInfo.getFilterName(tid, fid)
        fltType = g_WSInfo.getFilterType(tid, fid)

        Dlg = MyDialogSearch(self, fltName, fltType)
        AnsBtn = Dlg.ShowModal()
        opeStr = Dlg.getSearchOpString()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        ret = MSearch(tableName, fltName, sid, opeStr)
        self.outputLog(ret)
        if ret.retCode < 0:
            return
        g_WSTree.curSID = ret.retCode
        g_WSTree.curTID = tid

        # セットコメント設定
        scom = "Search Set:%d [%s]" % (sid, opeStr)
        ret = MSetComment(tableName, g_WSTree.curSID, scom)
        self.outputLog(ret)

        # ワークスペースに追加
        g_WSInfo.appendSet(g_WSTree.curTID, g_WSTree.curSID)
        g_WSTree.appendSet(g_WSTree.curTID, g_WSTree.curSID)

        # セットを開く
        self.openSet()

        # 使用メモリ
        self.updateUsedMemory()
        return

    ## 計算 ----------------------------------------------------------------------------------------
    def OnMenuItemCalc(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)

        # JOINチェック
        if g_WSInfo.getCountJoinRef(tid) > 0:
            Dlg = wx.MessageDialog(self, u"このテーブルはJoinで参照されています。\n操作の対象にできません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        if g_WSInfo.isJoinTable(tid):
            Dlg = wx.MessageDialog(self, u"Joinテーブルは操作の対象にできません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        # 選択範囲取得
        setSize = g_WSInfo.getSetSize(tid, sid)
        rowcol = grid.GetExSelectedRowsCols()
        cols = grid.GetSelectedCols()

        if self.selectAll == True:
            self.selectAll = False
            startRow = 1
            endRow   = grid.GetSelectionAllBottomRow()
            topLeft  = grid.GetSelectionBlockTopLeft()
            bottomRight = grid.GetSelectionBlockBottomRight()
            startCol = topLeft[0][1]
            endCol   = bottomRight[0][1]
        else:
            startRow = rowcol[0]
            endRow   = rowcol[1]
            startCol = rowcol[2]
            endCol   = rowcol[3]
        rowCnt = endRow - startRow + 1

        if 0 in cols:
            cols.remove(0) # RecNo列除外
        if len(cols) < 1:
            return

        # 計算式入力ダイアログ
        Dlg = MyDialogCalc(self, tid, g_WSInfo)
        AnsBtn = Dlg.ShowModal()
        calcStr = Dlg.getText()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        # 選択されている全ての列に適用
        tableName = g_WSInfo.getTableName(tid)
        listFilter = g_WSInfo.getFilterList(tid)
        for i, col in enumerate(cols):
            fid = listFilter[col-1]
            fltName = g_WSInfo.getFilterName(tid, fid)
            ret = MCalc(tableName, fltName, startRow, rowCnt, calcStr, sid)
            self.outputLog(ret)
            if ret.retCode < 0:
                return
        
        # グリッド表示更新
        grid.ResetCurrentView()

        # 使用メモリ
        self.updateUsedMemory()
        return

    ## ユニーク行抽出 ------------------------------------------------------------------------------
    def OnMenuItemExUnique(self, event):
        # 操作対象テーブル・セットのチェック
        if g_WSTree.curTID < 1:
            Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        if g_WSTree.curSID < 1:
            Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        listSet = g_WSInfo.getSetList(g_WSTree.curTID)
        listFilterName = g_WSInfo.getFilterNameList(g_WSTree.curTID)

        Dlg = MyDialogExUnique(self, g_WSTree.curSID, listSet, listFilterName)
        AnsBtn = Dlg.ShowModal()
        sid = Dlg.getSetId()
        bKeepOrder = Dlg.isKeepOrder()
        listSelectFilterName = Dlg.getSelectFilterNameList()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        tableName = g_WSInfo.getTableName(g_WSTree.curTID)
        ret = MExUnique(tableName, sid, listSelectFilterName, MAP_YN[bKeepOrder])
        self.outputLog(ret)
        if ret.retCode < 0:
            return
        g_WSTree.curSID = ret.retCode

        # セットコメント設定
        scom = "ExUnique Set:%d" % sid
        ret = MSetComment(tableName, g_WSTree.curSID, scom)
        self.outputLog(ret)

        # ワークスペースに追加
        g_WSInfo.appendSet(g_WSTree.curTID, g_WSTree.curSID)
        g_WSTree.appendSet(g_WSTree.curTID, g_WSTree.curSID)

        # セットを開く
        self.openSet()

        # 使用メモリ
        self.updateUsedMemory()
        return

    ## セット演算 ----------------------------------------------------------------------------------
    def OnMenuItemSetOp(self, event):
        # 操作対象テーブル・セットのチェック
        if g_WSTree.curTID < 1:
            Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        if g_WSTree.curSID < 1:
            Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        tableName = g_WSInfo.getTableName(g_WSTree.curTID)
        listSet = g_WSInfo.getSetList(g_WSTree.curTID)
        Dlg = MyDialogSetOp(self, tableName, listSet)
        AnsBtn = Dlg.ShowModal()

        setOp = Dlg.getSetOp()
        sidTgt = Dlg.getTargetSetId()
        sidSrc = Dlg.getSourceSetId()

        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        if setOp < 0:
            ret = MSetNOT(tableName, sidSrc)
            scom = "NOT Set:%d" % sidSrc
        else:
            if   setOp == lfmtblpy.D5_SETOPE_AND:
                ret = MSetAND(tableName, sidSrc, sidTgt)
            elif setOp == lfmtblpy.D5_SETOPE_OR:
                ret = MSetOR(tableName, sidSrc, sidTgt)
            elif setOp == lfmtblpy.D5_SETOPE_SUB:
                ret = MSetSUB(tableName, sidSrc, sidTgt)
            scom = "%s Set:%d,Set:%d" % (LIST_SET_OP[setOp], sidSrc, sidTgt)

        self.outputLog(ret)
        if ret.retCode < 0:
            return
        g_WSTree.curSID = ret.retCode

        # セットコメント設定
        ret = MSetComment(tableName, g_WSTree.curSID, scom)
        self.outputLog(ret)

        # ワークスペースに追加
        g_WSInfo.appendSet(g_WSTree.curTID, g_WSTree.curSID)
        g_WSTree.appendSet(g_WSTree.curTID, g_WSTree.curSID)

        # セットを開く
        self.openSet()

        # 使用メモリ
        self.updateUsedMemory()
        return

    # 指定行以降のRecNoを再設定（暫定）-------------------------------------------------------------
    def renumRecNo(self, grid, tid, sid):
        listRecNo = g_WSInfo.getRecNoList(tid, sid)
        for i, recNo in enumerate(listRecNo):
            grid.grid.SetCellValue(i, 0, str(recNo))
            grid.grid.SetCellAlignment(i, 0, wx.ALIGN_RIGHT, wx.ALIGN_TOP)
            grid.grid.SetReadOnly(i, 0, True)
        # resize
        # 行削除して0行になったら1行だけ追加
        # 0行テーブルに行挿入後、不要行削除
        nGridRow = grid.grid.GetNumberRows()
        nRow = len(listRecNo)
        if (nGridRow == 0) and (nRow == 0):
            grid.grid.InsertRows(pos=0, numRows=1)
        elif (nGridRow > nRow):
            grid.grid.DeleteRows(pos=nRow, numRows=(nGridRow - nRow))
        return

    ## 行挿入 --------------------------------------------------------------------------------------
    def OnMenuItemInsertRow(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)

        # 操作対象テーブルチェック
        if sid != 1:
            Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        if g_WSInfo.getCountJoinRef(tid) != 0:
            Dlg = wx.MessageDialog(self, u"このテーブルはJoinで参照されています。\n操作の対象にできません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        eventId = event.GetId()
        incr = -1
        if eventId in (xrc.XRCID("MenuItemAppendRow"), xrc.XRCID("PMenuItemAppendRow")): # Append
            incr = 1

        selrows = grid.GetSelectedRows()
        lenRows = len(selrows)
        if lenRows > 0: # 行選択あり
            ival = 0
            for insrow in selrows:
                ret = MInsertRow(g_WSInfo.getTableName(tid), insrow+ival+incr, 1)
                self.outputLog(ret)
                ival=ival+1
            # 情報更新
            g_WSInfo.setCountRow(tid, g_WSInfo.getCountRow(tid) + ival)
            ret = g_WSInfo.updateSet(tid, sid)
            self.outputLog(ret)
            if ret.retCode < 0:
                return

        # グリッド表示更新
        grid.ResetCurrentView()
        
        # 使用メモリ
        #self.updateUsedMemory()
        return

    ## 行削除 --------------------------------------------------------------------------------------
    def OnMenuItemDeleteRow(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)

        # 操作対象テーブルチェック
        if g_WSInfo.getCountJoinRef(tid) > 0: # JOIN参照されているテーブル
            Dlg = wx.MessageDialog(self, u"このテーブルはJoinで参照されています。\n操作の対象にできません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        if self.selectAll == True:
            # すべて選択
            self.selectAll = False
            startRow = 1
            lines = grid.GetSelectionAllBottomRow()
        else:
            selrows = grid.GetSelectedRows()
            startRow = selrows[0]
            lines = len(selrows)

        # DBからの行削除
        ret = MDeleteRow(g_WSInfo.getTableName(tid), startRow, lines, sid)
        self.outputLog(ret)
        if ret.retCode < 0:
            return

        # 情報更新
        g_WSInfo.setCountRow(tid, g_WSInfo.getCountRow(tid) - lines)
        ret = g_WSInfo.updateSet(tid, sid)
        self.outputLog(ret)
        if ret.retCode < 0:
            return

        g_WSTree.updateSetSizeAll(tid)

        # グリッド表示更新
        grid.ResetCurrentView()

        # 使用メモリ
        self.updateUsedMemory()
        return

    ## 列幅変更 ------------------------------------------------------------------------------------
    def OnMenuItemColumnWidth(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)

        cols = grid.GetSelectedCols()
        if len(cols) < 1: # 列が選択されていない
            return

        # 選択されている各列の現在幅取得
        listColSize = []
        for col in cols:
            listColSize.append(grid.grid.GetColSize(col))
        # 列幅入力
        Dlg = wx.TextEntryDialog(self, u"列幅：", u"列幅入力", defaultValue=str(max(listColSize))) 
        AnsBtn = Dlg.ShowModal()
        AnsTxt = Dlg.GetValue()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return
        try:
            colSize = int(AnsTxt)
        except:
            return

        # 選択されている全ての列に適用
        
        for col in cols:
            grid.grid.SetColSize(col, colSize)
            
        # グリッド表示更新
        grid.ResetCurrentView()
        return

    ## 項目移動 ------------------------------------------------------------------------------------
    def OnMenuItemMoveColumn(self, event):
        # 項目名変更
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)

        if g_WSInfo.isJoinTable(tid) or (g_WSInfo.getCountJoinRef(tid) > 0):
            return

        cols = grid.GetSelectedCols()
        if 0 in cols:
            cols.remove(0) # RecNo列除外
        if len(cols) < 1: # 列が選択されていない
            return
        fltName = grid.GetColLabelValue(min(cols)) # 一番左のラベル名→入力初期値
        tableName = g_WSInfo.getTableName(tid)
        listFilterName = g_WSInfo.getFilterNameList(tid)
        idxSrc = listFilterName.index(fltName)

        Dlg = wx.TextEntryDialog(self, u"移動先(Index)：", u"項目移動", defaultValue=str(idxSrc + 1)) 
        AnsBtn = Dlg.ShowModal()
        idxStr = Dlg.GetValue()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        try:
            idx = int(idxStr)
        except:
            return
        idx -= 1
        nFilter = len(listFilterName)
        if idx < 0:
            idx = 0
        elif idx >= nFilter:
            idx = nFilter - 1
        dstFltName = listFilterName[idx]

        ret = MMoveFilter(tableName, [fltName], dstFltName)
        self.outputLog(ret)
        if ret.retCode < 0:
            return

        # グリッド列移動
        listFilter = g_WSInfo.getFilterList(tid)
        fid = listFilter[idxSrc]
        listFilter.remove(fid)
        listFilter.insert(idx, fid)

        # グリッド表示更新
        self.ResetView()
        return

    ## 項目複製 ------------------------------------------------------------------------------------
    def OnMenuItemCopyColumn(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)
        
        cols = grid.GetSelectedCols()
        if 0 in cols:
            cols.remove(0) # RecNo列除外
        if len(cols) < 1: # 列が選択されていない
            return

        # 選択されている全ての列に適用
        tableName = g_WSInfo.getTableName(tid)
        listFilter = g_WSInfo.getFilterList(tid)
        for i, col in enumerate(cols):
            fltName = g_WSInfo.getFilterName(tid, listFilter[col-1+i])
            ret = MDuplFilter(tableName, fltName)
            self.outputLog(ret)
            if ret.retCode < 0:
                return
            fid = ret.retCode

            # 項目情報更新
            ret = g_WSInfo.appendFilter(tid, fid, col+i)
            self.outputLog(ret)

            # グリッドに挿入
            #grid.grid.InsertCols(pos=col+1+i, numCols=1)
            #grid.grid.SetColLabelValue(col+1+i, g_WSInfo.getFilterName(tid, fid))

            # グリッドデータ
            setSize = g_WSInfo.getSetSize(tid, sid)
            
            # グリッド表示更新
            self.ResetView()
            
        # 使用メモリ
        self.updateUsedMemory()
        return

    ## 型変換複製 ----------------------------------------------------------------------------------
    def OnMenuItemConvTypeColumn(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)

        cols = grid.GetSelectedCols()
        if 0 in cols:
            cols.remove(0) # RecNo列除外
        if len(cols) < 1: # 列が選択されていない
            return

        # 項目情報入力
        Dlg = MyDialogFilterCreate(self, inputName=False, inputFile=False)
        AnsBtn = Dlg.ShowModal()
        name      = Dlg.getName()
        scale     = Dlg.getScale()
        type      = Dlg.getType()
        typeC     = MAP_DATA_TYPE_NC[type]
        roundmode = Dlg.getRoundMode()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        # 選択されている全ての列に適用
        tableName = g_WSInfo.getTableName(tid)
        listFilter = g_WSInfo.getFilterList(tid)
        for i, col in enumerate(cols):
            fltName = g_WSInfo.getFilterName(tid, listFilter[col-1+i])
            if type == lfmtblpy.D5_DT_DECIMAL:
                ret = MTypeConvNumeric(tableName, fltName, scale, roundmode)
            else:
                ret = MTypeConv(tableName, fltName, typeC)
            self.outputLog(ret)
            if ret.retCode < 0:
                return
            fid = ret.retCode

            # 項目情報更新
            ret = g_WSInfo.appendFilter(tid, fid, col+i)
            self.outputLog(ret)

            # グリッドに挿入
            #grid.InsertCols(pos=col+1+i, numCols=1)
            #grid.SetColLabelValue(col+1+i, g_WSInfo.getFilterName(tid, fid))

            # グリッドデータ
            #setSize = g_WSInfo.getSetSize(tid, sid)
            #self.setGridDataFilter(grid, tid, sid, fid, setSize, col+1+i, bInit=True)
            
            #grid.AutoSizeColumn(col+1+i)

        # グリッド表示更新
        self.ResetView()
        
        # 使用メモリ
        self.updateUsedMemory()
        return

    ## 項目挿入 ------------------------------------------------------------------------------------
    def OnMenuItemInsertColumn(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)

        # 選択範囲取得
        rowcol = grid.GetExSelectedRowsCols()
        cols = grid.GetSelectedCols()
        lenCols = len(cols)

        if self.selectAll == True:
            self.selectAll = False
            startCol = topLeft[0][1]
            endCol   = bottomRight[0][1]
        else:
            startCol = rowcol[2]
            endCol   = rowcol[3]
        lenCols = endCol - startCol + 1

        # 新項目情報入力ダイアログ
        Dlg = MyDialogFilterCreate(self)
        AnsBtn = Dlg.ShowModal()
        name      = Dlg.getName()
        scale     = Dlg.getScale()
        type      = Dlg.getType()
        typeC     = MAP_DATA_TYPE_NC[type]
        roundmode = Dlg.getRoundMode()
        filePath  = Dlg.getFilePath()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        eventId = event.GetId()
        if eventId in (xrc.XRCID("MenuItemInsertColumn"), xrc.XRCID("PMenuItemInsertColumn")): # insert
            startCol -= 1

        # 位置
        if startCol < 1:
            startCol = 0
            posFilName = ""
        else:
            listFilter = g_WSInfo.getFilterList(tid)
            posFid = listFilter[startCol - 1]
            posFilName = g_WSInfo.getFilterName(tid, posFid)

        # ファイル
        Fpath = os.path.dirname(filePath)
        Fname = os.path.basename(filePath)

        if type == lfmtblpy.D5_DT_DECIMAL:
            ret = MAddRealFilterNumeric(g_WSInfo.getTableName(tid), posFilName, name, typeC, scale, roundmode, Fpath, Fname)
        else:
            ret = MAddRealFilter(g_WSInfo.getTableName(tid), posFilName, name, typeC, Fpath, Fname)
        self.outputLog(ret)
        if ret.retCode < 0:
            return
        fid = ret.retCode

        # 項目情報更新
        ret = g_WSInfo.appendFilter(tid, fid, startCol)
        self.outputLog(ret)

        # グリッドに挿入
        #grid.InsertCols(pos=startCol+1, numCols=1)
        #grid.SetColLabelValue(startCol+1, g_WSInfo.getFilterName(tid, fid))

        # グリッドデータ
        #setSize = g_WSInfo.getSetSize(tid, sid)
        #self.setGridDataFilter(grid, tid, sid, fid, setSize, startCol+1, bInit=True)

        # グリッド表示更新
        self.ResetView()

        # 使用メモリ
        self.updateUsedMemory()
        return

    ## 項目削除 ------------------------------------------------------------------------------------
    def OnMenuItemDeleteColumn(self, event):
        if self.datatab.GetPageCount() < 1: # グリッドなし
            Dlg = wx.MessageDialog(self, u"操作対象のテーブルが開かれていません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        idxPage = self.datatab.GetSelection()
        grid = g_WSTree.listGrid[idxPage]
        (tid, sid) = g_WSTree.getTidSidFromGrid(grid)

        startCol = -1
        cols = grid.GetSelectedCols()
        if 0 in cols:
            cols.remove(0) # RecNo列除外
        lenCols = len(cols)
        if lenCols > 0: # 列選択あり
            startCol = min(cols)

        if startCol < 1: # RecNo列は消せない
            return

        # 項目削除
        tableName = g_WSInfo.getTableName(tid)
        listFilter = g_WSInfo.getFilterList(tid)
        if lenCols == 1:
            fid = listFilter[startCol - 1]
            ret = MDelFilter(tableName, g_WSInfo.getFilterName(tid, fid))
            self.outputLog(ret)
            if ret.retCode < 0:
                return
            g_WSInfo.deleteFilter(tid, fid) # 項目情報削除
        else: # 複数
            listDelFilter = []
            listDelFilterName = []
            cols.sort() # 昇順にしておく
            for col in cols:
                fid = listFilter[col - 1]
                listDelFilter.append(fid)
                listDelFilterName.append(g_WSInfo.getFilterName(tid, fid))
            ret = MMultiDelFilter(tableName, listDelFilterName)
            self.outputLog(ret)
            if ret.retCode < 0:
                return
            for fid, col in reversed(zip(listDelFilter, cols)): # 降順(後ろから)
                g_WSInfo.deleteFilter(tid, fid) # 項目情報削除


        # 項目名再設定
        #listFilter2 = listFilter[(startCol - 1):] # 削除列以降
        #for i, fid in enumerate(listFilter2):
        #   grid.SetColLabelValue(startCol + i, g_WSInfo.getFilterName(tid, fid), g_WSInfo.getFilterType(tid, fid))

        # グリッド表示更新
        self.ResetView()

        # 使用メモリ
        self.updateUsedMemory()

        return

    ## コンデンス ----------------------------------------------------------------------------------
    def condenseTable(self, tid):
        # 操作対象テーブルチェック
        if tid <= 0:
            Dlg = wx.MessageDialog(self, u"この操作は実行できません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        if g_WSInfo.isJoinTable(tid):
            Dlg = wx.MessageDialog(self, u"Joinテーブルはコンデンスできません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return
        if g_WSInfo.getCountJoinRef(tid) > 0:
            Dlg = wx.MessageDialog(self, u"このテーブルはJoinで参照されています。\n操作の対象にできません。", u"エラー", wx.OK | wx.ICON_ERROR)
            Dlg.ShowModal()
            return

        ret = MCondense(g_WSInfo.getTableName(tid))
        self.outputLog(ret)
        return

    def OnMenuItemCondense(self, event):
        self.condenseTable(g_WSTree.curTID)

        # 使用メモリ
        self.updateUsedMemory()
        return

    def OnMenuItemCondenseAll(self, event):
        for tid in g_WSInfo.getTableList():
            self.condenseTable(tid)

        # 使用メモリ
        self.updateUsedMemory()
        return

    ## バージョン情報 ------------------------------------------------------------------------------
    def OnMenuItemAbout(self, event):
        # 情報設定
        infoAbout = wx.AboutDialogInfo()
        infoAbout.Name = ABOUT_NAME
        infoAbout.Version = ABOUT_VERSION
        infoAbout.Copyright = ABOUT_COPYRIGHT
        infoAbout.SetIcon(wx.Icon(ICON_MAIN_FRAME, wx.BITMAP_TYPE_GIF))

        # 表示
        wx.AboutBox(infoAbout)
        return

    def OnMenuItemLicenseUpdate(self, event):
        # ライセンスキー入力
        licensekey= getLicense()
        Dlg = wx.TextEntryDialog(self, u"ライセンスキ:", u"ライセンスキ入力", defaultValue=licensekey)
        AnsBtn = Dlg.ShowModal()
        licensekey = Dlg.GetValue()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return
            
        password = "ENGINE="
        password += licensekey
        file=open("LFM_Server.pwd", 'w')
        file.write(password)
        file.close()
        return
# --------------------------------------------------------------------------------------------------
class OutputLogThread(threading.Thread):
    def __init__(self, ctrl, queue):
        threading.Thread.__init__(self)
        self.ctrl = ctrl
        self.queue = queue
        return

    def run(self):
        THREAD_WAIT_TIME = 5
        while True:
            try:
                msgs = self.queue.get(THREAD_WAIT_TIME)
                if msgs == None:
                    break
            except Empty:
                continue
            except:
                break

            self.ctrl.SetInsertionPointEnd()
            for msg in msgs:
                self.ctrl.WriteText(msg)
        return

    def stop(self):
        self.queue.put(None)
        return

# ダイアログ ---------------------------------------------------------------------------------------
## OK/CANCELボタン追加
def addButtonOkCancel(dlg):
    sizer = dlg.GetSizer()
    btnsizer = wx.StdDialogButtonSizer()

    btn = wx.Button(dlg, wx.ID_OK)
    dlg.buttonOK = btn
    btnsizer.AddButton(btn)
    btn.SetDefault()

    btn = wx.Button(dlg, wx.ID_CANCEL)
    dlg.buttonCancel = btn
    btnsizer.AddButton(btn)

    btnsizer.Realize()
    sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)
    return

## 選択アイテム設定 --------------------------------------------------------------------------------
def setChoiseList(ctrl, list, select=0):
    ctrl.Clear()
    if len(list) < 1:
        return
    for i, v in enumerate(list):
        ctrl.Insert(unicode(v), i)
    if select >= 0:
        ctrl.SetSelection(select)
    return

# --------------------------------------------------------------------------------------------------
class MyDialogTableCreate(wx.Dialog):
    def __init__(self, frame):
        pre = wx.PreDialog()
        frame.app.res.LoadOnDialog(pre, frame, "DialogTableCreate")
        self.PostCreate(pre)
        addButtonOkCancel(self) # OK/CANCELボタン
        return

# --------------------------------------------------------------------------------------------------
class MyDialogFilterCreate(wx.Dialog):
    def __init__(self, frame, inputName=True, inputFile=True):
        pre = wx.PreDialog()
        frame.app.res.LoadOnDialog(pre, frame, "DialogFilterCreate")
        self.PostCreate(pre)
        addButtonOkCancel(self) # OK/CANCELボタン

        # event
        panelType = xrc.XRCCTRL(self, "PanelFilterCreateType")
        panelType.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButtonFilterCreateType)
        self.Bind(wx.EVT_BUTTON, self.OnButtonFilterCreateFile, id=xrc.XRCID("ButtonFilterCreateFile"))

        # NameとFileの入力有効設定
        xrc.XRCCTRL(self, "TextCtrlFilterCreateName").Enable(inputName)
        xrc.XRCCTRL(self, "PanelFilterCreateFile").Enable(inputFile)

        # ScaleとRoundModeを無効化
        xrc.XRCCTRL(self, "ChoiceFilterCreateScale").Enable(False)
        xrc.XRCCTRL(self, "PanelFilterCreateRMode").Enable(False)
        return

    def OnRadioButtonFilterCreateType(self, event):
        # Numeric選択時のみScaleとRoundModeを有効化
        if event.GetId() == xrc.XRCID("RadioButtonFilterCreateTypeNumeric"):
            xrc.XRCCTRL(self, "ChoiceFilterCreateScale").Enable(True)
            xrc.XRCCTRL(self, "PanelFilterCreateRMode").Enable(True)
        else:
            xrc.XRCCTRL(self, "ChoiceFilterCreateScale").Enable(False)
            xrc.XRCCTRL(self, "PanelFilterCreateRMode").Enable(False)
        return

    def OnButtonFilterCreateFile(self, event):
        global g_CurPath
        Dlg = wx.FileDialog(self, message=u"出力ファイル選択", defaultDir=g_CurPath, defaultFile="",
                            wildcard = "Text File (*.txt)|*.txt|CSV File (*.csv)|*.csv|All (*.*)|*.*")
        AnsBtn = Dlg.ShowModal()
        AnsFilename = Dlg.GetFilename()
        AnsFilePath = Dlg.GetPath()
        AnsDirPath = Dlg.GetDirectory()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return
        g_CurPath = AnsDirPath

        ctrlFilepath = xrc.XRCCTRL(self, "TextCtrlFilterCreateFile")
        ctrlFilepath.SetValue(AnsFilePath)
        return

    def getFilePath(self):
        retval = xrc.XRCCTRL(self, "TextCtrlFilterCreateFile").GetValue()
        return retval

    def getName(self):
        retval = xrc.XRCCTRL(self, "TextCtrlFilterCreateName").GetValue()
        return retval

    def getScale(self):
        retval = xrc.XRCCTRL(self, "ChoiceFilterCreateScale").GetCurrentSelection()
        return retval

    def getType(self):
        if   xrc.XRCCTRL(self, "RadioButtonFilterCreateTypeInt").GetValue():
            retval = lfmtblpy.D5_DT_INTEGER
        elif xrc.XRCCTRL(self, "RadioButtonFilterCreateTypeDbl").GetValue():
            retval = lfmtblpy.D5_DT_DOUBLE
        elif xrc.XRCCTRL(self, "RadioButtonFilterCreateTypeDate").GetValue():
            retval = lfmtblpy.D5_DT_DATE
        elif xrc.XRCCTRL(self, "RadioButtonFilterCreateTypeTime").GetValue():
            retval = lfmtblpy.D5_DT_TIME
        elif xrc.XRCCTRL(self, "RadioButtonFilterCreateTypeDateTime").GetValue():
            retval = lfmtblpy.D5_DT_DATETIME
        elif xrc.XRCCTRL(self, "RadioButtonFilterCreateTypeString").GetValue():
            retval = lfmtblpy.D5_DT_STRING
        elif xrc.XRCCTRL(self, "RadioButtonFilterCreateTypeNumeric").GetValue():
            retval = lfmtblpy.D5_DT_DECIMAL
        else:
            retval = -1
        return retval

    def getRoundMode(self):
        if   xrc.XRCCTRL(self, "RadioButtonFilterCreateRModeUp").GetValue():
            retval = MAP_ROUND_MODE["ROUND_UP"]
        elif xrc.XRCCTRL(self, "RadioButtonFilterCreateRModeDown").GetValue():
            retval = MAP_ROUND_MODE["ROUND_DOWN"]
        elif xrc.XRCCTRL(self, "RadioButtonFilterCreateRModeCeiling").GetValue():
            retval = MAP_ROUND_MODE["ROUND_CEILING"]
        elif xrc.XRCCTRL(self, "RadioButtonFilterCreateRModeFloor").GetValue():
            retval = MAP_ROUND_MODE["ROUND_FLOOR"]
        elif xrc.XRCCTRL(self, "RadioButtonFilterCreateRModeHUp").GetValue():
            retval = MAP_ROUND_MODE["ROUND_HALF_UP"]
        elif xrc.XRCCTRL(self, "RadioButtonFilterCreateRModeHDown").GetValue():
            retval = MAP_ROUND_MODE["ROUND_HALF_DOWN"]
        elif xrc.XRCCTRL(self, "RadioButtonFilterCreateRModeHEven").GetValue():
            retval = MAP_ROUND_MODE["ROUND_HALF_EVEN"]
        else:
            retval = -1
        return retval


# --------------------------------------------------------------------------------------------------
class MyDialogSetOp(wx.Dialog):
    def __init__(self, frame, tableName="", listSet=[]):
        pre = wx.PreDialog()
        frame.app.res.LoadOnDialog(pre, frame, "DialogSetOp")
        self.PostCreate(pre)
        addButtonOkCancel(self) # OK/CANCELボタン

        choiceTbl = xrc.XRCCTRL(self, "ChoiceSetOpArgTable")
        choiceTbl.Insert(tableName, 0)

        choiceTgt = xrc.XRCCTRL(self, "ChoiceSetOpArgTarget")
        for i, v in enumerate(listSet):
            choiceTgt.Insert(str(listSet[i]), i)

        choiceSrc = xrc.XRCCTRL(self, "ChoiceSetOpArgSource")
        for i, v in enumerate(listSet):
            choiceSrc.Insert(str(listSet[i]), i)

        # event
        self.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButtonSetOpOp)

        choiceTbl.SetSelection(0)
        choiceTgt.SetSelection(0)
        choiceSrc.SetSelection(0)
        choiceSrc.Enable(True)

        self.listSet = listSet
        return

    def OnRadioButtonSetOpOp(self, event):
        # NOT選択時だけTagetを無効化
        if event.GetId() == xrc.XRCID("RadioButtonSetOpOpNot"):
            xrc.XRCCTRL(self, "ChoiceSetOpArgTarget").Enable(False)
        else:
            xrc.XRCCTRL(self, "ChoiceSetOpArgTarget").Enable(True)
        return

    def getSetOp(self):
        if   xrc.XRCCTRL(self, "RadioButtonSetOpOpAnd").GetValue():
            retval = lfmtblpy.D5_SETOPE_AND
        elif xrc.XRCCTRL(self, "RadioButtonSetOpOpOr").GetValue():
            retval = lfmtblpy.D5_SETOPE_OR
        elif xrc.XRCCTRL(self, "RadioButtonSetOpOpSub").GetValue():
            retval = lfmtblpy.D5_SETOPE_SUB
        else:
            retval = -1
        return retval

    def getTargetSetId(self):
        idx = xrc.XRCCTRL(self, "ChoiceSetOpArgTarget").GetSelection()
        sid = self.listSet[idx]
        return sid

    def getSourceSetId(self):
        idx = xrc.XRCCTRL(self, "ChoiceSetOpArgSource").GetSelection()
        sid = self.listSet[idx]
        return sid


# --------------------------------------------------------------------------------------------------
class MyDialogSearch(wx.Dialog):
    def __init__(self, frame, fltName, fltType):
        self.fltName = fltName
        self.fltType = fltType

        pre = wx.PreDialog()
        frame.app.res.LoadOnDialog(pre, frame, "DialogSearch")
        self.PostCreate(pre)
        addButtonOkCancel(self) # OK/CANCELボタン

        if fltType == lfmtblpy.D5_DT_STRING:
            xrc.XRCCTRL(self, "RadioButtonSearchOpNull").Enable(False)
            xrc.XRCCTRL(self, "RadioButtonSearchOpNotNull").Enable(False)
            xrc.XRCCTRL(self, "RadioButtonSearchOpWCL").Enable(True)
            xrc.XRCCTRL(self, "RadioButtonSearchOpWCM").Enable(True)
            xrc.XRCCTRL(self, "RadioButtonSearchOpWCR").Enable(True)

        # event
        self.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButtonSearchOp)

        return

    def OnRadioButtonSearchOp(self, event):
        eventId = event.GetId()
        if   eventId in (xrc.XRCID("RadioButtonSearchOpNull"), xrc.XRCID("RadioButtonSearchOpNotNull")):
            xrc.XRCCTRL(self, "TextCtrlSearchVal1").Enable(False)
            xrc.XRCCTRL(self, "TextCtrlSearchVal2").Enable(False)
        elif eventId in (xrc.XRCID("RadioButtonSearchOpBW"), xrc.XRCID("RadioButtonSearchOpWI")):
            xrc.XRCCTRL(self, "TextCtrlSearchVal1").Enable(True)
            xrc.XRCCTRL(self, "TextCtrlSearchVal2").Enable(True)
        else:
            xrc.XRCCTRL(self, "TextCtrlSearchVal1").Enable(True)
            xrc.XRCCTRL(self, "TextCtrlSearchVal2").Enable(False)
        return

    def getSearchOpString(self):
        val1 = xrc.XRCCTRL(self, "TextCtrlSearchVal1").GetValue()
        val2 = xrc.XRCCTRL(self, "TextCtrlSearchVal2").GetValue()
        if self.fltType in LIST_NUM_TYPE: # 数値
            strVal1 = val1
            strVal2 = val2
        else:
            strVal1 = "'" + val1 + "'"
            strVal2 = "'" + val2 + "'"

        if   xrc.XRCCTRL(self, "RadioButtonSearchOpNull").GetValue():
            retval = "%s IS NULL" % self.fltName
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpNotNull").GetValue():
            retval = "%s IS NOT NULL" % self.fltName
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpEQ").GetValue():
            retval = "%s = %s" % (self.fltName, strVal1)
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpNE").GetValue():
            retval = "%s <> %s" % (self.fltName, strVal1)
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpLE").GetValue():
            retval = "%s <= %s" % (self.fltName, strVal1)
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpME").GetValue():
            retval = "%s >= %s" % (self.fltName, strVal1)
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpLT").GetValue():
            retval = "%s < %s" % (self.fltName, strVal1)
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpMT").GetValue():
            retval = "%s > %s" % (self.fltName, strVal1)
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpBW").GetValue():
            retval = "%s BETWEEN %s AND %s" % (self.fltName, strVal1, strVal2)
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpWI").GetValue():
            retval = "%s WITHIN %s AND %s" % (self.fltName, strVal1, strVal2)
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpWCL").GetValue():
            retval = "%s*" % val1.replace(SEARCH_SYMBOL, SEARCH_ESCAPE + SEARCH_SYMBOL)
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpWCM").GetValue():
            retval = "*%s*" % val1.replace(SEARCH_SYMBOL, SEARCH_ESCAPE + SEARCH_SYMBOL)
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpWCR").GetValue():
            retval = "*%s" % val1.replace(SEARCH_SYMBOL, SEARCH_ESCAPE + SEARCH_SYMBOL)
        else:
            retval = ""

        return retval

    def getOpeType(self):
        if   xrc.XRCCTRL(self, "RadioButtonSearchOpNull").GetValue():
            retval = lfmtblpy.D5_OPETYPE_EQUAL
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpNotNull").GetValue():
            retval = lfmtblpy.D5_OPETYPE_NOTEQUAL
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpEQ").GetValue():
            retval = lfmtblpy.D5_OPETYPE_EQUAL
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpNE").GetValue():
            retval = lfmtblpy.D5_OPETYPE_NOTEQUAL
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpLE").GetValue():
            retval = lfmtblpy.D5_OPETYPE_LESSEQUAL
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpME").GetValue():
            retval = lfmtblpy.D5_OPETYPE_GREATEREQUAL
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpLT").GetValue():
            retval = lfmtblpy.D5_OPETYPE_LESS
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpMT").GetValue():
            retval = lfmtblpy.D5_OPETYPE_GREATER
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpBW").GetValue():
            retval = lfmtblpy.D5_OPETYPE_BETWEEN
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpWI").GetValue():
            retval = lfmtblpy.D5_OPETYPE_WITHIN
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpWCL").GetValue():
            retval = lfmtblpy.D5_OPETYPE_STR_LEFT
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpWCM").GetValue():
            retval = lfmtblpy.D5_OPETYPE_STR_MID
        elif xrc.XRCCTRL(self, "RadioButtonSearchOpWCR").GetValue():
            retval = lfmtblpy.D5_OPETYPE_STR_RIGHT
        else:
            retval = -1

        return retval

    def getVal1(self):
        if (xrc.XRCCTRL(self, "RadioButtonSearchOpNull").GetValue()) \
            or (xrc.XRCCTRL(self, "RadioButtonSearchOpNotNull").GetValue()):
            retval = ""
        else:
            retval = xrc.XRCCTRL(self, "TextCtrlSearchVal1").GetValue()
        return retval

    def getVal2(self):
        if (xrc.XRCCTRL(self, "RadioButtonSearchOpNull").GetValue()) \
            or (xrc.XRCCTRL(self, "RadioButtonSearchOpNotNull").GetValue()):
            retval = ""
        else:
            retval = xrc.XRCCTRL(self, "TextCtrlSearchVal2").GetValue()
        return retval


# --------------------------------------------------------------------------------------------------
class MyDialogExUnique(wx.Dialog):
    def __init__(self, frame, sid, listSet, listFilterName):
        self.listSet = listSet
        self.listFilterName = listFilterName

        pre = wx.PreDialog()
        frame.app.res.LoadOnDialog(pre, frame, "DialogExUnique")
        self.PostCreate(pre)

        # 項目チェックリストボックス
        panel = xrc.XRCCTRL(self, "PanelExUnique")
        self.checkListBoxFilter = wx.CheckListBox(panel, -1, (-1, 100), wx.DefaultSize, listFilterName)
        sizer = panel.GetSizer()
        sizer.Add(self.checkListBoxFilter, 0, wx.ALIGN_LEFT|wx.EXPAND , 0)

        addButtonOkCancel(self) # OK/CANCELボタン

        self.choiceSet = xrc.XRCCTRL(self, "ChoiceExUniqueSet")
        for i, v in enumerate(listSet):
            self.choiceSet.Insert(str(listSet[i]), i)
        if sid < 1:
            self.choiceSet.SetSelection(0)
        else:
            self.choiceSet.SetSelection(listSet.index(sid))

        # event
        self.Bind(wx.EVT_BUTTON, self.OnButtonExUniqueSelectAll, id=xrc.XRCID("ButtonExUniqueSelectAll"))

        return

    def getSetId(self):
        idx = xrc.XRCCTRL(self, "ChoiceExUniqueSet").GetSelection()
        sid = self.listSet[idx]
        return sid

    def isKeepOrder(self):
        return xrc.XRCCTRL(self, "CheckBoxExUniqueOrder").GetValue()

    def OnButtonExUniqueSelectAll(self, event):
        # 全選択されていたら全解除
        bFlag = False
        for i, name in enumerate(self.listFilterName):
            if not self.checkListBoxFilter.IsChecked(i):
                bFlag = True # 1つでも選択されていなかったら全選択
                break

        for i, name in enumerate(self.listFilterName):
            self.checkListBoxFilter.Check(i, bFlag)
        return

    def getSelectFilterNameList(self):
        listSelectFilterName = []
        for i, name in enumerate(self.listFilterName):
            if self.checkListBoxFilter.IsChecked(i):
                listSelectFilterName.append(name)
        return listSelectFilterName


# --------------------------------------------------------------------------------------------------
class MyDialogJoinRealize(wx.Dialog):
    def __init__(self, frame, tableName, sid, listSet, listFilterName):
        self.tableName = tableName
        self.listSet = listSet
        self.listFilterName = listFilterName

        pre = wx.PreDialog()
        frame.app.res.LoadOnDialog(pre, frame, "DialogJoinRealize")
        self.PostCreate(pre)

        # 項目チェックリストボックス
        panel = xrc.XRCCTRL(self, "PanelJoinRealize")
        self.checkListBoxFilter = wx.CheckListBox(panel, -1, (-1, 100), wx.DefaultSize, listFilterName)
        sizer = panel.GetSizer()
        sizer.Add(self.checkListBoxFilter, 0, wx.ALIGN_LEFT|wx.EXPAND , 0)

        addButtonOkCancel(self) # OK/CANCELボタン

        xrc.XRCCTRL(self, "TextCtrlJoinRealizeTable").SetValue(tableName)

        self.choiceSet = xrc.XRCCTRL(self, "ChoiceJoinRealizeSet")
        for i, v in enumerate(listSet):
            self.choiceSet.Insert(str(listSet[i]), i)
        if sid < 1:
            self.choiceSet.SetSelection(0)
        else:
            self.choiceSet.SetSelection(listSet.index(sid))

        # event
        self.Bind(wx.EVT_BUTTON, self.OnButtonJoinRealizeSelectAll, id=xrc.XRCID("ButtonJoinRealizeSelectAll"))

        return

    def getTableName(self):
        return xrc.XRCCTRL(self, "TextCtrlJoinRealizeTable").GetValue()

    def getSetId(self):
        idx = xrc.XRCCTRL(self, "ChoiceJoinRealizeSet").GetSelection()
        sid = self.listSet[idx]
        return sid

    def isMaster(self):
        return xrc.XRCCTRL(self, "CheckBoxJoinRealizeMaster").GetValue()

    def isSlave(self):
        return xrc.XRCCTRL(self, "CheckBoxJoinRealizeSlave").GetValue()

    def OnButtonJoinRealizeSelectAll(self, event):
        # 全選択されていたら全解除
        bFlag = False
        for i, name in enumerate(self.listFilterName):
            if not self.checkListBoxFilter.IsChecked(i):
                bFlag = True # 1つでも選択されていなかったら全選択
                break

        for i, name in enumerate(self.listFilterName):
            self.checkListBoxFilter.Check(i, bFlag)
        return

    def getSelectFilterNameList(self):
        listSelectFilterName = []
        for i, name in enumerate(self.listFilterName):
            if self.checkListBoxFilter.IsChecked(i):
                listSelectFilterName.append(name)
        return listSelectFilterName


# --------------------------------------------------------------------------------------------------
class MyDialogJoin(wx.Dialog):
    def __init__(self, frame, tid, tableNameJoin, WSTree):
        self.frame = frame
        self.MasterTID = tid
        self.SlaveTID  = tid
        self.WSTree = WSTree
        self.WSInfo = WSTree.WSInfo

        pre = wx.PreDialog()
        frame.app.res.LoadOnDialog(pre, frame, "DialogJoin")
        self.PostCreate(pre)
        addButtonOkCancel(self) # OK/CANCELボタン

        self.textCtrlNewTable = xrc.XRCCTRL(self, "TextCtrlJoinTable")
        self.buttonKeySet = xrc.XRCCTRL(self, "ButtonJoinKeySet")
        self.buttonKeyUnset = xrc.XRCCTRL(self, "ButtonJoinKeyUnset")
        self.choiceMasterTable = xrc.XRCCTRL(self, "ChoiceJoinMasterTable")
        self.choiceSlaveTable = xrc.XRCCTRL(self, "ChoiceJoinSlaveTable")
        self.choiceMasterSet = xrc.XRCCTRL(self, "ChoiceJoinMasterSet")
        self.choiceSlaveSet = xrc.XRCCTRL(self, "ChoiceJoinSlaveSet")
        self.listCtrlMasterFilter = xrc.XRCCTRL(self, "ListCtrlJoinMasterFilter")
        self.listCtrlSlaveFilter = xrc.XRCCTRL(self, "ListCtrlJoinSlaveFilter")
        self.listCtrlMasterKey = xrc.XRCCTRL(self, "ListCtrlJoinMasterKey")
        self.listCtrlSlaveKey = xrc.XRCCTRL(self, "ListCtrlJoinSlaveKey")

        self.textCtrlNewTable.SetValue(tableNameJoin)
        self.buttonKeySet.Enable(False)
        self.buttonOK.Enable(False)

        # 項目リスト
        self.listCtrlMasterFilter.InsertColumn(0, TITLE_ID)
        self.listCtrlMasterFilter.InsertColumn(1, TITLE_TYPE)
        self.listCtrlMasterFilter.InsertColumn(2, TITLE_FILTER_NAME)
        self.listCtrlSlaveFilter.InsertColumn(0, TITLE_ID)
        self.listCtrlSlaveFilter.InsertColumn(1, TITLE_TYPE)
        self.listCtrlSlaveFilter.InsertColumn(2, TITLE_FILTER_NAME)

        # JOINキーリスト
        self.listCtrlMasterKey.InsertColumn(0, TITLE_ID)
        self.listCtrlMasterKey.InsertColumn(1, TITLE_TYPE)
        self.listCtrlMasterKey.InsertColumn(2, TITLE_FILTER_NAME)
        self.listCtrlSlaveKey.InsertColumn(0, TITLE_ID)
        self.listCtrlSlaveKey.InsertColumn(1, TITLE_TYPE)
        self.listCtrlSlaveKey.InsertColumn(2, TITLE_FILTER_NAME)

        # テーブル情報設定
        listTable = self.WSInfo.getRealTableList()
        listTableName = self.WSInfo.getRealTableNameList()
        setChoiseList(self.choiceMasterTable, listTableName)
        setChoiseList(self.choiceSlaveTable,  listTableName)
        idxTid = listTable.index(tid)
        self.choiceMasterTable.SetSelection(idxTid)
        self.choiceSlaveTable.SetSelection(idxTid)

        # セット情報設定
        self.setTableInfo(tid, self.choiceMasterSet, self.listCtrlMasterFilter)
        self.setTableInfo(tid, self.choiceSlaveSet,  self.listCtrlSlaveFilter)

        # リスト列リサイズ
        self.listCtrlMasterFilter.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlMasterFilter.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlMasterFilter.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlSlaveFilter.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlSlaveFilter.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlSlaveFilter.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlMasterKey.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlMasterKey.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlMasterKey.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlSlaveKey.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlSlaveKey.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlSlaveKey.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)

        # event
        self.Bind(wx.EVT_CHOICE, self.OnChoiceTable, self.choiceMasterTable)
        self.Bind(wx.EVT_CHOICE, self.OnChoiceTable, self.choiceSlaveTable)
        self.Bind(wx.EVT_BUTTON, self.OnButtonKeySet, self.buttonKeySet)
        self.Bind(wx.EVT_BUTTON, self.OnButtonKeyUnset, self.buttonKeyUnset)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnFilterSelect, self.listCtrlMasterFilter)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnFilterSelect, self.listCtrlSlaveFilter)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnFilterDeselect, self.listCtrlMasterFilter)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnFilterDeselect, self.listCtrlSlaveFilter)

        return

    ## 項目情報をリストコントロールに設定 ----------------------------------------------------------
    def setListCtrlFilter(self, ctrl, listFilter, listFilterType, listFilterName):
        ctrl.DeleteAllItems()
        if len(listFilter) < 1:
            return
        for i, id in enumerate(listFilter):
            ctrl.InsertStringItem(i, str(id))
            ctrl.SetStringItem(i, 1, MAP_DATA_TYPE_NC[listFilterType[i]])
            ctrl.SetStringItem(i, 2, listFilterName[i])
        return

    ## テーブル情報設定 ----------------------------------------------------------------------------
    def setTableInfo(self, tid, choiceSet, listCtrlFilter):
        ret = self.frame.checkOpenTable(tid) # テーブルが開いていなかったら開く
        if ret < 0:
            return

        listSet = self.WSInfo.getSetList(tid)
        setChoiseList(choiceSet, listSet)

        listFilter = self.WSInfo.getFilterList(tid)
        listFilterType = self.WSInfo.getFilterTypeList(tid)
        listFilterName = self.WSInfo.getFilterNameList(tid)
        self.setListCtrlFilter(listCtrlFilter, listFilter, listFilterType, listFilterName)
        return

    ## テーブル選択イベント ------------------------------------------------------------------------
    def OnChoiceTable(self, event):
        choice = event.GetClientObject()
        idx = event.GetSelection()
        listTable = self.WSInfo.getRealTableList()
        tid = listTable[idx]
        if choice == self.choiceMasterTable: # Master
            if tid == self.MasterTID: # 変化なし
                return
            else:
                self.MasterTID = tid
        else: # Slave
            if tid == self.SlaveTID: # 変化なし
                return
            else:
                self.SlaveTID  = tid

        # reset
        self.setTableInfo(self.MasterTID, self.choiceMasterSet, self.listCtrlMasterFilter)
        self.setTableInfo(self.SlaveTID,  self.choiceSlaveSet,  self.listCtrlSlaveFilter)
        self.listCtrlMasterKey.DeleteAllItems()
        self.listCtrlSlaveKey.DeleteAllItems()
        self.buttonKeySet.Enable(False)
        return

    ## 選択されているJOINキー(項目)情報取得 --------------------------------------------------------
    def getSelectKeyInfo(self, ctrl):
        idx = ctrl.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if idx == -1: # 未選択
            return None
        id = int(ctrl.GetItem(idx, col=0).GetText())
        type = ctrl.GetItem(idx, col=1).GetText()
        name = ctrl.GetItem(idx, col=2).GetText()
        return (id, type, name)

    ## 項目選択イベント ----------------------------------------------------------------------------
    def OnFilterSelect(self, event):
        # JOINキーのタイプが一致したときのみボタンを有効化
        infoFilterMaster = self.getSelectKeyInfo(self.listCtrlMasterFilter)
        infoFilterSlave  = self.getSelectKeyInfo(self.listCtrlSlaveFilter)
        if (infoFilterMaster == None) or (infoFilterSlave == None) or (infoFilterMaster[1] != infoFilterSlave[1]):
            self.buttonKeySet.Enable(False)
        else:
            self.buttonKeySet.Enable(True)
        return

    ## 項目選択解除イベント ------------------------------------------------------------------------
    def OnFilterDeselect(self, event):
        self.buttonKeySet.Enable(False)
        return

    ## JOINキーリストコントロールに追加 ------------------------------------------------------------
    def appendListCtrlKey(self, ctrl, infoFilter):
        tail = ctrl.GetItemCount()
        ctrl.InsertStringItem(tail, str(infoFilter[0]))
        ctrl.SetStringItem(tail, 1, infoFilter[1])
        ctrl.SetStringItem(tail, 2, infoFilter[2])
        return

    ## JOINキー設定ボタンイベント ------------------------------------------------------------------
    def OnButtonKeySet(self, event):
        infoFilterMaster = self.getSelectKeyInfo(self.listCtrlMasterFilter)
        if infoFilterMaster == None:
            return
        infoFilterSlave  = self.getSelectKeyInfo(self.listCtrlSlaveFilter)
        if infoFilterSlave == None:
            return
        if infoFilterMaster[1] != infoFilterSlave[1]: # type mismatch
            return

        self.appendListCtrlKey(self.listCtrlMasterKey, infoFilterMaster)
        self.appendListCtrlKey(self.listCtrlSlaveKey,  infoFilterSlave)
        self.buttonOK.Enable(True)
        return

    ## JOINキー削除ボタンイベント ------------------------------------------------------------------
    def OnButtonKeyUnset(self, event):
        self.listCtrlMasterKey.DeleteAllItems()
        self.listCtrlSlaveKey.DeleteAllItems()
        self.buttonOK.Enable(False)
        return

    ## JOINテーブル名を取得 ------------------------------------------------------------------------
    def getNewTableName(self):
        return self.textCtrlNewTable.GetValue()

    ## Outer JOIN? ---------------------------------------------------------------------------------
    def isOuter(self):
        return xrc.XRCCTRL(self, "CheckBoxJoinOuter").GetValue()

    ## 選択されているテーブル名を取得 (マスター, スレーブ) -----------------------------------------
    def getTableNames(self):
        tableNameMaster = self.choiceMasterTable.GetStringSelection()
        tableNameSlave  = self.choiceSlaveTable.GetStringSelection()
        return (tableNameMaster, tableNameSlave)

    ## 選択されているセットIDを取得 (マスター, スレーブ) -------------------------------------------
    def getSetIds(self):
        sidMaster = int(self.choiceMasterSet.GetStringSelection())
        sidSlave  = int(self.choiceSlaveSet.GetStringSelection())
        return (sidMaster, sidSlave)

    ## 選択されているJOINキーリストを取得 (マスター, スレーブ) -------------------------------------
    def getKeyLists(self):
        listFilterNameMaster = []
        listFilterNameSlave = []
        for i in range(self.listCtrlMasterKey.GetItemCount()):
            filterNameMaster = self.listCtrlMasterKey.GetItem(i, col=2).GetText()
            listFilterNameMaster.append(filterNameMaster)
            filterNameSlave  = self.listCtrlSlaveKey.GetItem(i, col=2).GetText()
            listFilterNameSlave.append(filterNameSlave)
        return (listFilterNameMaster, listFilterNameSlave)


# --------------------------------------------------------------------------------------------------
class MyDialogUnion(wx.Dialog):
    def __init__(self, frame, tid, tableNameUnion, WSTree):
        self.frame = frame
        self.MasterTID = tid
        self.SlaveTID  = tid
        self.WSTree = WSTree
        self.WSInfo = WSTree.WSInfo

        pre = wx.PreDialog()
        frame.app.res.LoadOnDialog(pre, frame, "DialogUnion")
        self.PostCreate(pre)
        addButtonOkCancel(self) # OK/CANCELボタン

        self.textCtrlNewTable = xrc.XRCCTRL(self, "TextCtrlUnionTable")
        self.buttonKeySet = xrc.XRCCTRL(self, "ButtonUnionKeySet")
        self.buttonKeyUnset = xrc.XRCCTRL(self, "ButtonUnionKeyUnset")
        self.ButtonKeyAuto = xrc.XRCCTRL(self, "ButtonUnionKeyAuto")
        self.choiceMasterTable = xrc.XRCCTRL(self, "ChoiceUnionMasterTable")
        self.choiceSlaveTable = xrc.XRCCTRL(self, "ChoiceUnionSlaveTable")
        self.choiceMasterSet = xrc.XRCCTRL(self, "ChoiceUnionMasterSet")
        self.choiceSlaveSet = xrc.XRCCTRL(self, "ChoiceUnionSlaveSet")
        self.listCtrlMasterFilter = xrc.XRCCTRL(self, "ListCtrlUnionMasterFilter")
        self.listCtrlSlaveFilter = xrc.XRCCTRL(self, "ListCtrlUnionSlaveFilter")
        self.listCtrlMasterKey = xrc.XRCCTRL(self, "ListCtrlUnionMasterKey")
        self.listCtrlSlaveKey = xrc.XRCCTRL(self, "ListCtrlUnionSlaveKey")
        self.checkBoxMasterNoFiler = xrc.XRCCTRL(self, "CheckBoxUnionMasterNoFilter")
        self.checkBoxSlaveNoFiler = xrc.XRCCTRL(self, "CheckBoxUnionSlaveNoFilter")

        self.textCtrlNewTable.SetValue(tableNameUnion)
        self.buttonKeySet.Enable(False)
        self.buttonOK.Enable(False)

        # 項目リスト
        self.listCtrlMasterFilter.InsertColumn(0, TITLE_ID)
        self.listCtrlMasterFilter.InsertColumn(1, TITLE_TYPE)
        self.listCtrlMasterFilter.InsertColumn(2, TITLE_FILTER_NAME)
        self.listCtrlSlaveFilter.InsertColumn(0, TITLE_ID)
        self.listCtrlSlaveFilter.InsertColumn(1, TITLE_TYPE)
        self.listCtrlSlaveFilter.InsertColumn(2, TITLE_FILTER_NAME)

        # Unionキーリスト
        self.listCtrlMasterKey.InsertColumn(0, TITLE_ID)
        self.listCtrlMasterKey.InsertColumn(1, TITLE_TYPE)
        self.listCtrlMasterKey.InsertColumn(2, TITLE_FILTER_NAME)
        self.listCtrlSlaveKey.InsertColumn(0, TITLE_ID)
        self.listCtrlSlaveKey.InsertColumn(1, TITLE_TYPE)
        self.listCtrlSlaveKey.InsertColumn(2, TITLE_FILTER_NAME)

        # テーブル情報設定
        listTable = self.WSInfo.getRealTableList()
        listTableName = self.WSInfo.getRealTableNameList()
        setChoiseList(self.choiceMasterTable, listTableName)
        setChoiseList(self.choiceSlaveTable,  listTableName)
        idxTid = listTable.index(tid)
        self.choiceMasterTable.SetSelection(idxTid)
        self.choiceSlaveTable.SetSelection(idxTid)

        # セット情報設定
        (self.listMasterFilter, self.listMasterFilterType, self.listMasterFilterName) \
            = self.setTableInfo(tid, self.choiceMasterSet, self.listCtrlMasterFilter)
        (self.listSlaveFilter, self.listSlaveFilterType, self.listSlaveFilterName) \
            = self.setTableInfo(tid, self.choiceSlaveSet,  self.listCtrlSlaveFilter)

        # リスト列リサイズ
        self.listCtrlMasterFilter.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlMasterFilter.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
        width = self.listCtrlMasterFilter.GetColumnWidth(1) # 「項目なし」タイプ設定後の列幅
        self.listCtrlMasterFilter.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlSlaveFilter.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlSlaveFilter.SetColumnWidth(1, width)
        self.listCtrlSlaveFilter.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlMasterKey.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlMasterKey.SetColumnWidth(1, width)
        self.listCtrlMasterKey.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlSlaveKey.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlSlaveKey.SetColumnWidth(1, width)
        self.listCtrlSlaveKey.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)

        # event
        self.Bind(wx.EVT_CHOICE, self.OnChoiceTable, self.choiceMasterTable)
        self.Bind(wx.EVT_CHOICE, self.OnChoiceTable, self.choiceSlaveTable)
        self.Bind(wx.EVT_BUTTON, self.OnButtonKeySet, self.buttonKeySet)
        self.Bind(wx.EVT_BUTTON, self.OnButtonKeyUnset, self.buttonKeyUnset)
        self.Bind(wx.EVT_BUTTON, self.OnButtonKeyAuto, self.ButtonKeyAuto)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnFilterSelect, self.listCtrlMasterFilter)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnFilterSelect, self.listCtrlSlaveFilter)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnFilterDeselect, self.listCtrlMasterFilter)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnFilterDeselect, self.listCtrlSlaveFilter)
        self.Bind(wx.EVT_CHECKBOX, self.OnCheckboxNoFiler, self.checkBoxMasterNoFiler)
        self.Bind(wx.EVT_CHECKBOX, self.OnCheckboxNoFiler, self.checkBoxSlaveNoFiler)

        return

    ## 項目情報をリストコントロールに設定 ----------------------------------------------------------
    def setListCtrlFilter(self, ctrl, listFilter, listFilterType, listFilterName):
        ctrl.DeleteAllItems()
        row = 0
        if len(listFilter) > 0:
            for i, id in enumerate(listFilter):
                ctrl.InsertStringItem(i, str(id))
                ctrl.SetStringItem(i, 1, MAP_DATA_TYPE_NC[listFilterType[i]])
                ctrl.SetStringItem(i, 2, listFilterName[i])
            row = i + 1

        # 「項目なし」追加
        ctrl.InsertStringItem(row, str(FILTER_TYPE_NONE_ID))
        ctrl.SetStringItem(row, 1, FILTER_TYPE_NONE_TYPE_STR)
        ctrl.SetStringItem(row, 2, FILTER_TYPE_NONE_NAME)
        return

    ## テーブル情報設定 ----------------------------------------------------------------------------
    def setTableInfo(self, tid, choiceSet, listCtrlFilter):
        ret = self.frame.checkOpenTable(tid) # テーブルが開いていなかったら開く
        if ret < 0:
            return

        listSet = self.WSInfo.getSetList(tid)
        setChoiseList(choiceSet, listSet)

        listFilter = self.WSInfo.getFilterList(tid)
        listFilterType = self.WSInfo.getFilterTypeList(tid)
        listFilterName = self.WSInfo.getFilterNameList(tid)
        self.setListCtrlFilter(listCtrlFilter, listFilter, listFilterType, listFilterName)
        return (listFilter, listFilterType, listFilterName)

    ## テーブル選択イベント ------------------------------------------------------------------------
    def OnChoiceTable(self, event):
        choice = event.GetClientObject()
        idx = event.GetSelection()
        listTable = self.WSInfo.getRealTableList()
        tid = listTable[idx]
        if choice == self.choiceMasterTable: # Master
            if tid == self.MasterTID: # 変化なし
                return
            else:
                self.MasterTID = tid
        else: # Slave
            if tid == self.SlaveTID: # 変化なし
                return
            else:
                self.SlaveTID  = tid

        # reset
        (self.listMasterFilter, self.listMasterFilterType, self.listMasterFilterName) \
            = self.setTableInfo(self.MasterTID, self.choiceMasterSet, self.listCtrlMasterFilter)
        (self.listSlaveFilter, self.listSlaveFilterType, self.listSlaveFilterName) \
            = self.setTableInfo(self.SlaveTID,  self.choiceSlaveSet,  self.listCtrlSlaveFilter)
        self.listCtrlMasterKey.DeleteAllItems()
        self.listCtrlSlaveKey.DeleteAllItems()
        self.buttonKeySet.Enable(False)
        return

    ## 「項目なし」チェックボックスイベント --------------------------------------------------------
    def OnCheckboxNoFiler(self, event):
        ctrl = event.GetEventObject()
        bFlag = ctrl.GetValue()
        if ctrl == self.checkBoxMasterNoFiler:
            listCtrl = self.listCtrlMasterFilter
        else:
            listCtrl = self.listCtrlSlaveFilter
        if bFlag:
            idx = listCtrl.GetItemCount() - 1 # 末尾
        else:
            idx = 0 # 先頭
        listCtrl.Select(idx, True)
        return

    ## 選択されているUnionキー(項目)情報取得 -------------------------------------------------------
    def getSelectKeyInfo(self, ctrl):
        idx = ctrl.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if idx == -1: # 未選択
            return None
        id = int(ctrl.GetItem(idx, col=0).GetText())
        type = ctrl.GetItem(idx, col=1).GetText()
        name = ctrl.GetItem(idx, col=2).GetText()
        return (id, type, name)

    ## 項目選択イベント ----------------------------------------------------------------------------
    def OnFilterSelect(self, event):
        # Unionキーのタイプが一致したときのみボタンを有効化
        # 「項目なし」はどのタイプとも一致
        infoFilterMaster = self.getSelectKeyInfo(self.listCtrlMasterFilter)
        infoFilterSlave  = self.getSelectKeyInfo(self.listCtrlSlaveFilter)
        if (infoFilterMaster == None) or (infoFilterSlave == None) \
            or ((infoFilterMaster[1] != infoFilterSlave[1]) \
                and ((infoFilterMaster[1] != FILTER_TYPE_NONE_TYPE_STR) and (infoFilterSlave[1] != FILTER_TYPE_NONE_TYPE_STR))):
            bFlag = False
        else:
            bFlag = True
        self.buttonKeySet.Enable(bFlag)

        # 「項目なし」以外が選ばれたらチェックボックスオフ
        ctrl = event.GetEventObject()
        if ctrl == self.listCtrlMasterFilter:
            infoFilter = infoFilterMaster
            checkBox = self.checkBoxMasterNoFiler
        else:
            infoFilter = infoFilterSlave
            checkBox = self.checkBoxSlaveNoFiler
        if (infoFilter == None) or (infoFilter[1] != FILTER_TYPE_NONE_TYPE_STR):
            checkBox.SetValue(False)
        return

    ## 項目選択解除イベント ------------------------------------------------------------------------
    def OnFilterDeselect(self, event):
        # 非選択になった側の「項目なし」チェックボックスオフ
        ctrl = event.GetEventObject()
        infoFilter = self.getSelectKeyInfo(ctrl)
        if infoFilter == None: # 選択項目が無くなった
            """
            if ctrl == self.listCtrlMasterFilter:
                checkBox = self.checkBoxMasterNoFiler
            else:
                checkBox = self.checkBoxSlaveNoFiler
            checkBox.SetValue(False)
            """

            self.buttonKeySet.Enable(False)
        return

    ## Unionキーリストコントロールに追加 -----------------------------------------------------------
    def appendListCtrlKey(self, ctrl, infoFilter):
        tail = ctrl.GetItemCount()
        ctrl.InsertStringItem(tail, str(infoFilter[0]))
        ctrl.SetStringItem(tail, 1, infoFilter[1])
        ctrl.SetStringItem(tail, 2, infoFilter[2])
        return

    ## Unionキー設定ボタンイベント -----------------------------------------------------------------
    def OnButtonKeySet(self, event):
        infoFilterMaster = self.getSelectKeyInfo(self.listCtrlMasterFilter)
        infoFilterSlave  = self.getSelectKeyInfo(self.listCtrlSlaveFilter)
        if (infoFilterMaster == None) or (infoFilterSlave == None) \
            or ((infoFilterMaster[1] != infoFilterSlave[1]) \
                and ((infoFilterMaster[1] != FILTER_TYPE_NONE_TYPE_STR) and (infoFilterSlave[1] != FILTER_TYPE_NONE_TYPE_STR))):
            return

        self.appendListCtrlKey(self.listCtrlMasterKey, infoFilterMaster)
        self.appendListCtrlKey(self.listCtrlSlaveKey,  infoFilterSlave)
        self.buttonOK.Enable(True)
        return

    ## Unionキー削除ボタンイベント -----------------------------------------------------------------
    def OnButtonKeyUnset(self, event):
        self.listCtrlMasterKey.DeleteAllItems()
        self.listCtrlSlaveKey.DeleteAllItems()
        self.buttonOK.Enable(False)
        return

    ## 自動設定ボタンイベント ----------------------------------------------------------------------
    def OnButtonKeyAuto(self, event):
        self.OnButtonKeyUnset(event) # Unionキークリア
        bFlag = False
        sizeMaster = len(self.listMasterFilter)
        sizeSlave  = len(self.listSlaveFilter)
        offsetSlave = 0
        for i in range(sizeMaster):
            for j in range(offsetSlave, sizeSlave):
                if self.listMasterFilterType[i] == self.listSlaveFilterType[j]: # 項目タイプ一致
                    # Unionキー追加
                    infoFilterMaster = (self.listMasterFilter[i], MAP_DATA_TYPE_NC[self.listMasterFilterType[i]], self.listMasterFilterName[i])
                    infoFilterSlave = (self.listSlaveFilter[j], MAP_DATA_TYPE_NC[self.listSlaveFilterType[j]], self.listSlaveFilterName[j])
                    self.appendListCtrlKey(self.listCtrlMasterKey, infoFilterMaster)
                    self.appendListCtrlKey(self.listCtrlSlaveKey,  infoFilterSlave)
                    bFlag = True
                    break
            if j >= sizeSlave:
                break
            offsetSlave = j + 1

        self.buttonOK.Enable(bFlag)
        return

    ## Unionテーブル名を取得 -----------------------------------------------------------------------
    def getNewTableName(self):
        return self.textCtrlNewTable.GetValue()

    ## Table ID? -----------------------------------------------------------------------------------
    def isTableId(self):
        return xrc.XRCCTRL(self, "CheckBoxUnionTableId").GetValue()

    ## Rec No? -------------------------------------------------------------------------------------
    def isRecNo(self):
        return xrc.XRCCTRL(self, "CheckBoxUnionRecNo").GetValue()

    ## Delete Source Table? ------------------------------------------------------------------------
    def isDeleteTable(self):
        return xrc.XRCCTRL(self, "CheckBoxUnionDeleteTable").GetValue()

    ## 選択されているテーブル名を取得 (マスター, スレーブ) -----------------------------------------
    def getTableNames(self):
        tableNameMaster = self.choiceMasterTable.GetStringSelection()
        tableNameSlave  = self.choiceSlaveTable.GetStringSelection()
        return (tableNameMaster, tableNameSlave)

    ## 選択されているセットIDを取得 (マスター, スレーブ) -------------------------------------------
    def getSetIds(self):
        sidMaster = int(self.choiceMasterSet.GetStringSelection())
        sidSlave  = int(self.choiceSlaveSet.GetStringSelection())
        return (sidMaster, sidSlave)

    ## 選択されているUnionキーリストを取得 (マスター, スレーブ) ------------------------------------
    def getKeyLists(self):
        listFilterNameMaster = []
        listFilterNameSlave = []
        for i in range(self.listCtrlMasterKey.GetItemCount()):
            filterNameMaster = self.listCtrlMasterKey.GetItem(i, col=2).GetText()
            if len(filterNameMaster) == 0:
                listFilterNameMaster.append(NO_FILTER_MARK)
            else:
                listFilterNameMaster.append(filterNameMaster)
            filterNameSlave  = self.listCtrlSlaveKey.GetItem(i, col=2).GetText()
            if len(filterNameSlave) == 0:
                listFilterNameSlave.append(NO_FILTER_MARK)
            else:
                listFilterNameSlave.append(filterNameSlave)
        return (listFilterNameMaster, listFilterNameSlave)


# --------------------------------------------------------------------------------------------------
class MyDialogExtractInOut(wx.Dialog):
    def __init__(self, frame):
        pre = wx.PreDialog()
        frame.app.res.LoadOnDialog(pre, frame, "DialogExtractInOut")
        self.PostCreate(pre)
        addButtonOkCancel(self) # OK/CANCELボタン
        return

    ## Slave? --------------------------------------------------------------------------------------
    def isSlave(self):
        return xrc.XRCCTRL(self, "RadioButtonExtractInOutSlave").GetValue()

    ## IN? -----------------------------------------------------------------------------------------
    def isIN(self):
        return xrc.XRCCTRL(self, "RadioButtonExtractInOutIN").GetValue()


# --------------------------------------------------------------------------------------------------
class MyDialogCalc(wx.Dialog):
    def __init__(self, frame, tid, WSInfo):
        self.frame  = frame
        self.WSInfo = WSInfo

        pre = wx.PreDialog()
        frame.app.res.LoadOnDialog(pre, frame, "DialogCalc")
        self.PostCreate(pre)
        addButtonOkCancel(self) # OK/CANCELボタン

        self.textCtrlText = xrc.XRCCTRL(self, "TextCtrlText")
        self.buttonTextClear = xrc.XRCCTRL(self, "ButtonTextClear")
        self.listCtrlFunc = xrc.XRCCTRL(self, "ListCtrlFunc")
        self.toggleButtonFuncAll = xrc.XRCCTRL(self, "ToggleButtonFuncAll")
        self.toggleButtonFuncStr = xrc.XRCCTRL(self, "ToggleButtonFuncStr")
        self.toggleButtonFuncNum = xrc.XRCCTRL(self, "ToggleButtonFuncNum")
        self.toggleButtonFuncCmp = xrc.XRCCTRL(self, "ToggleButtonFuncCmp")
        self.toggleButtonFuncSp  = xrc.XRCCTRL(self, "ToggleButtonFuncSp")
        self.listCtrlFilter = xrc.XRCCTRL(self, "ListCtrlFilter")

        # 項目リスト
        self.listCtrlFilter.InsertColumn(0, TITLE_ID)
        self.listCtrlFilter.InsertColumn(1, TITLE_TYPE)
        self.listCtrlFilter.InsertColumn(2, TITLE_FILTER_NAME)

        # 関数リスト
        self.listCtrlFunc.InsertColumn(0, TITLE_FUNCTION)

        # リスト列リサイズ
        self.listCtrlFunc.SetColumnWidth(0, 100)
        self.listCtrlFilter.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlFilter.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
        self.listCtrlFilter.SetColumnWidth(2, wx.LIST_AUTOSIZE_USEHEADER)

        ## 関数情報設定
        self.setListCtrlFunc(self.listCtrlFunc, LIST_CALC_FUNC_ALL)

        ## 項目情報設定
        self.setListCtrlFilter(self.listCtrlFilter, tid)

        # event
        self.Bind(wx.EVT_BUTTON, self.OnButtonTextClear, self.buttonTextClear)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.OnToggleButton)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnFuncActivate, self.listCtrlFunc)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnFilterActivate, self.listCtrlFilter)
        self.textCtrlText.Bind(wx.EVT_CONTEXT_MENU, self.OnTextPopup)
        self.textCtrlText.Bind(wx.EVT_MENU, self.OnTextPopupSelect)

        return

    ## テキストポップアップ ------------------------------------------------------------------------
    def OnTextPopup(self, event):
        menu = self.frame.app.res.LoadMenu("PMenuTextEdit")
        menu.Enable(xrc.XRCID("PMenuItemCut"), self.textCtrlText.CanCut())
        menu.Enable(xrc.XRCID("PMenuItemCopy"), self.textCtrlText.CanCopy())
        menu.Enable(xrc.XRCID("PMenuItemPaste"), self.textCtrlText.CanPaste())
        menu.Enable(xrc.XRCID("PMenuItemDelete"), self.textCtrlText.CanCut())
        self.textCtrlText.PopupMenu(menu)
        return

    ## テキストポップアップ選択 --------------------------------------------------------------------
    def OnTextPopupSelect(self, event):
        eventId = event.GetId()
        if   eventId == xrc.XRCID("PMenuItemCut"):
            self.textCtrlText.Cut()
        elif eventId == xrc.XRCID("PMenuItemCopy"):
            self.textCtrlText.Copy()
        elif eventId == xrc.XRCID("PMenuItemPaste"):
            self.textCtrlText.Paste()
        elif eventId == xrc.XRCID("PMenuItemDelete"):
            self.textCtrlText.WriteText("")
        elif eventId == xrc.XRCID("PMenuItemAll"):
            self.textCtrlText.SetSelection(-1, -1)
        return

    ## 関数情報設定 --------------------------------------------------------------------------------
    def setListCtrlFunc(self, ctrl, list):
        ctrl.DeleteAllItems()
        for i, func in enumerate(list):
            ctrl.InsertStringItem(i, func)
        return

    ## トグルボタン押下 ----------------------------------------------------------------------------
    def OnToggleButton(self, event):
        ctrl = event.GetEventObject()
        if ctrl == self.toggleButtonFuncAll:
            self.setListCtrlFunc(self.listCtrlFunc, LIST_CALC_FUNC_ALL)
        else:
            self.toggleButtonFuncAll.SetValue(False)
        if ctrl == self.toggleButtonFuncStr:
            self.setListCtrlFunc(self.listCtrlFunc, LIST_CALC_FUNC_STR)
        else:
            self.toggleButtonFuncStr.SetValue(False)
        if ctrl == self.toggleButtonFuncNum:
            self.setListCtrlFunc(self.listCtrlFunc, LIST_CALC_FUNC_NUM)
        else:
            self.toggleButtonFuncNum.SetValue(False)
        if ctrl == self.toggleButtonFuncCmp:
            self.setListCtrlFunc(self.listCtrlFunc, LIST_CALC_FUNC_CMP)
        else:
            self.toggleButtonFuncCmp.SetValue(False)
        if ctrl == self.toggleButtonFuncSp:
            self.setListCtrlFunc(self.listCtrlFunc, LIST_CALC_FUNC_SP)
        else:
            self.toggleButtonFuncSp.SetValue(False)
        self.textCtrlText.SetFocus()
        return

    ## 項目情報設定 --------------------------------------------------------------------------------
    def setListCtrlFilter(self, ctrl, tid):
        listFilter = self.WSInfo.getFilterList(tid)
        listFilterType = self.WSInfo.getFilterTypeList(tid)
        listFilterName = self.WSInfo.getFilterNameList(tid)
        if len(listFilter) < 1:
            return
        for i, id in enumerate(listFilter):
            ctrl.InsertStringItem(i, str(id))
            ctrl.SetStringItem(i, 1, MAP_DATA_TYPE_NC[listFilterType[i]])
            ctrl.SetStringItem(i, 2, listFilterName[i])
        return

    ## クリアボタン押下 ----------------------------------------------------------------------------
    def OnButtonTextClear(self, event):
        self.textCtrlText.Clear()
        self.textCtrlText.SetFocus()
        return

    ## 関数ダブルクリック --------------------------------------------------------------------------
    def OnFuncActivate(self, event):
        ctrl = event.GetEventObject()
        idx = ctrl.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if idx == -1: # 未選択
            return
        name = ctrl.GetItem(idx, col=0).GetText()
        self.textCtrlText.WriteText(name)
        self.textCtrlText.SetFocus()
        return

    ## 項目ダブルクリック --------------------------------------------------------------------------
    def OnFilterActivate(self, event):
        ctrl = event.GetEventObject()
        idx = ctrl.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if idx == -1: # 未選択
            return
        name = ctrl.GetItem(idx, col=2).GetText()
        self.textCtrlText.WriteText("@" + name)
        self.textCtrlText.SetFocus()
        return

    ## 計算式を取得 --------------------------------------------------------------------------------
    def getText(self):
        return self.textCtrlText.GetValue()


# --------------------------------------------------------------------------------------------------
class MyDialogProperty(wx.Dialog):
    def __init__(self, frame, tableName, propertyText):
        pre = wx.PreDialog()
        frame.app.res.LoadOnDialog(pre, frame, "DialogProperty")
        self.PostCreate(pre)

        self.textCtrlPropertyName = xrc.XRCCTRL(self, "TextCtrlPropertyName")
        self.textCtrlProperty = xrc.XRCCTRL(self, "TextCtrlProperty")

        self.textCtrlPropertyName.WriteText(tableName)
        self.textCtrlProperty.WriteText(propertyText)
        return


# --------------------------------------------------------------------------------------------------
## 測度設定部品クラス（集計ダイアログ用）
class SumMsrCtrl():
    def __init__(self, staticText=None, choice=None, checkBoxRecs=None, checkBoxMin=None, checkBoxMax=None, checkBoxTotal=None, checkBoxAvg=None):
        self.staticText    = staticText
        self.choice        = choice
        self.checkBoxRecs  = checkBoxRecs
        self.checkBoxMin   = checkBoxMin
        self.checkBoxMax   = checkBoxMax
        self.checkBoxTotal = checkBoxTotal
        self.checkBoxAvg   = checkBoxAvg
        return


# --------------------------------------------------------------------------------------------------
class MyDialogSum(wx.Dialog):
    def __init__(self, frame, tid, WSInfo):
        self.frame  = frame
        self.WSInfo = WSInfo
        self.listDimChoice = []
        self.listMsrCtrl = []

        pre = wx.PreDialog()
        frame.app.res.LoadOnDialog(pre, frame, "DialogSum")
        self.PostCreate(pre)
        addButtonOkCancel(self) # OK/CANCELボタン

        self.textCtrlTableSetTableName = xrc.XRCCTRL(self, "TextCtrlTableSetTableName")
        self.textCtrlTableSetTableKind = xrc.XRCCTRL(self, "TextCtrlTableSetTableKind")
        self.choiceTableSetSetId = xrc.XRCCTRL(self, "ChoiceTableSetSetId")
        self.scrolledWindowSumDim = xrc.XRCCTRL(self, "ScrolledWindowSumDim")
        self.scrolledWindowSumMsr = xrc.XRCCTRL(self, "ScrolledWindowSumMsr")

        # スクロールウィンドウ設定
        self.scrolledWindowSumDim.SetScrollRate(16, 16)
        self.scrolledWindowSumMsr.SetScrollRate(16, 16)

        # テーブル情報
        ret = self.frame.checkOpenTable(tid) # テーブルが開いていなかったら開く
        if ret < 0:
            return

        tableName = self.WSInfo.getTableName(tid)
        self.textCtrlTableSetTableName.WriteText(tableName)
        bJoin = self.WSInfo.isJoinTable(tid)
        if bJoin:
            tableKind = "JOIN"
        else:
            tableKind = "REAL"
        self.textCtrlTableSetTableKind.WriteText(tableKind)

        # セット情報
        self.listSet = self.WSInfo.getSetList(tid)
        setChoiseList(self.choiceTableSetSetId, self.listSet)

        # 次元・測度部構築
        self.buildDimMsr(g_WSInfo.getCountFilter(tid))

        # 項目情報
        listFilterChoise = self.createFilterChoiseList(tid)
        self.setFilterChoiseList(listFilterChoise)

        # event
        self.Bind(wx.EVT_CHOICE, self.OnChoice)
        self.Bind(wx.EVT_BUTTON, self.OnButtonCheck, id=xrc.XRCID("ButtonCheckAll"))
        self.Bind(wx.EVT_BUTTON, self.OnButtonCheck, id=xrc.XRCID("ButtonCheckNone"))

        return

    ## 次元・測度部構築 ----------------------------------------------------------------------------
    def buildDimMsr(self, nFilter):
        # 次元
        sizerDim = self.scrolledWindowSumDim.GetSizer()
        del self.listDimChoice[:]
        for i in range(MAX_DIM):
            panel = wx.Panel(self.scrolledWindowSumDim, -1)
            sizer = wx.BoxSizer()
            staticText = wx.StaticText(panel, -1, "%02d:" % (i + 1))
            choice = wx.Choice(panel, -1)
            self.listDimChoice.append(choice)
            sizer.Add(staticText, 0, wx.ALIGN_RIGHT|wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 1)
            sizer.Add(choice, 1, wx.ALL|wx.EXPAND, 1)
            panel.SetSizer(sizer)
            sizerDim.Add(panel, 0, wx.ALL|wx.EXPAND, 1)
            if i >= nFilter:
                panel.Enable(False)

        # 測度
        sizerDim = self.scrolledWindowSumMsr.GetSizer()
        del self.listMsrCtrl[:]
        for i in range(MAX_DIM):
            panel = wx.Panel(self.scrolledWindowSumMsr, -1)
            sizer = wx.BoxSizer()
            staticText = wx.StaticText(panel, -1, "%02d:" % (i + 1))
            choice = wx.Choice(panel, -1)
            checkBoxRecs  = wx.CheckBox(panel, -1, u"件数")
            checkBoxMin   = wx.CheckBox(panel, -1, u"最小")
            checkBoxMax   = wx.CheckBox(panel, -1, u"最大")
            checkBoxTotal = wx.CheckBox(panel, -1, u"合計")
            checkBoxAvg   = wx.CheckBox(panel, -1, u"平均")
            checkBoxMin.Enable(False)
            checkBoxMax.Enable(False)
            checkBoxTotal.Enable(False)
            checkBoxAvg.Enable(False)
            sizer.Add(staticText, 0, wx.ALIGN_RIGHT|wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 1)
            sizer.Add(choice, 1, wx.ALL|wx.EXPAND, 1)
            sizer.Add(checkBoxRecs,  0, wx.ALIGN_CENTRE_VERTICAL)
            sizer.Add(checkBoxMin ,  0, wx.ALIGN_CENTRE_VERTICAL)
            sizer.Add(checkBoxMax,   0, wx.ALIGN_CENTRE_VERTICAL)
            sizer.Add(checkBoxTotal, 0, wx.ALIGN_CENTRE_VERTICAL)
            sizer.Add(checkBoxAvg,   0, wx.ALIGN_CENTRE_VERTICAL)
            panel.SetSizer(sizer)
            sizerDim.Add(panel, 0, wx.ALL|wx.EXPAND, 1)
            msrCtrl = SumMsrCtrl(staticText, choice, checkBoxRecs, checkBoxMin, checkBoxMax, checkBoxTotal, checkBoxAvg)
            self.listMsrCtrl.append(msrCtrl)
        return

    ## 項目情報リスト作成 --------------------------------------------------------------------------
    def createFilterChoiseList(self, tid):
        listFilter = self.WSInfo.getFilterList(tid)
        listFilterType = self.WSInfo.getFilterTypeList(tid)
        listFilterName = self.WSInfo.getFilterNameList(tid)
        if len(listFilter) < 1:
            return

        listFilterChoise = [""] # 1番目に空行を入れておく
        for i, id in enumerate(listFilter):
            listFilterChoise.append("%d: %s (%s)" % (id, listFilterName[i], MAP_DATA_TYPE_NC[listFilterType[i]]))

        self.listFilterType = listFilterType # OnChoice()で使用
        self.listFilterName = listFilterName # getterで使用
        return listFilterChoise

    ## 項目情報リスト設定 --------------------------------------------------------------------------
    def setFilterChoiseList(self, listFilterChoise):
        for choiceDim, msrCtrl in zip(self.listDimChoice, self.listMsrCtrl):
            setChoiseList(choiceDim, listFilterChoise)
            setChoiseList(msrCtrl.choice, listFilterChoise)
        return

    ## チェック状態設定 ----------------------------------------------------------------------------
    def checkCheckBox(self, msrCtrl, bFlag):
        msrCtrl.checkBoxRecs.SetValue(bFlag)
        msrCtrl.checkBoxMin.SetValue(bFlag)
        msrCtrl.checkBoxMax.SetValue(bFlag)
        msrCtrl.checkBoxTotal.SetValue(bFlag)
        msrCtrl.checkBoxAvg.SetValue(bFlag)
        return

    ## チェック状態設定（文字列(日付時刻含む)用）---------------------------------------------------
    def checkCheckBoxStr(self, msrCtrl, bFlag=False, change=True):
        if change:
            msrCtrl.checkBoxRecs.SetValue(bFlag)
            msrCtrl.checkBoxMin.SetValue(bFlag)
            msrCtrl.checkBoxMax.SetValue(bFlag)
        msrCtrl.checkBoxTotal.SetValue(False)
        msrCtrl.checkBoxAvg.SetValue(False)
        return

    ## 有効状態設定 --------------------------------------------------------------------------------
    def enableCheckBox(self, msrCtrl, bFlag):
        msrCtrl.checkBoxMin.Enable(bFlag)
        msrCtrl.checkBoxMax.Enable(bFlag)
        msrCtrl.checkBoxTotal.Enable(bFlag)
        msrCtrl.checkBoxAvg.Enable(bFlag)
        return

    ## 有効状態設定（文字列(日付時刻含む)用）-------------------------------------------------------
    def enableCheckBoxStr(self, msrCtrl):
        msrCtrl.checkBoxMin.Enable(True)
        msrCtrl.checkBoxMax.Enable(True)
        msrCtrl.checkBoxTotal.Enable(False)
        msrCtrl.checkBoxAvg.Enable(False)
        return

    ## Choiceイベント ------------------------------------------------------------------------------
    def OnChoice(self, event):
        choice = event.GetEventObject()
        for msrCtrl in self.listMsrCtrl:
            if msrCtrl.choice == choice:
                idx = event.GetSelection()
                if idx == 0:
                    self.enableCheckBox(msrCtrl, False) # 有効状態
                    self.checkCheckBox(msrCtrl, False) # チェック状態
                else:
                    if self.listFilterType[idx-1] in LIST_NUM_TYPE: # 数値
                        self.enableCheckBox(msrCtrl, True) # 有効状態
                    else: # 文字
                        self.enableCheckBoxStr(msrCtrl) # 有効状態
                        self.checkCheckBoxStr(msrCtrl, change=False) # チェック状態
                break
        return

    ## Checkボタンイベント -------------------------------------------------------------------------
    def OnButtonCheck(self, event):
        if event.GetId() == xrc.XRCID("ButtonCheckAll"):
            bFlag = True
        else:
            bFlag = False
        for msrCtrl in self.listMsrCtrl:
            idx = msrCtrl.choice.GetSelection()
            if idx > 0:
                if self.listFilterType[idx-1] in LIST_NUM_TYPE: # 数値
                    self.checkCheckBox(msrCtrl, bFlag) # チェック状態
                else: # 文字
                    self.checkCheckBoxStr(msrCtrl, bFlag) # チェック状態
        return

    ## セットID取得 --------------------------------------------------------------------------------
    def getSetId(self):
        idx = self.choiceTableSetSetId.GetSelection()
        sid = self.listSet[idx]
        return sid

    ## 次元リスト取得 ------------------------------------------------------------------------------
    def getDimList(self):
        listDim = []
        for choice in self.listDimChoice:
            idx = choice.GetSelection()
            if idx > 0:
                listDim.append(self.listFilterName[idx - 1])
        return listDim

    ## 測度リスト取得 ------------------------------------------------------------------------------
    def getMsrsList(self):
        listMsrs = []
        for msrCtrl in self.listMsrCtrl:
            listMsr = []
            idx = msrCtrl.choice.GetSelection()
            if idx > 0:
                listMsr.append(self.listFilterName[idx - 1])
                if msrCtrl.checkBoxRecs.GetValue():
                    listMsr.append(1)
                else:
                    listMsr.append(0)
                if msrCtrl.checkBoxMin.GetValue():
                    listMsr.append(1)
                else:
                    listMsr.append(0)
                if msrCtrl.checkBoxMax.GetValue():
                    listMsr.append(1)
                else:
                    listMsr.append(0)
                if msrCtrl.checkBoxTotal.GetValue():
                    listMsr.append(1)
                else:
                    listMsr.append(0)
                if msrCtrl.checkBoxAvg.GetValue():
                    listMsr.append(1)
                else:
                    listMsr.append(0)
                listMsr.append(-1)
                listMsrs.append(listMsr)
        return listMsrs

def getLicense():
    file=open("LFM_Server.pwd", 'r')
    while 1:
        line = file.readline()
        if not line:
            break
	line.strip()
	if line.find("ENGINE=") != -1:
            a = line.split("=")
            file.close()
            return a[1]
    file.close()
    return null
# --------------------------------------------------------------------------------------------------
## メイン
if __name__ == "__main__":

    # py2exeで配布物作成時、sitecustomize.pyが取り込まれない対策
    import sys
    if hasattr(sys,"setdefaultencoding"):
        sys.setdefaultencoding(ENC_OS)

    print "Start\n"
    # 引数
    argvs = sys.argv
    argc = len(argvs)
    if argc > 1:
        ENC_OS = argvs[1]
    if argc > 2:
        ENC_DB = argvs[2]
    print "ENC_OS[%s],ENC_DB[%s]" % (ENC_OS, ENC_DB)

    app = MyApp(False)
    g_App = app
    app.MainLoop()
    
    print "\nEnd"

# --------------------------------------------------------------------------------------------------

