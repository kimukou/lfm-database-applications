#!/usr/bin/env python
# -*- coding: utf-8 -*-

## @package LFM_GUI
# LFM GUI
#
# @author Turbo Data Laboratories, Inc.
# @date 2010/02/20

import sys
import codecs
import decimal
import re
import time

# wxPython
import wx
import wx.grid
import wx.grid as gridlib
import wx.xrc as xrc
import wx.lib.mixins.gridlabelrenderer as glr

# LFM
from LFM_Macro import *
from wx.lib.embeddedimage import PyEmbeddedImage

# ##################################################################################################
#
#         PyFIT 仮想グリッド
#
# ##################################################################################################

# 文字コード ---------------------------------------------------------------------------------------
ENC_OS      = "MS932"        # OS文字コード
ENC_DB      = "MS932"        # DB文字コード
#ENC_DB     = "UTF8"

# 標準入出力文字コード設定 -------------------------------------------------------------------------
sys.stdin  = codecs.getreader(ENC_OS)(sys.stdin)
sys.stdout = codecs.getwriter(ENC_OS)(sys.stdout)
sys.stderr = codecs.getwriter(ENC_OS)(sys.stderr)

#---------------------------------------------------------------------------------------------------
## データタイプアイコン
Numeric = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAHtJ"
    "REFUOI2lk0sOwCAIRAG5a3ske1eFrpqahl8qK8jgc0RFpAY7wQAAXYb+WXwSI6/Fk1tATyeP"
    "HO18wCubgG9TFC4AqWEFYgJUplYhroOqExewThqpuYTQQeV9pEfIICkgg5QAJQddhqpMfa7Q"
    "cmHpvBYXxDOzdNz9zjdIqTs34b72+AAAAABJRU5ErkJggg==")
#-------------------------------------------------------------------------------
Float = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAHNJ"
    "REFUOI2tU0EOwCAIazf/DMs+oK9mJxJn1GlYr5S2NIE8TkSQTNQiAkfIHkACAJbMdjBL5nwT"
    "NXoH9UJNGC37fOuEXtKtEp1bC/1ToqO9b0XglcBErRdzKsCSuUr+TDDCzCReoolaz2G1ROK6"
    "Q8/E6Ds/D+Y3P4R26xcAAAAASUVORK5CYII=")
#-------------------------------------------------------------------------------
Integer = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAGtJ"
    "REFUOI2lk8EOwCAIQ0v1q7e7f725k4kxyDDlptCHoWLGAiXsBroCoNQeQJ0PjcUA4Hqf7t17"
    "OXpFEXSt44nYg3Ak1qdlo0bJDPTIBW/IacDOoRRgJ04BIjHwM8TZrtXqAZS/srxMpq7zB0Fw"
    "N68tR4EKAAAAAElFTkSuQmCC")
#-------------------------------------------------------------------------------
Date = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAI5J"
    "REFUOI2lktsOwzAIQ43pX0/99Jq9LNFKc2EaUhQUhRObYEZH6AoUwuiWz46WSFoWk0Toigzp"
    "ACO3CiSB5A3SAbFRgM8DGXIsix6Mp0rOLuS89Sj3ami8FXxDztc5VvWL3GEYHQCiLUml3egw"
    "+ngOst+Z/6WFqo2/ezC9tRvtsoKdkukkVhV0QPnfU7wB4lVRquZBS6kAAAAASUVORK5CYII=")
#-------------------------------------------------------------------------------
String = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAHNJ"
    "REFUOI3FU0kKwDAIVJNHh3oPeXXsoQhiKxWkVMhpljioiNSgUv3YQyoGVPo+YzBp4aSF/3Xw"
    "uUEHuHJ6wE/HcxRH3QMrUPKxh1ihciye3oOIF0bIVrft+AiZuk0hEoemDCxIDZ7eG8bAggxc"
    "OiasnvMJMXQ0amh0qVgAAAAASUVORK5CYII=")
