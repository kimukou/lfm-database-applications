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
import csv

# wxPython
import wx
import wx.grid
import wx.grid as gridlib
import wx.xrc as xrc
import wx.wizard as wiz

# LFM
from LFM_Macro import *
import lfmtblpy
import lfmutilpy

# ##################################################################################################
#
#         PyFIT インポートウイザード
#
# ##################################################################################################

## デフォルト文字コード
ENC_DEFAULT = "UTF8"

## OS文字コード
ENC_OS = "MS932"
#ENC_OS = "UTF8"

## DB文字コード
ENC_DB = "MS932"
#ENC_DB = "UTF8"

#---------------------------------------------------------------------------------------------------
class TextImportWizard(wiz.Wizard):
    def __init__(self, app, wsInfo, wsTree, wsFrame):
        pre = wx.wizard.PreWizard()
        self.wsInfo = wsInfo
        self.wsTree = wsTree
        self.wsFrame = wsFrame
        self.frame = app.res.LoadObject(pre, 'ImportWizard', 'wxWizard')
        self.PostCreate(pre)

        self.page1 = xrc.XRCCTRL(self, "TxWzFileSelect")
        self.page2 = xrc.XRCCTRL(self, "TxWzSettingPage")
        self.page3 = xrc.XRCCTRL(self, "TxWzDisplayPage")
        self.skipline= 0
        self.pageNo = 1
        self.Path = ""
        self.csvfilename = ""
        self.filename = ""

        self.wizard_fltnames      = []
        self.wizard_tablename     = ""
        self.wizard_fltdatatypes  = []
        self.wizard_fltdata       = []
        self.wizard_separator     = ','
        self.wizard_prv_separator = ','
        self.wizard_gridlines     = 0
        self.selIndex = 0
        self.p2grid = None
        self.IsRefresh = 0

        self.Bind(wiz.EVT_WIZARD_PAGE_CHANGING, self.onPageChanging)
        self.Bind(wiz.EVT_WIZARD_FINISHED, self.onFinished)

        ## Page1
        self.CSVRadioButton = xrc.XRCCTRL(self.page1, "RadioButtonSelectCSV")
        self.TABRadioButton = xrc.XRCCTRL(self.page1, "RadioButtonSelectTAB")
        wx.FindWindowById(wx.ID_FORWARD).Disable()

        self.fileType       = xrc.XRCCTRL(self.page1, "RadioButtonSelectCSV")
        self.fileSelButton  = xrc.XRCCTRL(self.page1, "FileSelect")
        self.fileAbsName    = xrc.XRCCTRL(self.page1, "FileAbsName")
        self.page1.Bind(wx.EVT_BUTTON, self.onFileSelect, self.fileSelButton)
        self.CSVRadioButton.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButtonCSVSelection)
        self.TABRadioButton.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButtonTABSelection)

        ## Page2
        self.tableNameCtl = xrc.XRCCTRL(self.page2, "TextCtrlTableName")
        self.tableNameCtl.SetValue("NewTable")  # テーブル名
        self.tableNameCtl.SetFocus()
        self.tableNameCtl.SetSelection(-1, -1)  # 全テキスト選択
        wizard_tablename = self.tableNameCtl.GetValue()

        self.cuttop = xrc.XRCCTRL(self.page2, "CheckBoxCutTop")
        self.page2.Bind(wx.EVT_CHECKBOX, self.onCutTopSelect, self.cuttop)

        self.fltListCtl = xrc.XRCCTRL(self.page2, "ListBoxFilterItems")
        self.page2.Bind(wx.EVT_LISTBOX, self.onFilterSelect, self.fltListCtl)

        self.FilterNameCtl = xrc.XRCCTRL(self.page2, "TextCtrlFilterName")
        self.FilterNameCtl.Bind(wx.EVT_TEXT, self.OnFilterNameUpdate)

        self.FilterRadioButtonTypeStr      = xrc.XRCCTRL(self.page2, "RadioButtonStringType")
        self.FilterRadioButtonTypeInteger  = xrc.XRCCTRL(self.page2, "RadioButtonIntegerType")
        self.FilterRadioButtonTypeDouble   = xrc.XRCCTRL(self.page2, "RadioButtonDoubleType")
        self.FilterRadioButtonTypeDate     = xrc.XRCCTRL(self.page2, "RadioButtonDateType")
        self.FilterRadioButtonTypeTime     = xrc.XRCCTRL(self.page2, "RadioButtonTimeType")
        self.FilterRadioButtonTypeDateTime = xrc.XRCCTRL(self.page2, "RadioButtonDateTimeType")
        self.FilterRadioButtonTypeNumeric  = xrc.XRCCTRL(self.page2, "RadioButtonNumericType")

        self.FilterRadioButtonTypeStr.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButtonSelString)
        self.FilterRadioButtonTypeInteger.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButtonSelInteger)
        self.FilterRadioButtonTypeDouble.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButtonSelDouble)
        self.FilterRadioButtonTypeDate.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButtonSelDate)
        self.FilterRadioButtonTypeTime.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButtonSelTime)
        self.FilterRadioButtonTypeDateTime.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButtonSelDateTime)
        self.FilterRadioButtonTypeNumeric.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButtonSelNumeric)

        self.filterdisplay  = xrc.XRCCTRL(self.page2, "FilterDisplay")

        ## Page3
        self.filterdisplay2 = xrc.XRCCTRL(self.page3, "FilterDisplay")
        self.tableinfo      = xrc.XRCCTRL(self.page3, "TableInfo")

    def OnRadioButtonCSVSelection(self, evt):
        return

    def OnRadioButtonTABSelection(self, evt):
        return

    def ReInit(self):
        prev_rows = self.p2grid.table.GetView().GetNumberRows()
        prev_cols = len(self.wizard_fltnames)
        self.skipline= 0
        self.cuttop.SetValue(False)
        self.fltListCtl.Clear()
        self.update_page2()
        self.cols = len(self.wizard_fltdata[0])

        self.p2grid.BeginBatch()

        if self.count < prev_rows :
            msg = wx.grid.GridTableMessage(self.p2grid.table, gridlib.GRIDTABLE_NOTIFY_ROWS_DELETED, 0, prev_rows-self.count)
            self.p2grid.table.GetView().ProcessTableMessage(msg)
        elif self.count > prev_rows :
            msg = wx.grid.GridTableMessage(self.p2grid.table, gridlib.GRIDTABLE_NOTIFY_ROWS_APPENDED, self.count-prev_rows,0 )
            self.p2grid.table.GetView().ProcessTableMessage(msg)

        if self.cols < prev_cols :
            msg = wx.grid.GridTableMessage(self.p2grid.table, gridlib.GRIDTABLE_NOTIFY_COLS_DELETED,0,prev_cols-self.cols)
            self.p2grid.table.GetView().ProcessTableMessage(msg)
        elif self.cols > prev_cols :
            msg = wx.grid.GridTableMessage(self.p2grid.table, gridlib.GRIDTABLE_NOTIFY_COLS_APPENDED, self.cols-prev_cols,0)
            self.p2grid.ProcessTableMessage(msg)

        self.p2grid.EndBatch()
        self.p2grid.AdjustScrollbars()
        self.p2grid.AutoSizeColumns(True)
        self.p2grid.ForceRefresh()

        return

    def Type2String(self, type):
        self.type = type
        if self.type == lfmtblpy.D5_DT_STRING:
            return u"文字列"
        elif self.type == lfmtblpy.D5_DT_INTEGER:
            return u"整数"
        elif self.type == lfmtblpy.D5_DT_DOUBLE:
            return u"浮動小数"
        elif self.type == lfmtblpy.D5_DT_DATE:
            return u"日付"
        elif self.type == lfmtblpy.D5_DT_TIME:
            return u"時刻"
        elif self.type == lfmtblpy.D5_DT_DATETIME:
            return u"日付時刻"
        elif self.type == lfmtblpy.D5_DT_DECIMAL:
            return u"NUMERIC"
        return u"文字列"

    def OnUpdateFilterListCtl(self,isSkip):
        if isSkip == 1:
            for i in range(len(self.wizard_fltnames)):
                self.type = self.wizard_fltdatatypes[i]
                typestr = self.Type2String(self.type)
                fltname =self.wizard_fltdata[0][i]
                liststr = "%i.  %s  %s" % (i+1, typestr, fltname)
                self.fltListCtl.Delete(i)
                self.fltListCtl.Insert(liststr, i)
        else:
            for i in range(len(self.wizard_fltnames)):
                self.type = self.wizard_fltdatatypes[i]
                typestr = self.Type2String(self.type)
                fltname =self.wizard_fltnames[i]
                liststr = "%i.  %s  %s" % (i+1, typestr, fltname)
                self.fltListCtl.Delete(i)
                self.fltListCtl.Insert(liststr,i)
                self.fltListCtl.SetSelection(self.selIndex, True)

    def OnListCtrlUpdate(self):
        if self.skipline == 1 :
            fltname =self.wizard_fltdata[0][self.selIndex]
        else:
            fltname = self.wizard_fltnames[self.selIndex]
        self.type = self.wizard_fltdatatypes[self.selIndex]
        typestr = self.Type2String(self.type)
        liststr = "%i.  %s  %s" % (self.selIndex+1, typestr, fltname)
        self.fltListCtl.Delete(self.selIndex)
        self.fltListCtl.Insert(liststr,self.selIndex)
        self.fltListCtl.SetSelection(self.selIndex, True)
        
        self.p2grid.ForceRefresh()
        self.p2grid.ClearSelection()
        self.p2grid.SelectCol(self.selIndex, True)
        self.p2grid.MakeCellVisible(0, self.selIndex)

    def OnFilterNameUpdate(self, evt):
        if self.skipline == 0 :
            fltname = self.FilterNameCtl.GetValue()
            self.wizard_fltnames[self.selIndex] = fltname
            self.OnListCtrlUpdate()
        return

    def OnRadioButtonSelString(self, evt):
        self.wizard_fltdatatypes[self.selIndex] = lfmtblpy.D5_DT_STRING
        self.OnListCtrlUpdate()
        return

    def OnRadioButtonSelInteger(self, evt):
        self.wizard_fltdatatypes[self.selIndex] = lfmtblpy.D5_DT_INTEGER
        self.OnListCtrlUpdate()
        return

    def OnRadioButtonSelDouble(self, evt):
        self.wizard_fltdatatypes[self.selIndex] = lfmtblpy.D5_DT_DOUBLE
        self.OnListCtrlUpdate()
        return

    def OnRadioButtonSelDate(self, evt):
        self.wizard_fltdatatypes[self.selIndex] = lfmtblpy.D5_DT_DATE
        self.OnListCtrlUpdate()
        return

    def OnRadioButtonSelTime(self, evt):
        self.wizard_fltdatatypes[self.selIndex] = lfmtblpy.D5_DT_TIME
        self.OnListCtrlUpdate()
        return

    def OnRadioButtonSelDateTime(self, evt):
        self.wizard_fltdatatypes[self.selIndex] = lfmtblpy.D5_DT_DATETIME
        self.OnListCtrlUpdate()
        return

    def OnRadioButtonSelNumeric(self, evt):
        self.wizard_fltdatatypes[self.selIndex] = lfmtblpy.D5_DT_DECIMAL
        self.OnListCtrlUpdate()
        return

    def onFilterSelect(self, evt):
        self.selIndex = self.fltListCtl.GetSelection()
        if self.skipline == 1:
            self.FilterNameCtl.SetValue(self.wizard_fltdata[0][self.selIndex])
        else:
            self.FilterNameCtl.SetValue(self.wizard_fltnames[self.selIndex])
        self.type = self.wizard_fltdatatypes[self.selIndex]
        if self.type == lfmtblpy.D5_DT_STRING:
            self.FilterRadioButtonTypeStr.SetValue(True)
        elif self.type == lfmtblpy.D5_DT_INTEGER:
            self.FilterRadioButtonTypeInteger.SetValue(True)
        elif self.type == lfmtblpy.D5_DT_DOUBLE:
            self.FilterRadioButtonTypeDouble.SetValue(True)
        elif self.type == lfmtblpy.D5_DT_DATE:
            self.FilterRadioButtonTypeDate.SetValue(True)
        elif self.type == lfmtblpy.D5_DT_TIME:
            self.FilterRadioButtonTypeTime.SetValue(True)
        elif self.type == lfmtblpy.D5_DT_DATETIME:
            self.FilterRadioButtonTypeDateTime.SetValue(True)
        elif self.type == lfmtblpy.D5_DT_DECIMAL:
            self.FilterRadioButtonTypeNumeric.SetValue(True)

        return

    def onFileSelect(self, evt):
        global g_CurPath
        Dlg = wx.FileDialog(self.page1, message=u"インポートファイル選択", defaultDir="", defaultFile="",
                            wildcard = "CSV File (*.CSV)|*.csv|Text File (*.TXT)|*.txt|All (*.*)|*.*")
        AnsBtn = Dlg.ShowModal()
        AnsFilename = Dlg.GetFilename()
        AnsFilePath = Dlg.GetPath()
        AnsDirPath = Dlg.GetDirectory()
        Dlg.Destroy()
        if AnsBtn != wx.ID_OK:
            return

        g_CurPath = AnsDirPath
        #self.fileAbsName.SetValue(AnsFilePath)
        self.csvfilename = AnsFilePath
        self.filename    = AnsFilename
        self.Path        = AnsDirPath
        self.IsRefresh   = 1

        p1grid = ImportWizardPage1TableGrid(self.fileAbsName, self.Path, self.filename)
        rect = self.fileAbsName.GetSize()
        p1grid.SetSize(rect)

        wx.FindWindowById(wx.ID_FORWARD).Enable()

        return

    def onCutTopSelect(self, evt):
        if self.cuttop.GetValue() == True:
            self.skipline = 1
            self.FilterNameCtl.SetValue(self.wizard_fltdata[0][self.selIndex])
            self.FilterNameCtl.Disable()
            msg = gridlib.GridTableMessage(self.p2grid.table,                             # The table
                                           gridlib.GRIDTABLE_NOTIFY_ROWS_DELETED,         # what we did to it
                                           1,
                                           1                                              # how many
                                          )
        else:
            self.skipline = 0
            self.FilterNameCtl.SetValue(self.wizard_fltnames[self.selIndex])
            self.FilterNameCtl.Enable()
            msg = gridlib.GridTableMessage(self.p2grid.table,                             # The table
                                           gridlib.GRIDTABLE_NOTIFY_ROWS_APPENDED,        # what we did to it
                                           1                                              # how many
                                          )
        self.OnUpdateFilterListCtl(self.skipline)
        self.p2grid.table.GetView().ProcessTableMessage(msg)
        self.p2grid.AutoSizeColumns(True)
        self.p2grid.ForceRefresh()

        return

    def update_page2(self):
        self.tableNameCtl.SetValue(self.filename.split('.')[0])
        self.wizard_separator = ','
        if self.fileType.GetValue() == False:
            self.wizard_separator = '\t'

        #self.file=file(self.csvfilename, 'r')
        # read maximum 10k bytes
        #lines = self.file.readlines(10000)

        self.file=codecs.open(self.csvfilename, 'r', ENC_OS)
        lines = []
        for readcount in range( 11 ):
            lines.append(self.file.readline())

        self.count = len(lines)
        del self.wizard_fltnames[0::]
        del self.wizard_fltdatatypes[0::]
        del self.wizard_fltdata[0::]

        self.wizard_prv_separator = self.wizard_separator
        if self.count > 10:
            self.count = 10
        self.wizard_gridlines=self.count

        csvfile = csv.reader(lines, delimiter=self.wizard_separator)
        self.wizard_fltdata.extend(csvfile)
        #self.file.seek(0)

        for i in range(len(self.wizard_fltdata[0])):
            self.wizard_fltnames.append(u"項目_%d"%(i+1))
            typestr = u"文字列"
            fltname = u"項目_%d"%(i+1)
            liststr = "%i.  %s  %s" % (i+1, typestr, fltname)
            self.fltListCtl.Append(liststr)
            self.wizard_fltdatatypes.append(lfmtblpy.D5_DT_STRING)

        return 

    def onPageChanging(self, evt):
        pg=evt.GetPage()
        if evt.GetDirection():
            # forward
            self.separator = ','
            if self.fileType.GetValue() == False:
                self.separator= '\t'
            if self.wizard_prv_separator != self.separator:
                self.IsRefresh = 1
            if  self.pageNo == 1: 
                if len(self.wizard_fltnames) > 0 :
                    if self.IsRefresh == 1:
                        self.ReInit()
                        self.IsRefresh = 0
                else:
                    self.update_page2()
            self.pageNo += 1
        else:
            # backward
            self.pageNo -= 1
        if  self.pageNo == 2:
            if self.p2grid == None:
                p2grid = ImportWizardGrid(self,self.filterdisplay)
                rect = self.filterdisplay.GetSize()
                p2grid.SetSize(rect)
                self.p2grid = p2grid
        if  self.pageNo == 3:
            infos = u"テーブル名："
            infos += self.tableNameCtl.GetValue()
            self.tableinfo.SetValue(infos)
            sinfo = u"\n項目数：%i" % len(self.wizard_fltnames)
            self.tableinfo.AppendText(sinfo)
            self.tableinfo.AppendText("\n")
            self.tableinfo.AppendText("\n")
            #sinfo = "click Finish to create Table"
            #self.tableinfo.AppendText(sinfo)
            
            p3grid = ImportWizardGrid(self,self.filterdisplay2)
            rect = self.filterdisplay2.GetSize()
            p3grid.SetSize(rect)

    def onFinished(self, evt):
        S_tablename = self.tableNameCtl.GetValue()
        structfilename = "py_struct_tmp.txt"
        #catalogfile=file(structfilename, 'w')
        catalogfile=codecs.open(self.Path +"/"+ structfilename, 'w', ENC_OS)
        if self.skipline == 1 :
            catalogfile.write("//cuttop")
            catalogfile.write("\n")
        if self.fileType.GetValue() == True:
            catalogfile.write("//csv")
        else:
            catalogfile.write("//tab")
        catalogfile.write("\n")
        i = 0
        for i in range(len(self.wizard_fltnames)):
            self.type = self.wizard_fltdatatypes[i]
            if self.type == lfmtblpy.D5_DT_STRING:
                catalogfile.write("A\t01\t")
            elif self.type == lfmtblpy.D5_DT_INTEGER:
                catalogfile.write("I\t01\t")
            elif self.type == lfmtblpy.D5_DT_DOUBLE:
                catalogfile.write("F\t01\t")
            elif self.type == lfmtblpy.D5_DT_DATE:
                catalogfile.write("D\t01\t")
            elif self.type == lfmtblpy.D5_DT_TIME:
                catalogfile.write("T\t01\t")
            elif self.type == lfmtblpy.D5_DT_DATETIME:
                catalogfile.write("E\t01\t")
            elif self.type == lfmtblpy.D5_DT_DECIMAL:
                catalogfile.write("N\t01\t")

            if self.skipline == 1:
                catalogfile.write(self.wizard_fltdata[0][i])
            else:
                catalogfile.write(self.wizard_fltnames[i])
            catalogfile.write("\n") 

        catalogfile.close()

        ret = MCatalogEx(S_tablename, self.Path, structfilename, self.Path, self.filename)
        # remove temporary catalog file
        #os.remove(structfilename)
        os.remove(self.Path +"/"+ structfilename)

        self.wsFrame.outputLog(ret)

        if ret.retCode < 0:
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
        self.wsInfo.appendTable(tid)
        self.wsTree.appendTable(tid)

        return