#-------------------------------------------------------------------------------
Time = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAALVJ"
    "REFUOI2tU1EWwyAIS7D3v1Hpybbsw0op2n3sLX8CCUSUtIYKvV+qMVrjVAiAWWAQJzaAwa5C"
    "lsk6ye47IIEQIMF9x8jV6UhrQe5KSsnbsQfOacYkhgxp1FStHtdszkZ3930iFW3grMtWLt0n"
    "5gpk2NhKfPJcd6fSaLsnM5eQtFxpRlyiHz6RV8h1vTav8cs9hL3k/zZBVD0cB3lpgdauFBlj"
    "xuoOXz6isBBdfvgL/Otv/AUfuWlxBBjvyGsAAAAASUVORK5CYII=")
#-------------------------------------------------------------------------------
TimeOfDate = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAANhJ"
    "REFUOI2NUkEOwzAIM05P+/9rpjXPmrRD8A5LMkqqbkiRmmCMizFjgbwJf4SxWH7brpIx5E3y"
    "poybBP5DhfUmmWQS8IcC9AaZZIuYs1nEbjE/SLYMHqCJDEU8IWPuqH5q3UEWM75AFqt1h3vT"
    "MitjAQAZCwRI/Xsc8HW4D8yoWRSQxYTn7GK4fWXjqTzsSeDeVOu+FB3U9vda9zkjG5so/GFl"
    "CPcmZheGzKjAvSmzni5Slgl8rCKLXck6DPHxuC+LclYUcdZtnHKv5jB+L+IWG/OiZEtz/g0J"
    "+pKvqMadGQAAAABJRU5ErkJggg==")

#---------------------------------------------------------------------------------------------------
## 仮想グリッド管理クラス
class VirtualGrid(wx.Panel): 
    def __init__( self, parent, tid, sid, wsInfo, wsFrame, app): 
        wx.Panel.__init__( self, parent, -1 )
        self.parent  = parent
        self.wsInfo  = wsInfo                                    # ワークスペース
        self.wsFrame = wsFrame                                   # ワークスペースフレーム
        self.app     = app

        self.topView = 0
        self.currentView = 0
        self.tid=tid                                             # テーブルＩＤ
        self.sid=sid                                             # セットＩＤ
        self.listFilter = self.wsInfo.getFilterList(tid)         # 項目リスト
        self.listFilterName = self.wsInfo.getFilterNameList(tid) # 項目名リスト
        self.listFilterType = self.wsInfo.getFilterTypeList(tid) # 項目データタイプリスト
        self.rows = lfmtblpy.RD5GetSetSize(self.tid,self.sid)    # テーブル行数
        self.cols = lfmtblpy.RD5GetNFilter(self.tid) + 1         # テーブル列数
        self.row1 = lfmutilpy.CTypeIntAr(1)
        self.row2 = lfmutilpy.CTypeIntAr(1)
        
        self.topRowNo = -1        # 仮想テーブル上の選択行上端行番号
        self.bottomRowNo = -1     # 仮想テーブル上の選択行下端行番号
        self.leftColNo = -1       # 仮想テーブル上の選択行左端列番号
        self.rightColNo = -1      # 仮想テーブル上の選択行右端列番号
        self.skipselect = False   # 範囲選択イベント無視フラグ
        self.colsselect = False   # 列ラベル選択フラグ
        self.inLeftClick = False  # 実グリッド上で最下端行選択フラグ
        
        # 仮想グリッドパネル
        self.outer = wx.BoxSizer( wx.HORIZONTAL ) 
        self.inner = wx.BoxSizer( wx.VERTICAL ) 
        self.createGrid( self.parent )  # 実グリッド作成
        self.inner.Add( self.grid, 1, wx.EXPAND )
        self.outer.Add( self.inner, 1, wx.EXPAND )
        
        # 仮想グリッドの縦スクロールバー
        ID = wx.NewId() 
        self.scroll = wx.ScrollBar( self, ID, style = wx.SB_VERTICAL )
        self.scroll.SetScrollbar( 0, self.rowcount, self.rows, self.rowcount )
        self.outer.Add( self.scroll, 0, wx.EXPAND ) 
        self.scroll.Bind( wx.EVT_COMMAND_SCROLL, self.OnScroll )
        
        # グリッド操作用イベントハンドラー登録
        self.grid.Bind( gridlib.EVT_GRID_LABEL_RIGHT_CLICK, self.OnGridMenuPopup )
        self.grid.Bind( gridlib.EVT_GRID_LABEL_LEFT_CLICK, self.OnGridLabelClick )
        self.grid.Bind( gridlib.EVT_GRID_CELL_RIGHT_CLICK, self.OnGridMenuPopup )
        self.grid.Bind( gridlib.EVT_GRID_CELL_LEFT_CLICK, self.OnGridCellClick )
        self.grid.Bind( gridlib.EVT_GRID_RANGE_SELECT, self.OnGridRangeSelect )
        self.grid.Bind( gridlib.EVT_GRID_CELL_CHANGE, self.OnGridCellChange )
        self.grid.Bind( gridlib.wx.EVT_KEY_DOWN, self.OnGridKeyDownUp )
        #self.grid.Bind( gridlib.wx.EVT_KEY_UP, self.OnGridKeyDownUp )
        
        self.Bind( gridlib.wx.EVT_MENU, self.OnGridMenuSelect )
        
        # グリッド表示
        self.SetSizer(self.outer)
        self.SetAutoLayout(True)
        self.Display( self.topView )

    ## 実グリッド作成 ------------------------------------------------------------------------------
    def createGrid( self, parent ):
        self.grid = MyGrid( self )
        self.grid.SetColLabelAlignment( wx.ALIGN_LEFT, wx.ALIGN_CENTRE )
        self.grid.SetDefaultRowSize( 16, False )
        self.grid.SetDefaultColSize( 80, False )
        self.rowcount = self.GetMaxViewCouunt()
        if self.rowcount > self.rows:
            self.rowcount = self.rows
        self.gridrows = self.rowcount
        self.grid.CreateGrid( self.rowcount, self.cols )
        self.grid.SetCornerLabelRenderer( MyCornerLabelRenderer(Numberfmt(self.rows)) )
        for col in range( self.cols ):
            if col == 0:
                self.fname = "RecNo"
                self.grid.SetColFormatCustom( 0, gridlib.GRID_VALUE_NUMBER )
                self.typeicon = Integer
            else:
                self.fname = self.listFilterName[col-1]
                self.ftype = self.listFilterType[col-1]
                if self.ftype == lfmtblpy.D5_DT_STRING:
                    self.grid.SetColFormatCustom( col, gridlib.GRID_VALUE_STRING )
                    self.typeicon = String
                elif self.ftype == lfmtblpy.D5_DT_INTEGER:
                    self.grid.SetColFormatCustom( col, gridlib.GRID_VALUE_NUMBER )
                    self.typeicon = Integer
                elif self.ftype == lfmtblpy.D5_DT_DOUBLE:
                    self.grid.SetColFormatCustom( col, gridlib.GRID_VALUE_NUMBER )
                    self.typeicon = Float
                elif self.ftype == lfmtblpy.D5_DT_DATE:
                    self.grid.SetColFormatCustom( col, gridlib.GRID_VALUE_STRING )
                    self.typeicon = Date
                elif self.ftype == lfmtblpy.D5_DT_TIME:
                    self.grid.SetColFormatCustom( col, gridlib.GRID_VALUE_STRING )
                    self.typeicon = Time
                elif self.ftype == lfmtblpy.D5_DT_DATETIME:
                    self.grid.SetColFormatCustom( col, gridlib.GRID_VALUE_STRING )
                    self.typeicon = TimeOfDate
                elif self.ftype == lfmtblpy.D5_DT_DECIMAL:
                    self.grid.SetColFormatCustom( col, gridlib.GRID_VALUE_NUMBER )
                    self.typeicon = Numeric
            self.grid.SetColLabelRenderer( col, MyColLabelRenderer(self.typeicon, self.fname) )

    ## 仮想グリッドスクロール ----------------------------------------------------------------------
    def OnScroll( self, event ):
        position = event.GetPosition()
        if self.inLeftClick == True:
            self.bottomRowNo = position + self.rowcount
            if self.topRowNo > self.bottomRowNo:
                self.inLeftClick = False
                self.topRowNo = -1
                self.bottomRowNo = -1
                self.leftColNo = -1
                self.rightColNo = -1
        self.Display( position )
        event.Skip()

    ## 仮想グリッド表示 ----------------------------------------------------------------------------
    def Display( self, start):
        self.currentView = start
        if self.currentView + self.rowcount > self.rows:
            if self.rowcount > self.rows:
                delcount = self.gridrows - self.rows
                self.grid.DeleteRows( 0, delcount )
                self.gridrows = self.gridrows - delcount
            else:
                self.currentView = self.rows - self.rowcount
        else:
            if self.gridrows < self.rowcount:
                addcount = self.rowcount - self.gridrows
                self.grid.AppendRows( addcount )
            elif self.gridrows > self.rowcount:
                delcount = self.gridrows - self.rowcount
                self.grid.DeleteRows( 0, delcount )
            self.gridrows = self.rowcount
        for row in range( self.gridrows ):
            self.grid.SetRowLabelValue(row, Numberfmt(self.currentView + row + 1))
            for col in range( self.cols ):
                self.grid.SetCellValue(row, col, self.GetValue(self.currentView + row, col))
                if (self.currentView + row + 1) >= self.topRowNo and (self.currentView + row + 1) <= self.bottomRowNo and col >= self.leftColNo and col <= self.rightColNo:
                    self.grid.SetCellBackgroundColour(row, col, wx.Colour(0,153,255))
                    self.grid.SetCellTextColour(row, col, wx.Colour(255,255,255))
                else:
                    if (row % 2) == 0:
                        self.grid.SetCellBackgroundColour(row, col, wx.Colour(255,255,255))
                    else:
                        self.grid.SetCellBackgroundColour(row, col, wx.Colour(245,245,245))
                    self.grid.SetCellTextColour(row, col, wx.Colour(0,0,0))

    ## 実グリッド表示行数取得 ----------------------------------------------------------------------
    def GetMaxViewCouunt( self ):
        self.panelSize = self.parent.GetClientSize()
        self.maxViewCouunt = ( ( self.panelSize[1] - self.grid.GetDefaultColLabelSize() - 22 ) / 16 ) - 1
        return self.maxViewCouunt

    ## グリッド表示データ取得 ----------------------------------------------------------------------
    def GetValue(self, row, col):
        if col == 0:
            # 列番号0は行番号を取得
            ret= lfmtblpy.RD5GetRowNo1(self.tid, self.sid, row+1, self.row1.getPtr(), self.row2.getPtr())
            d = self.row1.at(0)
            d2 = self.row2.at(0)
            return Numberfmt(d)
        else:
            col-=1
        type = self.listFilterType[col]
        data = ""
        if type == lfmtblpy.D5_DT_INTEGER:
            # 整数型データ
            d = lfmtblpy.RD5GetData1IntR1(self.tid, self.listFilter[col], self.sid, row+1)
            if d != D5_NULL_INT:
                data = Numberfmt(d)
        elif type in LIST_DOUBLE_TYPE:
            # 浮動小数型データ
            d = lfmtblpy.RD5GetData1DblR1(self.tid, self.listFilter[col], self.sid, row+1)
            if d != D5_NULL_DBL:
                if type == lfmtblpy.D5_DT_TIME:
                    # 時刻形式
                    data = TimeDbl2Str(d)
                elif type == lfmtblpy.D5_DT_DATE:
                    # 日付形式
                    data = DateDbl2Str(d)
                elif type == lfmtblpy.D5_DT_DATETIME:
                    # 日付時刻形式
                    data = DateTimeDbl2Str(d)
                else:
                    # 小数点以下桁数反映して文字列化
                    scale = self.wsInfo.getFilterScale(self.tid, self.listFilter[col])
                    fmt = r"%." + str(scale) + "f"
                    data = fmt % d
        elif type == lfmtblpy.D5_DT_STRING:
            # 文字列型データ
            d = lfmtblpy.RD5GetData1StrR1(self.tid, self.listFilter[col], self.sid, row+1).decode(ENC_DB)
            data=d
        elif type == lfmtblpy.D5_DT_DECIMAL:
            # NUMERIC型データ
            NInfo = lfmutilpy.CNumericInfo()
            ret = lfmtblpy.RD5GetNumericInfoR1(self.tid, self.listFilter[col], NInfo.getPtr())
            ndata = lfmutilpy.CNumeric()
            ret = lfmtblpy.RD5GetData1NumericR1(self.tid, self.listFilter[col], self.sid, row+1, ndata.getPtr())
            sdata = lfmtblpy.RD5NumericNum2StrR1(ndata.getPtr(), NInfo.getPtr(), 0, NInfo.getScale())
            data = sdata
        return data

    ## カーソルダウン/アップ -----------------------------------------------------------------------
    def OnGridKeyDownUp(self, event):
        cursorRow = self.grid.GetGridCursorRow() + self.currentView
        if event.KeyCode == wx.WXK_DOWN:
            if cursorRow + 1 >= self.currentView + self.gridrows:
                if cursorRow < self.rows:
                    self.Display( self.currentView + 1 )
                    self.scroll.SetScrollbar( cursorRow, self.rowcount, self.rows, self.rowcount )
            event.Skip()
        elif event.KeyCode == wx.WXK_UP:
            if cursorRow <= self.currentView:
                if cursorRow > 0:
                    self.Display( self.currentView - 1 )
                    self.scroll.SetScrollbar( cursorRow, self.rowcount, self.rows, self.rowcount )
            event.Skip()
        else:
            event.Skip()

    ## グリッド列ラベル取得 ------------------------------------------------------------------------
    def GetColLabelValue(self, col):
        if col == 0:
            return "RecNo"
        else:
            col-=1
        return self.listFilterName[col]

    ## グリッド列ラベル情報（名前、データタイプ）変更 ----------------------------------------------
    def SetColLabelValue(self, col, value1, value2):
        self.listFilterName[col] = value1
        self.listFilterType[col] = value2

    ## テーブル行数取得 ----------------------------------------------------------------------------
    def GetNumberRows(self):
        return lfmtblpy.RD5GetSetSize(self.tid,self.sid)

    ## テーブル列数取得 ----------------------------------------------------------------------------
    def GetNumberCols(self):
        return (lfmtblpy.RD5GetNFilter(self.tid)) + 1

    ## 選択行番号取得 ------------------------------------------------------------------------------
    def GetSelectedRows(self):
        selRows = []
        if self.topRowNo == self.bottomRowNo:
            selRows.append(self.topRowNo)
        else:
            for rno in range(self.bottomRowNo - self.topRowNo + 1):
                selRows.append(self.topRowNo + rno)
        return selRows

    ## 選択列番号取得 ------------------------------------------------------------------------------
    def GetSelectedCols(self):
        selCols = []
        if self.leftColNo == self.rightColNo:
            selCols.append(self.leftColNo)
        else:
            for cno in range(self.rightColNo - self.leftColNo + 1):
                selCols.append(self.leftColNo + cno)
        return selCols

    ## カーソル行番号取得 --------------------------------------------------------------------------
    def GetGridCursorRow(self):
        return self.grid.GetGridCursorRow() + self.currentView

    ## カーソル列番号取得 --------------------------------------------------------------------------
    def GetGridCursorCol(self):
        return self.grid.GetGridCursorCol()

    ## 選択ボックスの上端行番号・左端列番号取得 ----------------------------------------------------
    def GetSelectionBlockTopLeft(self):
        self.topLeft = self.grid.GetSelectionBlockTopLeft()
        self.tval1 = self.topLeft[0][0] + self.currentView
        self.tval2 = self.topLeft[0][1]
        return [(self.tval1, self.tval2)]

    ## 選択ボックスの下端行番号・右端列番号取得 ----------------------------------------------------
    def GetSelectionBlockBottomRight(self):
        self.bottomRight = self.grid.GetSelectionBlockBottomRight()
        self.bval1 = self.bottomRight[0][0] + self.currentView
        self.bval2 = self.bottomRight[0][1]
        return [(self.bval1, self.bval2)]

    ## すべて選択時の最終行番号取得
    def GetSelectionAllBottomRow(self):
        return self.rows

    ## 仮想グリッド上の選択ボックスの上端行番号・下端列番号・左端列番号・右端列番号取得 ------------
    def GetExSelectedRowsCols(self):
        return [self.topRowNo, self.bottomRowNo, self.leftColNo, self.rightColNo]

    ## 仮想グリッド上でカーソル位置設定 ------------------------------------------------------------
    def SetGridCursor(self, rowPos, col):
        self.winRow = rowPos
        if self.rows > self.rowcount:
            if self.winRow >= self.rows - self.rowcount:
                self.winRow = rowPos - (self.rows - self.rowcount)
                self.winView = self.rows - self.rowcount
            else:
                self.winRow = rowPos % self.rowcount
                self.winView = rowPos - self.winRow
            self.Display( self.winView )
        self.grid.SetFocus()
        self.grid.ClearSelection()
        self.grid.SetGridCursor(self.winRow, col)
        self.scroll.SetScrollbar( rowPos, self.rowcount, self.rows, self.rowcount ) 

    ## 画面リセット再表示 --------------------------------------------------------------------------
    def ResetCurrentView(self):
        self.topRowNo = -1
        self.bottomRowNo = -1
        self.leftColNo = -1
        self.rightColNo = -1
        self.skipselect = False
        self.colsselect = False
        self.inLeftClick = False
        self.wsFrame.selectAll = False
        
        self.rows = lfmtblpy.RD5GetSetSize(self.tid,self.sid)
        self.cols = lfmtblpy.RD5GetNFilter(self.tid) + 1
        self.grid.SetCornerLabelRenderer( MyCornerLabelRenderer(Numberfmt(self.rows)) )
        self.scroll.SetScrollbar( self.currentView, self.rowcount, self.rows, self.rowcount ) 
        self.Display( self.currentView )
        self.grid.ClearSelection()
        self.Refresh(True)

    ## グリッドのリセット再表示 --------------------------------------------------------------------
    def ResetGridView(self):
        self.rowcount = self.GetMaxViewCouunt()
        if self.rowcount > self.rows:
            self.rowcount = self.rows
        self.ResetCurrentView()

    ## グリッドメニュー表示 ------------------------------------------------------------------------
    def OnGridMenuPopup(self, event):
        menu = self.app.res.LoadMenu("PMenuGrid")
        self.PopupMenu(menu)
        return

    ## グリッドラベル部クリックイベント処理 --------------------------------------------------------
    def OnGridLabelClick(self, event):
        if event.GetCol() == -1 and event.GetRow() == -1:
            self.topRowNo = 1
            self.bottomRowNo = self.rows
            self.leftColNo = 0
            self.rightColNo = self.cols - 1
            self.SetGridCursor( 0, 0 )
            self.wsFrame.OnMenuItemSelectAll(event)
        else:
            if event.GetCol() == -1 and event.GetRow() != -1:
                self.topRowNo = int(re.sub(",", "", self.grid.GetRowLabelValue(event.GetRow())))
                self.bottomRowNo = self.topRowNo
                self.leftColNo = 1
                self.rightColNo = self.cols - 1
                self.colsselect = False
            else:
                self.topRowNo = 1
                self.bottomRowNo = self.rows
                self.leftColNo = event.GetCol()
                self.rightColNo = self.leftColNo
                self.colsselect = True
            self.wsFrame.selectAll = False
        self.inLeftClick = False
        #self.skipselect = True
        event.Skip()

    ## グリッドセル部クリックイベント処理 ----------------------------------------------------------
    def OnGridCellClick(self, event):
        self.wsFrame.selectAll = False
        self.colsselect = False
        self.inLeftClick = False
        self.topRowNo = int(re.sub(",", "", self.grid.GetRowLabelValue(event.GetRow())))
        self.bottomRowNo = self.topRowNo
        self.leftColNo = event.GetCol()
        self.rightColNo = self.leftColNo
        self.grid.SetGridCursor( event.GetRow(), event.GetCol() )
        self.grid.ClearSelection()
        event.Skip()

    ## グリッド範囲選択イベント処理 ----------------------------------------------------------------
    def OnGridRangeSelect(self, event):
        #if self.skipselect == True or self.wsFrame.selectAll == True or self.colsselect == True:
        if self.skipselect == True or self.wsFrame.selectAll == True:
            self.skipselect = False
            event.Skip()
            return
        self.wsFrame.selectAll = False
        if self.grid.IsSelection() == True:
            if self.colsselect == True:
                self.SetGridCursor( 0, event.GetLeftCol( ))
                self.leftColNo = event.GetLeftCol()
                self.rightColNo = event.GetRightCol()
            else:
                self.grid.SetGridCursor( event.GetTopRow(), event.GetLeftCol())
                self.topRowNo = int(re.sub(",", "", self.grid.GetRowLabelValue(event.GetTopRow())))
                self.bottomRowNo = int(re.sub(",", "", self.grid.GetRowLabelValue(event.GetBottomRow())))
                self.leftColNo = event.GetLeftCol()
                self.rightColNo = event.GetRightCol()
                if self.bottomRowNo == (self.currentView + self.rowcount):
                    self.inLeftClick = True
                self.skipselect = True
                self.grid.ClearSelection()
        else:
            self.inLeftClick = False
        self.Display( self.currentView )
        event.Skip()

    ## グリッドセル変更イベント処理 ------------------------------------------------------------
    def OnGridCellChange(self, event):
        self.wsFrame.OnGridCellChange(event)
        event.Skip()

    ## グリッドメニュー選択イベント処理 ------------------------------------------------------------
    def OnGridMenuSelect(self, event):
        self.SetFocus()
        eventId = event.GetId()
        if   eventId == xrc.XRCID("PMenuItemGridRenameFilter"):
            self.wsFrame.OnMenuItemChangeName(event)
        elif eventId == xrc.XRCID("PMenuItemInsertRow"):
            self.wsFrame.OnMenuItemInsertRow(event)
        elif eventId == xrc.XRCID("PMenuItemAppendRow"):
            self.wsFrame.OnMenuItemInsertRow(event)
        elif eventId == xrc.XRCID("PMenuItemDeleteRow"):
            self.wsFrame.OnMenuItemDeleteRow(event)
        elif eventId == xrc.XRCID("PMenuItemColumnWidth"):
            self.wsFrame.OnMenuItemColumnWidth(event)
        elif eventId == xrc.XRCID("PMenuItemMoveColumn"):
            self.wsFrame.OnMenuItemMoveColumn(event)
        elif eventId == xrc.XRCID("PMenuItemCopyColumn"):
            self.wsFrame.OnMenuItemCopyColumn(event)
        elif eventId == xrc.XRCID("PMenuItemConvTypeColumn"):
            self.wsFrame.OnMenuItemConvTypeColumn(event)
        elif eventId == xrc.XRCID("PMenuItemInsertColumn"):
            self.wsFrame.OnMenuItemInsertColumn(event)
        elif eventId == xrc.XRCID("PMenuItemAppendColumn"):
            self.wsFrame.OnMenuItemInsertColumn(event)
        elif eventId == xrc.XRCID("PMenuItemDeleteColumn"):
            self.wsFrame.OnMenuItemDeleteColumn(event)
        elif eventId == xrc.XRCID("PMenuItemTransferFilter"):
            self.wsFrame.OnMenuItemTransferFilter(event)
        elif eventId == xrc.XRCID("PMenuItemSearch"):
            self.wsFrame.OnMenuItemSearch(event)
        elif eventId == xrc.XRCID("PMenuItemSortAscend"):
            self.wsFrame.OnMenuSort(event)
        elif eventId == xrc.XRCID("PMenuItemSortDescend"):
            self.wsFrame.OnMenuSort(event)
        elif eventId == xrc.XRCID("PMenuItemSortSpecify"):
            self.wsFrame.OnMenuSort(event)
        elif eventId == xrc.XRCID("PMenuItemCalc"):
            self.wsFrame.OnMenuItemCalc(event)
        elif eventId == xrc.XRCID("PMenuItemJump"):
            self.wsFrame.OnMenuItemJump(event)
        elif eventId == xrc.XRCID("PMenuItemFind"):
            self.wsFrame.OnMenuItemFind(event)
        elif eventId == xrc.XRCID("PMenuItemPrev"):
            self.wsFrame.OnMenuItemPrevNext(event)
        elif eventId == xrc.XRCID("PMenuItemNext"):
            self.wsFrame.OnMenuItemPrevNext(event)
        elif eventId == xrc.XRCID("PMenuItemCopy"):
            self.wsFrame.OnMenuItemCopy(event)
        elif eventId == xrc.XRCID("PMenuItemCopyWithName"):
            self.wsFrame.OnMenuItemCopy(event)
        elif eventId == xrc.XRCID("PMenuItemPaste"):
            self.wsFrame.OnMenuItemPaste(event)
        elif eventId == xrc.XRCID("PMenuItemClearData"):
            self.wsFrame.OnMenuItemPaste(event)
        elif eventId == xrc.XRCID("PMenuItemEditData"):
            self.wsFrame.OnMenuItemPaste(event)
        elif eventId == xrc.XRCID("PMenuItemGridSelectAll"):
            self.topRowNo = 1
            self.bottomRowNo = self.rows
            self.leftColNo = 1
            self.rightColNo = self.cols - 1
            self.wsFrame.OnMenuItemSelectAll(event)
        return