#---------------------------------------------------------------------------------------------------
class ImportWizardGridTable(gridlib.PyGridTableBase):
    def __init__(self, txtWizard):
        gridlib.PyGridTableBase.__init__(self)
        self.txtWizard = txtWizard

    def GetNumberRows(self):
        if self.txtWizard.skipline == 1:
            return (self.txtWizard.wizard_gridlines - 1)
        return (self.txtWizard.wizard_gridlines)

    def GetNumberCols(self):
        return len(self.txtWizard.wizard_fltnames)

    def IsEmptyCell(self, row, col):
        return True

    def GetValue(self, row, col):
        if self.txtWizard.skipline == 1:
            return self.txtWizard.wizard_fltdata[row+1][col]
        else:
            return self.txtWizard.wizard_fltdata[row][col]

    def GetColLabelValue(self, col):
        if self.txtWizard.skipline == 1:
            return self.txtWizard.wizard_fltdata[0][col]
        else:
            return self.txtWizard.wizard_fltnames[col]

    def GetRowLabelValue(self, row):
        return row + 1

#---------------------------------------------------------------------------------------------------
class ImportWizardGrid(gridlib.Grid):
    def __init__(self, txtWizard, parent):
        gridlib.Grid.__init__(self,parent, -1)
        table = ImportWizardGridTable(txtWizard)
        self.table =table
        self.SetTable(table, True)
        self.SetRowLabelSize(30)
        attr = gridlib.GridCellAttr()
        attr.SetTextColour(wx.BLACK)
        attr.SetBackgroundColour('#A9A9A9')
        attr.SetFont(wx.Font(9, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.SetMargins(0,0)
        self.AutoSizeColumns(True)

        gridlib.EVT_GRID_CELL_LEFT_DCLICK(self, self.OnLeftDClick)

    def OnLeftDClick(self, evt):
        if self.CanEnableCellControl():
            self.EnableCellEditControl()

#---------------------------------------------------------------------------
class ImportWizardPage1TableGrid(gridlib.Grid):
    def __init__(self, parent, pathname, filename):
        gridlib.Grid.__init__(self, parent, -1)
        table = ImportWizardPage1Grid(pathname, filename)
        self.table =table
        self.SetTable(table, True)
        self.SetRowLabelSize(30)
        self.SetMargins(0,0)
        self.AutoSizeColumns(False)

#---------------------------------------------------------------------------
class ImportWizardPage1Grid(gridlib.PyGridTableBase):
    def __init__(self, pathname, filename):
        gridlib.PyGridTableBase.__init__(self)
        self.Path = pathname
        self.filename = filename
        self.SetupInit()
        return 

    def SetupInit(self):
        #os.chdir(g_DirPath)
        self.file = codecs.open(self.Path +"/"+ self.filename, 'r', ENC_OS)
        self.lines = []
        for readcount in range( 10 ):
            line = self.file.readline()
            self.lines.append(line)
        self.count = len(self.lines)
        return

    def GetNumberRows(self):
        return self.count

    def GetNumberCols(self):
        return 1
        
    def IsEmptyCell(self, row, col):
        return True

    def GetValue(self, row, col):
        return self.lines[row]

    def SetValue(self, row, col, value):
        return

    def GetColLabelValue(self, col):
        return self.Path +"/"+ self.filename

#---------------------------------------------------------------------------------------------------