#---------------------------------------------------------------------------------------------------
## グリッドラベル部設定クラス
class MyGrid(gridlib.Grid, glr.GridWithLabelRenderersMixin):
    def __init__(self, parent):
        gridlib.Grid.__init__(self, parent)
        glr.GridWithLabelRenderersMixin.__init__(self)

#---------------------------------------------------------------------------------------------------
## グリッド列ラベル部設定クラス
class MyColLabelRenderer(glr.GridLabelRenderer):
    def __init__(self, icon, text):
        self._bmp = icon.GetBitmap()
        self._text = "     " + text
        
    def Draw(self, grid, dc, rect, col):
        dc.SetBrush(wx.Brush(grid.GetLabelBackgroundColour()))
        pen = wx.Pen(grid.GetGridLineColour())
        pen.SetWidth(1)
        dc.SetPen(pen)
        dc.DrawRectangleRect(rect)
        #x = rect.left + (rect.width - self._bmp.GetWidth()) / 2
        x = rect.left + 6
        y = rect.top + (rect.height - self._bmp.GetHeight()) / 2
        hAlign, vAlign = grid.GetColLabelAlignment()
        self.DrawText(grid, dc, rect, self._text, hAlign, vAlign)
        if col > 0:
            dc.DrawBitmap(self._bmp, x, y, True)

#---------------------------------------------------------------------------------------------------
## グリッドコーナーラベル部設定クラス
class MyCornerLabelRenderer(glr.GridLabelRenderer):
    def __init__(self, text):
        self._text = text
        
    def Draw(self, grid, dc, rect, col):
        dc.SetBrush(wx.Brush(grid.GetLabelBackgroundColour()))
        pen = wx.Pen(grid.GetGridLineColour())
        pen.SetWidth(1)
        dc.SetPen(pen)
        dc.DrawRectangleRect(rect)
        hAlign, vAlign = grid.GetColLabelAlignment()
        self.DrawText(grid, dc, rect, self._text, wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)


