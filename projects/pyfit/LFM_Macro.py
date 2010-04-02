#!/usr/bin/env python
# -*- coding: utf-8 -*-

## @package LFM_Macro
# LFM Macro
#
# @author Turbo Data Laboratories, Inc.
# @date 2010/02/20

import sys
import types
import codecs
import os
import atexit
import math
import time
import datetime
import fnmatch
import decimal
import ConfigParser
import tempfile
import re

# LFM
import lfmtblpy
import lfmutilpy

# ##################################################################################################
#
#         PyFIT マクロ
#
# ##################################################################################################

## デフォルト文字コード
ENC_DEFAULT = "UTF8"

## OS文字コード
ENC_OS = "MS932"
#ENC_OS = "UTF8"

## DB文字コード
ENC_DB = "UTF8"

# 標準入出力文字コード設定
sys.stdin  = codecs.getreader(ENC_OS)(sys.stdin)
sys.stdout = codecs.getwriter(ENC_OS)(sys.stdout)
sys.stderr = codecs.getwriter(ENC_OS)(sys.stderr)

# 設定ファイル
CONFIG_FILE = "LFM_Macro.ini"

# ログファイル
LOG_FILE_BASE_M = "LFM_Macro_"  # マクロログファイル名ベース
LOG_FILE_BASE_A = "LFM_API_"    # APIログファイル名ベース
LOG_FILE_EXT = ".log"           # ログファイル拡張子

LOG_FILE_PATH = "./log"         # ログファイルパス
LOG_FILE_MAX = 10               # 最大ログファイル数
LOG_FILE_CODE = "UTF8"          # ログファイル文字コード
LOG_LV_M = 0                    # マクロログ出力レベル
LOG_LV_A = 0                    # APIログ出力レベル

# 一時ファイル
TMP_ADD_HEADER_FILE = "__tmp_add_header.txt"

# 定数
FILE_EXT_WS     = ".D5D"
FILE_EXT_TABLE  = ".D5T"
TABLE_KIND_REAL = 0
TABLE_KIND_JOIN = 2

D5_NULL_INT  = -sys.maxint-1
D5_NULL_DBL  = float("-inf")
STR_NAN      = "NaN"
NULL_NUM_STR = "-170141183460469231731687303715884105728"

BYTE_SIZE_INTEGER =  4
BYTE_SIZE_DOUBLE  =  8
BYTE_SIZE_NUMERIC = 16
BYTE_SIZE_POINTER =  4 # ※初期化処理時に正式設定

MAP_DATA_TYPE_CN = {'I':lfmtblpy.D5_DT_INTEGER,  'F':lfmtblpy.D5_DT_DOUBLE \
                ,   'T':lfmtblpy.D5_DT_TIME,     'D':lfmtblpy.D5_DT_DATE   \
                ,   'E':lfmtblpy.D5_DT_DATETIME, 'A':lfmtblpy.D5_DT_STRING \
                ,   'N':lfmtblpy.D5_DT_DECIMAL}
MAP_DATA_TYPE_NC = {lfmtblpy.D5_DT_INTEGER: 'I', lfmtblpy.D5_DT_DOUBLE:'F' \
                ,   lfmtblpy.D5_DT_TIME:    'T', lfmtblpy.D5_DT_DATE:  'D' \
                ,   lfmtblpy.D5_DT_DATETIME:'E', lfmtblpy.D5_DT_STRING:'A' \
                ,   lfmtblpy.D5_DT_DECIMAL: 'N'}
MAP_DATA_TYPE_SIZE = {lfmtblpy.D5_DT_INTEGER : BYTE_SIZE_INTEGER \
                ,     lfmtblpy.D5_DT_DOUBLE  : BYTE_SIZE_DOUBLE  \
                ,     lfmtblpy.D5_DT_TIME    : BYTE_SIZE_DOUBLE  \
                ,     lfmtblpy.D5_DT_DATE    : BYTE_SIZE_DOUBLE  \
                ,     lfmtblpy.D5_DT_DATETIME: BYTE_SIZE_DOUBLE  \
                ,     lfmtblpy.D5_DT_DECIMAL : BYTE_SIZE_NUMERIC \
                ,     lfmtblpy.D5_DT_STRING  : BYTE_SIZE_POINTER}  # ※初期化処理時に正式設定
MAP_ROUND_MODE = {"ROUND_UP":0, "ROUND_DOWN":1, "ROUND_CEILING":2, "ROUND_FLOOR":3, "ROUND_HALF_UP":4, "ROUND_HALF_DOWN":5, "ROUND_HALF_EVEN":6 \
                , "0":0, "1":1, "2":2, "3":3, "4":4, "5":5, "6":6 \
                , 0:0, 1:1, 2:2, 3:3, 4:4, 5:5, 6:6}
LIST_DATETIME_TYPE = (lfmtblpy.D5_DT_TIME, lfmtblpy.D5_DT_DATE, lfmtblpy.D5_DT_DATETIME)
LIST_DOUBLE_TYPE   = (lfmtblpy.D5_DT_DOUBLE,) + LIST_DATETIME_TYPE
LIST_NUM_TYPE      = (lfmtblpy.D5_DT_INTEGER, lfmtblpy.D5_DT_DOUBLE, lfmtblpy.D5_DT_DECIMAL)

DATE_FORMAT = "%Y/%m/%d"
DATETIME_BASE = datetime.datetime(1899,12,30)
g_fMSecsPerDay = (24.0 * 60.0 * 60.0 * 1000.0)  # 一日のミリ秒(double)
g_iMSecsPerDay = (24 * 60 * 60 * 1000)          # 一日のミリ秒(int)

COMMA_ONOFF_FIELD            = 4    # カンマ編集のON/OFF指定情報
UNDER_0_DIGITS_FIELD         = 5    # 小数点以下桁数指定情報
UNDER_0_DIGITS_FIELD_NUMERIC = 6    # Numeric型小数点以下桁数指定情報
ROUNDING_MODE                = 7    # 丸め区分指定情報

RECONO_MARK_YES  = 'Y'
RECONO_MARK_NO   = 'N'
ALL_FILTERS_MARK = '*'
NO_FILTER_MARK   = '-'
MAP_YN = {0:RECONO_MARK_NO, 1:RECONO_MARK_YES, False:RECONO_MARK_NO, True:RECONO_MARK_YES}

LIST_SET_OP = ("AND", "OR", "SUB")

SORT_TYPE_ASC = "ASC"   # 昇順
SORT_TYPE_DSC = "DSC"   # 降順

SEARCH_SYMBOL = '*'
SEARCH_ESCAPE = '\\'

# global
g_MConfig = None        # マクロ設定値
g_flagInit = False      # フラグ：初期化
g_fLogM = None          # ファイルハンドル：マクロログ
g_fLogA = None          # ファイルハンドル：APIログ
g_flagRetObj = False    # フラグ：戻り値にメッセージ付加
g_Env = None            # 環境情報（lfmtblpy.TREnvironment）

## ログクラス
class MLog():
    LV_DBG = 0  # デバッグ
    LV_INF = 1  # 情報
    LV_WRN = 2  # 警告
    LV_ERR = 3  # エラー
    LV_FTL = 4  # 致命的
    MAP_LV_NC = {LV_DBG:'D', LV_INF:'I', LV_WRN:'W', LV_ERR:'E', LV_FTL:'F'}
    def __init__(self):
        return

## マクロ設定値クラス
class MConfig():
    def __init__(self, configFile):
        self.configFile = configFile
        self.configParser = ConfigParser.ConfigParser()

        # 文字コード
        self.ENC_OS = ENC_OS
        self.ENC_DB = ENC_DB

        # ログ
        self.LOG_FILE_PATH = LOG_FILE_PATH
        self.LOG_FILE_MAX  = LOG_FILE_MAX
        self.LOG_FILE_CODE = LOG_FILE_CODE
        self.LOG_LV_M = LOG_LV_M
        self.LOG_LV_A = LOG_LV_A

        return

    ## 文字列化：設定値一覧
    def __str__(self):
        buf = "[code]\n"
        buf += "ENC_OS=[%s]\n" % self.ENC_OS
        buf += "ENC_DB=[%s]\n" % self.ENC_DB
        buf += "[log]\n"
        buf += "LOG_FILE_PATH=[%s]\n" % self.LOG_FILE_PATH
        buf += "LOG_FILE_MAX=[%d]\n" % self.LOG_FILE_MAX
        buf += "LOG_FILE_CODE=[%s]\n" % self.LOG_FILE_CODE
        buf += "LOG_LV_M=[%d]\n" % self.LOG_LV_M
        buf += "LOG_LV_A=[%d]\n" % self.LOG_LV_A
        return buf

    ## 設定ファイル読み込み
    def load(self):
        ret = self.configParser.read(self.configFile)

        # 文字コード
        section = "code"
        if self.configParser.has_section(section):
            option = "ENC_OS"
            if self.configParser.has_option(section, option):
                self.ENC_OS = self.configParser.get(section, option)
            option = "ENC_DB"
            if self.configParser.has_option(section, option):
                self.ENC_DB = self.configParser.get(section, option)

        # ログ
        section = "log"
        if self.configParser.has_section(section):
            option = "LOG_FILE_PATH"
            if self.configParser.has_option(section, option):
                self.LOG_FILE_PATH = self.configParser.get(section, option)
            option = "LOG_FILE_MAX"
            if self.configParser.has_option(section, option):
                self.LOG_FILE_MAX = self.configParser.getint(section, option)
            option = "LOG_FILE_CODE"
            if self.configParser.has_option(section, option):
                self.LOG_FILE_CODE = self.configParser.get(section, option)
            option = "LOG_LV_M"
            if self.configParser.has_option(section, option):
                self.LOG_LV_M = self.configParser.getint(section, option)
            option = "LOG_LV_A"
            if self.configParser.has_option(section, option):
                self.LOG_LV_A = self.configParser.getint(section, option)

        return

## マクロ例外クラス
class MacroError(Exception):
    def __init__(self, retCode, msg):
        self.retCode = retCode
        self.msg = msg
    def __str__(self):
        return repr(self.msg)
#       return str(self.msg)

## マクロ戻り値クラス
class RetVal():
    def __init__(self):
        init()
        self.funcName = ""              # マクロ名
        self.startTime = time.clock()   # 開始時間
        self.retCode  = 0               # リターンコード
        self.retData  = None            # リターンデータ
        self.retMsgsM = []              # マクロログ
        self.retMsgsA = []              # APIログ
        self.logLv = MLog.LV_INF        # ログレベル
        return

    def __str__(self):
        return str(self.retCode)

    def appendLogM(self, msg, lv=MLog.LV_INF):
        #MACRO LOG DISABLED
        self.logLv = lv
        log = logM(msg)
        self.retMsgsM.append(log)
        return

    def appendLogM2(self, msg):
        #MACRO LOG DISABLED
        log = logM2(msg)
        self.retMsgsM.append(log)
        return

    def appendLogA(self, msg, lv=MLog.LV_INF):
        if lv >= g_MConfig.LOG_LV_A:
            log = logA(lv, msg)
            self.retMsgsA.append(log)
        return

    def makeRetVal(self, ret):
        self.elapsedTime = (time.clock() - self.startTime) * 1000   # 経過時間
        self.retCode = ret
        if ret < 0:
            self.logLv = MLog.LV_ERR
        if self.logLv >= g_MConfig.LOG_LV_M:
            log = logMRC(self.logLv, self.retMsgsM, self.funcName, self.retCode, self.elapsedTime)
            self.retMsgsM.append(log)
        else:
            del self.retMsgsM[:] # クリア
        if g_flagRetObj: # オブジェクトを返す
            return self
        return self.retCode # リターンコードのみ
        


## ワークスペース情報クラス
class WSInfo():
    def __init__(self):
        self.init()
        return

    ## 初期化共通
    def init(self):
        self.infoWSFile = None      # WSファイル(D5D)情報
        self.listTable = []         # テーブルIDリスト
        self.mapTableName = {}      # テーブル名マップ（名前→ID）
        self.mapTableInfo = {}      # テーブル情報マップ（ID→情報）
        self.mapJoinInfo = {}       # JOINテーブル情報マップ（ID→情報）
        return

    ## WSファイル(D5D)情報取得
    def getInfoWSFile(self, FilePath, FileName):
        funcName = "WSInfo.getFileD5DInfo"
        retVal = RetVal()
        msg = "## %s(ur\"%s\", ur\"%s\")" % (funcName, FilePath, FileName)
        retVal.appendLogM(msg, MLog.LV_DBG)

        try:
            if self.infoWSFile == None:
                self.infoWSFile = lfmtblpy.D5FileInfo()

            ret = getD5DFileInfo(retVal, FilePath, FileName, self.infoWSFile)

        except MacroError, e:
            ret = e.retCode
            print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        return retVal.makeRetVal(ret)

    ## テーブルファイル(D5T)情報取得
    def getInfoTableFile(self, FilePath, FileName):
        funcName = "WSInfo.getInfoTableFile"
        retVal = RetVal()
        msg = "## %s(ur\"%s\", ur\"%s\")" % (funcName, FilePath, FileName)
        retVal.appendLogM(msg, MLog.LV_DBG)

        try:
            infoFile = lfmtblpy.D5FileInfo()
            ret = getD5TFileInfo(retVal, FilePath, FileName, infoFile)

        except MacroError, e:
            ret = e.retCode
            print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        return retVal.makeRetVal(ret)

    def clearInfo(self):
        del self.listTable[:]
        self.mapTableName.clear()
        self.mapTableInfo.clear()
        self.mapJoinInfo.clear()
        return

    def update(self):
        funcName = "WSInfo.update"
        retVal = RetVal()
        msg = "## %s()" % (funcName)
        retVal.appendLogM(msg, MLog.LV_DBG)

        try:
            self.clearInfo()

            # テーブルIDリスト取得
            ret = getTableIDListM(retVal, self.listTable)

            # テーブル情報取得＆格納
            for tableId in self.listTable:
                self.appendTableSub(retVal, tableId)

            ret = 0

        except MacroError, e:
            ret = e.retCode
            print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        return retVal.makeRetVal(ret)

    def clear(self):
        funcName = "WSInfo.clear"
        retVal = RetVal()
        msg = "## %s()" % (funcName)
        retVal.appendLogM(msg, MLog.LV_DBG)

        self.clearInfo()
        ret = 0

        # Macro return
        return retVal.makeRetVal(ret)

    def getTotalMemorySize(self):
        funcName = "WSInfo.getTotalMemorySize"
        retVal = RetVal()
        #msg = "## %s()" % (funcName)
        #retVal.appendLogM(msg, MLog.LV_DBG)

        try:
            retVal.retData = getTotalMemorySize(retVal)
            #msg = "MemorySize=%d" % (retVal.retData)
            #retVal.appendLogM2(msg)
            ret = 0

        except MacroError, e:
            ret = e.retCode
            print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        #return retVal.makeRetVal(ret)
        return retVal

    def openTable(self, TableID):
        funcName = "WSInfo.openTable"
        retVal = RetVal()
        msg = "## %s(%d)" % (funcName, TableID)
        retVal.appendLogM(msg, MLog.LV_DBG)
        try:
            tableInfo = self.mapTableInfo[TableID]
            # セット情報取得
            tableInfo.nSet = getSetIDListM(retVal, TableID, tableInfo.listSet)
            tableInfo.curSetId = getCurrentSetID(retVal, TableID)
            for sid in tableInfo.listSet:
                self.appendSetSub(retVal, tableInfo, sid)
            # 項目情報取得
            tableInfo.nFilter = getFilterIDListM(retVal, TableID, tableInfo.listFilter)
            for fid in tableInfo.listFilter:
                self.appendFilterSub(retVal, tableInfo, fid)
            tableInfo.bOpen = True
            ret = 0

        except MacroError, e:
            ret = e.retCode
            print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        return retVal.makeRetVal(ret)

    def appendTable(self, TableID):
        funcName = "WSInfo.appendTable"
        retVal = RetVal()
        msg = "## %s(%d)" % (funcName, TableID)
        retVal.appendLogM(msg, MLog.LV_DBG)

        try:
            if TableID not in self.listTable:
                # テーブル情報取得＆格納
                self.listTable.append(TableID)
                self.appendTableSub(retVal, TableID)

            ret = 0

        except MacroError, e:
            ret = e.retCode
            print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        return retVal.makeRetVal(ret)

    def appendTableSub(self, retVal, TableID):
        # テーブル情報取得＆格納
        tableInfo = TableInfo()
        ret = getTablePropertyM(retVal, TableID, tableInfo)
        self.mapTableName[tableInfo.name] = TableID
        self.mapTableInfo[TableID] = tableInfo

        if self.isJoinTable(TableID):
            # JOINテーブル情報取得＆格納
            joinTableInfo = JoinTableInfo()
            ret = getJoinInfoExM(retVal, TableID, joinTableInfo)
            self.mapJoinInfo[TableID] = joinTableInfo

            # 参照先REALテーブル処理
            refTableInfo = self.mapTableInfo[joinTableInfo.idTableM]
            if TableID not in refTableInfo.listJoinRef:
                refTableInfo.listJoinRef.append(TableID)
            refTableInfo = self.mapTableInfo[joinTableInfo.idTableS]
            if TableID not in refTableInfo.listJoinRef:
                refTableInfo.listJoinRef.append(TableID)

        return

    def openSet(self, TableID, SetID):
        funcName = "WSInfo.openSet"
        retVal = RetVal()
        msg = "## %s(%d, %d)" % (funcName, TableID, SetID)
        retVal.appendLogM(msg, MLog.LV_DBG)

        try:
            # セット情報取得
            tableInfo = self.mapTableInfo[TableID]
            setInfo = tableInfo.mapSetInfo[SetID]
            ret = getSetInfoM(retVal, TableID, SetID, setInfo)

            setInfo.bOpen = True

            ret = 0

        except MacroError, e:
            ret = e.retCode
            print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        return retVal.makeRetVal(ret)

    def appendSet(self, TableID, SetID):
        funcName = "WSInfo.appendSet"
        retVal = RetVal()
        msg = "## %s(%d, %d)" % (funcName, TableID, SetID)
        retVal.appendLogM(msg, MLog.LV_DBG)

        try:
            tableInfo = self.mapTableInfo[TableID]
            if SetID not in tableInfo.listSet:
                # セット情報取得＆格納
                tableInfo.listSet.append(SetID)
                tableInfo.nSet += 1
                self.appendSetSub(retVal, tableInfo, SetID)

            ret = 0

        except MacroError, e:
            ret = e.retCode
            print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        return retVal.makeRetVal(ret)

    def appendSetSub(self, retVal, TableInfo, SetID):
        setInfo = SetInfo()
        ret = getSetInfoM(retVal, TableInfo.id, SetID, setInfo)
        TableInfo.mapSetInfo[SetID] = setInfo
        return

    def updateSet(self, TableID, SetID):
        funcName = "WSInfo.updateSet"
        retVal = RetVal()
        msg = "## %s(%d, %d)" % (funcName, TableID, SetID)
        retVal.appendLogM(msg, MLog.LV_DBG)

        try:
            # セット情報取得
            tableInfo = self.mapTableInfo[TableID]
            setInfo = tableInfo.mapSetInfo[SetID]
            ret = getSetInfoM(retVal, TableID, SetID, setInfo)

        except MacroError, e:
            ret = e.retCode
            print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        return retVal.makeRetVal(ret)

    def updateSetSize(self, TableID, SetID):
        funcName = "WSInfo.updateSetSize"
        retVal = RetVal()
        msg = "## %s(%d, %d)" % (funcName, TableID, SetID)
        retVal.appendLogM(msg, MLog.LV_DBG)

        try:
            # セット情報取得
            tableInfo = self.mapTableInfo[TableID]
            setInfo = tableInfo.mapSetInfo[SetID]
            ret = getSetSize(retVal, TableID, SetID)
            setInfo.size = ret

        except MacroError, e:
            ret = e.retCode
            print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        return retVal.makeRetVal(ret)

    def closeSet(self, TableID, SetID):
        funcName = "WSInfo.closeSet"
        retVal = RetVal()
        msg = "## %s(%d, %d)" % (funcName, TableID, SetID)
        retVal.appendLogM(msg, MLog.LV_DBG)

        try:
            # セット情報取得
            tableInfo = self.mapTableInfo[TableID]
            setInfo = tableInfo.mapSetInfo[SetID]

            setInfo.bOpen = False

            ret = 0

        except MacroError, e:
            ret = e.retCode
            print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        return retVal.makeRetVal(ret)

    ## 指定テーブルのカレントセットID更新
    def updateCurSetId(self, TableID):
        funcName = "WSInfo.updateCurSetId"
        retVal = RetVal()
        msg = "## %s(%d)" % (funcName, TableID)
        retVal.appendLogM(msg, MLog.LV_DBG)

        try:
            tableInfo = self.mapTableInfo[TableID]
            tableInfo.curSetId = getCurrentSetID(retVal, TableID)
            retVal.retData = tableInfo.curSetId
            msg = "CurSetId=%d" % (retVal.retData)
            retVal.appendLogM2(msg)
            ret = 0

        except MacroError, e:
            ret = e.retCode
            print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        return retVal.makeRetVal(ret)

    def appendFilter(self, TableID, FltID, Idx):
        funcName = "WSInfo.appendFilter"
        retVal = RetVal()
        msg = "## %s(%d, %d, %d)" % (funcName, TableID, FltID, Idx)
        retVal.appendLogM(msg, MLog.LV_DBG)

        try:
            tableInfo = self.mapTableInfo[TableID]
            if FltID not in tableInfo.listFilter:
                # 項目情報取得＆格納
                if Idx < 0:
                    tableInfo.listFilter.append(FltID)
                else:
                    tableInfo.listFilter.insert(Idx, FltID)
                tableInfo.nFilter += 1
                self.appendFilterSub(retVal, tableInfo, FltID)

            ret = 0

        except MacroError, e:
            ret = e.retCode
            print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        return retVal.makeRetVal(ret)

    def appendFilterSub(self, retVal, TableInfo, FltID):
        filterInfo = FilterInfo()
        ret = getFilterInfoM(retVal, TableInfo.id, FltID, filterInfo)
        TableInfo.mapFilterInfo[FltID] = filterInfo
        TableInfo.mapFilterName[filterInfo.name] = FltID
        return

    ## テーブル名生成
    def generateTableName(self, PCSeedName):
        funcName = "WSInfo.generateTableName"
        retVal = RetVal()
        msg = "## %s(ur\"%s\")" % (funcName, PCSeedName)
        retVal.appendLogM(msg, MLog.LV_DBG)

        try:
            retVal.retData = generateTableName(retVal, PCSeedName)
            msg = "Name=%s" % (retVal.retData)
            retVal.appendLogM2(msg)
            ret = 0

        except MacroError, e:
            ret = e.retCode
            print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        return retVal.makeRetVal(ret)

    def getData1M(self, TableID, FltID, SetID, RowNo, ListData):
        funcName = "WSInfo.getData1M"
        retVal = RetVal()
        msg = "## %s(%d, %d, %d, %d, %s)" % (funcName, TableID, FltID, SetID, RowNo, strList(ListData))
        retVal.appendLogM(msg, MLog.LV_DBG)

        try:
            ret = getData1M(retVal, TableID, FltID, SetID, RowNo, ListData)

        except MacroError, e:
            ret = e.retCode
            print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        return retVal.makeRetVal(ret)

    def openFind(self, TableID, FltID, Kind, Val1, Val2):
        funcName = "WSInfo.openFind"
        retVal = RetVal()
        msg = "## %s(%d, %d, %d, ur\"%s\", ur\"%s\")" % (funcName, TableID, FltID, Kind, Val1, Val2)
        retVal.appendLogM(msg, MLog.LV_DBG)

        try:
            # 型別処理
            type = self.getFilterType(TableID, FltID)
            if   type == lfmtblpy.D5_DT_INTEGER:
                try:
                    val1 = int(Val1)
                except:
                    val1 = D5_NULL_INT
                try:
                    val2 = int(Val2)
                except:
                    val2 = D5_NULL_INT
                startTime = time.clock()
                ret = lfmtblpy.RD5OpenIntFindReal(TableID, FltID, Kind, val1, val2)
                elapsedTime = (time.clock() - startTime) * 1000
                msg = "[RD5OpenIntFindReal] retval=%d [RealTblID=%d,SrchFltID=%d,ValSrchKind=%d,SrchVal1=%d,SrchVal2=%d] (%.3fms)" \
                    % (ret, TableID, FltID, Kind, val1, val2, elapsedTime)
                if ret < 0:
                    retVal.appendLogA(msg, MLog.LV_ERR)
                    raise MacroError(ret, msg)
                retVal.appendLogA(msg, MLog.LV_DBG)
            elif type in LIST_DOUBLE_TYPE:
                if   type == lfmtblpy.D5_DT_DOUBLE:
                    try:
                        val1 = float(Val1)
                    except:
                        val1 = D5_NULL_DBL
                    try:
                        val2 = float(Val2)
                    except:
                        val2 = D5_NULL_DBL
                elif type == lfmtblpy.D5_DT_TIME:
                    val1 = TimeStr2Dbl(Val1)
                    val2 = TimeStr2Dbl(Val2)
                elif type == lfmtblpy.D5_DT_DATE:
                    val1 = DateStr2Dbl(Val1)
                    val2 = DateStr2Dbl(Val2)
                elif type == lfmtblpy.D5_DT_DATETIME:
                    val1 = DateTimeStr2Dbl(Val1)
                    val2 = DateTimeStr2Dbl(Val2)
                startTime = time.clock()
                ret = lfmtblpy.RD5OpenFloatFindReal(TableID, FltID, Kind, val1, val2)
                elapsedTime = (time.clock() - startTime) * 1000
                msg = "[RD5OpenFloatFindReal] retval=%d [RealTblID=%d,SrchFltID=%d,ValSrchKind=%d,SrchVal1=%f,SrchVal2=%f] (%.3fms)" \
                    % (ret, TableID, FltID, Kind, val1, val2, elapsedTime)
                if ret < 0:
                    retVal.appendLogA(msg, MLog.LV_ERR)
                    raise MacroError(ret, msg)
                retVal.appendLogA(msg, MLog.LV_DBG)
            elif type == lfmtblpy.D5_DT_STRING:
                val1 = Val1.encode(ENC_DB)
                val2 = Val2.encode(ENC_DB)
                startTime = time.clock()
                ret = lfmtblpy.RD5OpenStrFindReal(TableID, FltID, Kind, val1, val2)
                elapsedTime = (time.clock() - startTime) * 1000
                msg = "[RD5OpenStrFindReal] retval=%d [RealTblID=%d,SrchFltID=%d,StrSrchKind=%d,SrchStr1=%s,SrchStr2=%s] (%.3fms)" \
                    % (ret, TableID, FltID, Kind, Val1, Val2, elapsedTime)
                if ret < 0:
                    retVal.appendLogA(msg, MLog.LV_ERR)
                    raise MacroError(ret, msg)
                retVal.appendLogA(msg, MLog.LV_DBG)
            elif type == lfmtblpy.D5_DT_DECIMAL:
                nInfo = lfmutilpy.CNumericInfo()
                ret = getNumericInfo(retVal, TableID, FltID, nInfo)
                try:
                    float(Val1) # 数値チェック
                    val1 = lfmutilpy.CNumeric(str(Val1), nInfo.getScale(), nInfo.getRoundingMode())
                except:
                    val1 = lfmutilpy.CNumeric(NULL_NUM_STR, 0, nInfo.getRoundingMode())
                try:
                    float(Val2) # 数値チェック
                    val2 = lfmutilpy.CNumeric(str(Val2), nInfo.getScale(), nInfo.getRoundingMode())
                except:
                    val2 = lfmutilpy.CNumeric(NULL_NUM_STR, 0, nInfo.getRoundingMode())
                startTime = time.clock()
                ret = lfmtblpy.RD5OpenNumericFindReal(TableID, FltID, Kind, val1.getPtr(), val2.getPtr())
                elapsedTime = (time.clock() - startTime) * 1000
                msg = "[RD5OpenNumericFindReal] retval=%d [RealTblID=%d,SrchFltID=%d,ValSrchKind=%d,SrchVal1=%s,SrchVal2=%s] (%.3fms)" \
                    % (ret, TableID, FltID, Kind, Val1, Val2, elapsedTime)
                if ret < 0:
                    retVal.appendLogA(msg, MLog.LV_ERR)
                    raise MacroError(ret, msg)
                retVal.appendLogA(msg, MLog.LV_DBG)

        except MacroError, e:
            ret = e.retCode
            #print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        return retVal.makeRetVal(ret)

    def getNextHit(self, TableID, SrchID, SetID, CurPos, Dir):
        funcName = "WSInfo.getNextHit"
        retVal = RetVal()
        msg = "## %s(%d, %d, %d, %d, %d)" % (funcName, TableID, SrchID, SetID, CurPos, Dir)
        retVal.appendLogM(msg, MLog.LV_DBG)

        try:
            fltID   = lfmutilpy.CTypeIntAr(1)
            nextPos = lfmutilpy.CTypeIntAr(1)
            startTime = time.clock()
            ret = lfmtblpy.RD5GetNextHitReal(TableID, SrchID, SetID, CurPos, Dir, fltID.getPtr(), nextPos.getPtr())
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5GetNextHitReal] retval=%d [RealTblID=%d,SrchID=%d,SetID=%d,CurPos=%d,Dir=%d][FltID=%d,NextPos=%d] (%.3fms)" \
                % (ret, TableID, SrchID, SetID, CurPos, Dir, fltID.at(0), nextPos.at(0), elapsedTime)
            if ret < 0:
                retVal.appendLogA(msg, MLog.LV_ERR)
                raise MacroError(ret, msg)
            retVal.appendLogA(msg, MLog.LV_DBG)

            retVal.retData = (fltID.at(0), nextPos.at(0))
            msg = "FltID=%d,NextPos=%d" % retVal.retData
            retVal.appendLogM2(msg)

        except MacroError, e:
            ret = e.retCode
            #print >>sys.stderr, e
        except:
            print >>sys.stderr, "Unexpected error:", sys.exc_info()
            raise

        # Macro return
        return retVal.makeRetVal(ret)

    ## 指定テーブル情報削除
    def deleteTable(self, id):
        if id in self.mapJoinInfo:
            # JOIN参照先REALテーブル処理→参照情報削除
            joinTableInfo = self.mapJoinInfo[id] 
            refTableInfo = self.mapTableInfo[joinTableInfo.idTableM]
            if id in refTableInfo.listJoinRef:
                refTableInfo.listJoinRef.remove(id)
            refTableInfo = self.mapTableInfo[joinTableInfo.idTableS]
            if id in refTableInfo.listJoinRef:
                refTableInfo.listJoinRef.remove(id)

            del self.mapJoinInfo[id]

        if id in self.mapTableInfo:
            name = self.mapTableInfo[id].name
            del self.mapTableName[name]
            del self.mapTableInfo[id]
            self.listTable.remove(id)

        return

    ## ワークスペース中のテーブル数取得
    def getCountTable(self):
        return len(self.listTable)

    ## ワークスペース中のテーブルIDリスト取得
    def getTableList(self):
        return self.listTable

    ## ワークスペース中のREALテーブルIDリスト取得
    def getRealTableList(self):
        listTable = []
        for tid in self.listTable:
            if self.mapTableInfo[tid].kind == lfmtblpy.D5_TABLEKIND_REAL:
                listTable.append(tid)
        return listTable

    ## 指定テーブル名取得
    def getTableName(self, id):
        return self.mapTableInfo[id].name

    ## テーブル名リスト取得
    def getTableNameList(self):
        listTableName = []
        for tid in self.listTable:
            listTableName.append(self.mapTableInfo[tid].name)
        return listTableName

    ## REALテーブル名リスト取得
    def getRealTableNameList(self):
        listTableName = []
        for tid in self.listTable:
            if self.mapTableInfo[tid].kind == lfmtblpy.D5_TABLEKIND_REAL:
                listTableName.append(self.mapTableInfo[tid].name)
        return listTableName

    ## JOINテーブル名リスト取得
    def getJoinTableNameList(self):
        listTableName = []
        for tid in self.listTable:
            if self.mapTableInfo[tid].kind == lfmtblpy.D5_TABLEKIND_JOIN:
                listTableName.append(self.mapTableInfo[tid].name)
        return listTableName

    ## 指定テーブルID取得
    def getTableId(self, name):
        return self.mapTableName[name]

    ## 指定テーブル種別取得
    def getTableKind(self, id):
        return self.mapTableInfo[id].kind

    ## 指定テーブルの行数取得
    def getCountRow(self, TableID):
        tableInfo = self.mapTableInfo[TableID]
        return tableInfo.nRow

    ## 指定テーブルの行数設定
    def setCountRow(self, TableID, nRow):
        tableInfo = self.mapTableInfo[TableID]
        tableInfo.nRow = nRow
        return

    ## 指定テーブルはJOINテーブル？
    def isJoinTable(self, id):
        if self.mapTableInfo[id].kind == lfmtblpy.D5_TABLEKIND_JOIN:
            bRet = True
        else:
            bRet = False
        return bRet

    ## 指定テーブルは外部JOINテーブル？
    def isOuterJoinTable(self, id):
        return self.mapJoinInfo[id].bOut

    ## 指定JOINテーブルのJOINキー数取得
    def getCountJoinKey(self, id):
        return self.mapJoinInfo[id].nJoinKey

    ## 指定JOINテーブルのマスターテーブルID取得
    def getMasterTableId(self, id):
        return self.mapJoinInfo[id].idTableM

    ## 指定JOINテーブルのマスターテーブルセットID取得
    def getMasterSetId(self, id):
        return self.mapJoinInfo[id].idSetM

    ## 指定JOINテーブルのマスターJOINキーリスト取得
    def getMasterJoinKeyList(self, id):
        return self.mapJoinInfo[id].listIdFilterM

    ## 指定JOINテーブルのスレーブテーブルID取得
    def getSlaveTableId(self, id):
        return self.mapJoinInfo[id].idTableS

    ## 指定JOINテーブルのスレーブテーブルセットID取得
    def getSlaveSetId(self, id):
        return self.mapJoinInfo[id].idSetS

    ## 指定JOINテーブルのスレーブJOINキーリスト取得
    def getSlaveJoinKeyList(self, id):
        return self.mapJoinInfo[id].listIdFilterS

    ## 指定REALテーブルを参照しているJOINテーブル数
    def getCountJoinRef(self, id):
        return len(self.mapTableInfo[id].listJoinRef)

    ## 指定REALテーブルを参照しているJOINテーブルリスト
    def getJoinRefList(self, id):
        return self.mapTableInfo[id].listJoinRef

    ## テーブル名変更
    def renameTable(self, nameBefore, nameAfter):
        tableId = self.getTableId(nameBefore)
        self.mapTableInfo[tableId].name = nameAfter
        del self.mapTableName[nameBefore]
        self.mapTableName[nameAfter] = tableId
        return

    ## 指定セット情報削除
    def deleteSet(self, TableID, SetID):
        tableInfo = self.mapTableInfo[TableID]
        tableInfo.listSet.remove(SetID)
#       name = tableInfo.mapSetInfo[SetID].name
#       del tableInfo.mapSetName[name]
        del tableInfo.mapSetInfo[SetID]
        tableInfo.nSet -= 1
        return

    ## 指定テーブルの項目数
    def getCountSet(self, TableID):
        tableInfo = self.mapTableInfo[TableID]
        return tableInfo.nSet

    ## 指定テーブルのセットIDリスト取得
    def getSetList(self, TableID):
        tableInfo = self.mapTableInfo[TableID]
        return tableInfo.listSet

    ## 指定テーブルのカレントセットID取得
    def getCurSetId(self, TableID):
        tableInfo = self.mapTableInfo[TableID]
        return tableInfo.curSetId

    ## 指定テーブルのカレントセットID設定
    def setCurSetId(self, TableID, SetID):
        tableInfo = self.mapTableInfo[TableID]
        tableInfo.curSetId = SetID
        return

    ## 指定テーブルはオープン済み？
    def isOpenTable(self, TableID):
        tableInfo = self.mapTableInfo[TableID]
        return tableInfo.bOpen

    ## 指定セットはオープン済み？
    def isOpenSet(self, TableID, SetID):
        tableInfo = self.mapTableInfo[TableID]
        setInfo = tableInfo.mapSetInfo[SetID]
        return setInfo.bOpen

    ## 指定セットのサイズ取得
    def getSetSize(self, TableID, SetID):
        tableInfo = self.mapTableInfo[TableID]
        setInfo = tableInfo.mapSetInfo[SetID]
        return setInfo.size

    ## 指定セットのRecNoリスト取得
    def getRecNoList(self, TableID, SetID):
        tableInfo = self.mapTableInfo[TableID]
        setInfo = tableInfo.mapSetInfo[SetID]
        return setInfo.listRecNo

    ## 指定セットのコメント取得
    def getComment(self, TableID, SetID):
        tableInfo = self.mapTableInfo[TableID]
        setInfo = tableInfo.mapSetInfo[SetID]
        return setInfo.comment

    ## 指定項目情報削除
    def deleteFilter(self, TableID, FltID):
        tableInfo = self.mapTableInfo[TableID]
        tableInfo.listFilter.remove(FltID)
        name = tableInfo.mapFilterInfo[FltID].name
        del tableInfo.mapFilterName[name]
        del tableInfo.mapFilterInfo[FltID]
        tableInfo.nFilter -= 1
        return

    ## 指定テーブルの項目IDリスト取得
    def getFilterList(self, TableID):
        tableInfo = self.mapTableInfo[TableID]
        return tableInfo.listFilter

    ## 指定テーブルの項目数
    def getCountFilter(self, TableID):
        tableInfo = self.mapTableInfo[TableID]
        return tableInfo.nFilter

    ## 指定項目名取得
    def getFilterName(self, TableID, FltID):
        tableInfo = self.mapTableInfo[TableID]
        return tableInfo.mapFilterInfo[FltID].name

    ## 指定テーブルの項目名リスト取得
    def getFilterNameList(self, TableID):
        tableInfo = self.mapTableInfo[TableID]
        listFilterName = []
        for fid in tableInfo.listFilter:
            listFilterName.append(tableInfo.mapFilterInfo[fid].name)
        return listFilterName

    ## 指定項目タイプ取得
    def getFilterType(self, TableID, FltID):
        tableInfo = self.mapTableInfo[TableID]
        return tableInfo.mapFilterInfo[FltID].type

    ## 指定テーブルの項目タイプリスト取得
    def getFilterTypeList(self, TableID):
        tableInfo = self.mapTableInfo[TableID]
        listFilterType = []
        for fid in tableInfo.listFilter:
            listFilterType.append(tableInfo.mapFilterInfo[fid].type)
        return listFilterType

    ## 指定項目スケール取得
    def getFilterScale(self, TableID, FltID):
        tableInfo = self.mapTableInfo[TableID]
        return tableInfo.mapFilterInfo[FltID].scale

    ## 項目名変更
    def renameFilter(self, TableID, nameBefore, nameAfter):
        tableInfo = self.mapTableInfo[TableID]
        fid = tableInfo.mapFilterName[nameBefore]
        del tableInfo.mapFilterName[nameBefore]
        tableInfo.mapFilterName[nameAfter] = fid
        tableInfo.mapFilterInfo[fid].name =nameAfter
        return

## テーブル情報クラス
class TableInfo():
    def __init__(self, id=-1, name="", kind=0, nRow=0, nSet=0, nFilter=0):
        self.id = id                # テーブルID
        self.name = name            # テーブル名
        self.kind = kind            # 種類（REAL=0，JOIN=2)
        self.nRow = nRow            # 行数
        self.nSet = nSet            # セット数
        self.listSet = []           # セットIDリスト
        self.mapSetName = {}        # セット名マップ（名前→ID）
        self.mapSetInfo = {}        # セット情報マップ（ID→情報）
        self.curSetId = 1           # カレントセットID
        self.nFilter = nFilter      # 項目数
        self.listFilter = []        # 項目IDリスト
        self.mapFilterName = {}     # 項目名マップ（名前→ID）
        self.mapFilterInfo = {}     # 項目情報マップ（ID→情報）
        self.listJoinRef = []       # このテーブルを参照しているJOINテーブルIDリスト
        self.bOpen = False          # オープン済みならTrue
        return

## JOINテーブル情報クラス
class JoinTableInfo():
    def __init__(self):
        self.id = -1                # JOINテーブルID
        self.bOut = False           # 外部JOINならTrue
        self.nJoinKey = -1          # JOINキー(項目)数
        self.idTableM = -1          # マスターテーブルID
        self.idSetM = -1            # マスターテーブルセットID
        self.listIdFilterM = []     # マスターテーブル項目IDリスト
        self.idTableS =-1           # スレーブテーブルID
        self.idSetS = -1            # スレーブテーブルセットID
        self.listIdFilterS = []     # スレーブテーブル項目IDリスト
        return

## セット情報クラス
class SetInfo():
    def __init__(self, id=-1, name="", size=0, comment=""):
        self.id = id            # セットID
        self.name = name        # セット名
        self.size = size        # セットサイズ
        self.listRecNo = []     # RecNoリスト
        self.comment = comment  # コメント
        self.bOpen = False      # オープン済みならTrue
        return

## 項目情報クラス
class FilterInfo():
    def __init__(self, id=-1, name="", type=-1, scale=0, rmode=0, bComma=False):
        self.id = id            # 項目ID
        self.name = name        # 項目名
        self.type = type        # 項目タイプ(整数値)
        self.scale = scale      # 小数点以下桁数
        self.rmode = rmode      # 丸めモード
        self.bComma = bComma    # カンマ編集オンならTrue
        return


## 初期化処理
def init():
    global g_WSInfo, g_flagInit, g_MConfig, g_fLogM, g_fLogA, ENC_OS, ENC_DB

    if g_flagInit == True: # 初期化済み
        return

    # 設定ファイル
    g_MConfig = MConfig(CONFIG_FILE)
    g_MConfig.load()
    print g_MConfig #debug

    # グローバル変数
    ENC_OS = g_MConfig.ENC_OS
    ENC_DB = g_MConfig.ENC_DB

    # ログファイル数制限
    limitFileNo(g_MConfig.LOG_FILE_PATH, LOG_FILE_BASE_M + r'????????????' + LOG_FILE_EXT, g_MConfig.LOG_FILE_MAX - 1)
    limitFileNo(g_MConfig.LOG_FILE_PATH, LOG_FILE_BASE_A + r'????????????' + LOG_FILE_EXT, g_MConfig.LOG_FILE_MAX - 1)

    # ログファイルopen
    dt = datetime.datetime.now().strftime("%y%m%d%H%M%S")
    g_fLogM = open(os.path.normpath(os.path.join(g_MConfig.LOG_FILE_PATH, LOG_FILE_BASE_M + dt + LOG_FILE_EXT)), "w")
    g_fLogM = codecs.getwriter(g_MConfig.LOG_FILE_CODE)(g_fLogM)
    g_fLogA = open(os.path.normpath(os.path.join(g_MConfig.LOG_FILE_PATH, LOG_FILE_BASE_A + dt + LOG_FILE_EXT)), "w")
    g_fLogA = codecs.getwriter(g_MConfig.LOG_FILE_CODE)(g_fLogA)

    # 終了処理関数登録
    atexit.register(term)

    # マクロログヘッダ出力
    g_fLogM.write("#*** LOG START AT : %s ***\n" % getNowTime())
    g_fLogM.write("# -*- coding: utf-8 -*-\n")
    g_fLogM.write("from LFM_Macro import *\n\n")
    g_fLogM.flush()

    # ポインタサイズ
    global g_Env, BYTE_SIZE_POINTER, MAP_DATA_TYPE_SIZE
    g_Env = lfmtblpy.TREnvironment()
    startTime = time.clock()
    ret = lfmtblpy.RD5GetEnvironment(g_Env)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetEnvironment] retval=%d [HostName=%s,OSType=%d,OSMajorVersion=%d,OSMinorVersion=%d,MachineArchitecture=%d,Endian=%d,ELF=%d,ProcessorCount=%d,ProcessType=%d,OSCharCode=%s] (%.3fms)" \
        % (ret, g_Env.HostName, g_Env.OSType, g_Env.OSMajorVersion, g_Env.OSMinorVersion, g_Env.MachineArchitecture \
        , g_Env.Endian, g_Env.ELF, g_Env.ProcessorCount, g_Env.ProcessType, g_Env.DBCharCode, elapsedTime)
    if ret < 0:
        logA(MLog.LV_ERR, msg)
        print >>sys.stderr, "Initializing ERROR!: %s" % (msg)
    else:
        logA(MLog.LV_INF, msg)
        BYTE_SIZE_POINTER = int(g_Env.ELF / 8)
        MAP_DATA_TYPE_SIZE[lfmtblpy.D5_DT_STRING] = BYTE_SIZE_POINTER

    g_WSInfo = WSInfo()
    g_flagInit = True
    return

## 終了処理
def term():
    global g_flagInit, g_fLogM, g_fLogA

    if g_flagInit == False:
        return

    # ログファイルclose
    if g_fLogM != None:
        g_fLogM.close()
    if g_fLogA != None:
        g_fLogA.close()

    g_flagInit = False
    return

## ファイル数制限（オーバー分削除）
def limitFileNo(path, pattern, max):
    names = os.listdir(path)                # ファイルリスト
    match = fnmatch.filter(names, pattern)  # ファイル抽出
    match.sort()                            # ファイル名ソート

    # max個残して古いファイル削除
    for name in match[:-max]:
        file = os.path.normpath(os.path.join(path, name))
        os.remove(file)
#       print "Delete Log File[%s]" % file #debug

    return

## 現在時刻取得
def getNowTime():
    time = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    return time

## マクロログファイル出力
def logM(msg):
    log = "# %s\n%s\n" % (getNowTime(), msg)
    return log

## マクロログファイル出力（中間）
def logM2(msg):
    log = "# %s\n" % (msg)
    return log

## マクロログファイル出力（リターンコード）
def logMRC(lv, preLog, funcName, retCode, elapsedTime):
    for log in preLog:
        g_fLogM.write(log)
    log = "# [%s] %s retCode=%d elapsedTime=%.3fms\n\n" % (MLog.MAP_LV_NC[lv], funcName, retCode, elapsedTime)
    g_fLogM.write(log)
    g_fLogM.flush()
    return log

## APIログファイル出力
def logA(lv, msg):
    log = "%s [%s]%s\n" % (getNowTime(), MLog.MAP_LV_NC[lv], msg)
    g_fLogA.write(log)
    g_fLogA.flush()
    return log


## マルチバイト文字列リスト出力対応str()
def strList(list):
    retStr = "["
    if (list != None) and isinstance(list, types.ListType): # リスト型
        sz = len(list) - 1
        for i, s in enumerate(list):
            if isinstance(s, types.ListType): # リスト型
                retStr += strList(s) # 再帰
            elif isinstance(s, types.StringTypes): # 文字列要素(Unicode型含む)
                retStr += ('ur\"' + s + '\"')
            else:
                retStr += str(s)
            if i < sz:
                retStr += ', '
    retStr += "]"
    return retStr

## 配列をリスト化
# @param[in]    arry    at()メソッドで要素アクセスする配列クラス
# @param[in]    size    要素数
# @retval   リスト
def Array2List(arry, size):
    list = []
    if (arry != None) and (size > 0):
        for i in range(size):
            list.append(arry.at(i))
    return list

# Date(Double) -> String
def DateDbl2Str(val):
    if val == D5_NULL_DBL:
        return ""

    try:
        retval = datetime.datetime.fromordinal(int(val) + DATETIME_BASE.toordinal()).strftime(DATE_FORMAT)
    except OverflowError:
        retval = ""
    return retval

# Date(String) -> Double
def DateStr2Dbl(val):
    try:
        retval = float((datetime.datetime.strptime(val, DATE_FORMAT) - DATETIME_BASE).days)
    except ValueError:
        retval = D5_NULL_DBL
    return retval

# Time(Double) -> String
# JNI: [digo_jniutils.cpp]d5jni::double_to_date()から移植
def TimeDbl2Str(val):
    if val == D5_NULL_DBL:
        return ""

    try:
        #print "[TimeDbl2Str] val: ", val #debug
        iTime = int(val * g_fMSecsPerDay + 0.5) # 誤差の分としての0.5
        iMinCount = iTime / 60000
        iMSecCount = iTime % 60000
        iHour = iMinCount / 60
        iMin  = iMinCount % 60
        iSec  = iMSecCount / 1000
        #iMSec = iMSecCount % 1000
        sTime = "%02d:%02d:%02d" % (iHour, iMin, iSec)
    except OverflowError:
        sTime = ""
    return sTime

# Time(String) -> Double
def TimeStr2Dbl(val):
    sepVal = val.split(':')
    #print "[TimeStr2Dbl] speVal: ", sepVal #debug
    if len(sepVal) < 3:
        dTime = D5_NULL_DBL
    else:
        iHour = int(sepVal[0])
        iMin  = int(sepVal[1])
        iSec  = int(sepVal[2])
        iMSec = 0
        dTime = (iHour * 3600000 + iMin * 60000 + iSec * 1000 + iMSec) / g_fMSecsPerDay
    #print "[TimeStr2Dbl] dTime: ", dTime #debug
    return dTime

# DateTime(Double) -> String
def DateTimeDbl2Str(val):
    if val == D5_NULL_DBL:
        return ""

    dTime, dDate = math.modf(val) # 小数部,整数部
    sDate = DateDbl2Str(dDate)  # 整数部→日付
    sTime = TimeDbl2Str(dTime)  # 小数部→時刻
    sDateTime = "%s %s" % (sDate, sTime)
    return sDateTime

# DateTime(String) -> Double
def DateTimeStr2Dbl(val):
    sepVal = val.split(' ')
    if len(sepVal) < 2:
        dDateTime = D5_NULL_DBL
    else:
        sDate = sepVal[0]
        sTime = sepVal[1]
        dDate = DateStr2Dbl(sDate) # 日付
        dTime = TimeStr2Dbl(sTime) # 時刻
        dDateTime = dDate + dTime
    #print "[DateTimeStr2Dbl] dDateTime: ", dDateTime #debug
    return dDateTime

# Number(val) -> String nn,nnn
def Numberfmt(num):
    regex = re.compile(r'(\d)(?=(?:\d{3})+$)')
    strdata = regex.sub(r'\1,', str(num))
    return strdata


## D5Dファイル情報取得
def getD5DFileInfo(retVal, DBPath, DBName, Env):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetD5DFileInfo(DBPath.encode(ENC_OS), DBName.encode(ENC_OS), Env)
    elapsedTime = (time.clock() - startTime) * 1000
    listVersion = []
    if ret == 0: # 正常
        for i in range(4):
            listVersion.append(lfmutilpy.int_at(Env.Version, i))
    msg = "[RD5GetD5DFileInfo] retval=%d [DBPath=%s,DBName=%s][OSType=%d,Endian=%d,ELF=%d,DBCharCode=%s,Version=%s] (%.3fms)" \
        % (ret, DBPath, DBName, Env.OSType, Env.Endian, Env.ELF, Env.DBCharCode.split('\0')[0], str(listVersion), elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    retVal.retData = Env
    return ret

## D5Tファイル情報取得
def getD5TFileInfo(retVal, DBPath, DBName, Env):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetD5TFileInfo(DBPath.encode(ENC_OS), DBName.encode(ENC_OS), Env)
    elapsedTime = (time.clock() - startTime) * 1000
    listVersion = []
    if ret == 0: # 正常
        for i in range(4):
            listVersion.append(lfmutilpy.int_at(Env.Version, i))
    msg = "[RD5GetD5TFileInfo] retval=%d [DBPath=%s,DBName=%s][OSType=%d,Endian=%d,ELF=%d,DBCharCode=%s,Version=%s] (%.3fms)" \
        % (ret, DBPath, DBName, Env.OSType, Env.Endian, Env.ELF, Env.DBCharCode.split('\0')[0], str(listVersion), elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    retVal.retData = Env
    return ret

## テーブル名→ID
def getTableIDFromName(retVal, TblName):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetTableIDFromName(TblName.encode(ENC_DB))
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetTableIDFromName] retval=%d [TableName=%s] (%.3fms)" % (ret, TblName, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## 項目名→ID
def getFilterIDFromName(retVal, TableID, FltName):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetFilterIDFromName(TableID, FltName.encode(ENC_DB))
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetFilterIDFromName] retval=%d [TableID=%d,FilterName=%s] (%.3fms)" % (ret, TableID, FltName, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## 項目名→ID
def getFilterIDFromName2(retVal, TableID, IsSlave, FltName):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetFilterIDFromName2(TableID, IsSlave, FltName.encode(ENC_DB))
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetFilterIDFromName2] retval=%d [TableID=%d,isSlave=%d,FilterName=%s] (%.3fms)" % (ret, TableID, IsSlave, FltName, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## 全テーブル数取得
def getNTable(retVal):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetNTable()
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetNTable] retval=%d (%.3fms)" % (ret, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## 全テーブルIDリスト取得
def getTableIDList(retVal, IdList):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetTableIDList(IdList.getPtr())
    elapsedTime = (time.clock() - startTime) * 1000
    if ret > 0:
        listIdList = Array2List(IdList, ret)
    else:
        listIdList = []
    msg = "[RD5GetTableIDList] retval=%d [IDList=%s] (%.3fms)" % (ret, str(listIdList), elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## 全テーブルIDリスト取得
# @param[in]    retVal  戻り値オブジェクト
# @param[out]   ListId  テーブルIDリスト ※呼出側で空リストへの参照を渡すこと
# @retval   0以上   テーブル数
# @retval   負      エラーコード
def getTableIDListM(retVal, ListId):
    nTable = getNTable(retVal)

    idList = lfmutilpy.CTypeIntAr(nTable + 1)
    idList.put(nTable, 0) # 終端

    startTime = time.clock()
    ret = lfmtblpy.RD5GetTableIDList(idList.getPtr())
    elapsedTime = (time.clock() - startTime) * 1000
    if ret > 0:
        listIdList = Array2List(idList, ret)
    else:
        listIdList = []
    msg = "[RD5GetTableIDList] retval=%d [IDList=%s] (%.3fms)" % (ret, str(listIdList), elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)

    ListId[:] = listIdList[:]

    return ret

## テーブル名取得
def getTableName(retVal, TableID):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetTableNameR1(TableID)
    elapsedTime = (time.clock() - startTime) * 1000
    if ret != None:
        ret = ret.decode(ENC_DB)
    msg = "[RD5GetTableNameR1] retval=%s [TableID=%d] (%.3fms)" % (ret, TableID, elapsedTime)
    if ret == None:
        retVal.appendLogA(msg, MLog.LV_ERR)
        ret = -1
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## テーブル名生成
def generateTableName(retVal, PCSeedName):
    startTime = time.clock()
    ret = lfmtblpy.RD5GenerateTableNameR1(PCSeedName.encode(ENC_DB))
    elapsedTime = (time.clock() - startTime) * 1000
    if ret != None:
        ret = ret.decode(ENC_DB)
    msg = "[RD5GenerateTableNameR1] retval=%s [PCSeedName=%s] (%.3fms)" % (ret, PCSeedName, elapsedTime)
    if ret == None:
        retVal.appendLogA(msg, MLog.LV_ERR)
        ret = -1
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## テーブル情報取得
def getTableProperty(retVal, TableID, TableInfo):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetTableProperty(TableID, TableInfo)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetTableProperty] retval=%d [TableID=%d][TableKind=%d,nFilter=%d,nSet=%d,TotalRows=%d,TableName=%s] (%.3fms)" \
        % (ret, TableID, TableInfo.TableKind, TableInfo.nFilter, TableInfo.nSet, TableInfo.TotalRows, TableInfo.TableName.decode(ENC_DB), elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## テーブル情報取得
# @param[in]    retVal      戻り値オブジェクト
# @param[in]    TableID     テーブルID
# @param[out]   TableInfo   TableInfoオブジェクト ※呼出側で生成して参照を渡すこと
# @retval   0   成功
# @retval   負  エラーコード
def getTablePropertyM(retVal, TableID, TableInfo):
    tableInfo = lfmtblpy.TTableInfo()
    ret = getTableProperty(retVal, TableID, tableInfo)

    TableInfo.id      = tableInfo.TableID
    TableInfo.kind    = tableInfo.TableKind
    TableInfo.nFilter = tableInfo.nFilter
    TableInfo.nSet    = tableInfo.nSet
    TableInfo.nRow    = tableInfo.TotalRows
    TableInfo.name    = tableInfo.TableName.decode(ENC_DB)

    return ret

## JOINテーブル情報取得
def getJoinInfoExM(retVal, TableID, JoinTableInfo):
    IsOuter         = lfmutilpy.CTypeIntAr(1)
    nJoinKey        = lfmutilpy.CTypeIntAr(1)
    MasterTblID     = lfmutilpy.CTypeIntAr(1)
    MasterSetID     = lfmutilpy.CTypeIntAr(1)
    MasterFltIDs    = lfmutilpy.CTypeIntAr(lfmtblpy.D5_MAX_JOIN_KEY)
    SlaveTblID      = lfmutilpy.CTypeIntAr(1)
    SlaveSetID      = lfmutilpy.CTypeIntAr(1)
    SlaveFltIDs     = lfmutilpy.CTypeIntAr(lfmtblpy.D5_MAX_JOIN_KEY)

    startTime = time.clock()
    ret = lfmtblpy.RD5GetJoinInfoExR1(TableID, IsOuter.getPtr(), nJoinKey.getPtr() \
                                , MasterTblID.getPtr(), MasterSetID.getPtr(), MasterFltIDs.getPtr() \
                                , SlaveTblID.getPtr(), SlaveSetID.getPtr(), SlaveFltIDs.getPtr())
    elapsedTime = (time.clock() - startTime) * 1000
    listIdFilterM = Array2List(MasterFltIDs, nJoinKey.at(0))
    listIdFilterS = Array2List(SlaveFltIDs, nJoinKey.at(0))
    msg = "[RD5GetJoinInfoExR1] retval=%d [TableID=%d][IsOuter=%d,nJoinKey=%d,MasterTblID=%d,MasterSetID=%d,MasterFltIDs=%s,SlaveTblID=%d,SlaveSetID=%d,SlaveFltIDs=%s] (%.3fms)" \
        % (ret, TableID, IsOuter.at(0), nJoinKey.at(0), MasterTblID.at(0), MasterSetID.at(0) \
            , str(listIdFilterM), SlaveTblID.at(0), SlaveSetID.at(0), str(listIdFilterS), elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)

    JoinTableInfo.id = TableID
    if IsOuter.at(0) == 1:
        JoinTableInfo.bOut = True
    else:
        JoinTableInfo.bOut = False
    JoinTableInfo.nJoinKey      = nJoinKey.at(0)
    JoinTableInfo.idTableM      = MasterTblID.at(0)
    JoinTableInfo.idSetM        = MasterSetID.at(0)
    JoinTableInfo.listIdFilterM = listIdFilterM
    JoinTableInfo.idTableS      = SlaveTblID.at(0)
    JoinTableInfo.idSetS        = SlaveSetID.at(0)
    JoinTableInfo.listIdFilterS = listIdFilterS

    return ret


## 全セット数取得
def getNSet(retVal, TableID):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetNSet(TableID)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetNSet] retval=%d [TableID=%d] (%.3fms)" % (ret, TableID, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## 全セットIDリスト取得
def getSetIDList(retVal, TableID, nSet, IdList):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetSetIDList(TableID, nSet, IdList.getPtr())
    elapsedTime = (time.clock() - startTime) * 1000
    if ret > 0:
        listIdList = Array2List(IdList, ret)
    else:
        listIdList = []
    msg = "[RD5GetSetIDList] retval=%d [TableID=%d,Size=%d,SetIDList=%s] (%.3fms)" % (ret, TableID, nSet, str(Array2List(IdList, ret)), elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## 全セットIDリスト取得
# @param[in]    retVal  戻り値オブジェクト
# @param[in]    TableID テーブルID
# @param[out]   ListId  セットIDリスト ※呼出側で空リストへの参照を渡すこと
# @retval   0以上   セット数
# @retval   負      エラーコード
def getSetIDListM(retVal, TableID, ListId):
    nSet = getNSet(retVal, TableID)
    idList = lfmutilpy.CTypeIntAr(nSet)

    startTime = time.clock()
    ret = lfmtblpy.RD5GetSetIDList(TableID, nSet, idList.getPtr())
    elapsedTime = (time.clock() - startTime) * 1000
    if ret > 0:
        listIdList = Array2List(idList, ret)
    else:
        listIdList = []
    msg = "[RD5GetSetIDList] retval=%d [TableID=%d,Size=%d,SetIDList=%s] (%.3fms)" % (ret, TableID, nSet, str(listIdList), elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)

    ListId[:] = listIdList[:]

    return ret

## カレントセットID取得
def getCurrentSetID(retVal, TableID):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetCurrentSetID(TableID)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetCurrentSetID] retval=%d [TableID=%d] (%.3fms)" % (ret, TableID, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## セット取得
def getSetM(retVal, TableID, SetID, ListRecNo):
    setSize = lfmutilpy.CTypeIntAr(1)
    getCount = getSetSize(retVal, TableID, SetID)
    pSetArray = lfmutilpy.CTypeIntAr(getCount)

    startTime = time.clock()
    ret = lfmtblpy.RD5GetSet(TableID, SetID, setSize.getPtr(), getCount, pSetArray.getPtr())
    elapsedTime = (time.clock() - startTime) * 1000
    if ret > 0:
        list = Array2List(pSetArray, ret)
    else:
        list = []
    msg = "[RD5GetSet] retval=%d [TableID=%d,SetID=%d,GetCount=%d][SetSize=%d] (%.3fms)" \
        % (ret, TableID, SetID, getCount, setSize.at(0), elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)

    ListRecNo[:] = list[:]

    return ret

## セット情報取得
# @param[in]    retVal      戻り値オブジェクト
# @param[in]    TableID     テーブルID
# @param[in]    SetID       項目ID
# @param[out]   SetInfo     SetInfoオブジェクト ※呼出側で生成して参照を渡すこと
# @retval   >=0 セットサイズ
# @retval   負  エラーコード
def getSetInfoM(retVal, TableID, SetID, SetInfo):
    SetInfo.id = SetID
    SetInfo.comment = getCommentM(retVal, TableID, SetID)   # コメント
#   SetInfo.name = name     # セット名
#   SetInfo.size = getSetM(retVal, TableID, SetID, SetInfo.listRecNo)
    SetInfo.size = getSetSize(retVal, TableID, SetID)       # JoinTable(Set)の行数表示不正対策 
    return SetInfo.size

## 全項目数取得
def getNFilter(retVal, TableID):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetNFilter(TableID)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetNFilter] retval=%d [TableID=%d] (%.3fms)" % (ret, TableID, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## 全項目IDリスト取得
def getFilterIDList(retVal, TableID, IdList):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetFilterIDList(TableID, IdList.getPtr())
    elapsedTime = (time.clock() - startTime) * 1000
    if ret > 0:
        listIdList = Array2List(IdList, ret)
    else:
        listIdList = []
    msg = "[RD5GetFilterIDList] retval=%d [TableID=%d,IDList=%s] (%.3fms)" % (ret, TableID, str(listIdList), elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## 全項目IDリスト取得
# @param[in]    retVal  戻り値オブジェクト
# @param[in]    TableID テーブルID
# @param[out]   ListId  セットIDリスト ※呼出側で空リストへの参照を渡すこと
# @retval   0以上   項目数
# @retval   負      エラーコード
def getFilterIDListM(retVal, TableID, ListId):
    nFlt = getNFilter(retVal, TableID)
    idList = lfmutilpy.CTypeIntAr(nFlt)

    startTime = time.clock()
    ret = lfmtblpy.RD5GetFilterIDList(TableID, idList.getPtr())
    elapsedTime = (time.clock() - startTime) * 1000
    if ret > 0:
        listIdList = Array2List(idList, ret)
    else:
        listIdList = []
    msg = "[RD5GetFilterIDList] retval=%d [TableID=%d,IDList=%s] (%.3fms)" % (ret, TableID, str(listIdList), elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)

    ListId[:] = listIdList[:]

    return ret

## 項目ID取得クラス
# REALとJOINを識別し、適切な項目IDを返す。
# 同一テーブル内の項目IDを連続取得する場合に有効。
class FilterIdFromName():
    def __init__(self, retVal, tid):
        self.tid = tid
        tableInfo = TableInfo()
        ret = getTablePropertyM(retVal, tid, tableInfo)
        if tableInfo.kind == lfmtblpy.D5_TABLEKIND_REAL:
            self.bJoin = False
        else:
            self.bJoin = True
            self.listFilterName = getFilterNameList(retVal, tid)
        return

    def getId(self, retVal, name):
        if self.bJoin:
            if name in self.listFilterName:
                ret = self.listFilterName.index(name) + 1
            else:
                ret = -1
        else:
            ret = getFilterIDFromName(retVal, self.tid, name)
        return ret

## 項目名取得
def getFilterName(retVal, TableID, FltID):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetFilterNameR1(TableID, FltID)
    elapsedTime = (time.clock() - startTime) * 1000
    if ret != None:
        ret = ret.decode(ENC_DB)
    msg = "[RD5GetFilterNameR1] retval=%s [TableID=%d,FilterID=%d] (%.3fms)" % (ret, TableID, FltID, elapsedTime)
    if ret == None:
        retVal.appendLogA(msg, MLog.LV_ERR)
        ret = -1
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## 全項目名リスト取得
def getFilterNameList(retVal, TableID):
    nFlt = getNFilter(retVal, TableID)
    idList = lfmutilpy.CTypeIntAr(nFlt)
    nFlt = getFilterIDList(retVal, TableID, idList)
    idListList = Array2List(idList, nFlt)
    nameList = []
    for fltID in idListList:
        ret = getFilterName(retVal, TableID, fltID)
        nameList.append(ret)
    return nameList

## 項目データ型取得
def getFilterType(retVal, TableID, FltID):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetFilterType(TableID, FltID)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetFilterType] retval=%d [TableID=%d,FltID=%d] (%.3fms)" % (ret, TableID, FltID, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## 項目情報取得
# @param[in]    retVal      戻り値オブジェクト
# @param[in]    TableID     テーブルID
# @param[in]    FltID       項目ID
# @param[out]   FltInfo     FilterInfoオブジェクト ※呼出側で生成して参照を渡すこと
# @retval   0   成功
# @retval   負  エラーコード
def getFilterInfoM(retVal, TableID, FltID, FltInfo):
    FltInfo.id   = FltID
    FltInfo.name = getFilterName(retVal, TableID, FltID)
    FltInfo.type = getFilterType(retVal, TableID, FltID)

    # カンマ編集
    if FltInfo.type in LIST_NUM_TYPE:
        ret = getFilterAttr(retVal, TableID, FltID, COMMA_ONOFF_FIELD)
        FltInfo.bComma = (ret != 0)

    # 小数点以下桁数，丸めモード
    if   FltInfo.type == lfmtblpy.D5_DT_DOUBLE:
        FltInfo.scale = getFilterAttr(retVal, TableID, FltID, UNDER_0_DIGITS_FIELD) + 3
    elif FltInfo.type == lfmtblpy.D5_DT_DECIMAL:
        nInfo = lfmutilpy.CNumericInfo()
        ret = getNumericInfo(retVal, TableID, FltID, nInfo)
        FltInfo.scale = nInfo.getScale()
        FltInfo.rmode = nInfo.getRoundingMode()

    ret = 0

    #debug
#   print "[getFilterInfoM] retval=%d [TableID=%d,FltID=%d][id=%d,name=%s,type=%d,scale=%d,rmode=%d,bComma=%s]" \
#       % (ret, TableID, FltID, FltInfo.id, FltInfo.name, FltInfo.type, FltInfo.scale, FltInfo.rmode, str(FltInfo.bComma))

    return ret

## ルートセット行数取得
def getTotalRows(retVal, TableID):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetTotalRows(TableID)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetTotalRows] retval=%d [TableID=%d] (%.3fms)" % (ret, TableID, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## セット行数取得
def getSetSize(retVal, TableID, SetID):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetSetSize(TableID, SetID)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetSetSize] retval=%d [TableID=%d,SetID=%d] (%.3fms)" % (ret, TableID, SetID, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## Numeric項目情報取得
def getNumericInfo(retVal, TableID, FltID, NInfo):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetNumericInfoR1(TableID, FltID, NInfo.getPtr())
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetNumericInfoR1] retval=%d [TableID=%d,FilterID=%d,scale=%d,rounding_mode=%d] (%.3fms)" \
        % (ret, TableID, FltID, NInfo.getScale(), NInfo.getRoundingMode(), elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## 項目アトリビュート取得
def getFilterAttr(retVal, TableID, FltID, Idx):
    attrs = lfmutilpy.CFilterAttr()
    startTime = time.clock()
    ret = attrs.getAttr(TableID, FltID)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetFilterAttr] retval=%d [TableID=%d,FilterID=%d] (%.3fms)" % (ret, TableID, FltID, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)

    ret = attrs.at(Idx)

    return ret

## 項目アトリビュート設定
def setFilterAttr(retVal, TblName, FltName, Idx, Val):
    tableID = getTableIDFromName(retVal, TblName)
    fltID = getFilterIDFromName(retVal, tableID, FltName)

    attrs = lfmutilpy.CFilterAttr()
    startTime = time.clock()
    ret = attrs.getAttr(tableID, fltID)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetFilterAttr] retval=%d [TableID=%d,FilterID=%d] (%.3fms)" % (ret, tableID, fltID, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)

    attrs.put(Idx, Val)
    startTime = time.clock()
    ret = attrs.setAttr(tableID, fltID)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5SetFilterAttr] retval=%d [TableID=%d,FilterID=%d] (%.3fms)" % (ret, tableID, fltID, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## テーブル削除
def deleteTable(retVal, TableID):
    startTime = time.clock()
    ret = lfmtblpy.RD5DeleteTable(TableID)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5DeleteTable] retval=%d [TableID=%d] (%.3fms)" % (ret, TableID, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret


## 複数データ取得
def getData1M(retVal, TableID, FltID, SetID, RowNo, ListData):
    nGot = lfmutilpy.CTypeIntAr(1)
    nGot.put(0, 0)

    if ListData != None:
        retVal.retData = ListData
    else:
        retVal.retData = []
    del retVal.retData[:]

    ret = getSetSize(retVal, TableID, SetID)
    if ret > 0:
        # データ型別処理
        MAX_CACHE = lfmtblpy.D5_MAX_CACHE
        fltType = getFilterType(retVal, TableID, FltID)
        if   fltType == lfmtblpy.D5_DT_INTEGER:
            buf = lfmutilpy.CTypeIntAr(MAX_CACHE * 2)
            startTime = time.clock()
            ret = lfmtblpy.RD5GetData1MIntR1(TableID, FltID, SetID, RowNo, nGot.getPtr(), buf.getPtr())
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5GetData1MIntR1] retval=%d [TableID=%d,FltID=%d,SetID=%s,RowNo=%d][nGot=%d] (%.3fms)" \
                % (ret, TableID, FltID, SetID, RowNo, nGot.at(0), elapsedTime)
            retVal.retData.extend(Array2List(buf, nGot.at(0)))
        elif fltType in LIST_DOUBLE_TYPE:
            buf = lfmutilpy.CTypeDblAr(MAX_CACHE)
            startTime = time.clock()
            ret = lfmtblpy.RD5GetData1MDblR1(TableID, FltID, SetID, RowNo, nGot.getPtr(), buf.getPtr())
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5GetData1MDblR1] retval=%d [TableID=%d,FltID=%d,SetID=%s,RowNo=%d][nGot=%d] (%.3fms)" \
                % (ret, TableID, FltID, SetID, RowNo, nGot.at(0), elapsedTime)
            if   fltType == lfmtblpy.D5_DT_DOUBLE:
                retVal.retData.extend(Array2List(buf, nGot.at(0)))
            elif fltType == lfmtblpy.D5_DT_TIME:
                for i in range(nGot.at(0)):
                    retVal.retData.append(TimeDbl2Str(buf.at(i)))
            elif fltType == lfmtblpy.D5_DT_DATE:
                for i in range(nGot.at(0)):
                    retVal.retData.append(DateDbl2Str(buf.at(i)))
            elif fltType == lfmtblpy.D5_DT_DATETIME:
                for i in range(nGot.at(0)):
                    retVal.retData.append(DateTimeDbl2Str(buf.at(i)))
        elif fltType == lfmtblpy.D5_DT_STRING:
            offset = lfmutilpy.CTypeIntAr(MAX_CACHE)
            buf    = lfmutilpy.CTypeCharAr(lfmtblpy.D5_MAX_STRING_SIZE)
            startTime = time.clock()
            ret = lfmtblpy.RD5GetData1MStrR1(TableID, FltID, SetID, RowNo, nGot.getPtr(), offset.getPtr(), buf.getVPtr())
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5GetData1MStrR1] retval=%d [TableID=%d,FltID=%d,SetID=%s,RowNo=%d][nGot=%d] (%.3fms)" \
                % (ret, TableID, FltID, SetID, RowNo, nGot.at(0), elapsedTime)
            for i in range(nGot.at(0)):
                retVal.retData.append(buf.getPtr(offset.at(i)).decode(ENC_DB))
        elif fltType == lfmtblpy.D5_DT_DECIMAL:
            nInfo = lfmutilpy.CNumericInfo()
            ret = getNumericInfo(retVal, TableID, FltID, nInfo)
            buf = lfmutilpy.CTypeNumAr(MAX_CACHE, nInfo.getScale(), nInfo.getRoundingMode())
            startTime = time.clock()
            ret = lfmtblpy.RD5GetData1MNumericR1(TableID, FltID, SetID, RowNo, nGot.getPtr(), buf.getPtr())
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5GetData1MNumericR1] retval=%d [TableID=%d,FltID=%d,SetID=%s,RowNo=%d][nGot=%d] (%.3fms)" \
                % (ret, TableID, FltID, SetID, RowNo, nGot.at(0), elapsedTime)
            for i in range(nGot.at(0)):
                retVal.retData.append(buf.at(i))
        retVal.appendLogA(msg, MLog.LV_DBG)

    ret = nGot.at(0)

    return ret

## 使用メモリサイズ取得
def getTotalMemorySize(retVal):
    startTime = time.clock()
    ret = lfmtblpy.RD5GetTotalMemorySize()
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetTotalMemorySize] retval=%d (%.3fms)" % (ret, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## セット削除
def deleteSet(retVal, TableID, DelSetID):
    startTime = time.clock()
    ret = lfmtblpy.RD5DeleteSet(TableID, DelSetID)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5DeleteSet] retval=%d [TableID=%d,SetID=%d] (%.3fms)" % (ret, TableID, DelSetID, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## セットコメント取得
def getCommentM(retVal, TableID, SetID):
    attrs = lfmutilpy.CSubsetAttr()
    startTime = time.clock()
    ret = attrs.getAttr(TableID, SetID)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5GetSubsetAttr] retval=%d [TableID=%d,SetID=%d] (%.3fms)" % (ret, TableID, SetID, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)

    # 1バイトずつコードを文字化して文字列を作り、最後にデコード
    scom = ""
    for i in range(lfmtblpy.D5_FILTER_ATTR_SIZE):
        code = attrs.at(i)
        if   code == 0:
            break
        elif code < 0:
            code = 256 + code
        scom += chr(code)
    decodedScom = scom.decode(ENC_OS)

    return decodedScom

## セットコメント設定
def setComment(retVal, TableID, SetID, Scom):
    attrs = lfmutilpy.CSubsetAttr()
    if (Scom == None) or (len(Scom) == 0):
        attrs.put(0, 0) # 終端
    else:
        # エンコードして１バイトずつセット
        encodedScom = Scom.encode(ENC_OS)
        max = lfmtblpy.D5_FILTER_ATTR_SIZE - 2
        for i, c in enumerate(encodedScom):
            attrs.put(i, ord(c))
            if i >= max:
                break
        attrs.put(i + 1, 0) # 終端

    startTime = time.clock()
    ret = attrs.setAttr(TableID, SetID)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5SetSubsetAttr] retval=%d [TableID=%d,SetID=%d] (%.3fms)" % (ret, TableID, SetID, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## ソート
def sortTable(retVal, TableID, FltID, SetId, SortType):
    # SortDir
    if SortType == SORT_TYPE_DSC: # 降順
        sortDir = 1
    else:
        sortDir = 0

    startTime = time.clock()
    ret = lfmtblpy.RD5SortByField(TableID, FltID, SetId, sortDir)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5SortByField] retval=%d [TableID=%d,FltID=%d,SetInID=%d,SortDir=%d] (%.3fms)" % (ret, TableID, FltID, SetId, sortDir, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## 項目転送
def fltTransfer(retVal, TableID, FltID):
    startTime = time.clock()
    ret = lfmtblpy.RD5MoveSlaveFlt2Master(TableID, FltID)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5MoveSlaveFlt2Master] retval=%d [JoinTableID=%d,SlaveFltID=%d] (%.3fms)" % (ret, TableID, FltID, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## 項目削除
def delFilter(retVal, TableID, FltID):
    startTime = time.clock()
    ret = lfmtblpy.RD5DeleteRealFilter(TableID, FltID)
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5DeleteRealFilter] retval=%d [TableID=%d,FltID=%d] (%.3fms)" % (ret, TableID, FltID, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret

## テーブル名変更（文字コード指定）
def renameTable(retVal, TableID, TblName, enc):
    startTime = time.clock()
    ret = lfmtblpy.RD5SetTableName(TableID, TblName.encode(enc))
    elapsedTime = (time.clock() - startTime) * 1000
    msg = "[RD5SetTableName] retval=%d [TableID=%d,TableName=%s(%s)] (%.3fms)" % (ret, TableID, TblName, enc, elapsedTime)
    if ret < 0:
        retVal.appendLogA(msg, MLog.LV_ERR)
        raise MacroError(ret, msg)
    retVal.appendLogA(msg, MLog.LV_DBG)
    return ret


# マクロの戻り値をオブジェクトにするかどうかを設定
def MSetRetObj(bRet):
    global g_flagRetObj
    g_flagRetObj = bRet
    return 0


# === 実行 ===
#$Halt【未サポート】
#$Pause【未サポート】

# $Comment
# 【説明】
# 　文字コメントと時刻を表示します。
# 【引数】
# 　DATETIME：（日付時刻 ＋ ミリ秒）をコメント出力 複数指定時は初回指定のdatetimeのみ置換
# 　DATETIME以外：任意のコメント出力
# 　上記混在：任意のコメントと（日付時刻 ＋ ミリ秒）出力
def MComment(Scom):
    retVal = RetVal()
    retVal.funcName = "MComment"

    # Macro
    msg = "%s(ur\"%s\")" % (retVal.funcName, Scom)
    retVal.appendLogM(msg)
    ret = 0

    # Macro return
    return retVal.makeRetVal(ret)


# === 入出力 ===
# $DBLoad
# 【説明】
# 　ワークスペース（D5Dファイル）をロードします。
# 【引数】
# 　・ワークスペースの格納先フォルダ
# 　・ワークスペース名（拡張子無し）
def MDBLoad(WSPath, WSName):
    retVal = RetVal()
    retVal.funcName = "MDBLoad"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\")" % (retVal.funcName, WSPath, WSName)
    retVal.appendLogM(msg)

    # API
    try:
        startTime = time.clock()
        ret = lfmtblpy.RD5LoadDB(WSPath.encode(ENC_OS), WSName.encode(ENC_OS))
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5LoadDB] retval=%d [DBPath=%s,DBName=%s] (%.3fms)" % (ret, WSPath, WSName, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        else:
            g_WSInfo.update()
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $DBSave
# 【説明】
# 　ワークスペース（D5Dファイル）を保存します。
# 【引数】
# 　・ワークスペースの保存先フォルダ
# 　・保存するワークスペース名（拡張子無し）
def MDBSave(WSPath, WSName):
    retVal = RetVal()
    retVal.funcName = "MDBSave"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\")" % (retVal.funcName, WSPath, WSName)
    retVal.appendLogM(msg)

    # API
    try:
        startTime = time.clock()
        ret = lfmtblpy.RD5SaveDBAs(WSPath.encode(ENC_OS), WSName.encode(ENC_OS))
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5SaveDBAs] retval=%d [DBPath=%s,DBName=%s] (%.3fms)" % (ret, WSPath, WSName, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $DBSaveOldVer
# 【説明】
# 　ワークスペース（D5Dファイル）を指定されたファイルバージョンで保存します。
# 【引数】
# 　・ワークスペースの保存先フォルダ
# 　・保存するワークスペース名（拡張子無し）
# 　・ファイルバージョン
def MDBSaveOldVer(Path, DBName, FileVersion):
    retVal = RetVal()
    retVal.funcName = "MDBSaveOldVer"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\", %d)" % (retVal.funcName, Path, DBName, FileVersion)
    retVal.appendLogM(msg)

    # API
    try:
        startTime = time.clock()
        ret = lfmtblpy.RD5SaveDBAsOldVer(Path.encode(ENC_OS), DBName.encode(ENC_OS), FileVersion)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5SaveDBAsOldVer] retval=%d [DBPath=%s,DBName=%s,FileVersion=%d] (%.3fms)" % (ret, Path, DBName, FileVersion, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $Load
# 【説明】
# 　テーブル（D5Tファイル）をロードします。
# 【引数】
# 　・テーブルの格納先フォルダ
# 　・テーブル名（拡張子無し）
def MLoad(Path, TblName):
    retVal = RetVal()
    retVal.funcName = "MLoad"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\")" % (retVal.funcName, Path, TblName)
    retVal.appendLogM(msg)

    # API
    try:
        startTime = time.clock()
        ret = lfmtblpy.RD5LoadRealTable(Path.encode(ENC_OS), TblName.encode(ENC_OS))
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5LoadRealTable] retval=%d [PCTblPath=%s,PCTblName=%s] (%.3fms)" % (ret, Path, TblName, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        else:
            g_WSInfo.appendTableSub(retVal, ret)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $Save
# 【説明】
# 　テーブル（D5Tファイル）を保存します。
# 【引数】
# 　・テーブルの保存先フォルダ
# 　・保存するテーブル名（拡張子無し）
def MSave(Path, TblName):
    retVal = RetVal()
    retVal.funcName = "MSave"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\")" % (retVal.funcName, Path, TblName)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        # まず、OS文字コードにリネーム
        ret = renameTable(retVal, tableID, TblName, ENC_OS)

        startTime = time.clock()
        ret = lfmtblpy.RD5SaveRealTable(Path.encode(ENC_OS), tableID)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5SaveRealTable] retval=%d [PCTblPath=%s,TableID=%d] (%.3fms)" % (ret, Path, tableID, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

        # DB文字コードに戻す
        ret = renameTable(retVal, tableID, TblName, ENC_DB)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $SaveOLdVer
# 【説明】
# 　テーブル（D5Tファイル）を指定されたファイルバージョンで保存します。
# 【引数】
# 　・テーブルの保存先フォルダ
# 　・保存するテーブル名（拡張子無し）
# 　・ファイルバージョン
def MSaveOldVer(Path, TblName, FileVersion):
    retVal = RetVal()
    retVal.funcName = "MSaveOldVer"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\", %d)" % (retVal.funcName, Path, TblName, FileVersion)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        # まず、OS文字コードにリネーム
        ret = renameTable(retVal, tableID, TblName, ENC_OS)

        startTime = time.clock()
        ret = lfmtblpy.RD5SaveRealTableOldVer(Path.encode(ENC_OS), tableID, FileVersion)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5SaveRealTableOldVer] retval=%d [PCTblPath=%s,TableID=%d,FileVersion=%d] (%.3fms)" % (ret, Path, tableID, FileVersion, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

        # DB文字コードに戻す
        ret = renameTable(retVal, tableID, TblName, ENC_DB)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)


# $Drop
# 【説明】
# 　テーブル（D5Tファイル）をワークスペースから削除します。
# 【引数】
# 　・削除するテーブル名
def MDrop(DelTblName):
    retVal = RetVal()
    retVal.funcName = "MDrop"

    # Macro
    msg = "%s(ur\"%s\")" % (retVal.funcName, DelTblName)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, DelTblName)

        ret = deleteTable(retVal, tableID)

    except MacroError, e:
        ret = e.retCode
        print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $CatalogEx
# 【説明】
# 　カタログファイルからの読み込みを行います。
# 【引数】
# 　・ 作成するテーブル名
# 　・ カタログファイルの格納先フォルダ
# 　・ カタログファイル名（拡張子付き）
# 　・ ソースデータファイルの格納先フォルダ
# 　・ ソースデータファイル名（拡張子付き）
def MCatalogEx(TableName, CatalogPath, CatalogName, SourcePath, SourceName):
    retVal = RetVal()
    retVal.funcName = "MCatalogEx"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\", ur\"%s\", ur\"%s\", ur\"%s\")" % (retVal.funcName, TableName, CatalogPath, CatalogName, SourcePath, SourceName)
    retVal.appendLogM(msg)

    # API
    try:
        startTime = time.clock()
        ret = lfmtblpy.RD5AddCatalogFileEx2(CatalogPath.encode(ENC_OS), CatalogName.encode(ENC_OS) \
                                        , SourcePath.encode(ENC_OS), SourceName.encode(ENC_OS) \
                                        , TableName.encode(ENC_DB))
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5AddCatalogFileEx2] retval=%d [CatalogPath=%s,CatalogName=%s,SourcePath=%s,SourceName=%s,TableName=%s] (%.3fms)"\
            % (ret, CatalogPath, CatalogName, SourcePath, SourceName, TableName, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        else:
            g_WSInfo.appendTableSub(retVal, ret)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $Catalog
# 【説明】
# 　カタログファイル（StructInfo.txt）からの読み込みを行います。
# 【引数】
# 　・カタログファイルの格納先フォルダ
# 　・カタログファイル名（拡張子付き）
def MCatalog(Path, CatName):
    retVal = RetVal()
    retVal.funcName = "MCatalog"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\")" % (retVal.funcName, Path, CatName)
    retVal.appendLogM(msg)

    # API
    try:
        absPath = os.path.normpath(os.path.join(os.getcwd(), Path))
        startTime = time.clock()
        ret = lfmtblpy.RD5AddCatalogFile(absPath.encode(ENC_OS), CatName.encode(ENC_OS))
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5AddCatalogFile] retval=%d [FilePath=%s,FileName=%s] (%.3fms)" % (ret, absPath, CatName, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        else:
            g_WSInfo.appendTableSub(retVal, ret)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $ClearWS
# 【説明】
# 　ロード中のワークスペースをクリアします。
# 【引数】
# 　なし
def MClearWS():
    retVal = RetVal()
    retVal.funcName = "MClearWS"

    # Macro
    msg = "%s()" % (retVal.funcName)
    retVal.appendLogM(msg)

    # API
    try:
        startTime = time.clock()
        ret = lfmtblpy.RD5ClearDB()
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5ClearDB] retval=%d (%.3fms)" % (ret, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $TxtWrite
# 【説明】
# 　テーブルのデータをCSV／TAB区切りファイルに出力します。
# 【引数】
# 　・テーブル名
# 　・区切り文字
# 　・出力先ファイルパス
# 　・出力先ファイル名
# 　・書き出し開始行
# 　・書き出し終了行
# 　・書き出し開始列
# 　・書き出し終了列
# 　・項目行（ヘッダー）を表示するかしないか
# 　・集合ID（省略可）
def MTxtWrite(TblName, wAns, wFPath, wFName, wTop, wBottom, wLeft, wRight, Hans, SetID):
    retVal = RetVal()
    retVal.funcName = "MTxtWrite"

    # Macro
    msg = "%s(ur\"%s\", \"%s\", ur\"%s\", ur\"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", %d)" \
        % (retVal.funcName, TblName, wAns, wFPath, wFName, wTop, wBottom, wLeft, wRight, Hans, SetID)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        setID = SetID

        # 全項目リスト取得
        nFltAll = getNFilter(retVal, tableID)
        idListAll = lfmutilpy.CTypeIntAr(nFltAll)
        nFltAll = getFilterIDList(retVal, tableID, idListAll)
        idListAllList = Array2List(idListAll, nFltAll)

        # 対象項目IDリスト抽出
        iLeft = int(wLeft)
        if wRight == ALL_FILTERS_MARK:
            iRight = nFltAll
        else:
            iRight = int(wRight)
        nFlt = iRight - iLeft + 1
        idList  = lfmutilpy.CTypeIntAr(nFlt + 1)
        idList.put(nFlt, -1)
        for i in range(nFlt):
            idList.put(i, idListAllList[iLeft - 1 + i])

        rowFrom  = int(wTop)
        if wBottom == ALL_FILTERS_MARK:
            rowTo = -1
        else:
            rowTo = int(wBottom)
        datesep  = '/'
        filePath = wFPath
        fileName = wFName

        if wAns == "TAB":
            apiName = "RD5ExportAsTAB"
            startTime = time.clock()
            ret = lfmtblpy.RD5ExportAsTAB(tableID, setID, idList.getPtr(), rowFrom, rowTo, ord(datesep), filePath.encode(ENC_OS), fileName.encode(ENC_OS))
        else:
            apiName = "RD5ExportAsCSV"
            startTime = time.clock()
            ret = lfmtblpy.RD5ExportAsCSV(tableID, setID, idList.getPtr(), rowFrom, rowTo, ord(datesep), filePath.encode(ENC_OS), fileName.encode(ENC_OS))
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[%s] retval=%d [TableID=%d,SetID=%d,IDList=%s,RowFrom=%d,RowTo=%d,Datesep=%s,DBPath=%s,DBName=%s] (%.3fms)" \
            % (apiName, ret, tableID, setID, str(Array2List(idList, nFlt)), rowFrom, rowTo, datesep, filePath, fileName, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

        # ヘッダ（項目名）出力
        if Hans == RECONO_MARK_YES:
            if wAns == "TAB":
                dlm = '\t'
            else:
                dlm = ','

            # 一時ファイルにヘッダ書き出し
            fileOut = os.path.join(filePath, TMP_ADD_HEADER_FILE)
            fOut = open(fileOut, "w")
            for i in range(iLeft, iRight + 1):
                fltID = idListAllList[i - 1]
                try:
                    fltName = getFilterName(retVal, tableID, fltID)
                except MacroError, e:
                    fOut.close()
                    raise
                fOut.write('\"' + fltName + '\"')
                if i < iRight:
                    fOut.write(dlm)
                else:
                    fOut.write('\n')

            # ファイルマージ
            fileIn = os.path.join(filePath, fileName)
            fIn = open(fileIn, "r")
            for line in fIn:
                fOut.write(line)
            fIn.close()
            fOut.close()

            # ファイル置換
            os.remove(fileIn)
            os.rename(fileOut, fileIn)

            ret = 0

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $TxtWriteSelect
# 【説明】
# 　選択範囲を指定してテーブルのデータをCSV／TAB区切りファイルに出力します。
# 【引数】
# 　・テーブル名
# 　・区切り文字
# 　・出力先ファイルパス
# 　・出力先ファイル名
# 　・書き出し開始行
# 　・書き出し終了行
# 　・書き出し項目名
# 　・項目行（ヘッダー）を表示するかしないか
# 　・集合ID（省略可）
def MTxtWriteSelect(TblName, wAns, wFPath, wFName, wTop, wBottom, ItemList, Hans, SetID):
    retVal = RetVal()
    retVal.funcName = "MTxtWriteSelect"

    # Macro
    msg = "%s(ur\"%s\", \"%s\", ur\"%s\", ur\"%s\", \"%s\", \"%s\", %s, \"%s\", %d)" \
        % (retVal.funcName, TblName, wAns, wFPath, wFName, wTop, wBottom, strList(ItemList), Hans, SetID)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        setID = SetID

        # 対象項目IDリスト
        nFlt = len(ItemList) 
        idList  = lfmutilpy.CTypeIntAr(nFlt + 1)
        idList.put(nFlt, -1)
        for i, fltName in enumerate(ItemList):
            if fltName[0] == '+':
                isSlave = 1 # JOIN
                fltName = fltName[1:] # '+'除去
            else:
                isSlave = 0 # REAL
            ret = getFilterIDFromName2(retVal, tableID, isSlave, fltName)
            idList.put(i, ret)

        rowFrom  = int(wTop)
        if wBottom == ALL_FILTERS_MARK:
            rowTo = -1
        else:
            rowTo = int(wBottom)
        datesep  = '/'
        filePath = wFPath
        fileName = wFName

        if wAns == "TAB":
            apiName = "RD5ExportAsTAB"
            startTime = time.clock()
            ret = lfmtblpy.RD5ExportAsTAB(tableID, setID, idList.getPtr(), rowFrom, rowTo, ord(datesep), filePath.encode(ENC_OS), fileName.encode(ENC_OS))
        else:
            apiName = "RD5ExportAsCSV"
            startTime = time.clock()
            ret = lfmtblpy.RD5ExportAsCSV(tableID, setID, idList.getPtr(), rowFrom, rowTo, ord(datesep), filePath.encode(ENC_OS), fileName.encode(ENC_OS))
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[%s] retval=%d [TableID=%d,SetID=%d,IDList=%s,RowFrom=%d,RowTo=%d,Datesep=%s,DBPath=%s,DBName=%s] (%.3fms)" \
            % (apiName, ret, tableID, setID, str(Array2List(idList, nFlt)), rowFrom, rowTo, datesep, filePath, fileName, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

        # ヘッダ（項目名）出力
        if Hans == RECONO_MARK_YES:
            if wAns == "TAB":
                dlm = '\t'
            else:
                dlm = ','

            # 一時ファイルにヘッダ書き出し
            fileOut = os.path.join(filePath, TMP_ADD_HEADER_FILE)
            fOut = open(fileOut, "w")
            for i, fltName in enumerate(ItemList):
                if fltName[0] == '+':
                    fltName = fltName[1:] # '+'除去
                fOut.write('\"' + fltName + '\"')
                if i < (nFlt - 1):
                    fOut.write(dlm)
                else:
                    fOut.write('\n')

            # ファイルマージ
            fileIn = os.path.join(filePath, fileName)
            fIn = open(fileIn, "r")
            for line in fIn:
                fOut.write(line)
            fIn.close()
            fOut.close()

            # ファイル置換
            os.remove(fileIn)
            os.rename(fileOut, fileIn)

            ret = 0

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)


# $MultiDrop
# 【説明】
# 　テーブル（D5Tファイル）をワークスペースから削除します。(複数項目)
# 【引数】
# 　削除するテーブル名
def MMultiDrop(DelTblNameList):
    retVal = RetVal()
    retVal.funcName = "MMultiDrop"

    # Macro
    msg = "%s(%s)" % (retVal.funcName, strList(DelTblNameList))
    retVal.appendLogM(msg)

    # API
    try:
        for delTblName in DelTblNameList:
            tableID = getTableIDFromName(retVal, delTblName)

            startTime = time.clock()
            ret = lfmtblpy.RD5DeleteTable(tableID)
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5DeleteTable] retval=%d [TableID=%d] (%.3fms)" % (ret, tableID, elapsedTime)
            if ret < 0:
                retVal.appendLogA(msg, MLog.LV_ERR)
                raise MacroError(ret, msg)
            retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)


# === ﾃｰﾌﾞﾙ操作 ===
# $Union
# 【説明】
# 　縦結合を行います。
# 【引数】
# 　・縦結合テーブル名
# 　・マスターテーブル名
# 　・スレイブテーブル名
# 　・マスターテーブルの集合ID
# 　・スレイブテーブルの集合ID
# 　・マスターテーブルの結合キー項目
# 　・スレイブテーブルの結合キー項目
# 　・マスターテーブルのIDを表示するかしないか
# 　・スレイブテーブルのRecNoを表示するかしないか
# 　・元テーブルを削除するかしないか（省略可）
def MUnion(RTblName, MTblName, STblName, MSetID, SSetID, MJKeyNm, SJKeyNm, TblIDAns, RecNoAns, *DelTblAns):
    retVal = RetVal()
    retVal.funcName = "MUnion"

    # Macro
    if DelTblAns == (): # 省略
        delTblAns = ""
        msg = "%s(ur\"%s\", ur\"%s\", ur\"%s\", %d, %d, %s, %s, \"%s\", \"%s\")" \
            % (retVal.funcName, RTblName, MTblName, STblName, MSetID, SSetID, strList(MJKeyNm), strList(SJKeyNm), TblIDAns, RecNoAns)
    else:
        delTblAns = DelTblAns[0]
        msg = "%s(ur\"%s\", ur\"%s\", ur\"%s\", %d, %d, %s, %s, \"%s\", \"%s\", \"%s\")" \
            % (retVal.funcName, RTblName, MTblName, STblName, MSetID, SSetID, strList(MJKeyNm), strList(SJKeyNm), TblIDAns, RecNoAns, delTblAns)
    retVal.appendLogM(msg)

    # API
    try:
        tableID1 = getTableIDFromName(retVal, MTblName)
        tableID2 = getTableIDFromName(retVal, STblName)

        # FltIDs1
        if (MJKeyNm == ALL_FILTERS_MARK) or (MJKeyNm[0] == ALL_FILTERS_MARK): # 全項目
            nFlt1 = 0
            fltIDs1 = None
            argFltIDs1 = None
        else:
            nFlt1 = len(MJKeyNm)
            fltIDs1 = lfmutilpy.CTypeIntAr(nFlt1 + 1)
            fltIDs1.put(nFlt1, -1) # 終端
            for i, v in enumerate(MJKeyNm):
                if v == NO_FILTER_MARK: # 項目無指定
                    fltIDs1.put(i, 0)
                else:
                    ret = getFilterIDFromName(retVal, tableID1, v)
                    fltIDs1.put(i, ret)
            argFltIDs1 = fltIDs1.getPtr()

        # FltIDs2
        if (SJKeyNm == ALL_FILTERS_MARK) or (SJKeyNm[0] == ALL_FILTERS_MARK): # 全項目
            nFlt2 = 0
            fltIDs2 = None
            argFltIDs2 = None
        else:
            nFlt2 = len(SJKeyNm)
            fltIDs2 = lfmutilpy.CTypeIntAr(nFlt2 + 1)
            fltIDs2.put(nFlt2, -1) # 終端
            for i, v in enumerate(SJKeyNm):
                if v == NO_FILTER_MARK: # 項目無指定
                    fltIDs2.put(i, 0)
                else:
                    ret = getFilterIDFromName(retVal, tableID2, v)
                    fltIDs2.put(i, ret)
            argFltIDs2 = fltIDs2.getPtr()

        # IncludeTableID
        if TblIDAns == RECONO_MARK_YES:
            includeTableID = 1
        else:
            includeTableID = 0

        # IncludeRecNo
        if RecNoAns == RECONO_MARK_YES:
            includeRecNo = 1
        else:
            includeRecNo = 0

        startTime = time.clock()
        ret = lfmtblpy.RD5CombineRealTableEx(RTblName.encode(ENC_DB), includeTableID, includeRecNo \
                                            , tableID1, MSetID, argFltIDs1, tableID2, SSetID, argFltIDs2)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5CombineRealTableEx] retval=%d [PCTblName=%s,IncludeTableID=%d,IncludeRecNo=%d,TableID1=%d,SetID1=%d,FltIDs1=%s,TableID2=%d,SetID2=%d,FltIDs2=%s] (%.3fms)" \
            % (ret, RTblName, includeTableID, includeRecNo, tableID1, MSetID, str(Array2List(fltIDs1, nFlt1)), tableID2, SSetID, str(Array2List(fltIDs2, nFlt2)), elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        else:
            g_WSInfo.appendTableSub(retVal, ret)
        retVal.appendLogA(msg, MLog.LV_DBG)
        RTblID = ret

        # 元テーブル削除
        if delTblAns == RECONO_MARK_YES:
            ret = deleteTable(retVal, tableID1)
            if tableID1 != tableID2:
                ret = deleteTable(retVal, tableID2)

        ret = RTblID

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $CreateJoin
# 【説明】
# 　JOINテーブルを作成します。
# 【引数】
# 　・作成するJOIN テーブル名
# 　・マスターテーブル名
# 　・スレイブテーブル名
# 　・マスター集合ＩＤ
# 　・スレイブ集合ＩＤ
# 　・マスター側JOINキー項目名
# 　・スレイブ側JOINキー項目名
# 　・内部JOIN （Inner） か 外部JOIN （Outer）
def MCreateJoin(JTblName, MTblName, STblName, MSetID, SSetID, MJoinKeyItem, SJoinKeyItem, InOrOut):
    retVal = RetVal()
    retVal.funcName = "MCreateJoin"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\", ur\"%s\", %d, %d, ur\"%s\", ur\"%s\", ur\"%s\")" \
        % (retVal.funcName, JTblName, MTblName, STblName, MSetID, SSetID, strList(MJoinKeyItem), strList(SJoinKeyItem), InOrOut)
    retVal.appendLogM(msg)

    # API
    try:
        tableID1 = getTableIDFromName(retVal, MTblName)
        tableID2 = getTableIDFromName(retVal, STblName)

        # MasterFltIDs
        nFlt1 = len(MJoinKeyItem)
        fltIDs1 = lfmutilpy.CTypeIntAr(nFlt1 + 1)
        fltIDs1.put(nFlt1, -1) # 終端
        for i, v in enumerate(MJoinKeyItem):
            ret = getFilterIDFromName(retVal, tableID1, v)
            fltIDs1.put(i, ret)

        # SlaveFltIDs
        nFlt2 = len(SJoinKeyItem)
        fltIDs2 = lfmutilpy.CTypeIntAr(nFlt2 + 1)
        fltIDs2.put(nFlt2, -1) # 終端
        for i, v in enumerate(SJoinKeyItem):
            ret = getFilterIDFromName(retVal, tableID2, v)
            fltIDs2.put(i, ret)

        # IsOuter
        if InOrOut == RECONO_MARK_YES:
            isOuter = 1
        else:
            isOuter = 0

        startTime = time.clock()
        ret = lfmtblpy.RD5AddJoinTable(JTblName.encode(ENC_DB), isOuter, tableID1, MSetID, fltIDs1.getPtr(), tableID2, SSetID, fltIDs2.getPtr())
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5AddJoinTable] retval=%d [PCTblName=%s,IsOuter=%d,MasterTblID=%d,MasterSetID=%d,MasterFltIDs=%s,SlaveTblID=%d,SlaveSetID=%d,SlaveFltIDs=%s] (%.3fms)" \
            % (ret, JTblName, isOuter, tableID1, MSetID, str(Array2List(fltIDs1, nFlt1)), tableID2, SSetID, str(Array2List(fltIDs2, nFlt2)), elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        else:
            g_WSInfo.appendTableSub(retVal, ret)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $FltTransfer
# 【説明】
# 　項目転送を行います。
# 　（JOIN テーブルのスレイブ側項目をマスターテーブルに転送する機能）
# 【引数】
# 　・転送元JOIN テーブル名
# 　・転送項目名
def MFltTransfer(JTblName, SFltName):
    retVal = RetVal()
    retVal.funcName = "MFltTransfer"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\")" % (retVal.funcName, JTblName, SFltName)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, JTblName)
        fltID = getFilterIDFromName(retVal, g_WSInfo.getSlaveTableId(tableID), SFltName)

        ret = fltTransfer(retVal, tableID, fltID)

    except MacroError, e:
        ret = e.retCode
        print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

## $MultiFltTransfer
def MMultiFltTransfer(JTblName, FltNameList):
    retVal = RetVal()
    retVal.funcName = "MMultiFltTransfer"

    # Macro
    msg = "%s(ur\"%s\", %s)" % (retVal.funcName, JTblName, strList(FltNameList))
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, JTblName)

        for fltName in FltNameList:
            fltID = getFilterIDFromName(retVal, tableID, fltName)
            ret = fltTransfer(retVal, tableID, fltID)

    except MacroError, e:
        ret = e.retCode
        print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $INOUT
# 【説明】
# 　JOINテーブルのINまたはOUTの集合を、マスターまたはスレイブテーブルのサブテーブルとして作成します。
# 【引数】
# 　・Joinテーブル名
# 　・抽出するテーブルがスレイブテーブルかマスターテーブル
# 　・実テーブルおよびJOINテーブルにある行を抽出するか（IN集合）
# 　　実テーブルにありJOINテーブルにない行を抽出するか（OUT集合）を指定。
def MINOUT(JTblName, IsSlaveAns, IsJoinOutAns):
    retVal = RetVal()
    retVal.funcName = "MINOUT"

    # Macro
    msg = "%s(ur\"%s\", \"%s\", \"%s\")" % (retVal.funcName, JTblName, IsSlaveAns, IsJoinOutAns)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, JTblName)

        # PutSlave
        if IsSlaveAns == RECONO_MARK_YES:
            putSlave = 1
        else:
            putSlave = 0

        # PutJoinOut
        if IsJoinOutAns == RECONO_MARK_YES:
            putJoinOut = 1
        else:
            putJoinOut = 0

        targetTableID   = lfmutilpy.CTypeIntAr(1)
        targetSetID     = lfmutilpy.CTypeIntAr(1)

        startTime = time.clock()
        ret = lfmtblpy.RD5PutJoinSetToParent(tableID, putSlave, putJoinOut, targetTableID.getPtr(), targetSetID.getPtr())
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5PutJoinSetToParent] retval=%d [JTableID=%d,PutSlave=%d,PutJoinOut=%d][TargetTableID=%d,TargetSetID=%d] (%.3fms)"\
            % (ret, tableID, putSlave, putJoinOut, targetTableID.at(0), targetSetID.at(0), elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

        # 追加されたテーブルIDとセットID
        tid = targetTableID.at(0)
        sid = targetSetID.at(0)
        retVal.retData = (tid, sid)
        msg = "TargetTableID=%d,TargetSetID=%d" % (tid, sid)
        retVal.appendLogM2(msg)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $JoinRealize
# 【説明】
# 　JOINテーブルを実テーブルに変換します。
# 【引数】
# 　・実テーブルに変換するJOIN テーブル名
# 　・実体化テーブル名
# 　・変換する集合ID
# 　・マスターテーブルのRecNoを表示するかしないかを指定。
# 　・スレイブテーブルのRecNoを表示するかしないかを指定。
# 　・実テーブルに変換する項目名
def MJoinRealize(JTblName, TblName, SetID, MRecNoAns, SRecNoAns, FltName):
    retVal = RetVal()
    retVal.funcName = "MJoinRealize"

    # Macro
    if isinstance(FltName, types.ListType):
        msg = "%s(ur\"%s\", ur\"%s\", %d, \"%s\", \"%s\", %s)" % (retVal.funcName, JTblName, TblName, SetID, MRecNoAns, SRecNoAns, strList(FltName))
    else:
        msg = "%s(ur\"%s\", ur\"%s\", %d, \"%s\", \"%s\", \"%s\")" % (retVal.funcName, JTblName, TblName, SetID, MRecNoAns, SRecNoAns, FltName)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, JTblName)

        # IncludeRowNoM
        if MRecNoAns == RECONO_MARK_YES:
            includeRowNoM = 1
        else:
            includeRowNoM = 0

        # IncludeRowNoS
        if SRecNoAns == RECONO_MARK_YES:
            includeRowNoS = 1
        else:
            includeRowNoS = 0

        # FltIDs
        if (FltName == ALL_FILTERS_MARK) or (FltName[0] == ALL_FILTERS_MARK):
            # 全項目リスト取得
            nFlt = getNFilter(retVal, tableID)
            fltIDs = lfmutilpy.CTypeIntAr(nFlt + 1)
            fltIDs.put(nFlt, 0) # 終端
            ret = getFilterIDList(retVal, tableID, fltIDs)
        elif (FltName == NO_FILTER_MARK) or (FltName[0] == NO_FILTER_MARK): # 項目無指定
            nFlt = 1
            fltIDs = lfmutilpy.CTypeIntAr(nFlt)
            fltIDs.put(nFlt, 0) # 終端
        else:
            fltNameList = getFilterNameList(retVal, tableID)
            nFlt = len(FltName)
            fltIDs = lfmutilpy.CTypeIntAr(nFlt + 1)
            fltIDs.put(nFlt, 0) # 終端
            for i, v in enumerate(FltName):
                fltIDs.put(i, fltNameList.index(v) + 1) # JOINテーブル中のID

        # VLIsLinked（常に0）
        vlIsLinked = 0

        startTime = time.clock()
        ret = lfmtblpy.RD5ConvertJoinToReal(TblName.encode(ENC_DB), tableID, SetID, includeRowNoM, includeRowNoS, fltIDs.getPtr(), vlIsLinked)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5ConvertJoinToReal] retval=%d [PCTblName=%s,JoinTblID=%d,JSetID=%d,IncludeRowNoM=%d,IncludeRowNoS=%d,FltIDs=%s,VLIsLinked=%d] (%.3fms)" \
            % (ret, TblName, tableID, SetID, includeRowNoM, includeRowNoS, str(Array2List(fltIDs, nFlt)), vlIsLinked, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        else:
            g_WSInfo.appendTableSub(retVal, ret)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $ExUnique
# 【説明】
# 　ユニーク行の抽出を行います。
# 【引数】
# 　・対象テーブル名
# 　・集合ID
# 　・抽出項目
# 　・元の順序を保存するかどうか
def MExUnique(TblName, SetID, FltNameList, CnsvOdrAns):
    retVal = RetVal()
    retVal.funcName = "MExUnique"

    # Macro
    if isinstance(FltNameList, types.ListType):
        msg = "%s(ur\"%s\", %d, %s, \"%s\")" % (retVal.funcName, TblName, SetID, strList(FltNameList), CnsvOdrAns)
    else:
        msg = "%s(ur\"%s\", %d, ur\"%s\", \"%s\")" % (retVal.funcName, TblName, SetID, FltNameList, CnsvOdrAns)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        # FltIDs
        if (FltNameList == ALL_FILTERS_MARK) or (FltNameList[0] == ALL_FILTERS_MARK):
            # 全項目リスト取得
            nFlt = getNFilter(retVal, tableID)
            fltIDs = lfmutilpy.CTypeIntAr(nFlt + 1)
            fltIDs.put(nFlt, 0) # 終端
            ret = getFilterIDList(retVal, tableID, fltIDs)
        else:
            nFlt = len(FltNameList)
            fltIDs = lfmutilpy.CTypeIntAr(nFlt + 1)
            fltIDs.put(nFlt, 0) # 終端
            for i, v in enumerate(FltNameList):
                ret = getFilterIDFromName(retVal, tableID, v)
                fltIDs.put(i, ret)

        # ConserveOriginalOrder
        if CnsvOdrAns == RECONO_MARK_YES:
            conserveOriginalOrder = 1
        else:
            conserveOriginalOrder = 0

        startTime = time.clock()
        ret = lfmtblpy.RD5ExtractUniqueReal(0, tableID, SetID, fltIDs.getPtr(), conserveOriginalOrder)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5ExtractUniqueReal] retval=%d [TableID=%d,SetID=%d,FltIDs=%s,ConserveOriginalOrder=%d] (%.3fms)" \
            % (ret, tableID, SetID, str(Array2List(fltIDs, nFlt)), conserveOriginalOrder, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $ExtSubTable
# 【説明】
# 　サブテーブル（集合）を実テーブルに抽出します。
# 【引数】
# 　・抽出対象サブテーブルを保持するテーブル名
# 　・抽出対象集合ID
# 　・抽出対象テーブルのIDを表示するかしないか
# 　・抽出対象テーブルのRecNoを表示するかしないか
# 　・抽出項目
# 　・抽出後のテーブル名（省略可）
def MExtSubTable(TblName, SetID, TblIDAns, RecNoAns, FltNameList, *NewTblName):
    retVal = RetVal()
    retVal.funcName = "MExtSubTable"

    # Macro
    if NewTblName == (): # 省略
        newTblName = TblName
        msg = "%s(ur\"%s\", %d, \"%s\", \"%s\", %s)" % (retVal.funcName, TblName, SetID, TblIDAns, RecNoAns, strList(FltNameList))
    else:
        newTblName = NewTblName[0]
        msg = "%s(ur\"%s\", %d, \"%s\", \"%s\", %s, ur\"%s\")" % (retVal.funcName, TblName, SetID, TblIDAns, RecNoAns, strList(FltNameList), newTblName)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        # FltIDs
        if (FltNameList == ALL_FILTERS_MARK) or (FltNameList[0] == ALL_FILTERS_MARK):
            # 全項目リスト取得
            nFlt = getNFilter(retVal, tableID)
            fltIDs = lfmutilpy.CTypeIntAr(nFlt + 1)
            fltIDs.put(nFlt, 0) # 終端
            ret = getFilterIDList(retVal, tableID, fltIDs)
        else:
            nFlt = len(FltNameList)
            fltIDs = lfmutilpy.CTypeIntAr(nFlt + 1)
            fltIDs.put(nFlt, 0) # 終端
            for i, v in enumerate(FltNameList):
                ret = getFilterIDFromName(retVal, tableID, v)
                fltIDs.put(i, ret)

        # IncludeTableID
        if TblIDAns == RECONO_MARK_YES:
            includeTableID = 1
        else:
            includeTableID = 0

        # IncludeRecNo
        if RecNoAns == RECONO_MARK_YES:
            includeRecNo = 1
        else:
            includeRecNo = 0

        startTime = time.clock()
        ret = lfmtblpy.RD5ExtractRealTableEx(newTblName.encode(ENC_DB), tableID, SetID, includeTableID, includeRecNo, fltIDs.getPtr())
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5ExtractRealTableEx] retval=%d [PCTblName=%s,TableID=%d,SetID=%d,IncludeTableID=%d,IncludeTableID=%d,ExtractFilterIDList=%s] (%.3fms)" \
            % (ret, newTblName, tableID, SetID, includeTableID, includeRecNo, str(Array2List(fltIDs, nFlt)), elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)


# $Condense
# 【説明】
# 　テーブルを圧縮・最適化します。
# 【引数】
# 　・圧縮対象テーブル名
def MCondense(TableName):
    retVal = RetVal()
    retVal.funcName = "MCondense"

    # Macro
    msg = "%s(ur\"%s\")" % (retVal.funcName, TableName)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TableName)

        startTime = time.clock()
        ret = lfmtblpy.RD5CondenseRealTable(tableID)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5CondenseRealTable] retval=%d [TableID=%d] (%.3fms)" % (ret, tableID, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)


#$MISC
#$MultiFltTransfer


# === ﾃｰﾌﾞﾙ編集 ===
# $CreateTbl
# 【説明】
# テーブルを新規に作成します。
# 【引数】
# ・作成するテーブル行数
# ・作成するテーブル名
def MCreateTbl(Row, Name):
    retVal = RetVal()
    retVal.funcName = "MCreateTbl"

    # Macro
    msg = "%s(%d, ur\"%s\")" % (retVal.funcName, Row, Name)
    retVal.appendLogM(msg)

    # API
    try:
        startTime = time.clock()
        ret = lfmtblpy.RD5AddRealTable(Name.encode(ENC_DB), Row)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5AddRealTable] retval=%d [PCTblName=%s,RowCount=%d] (%.3fms)" % (ret, Name, Row, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        else:
            g_WSInfo.appendTableSub(retVal, ret)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $Rename
# 【説明】
# 　テーブル名を変更します。
# 【引数】
# 　・変更前テーブル名
# 　・変更後テーブル名
def MRename(BeforeName, AfterName):
    retVal = RetVal()
    retVal.funcName = "MRename"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\")" % (retVal.funcName, BeforeName, AfterName)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, BeforeName)

        ret = renameTable(retVal, tableID, AfterName, ENC_DB)

        # 実際に付けられた新しいテーブル名
        newName = getTableName(retVal, tableID)
        retVal.retData = newName
        msg = "NewName=%s" % (newName)
        retVal.appendLogM2(msg)

    except MacroError, e:
        ret = e.retCode
        print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $TableDupl
# 【説明】
# 　テーブルの複製を行います。
# 【引数】
# 　・複製元テーブルの名称
def MTableDupl(TblName):
    retVal = RetVal()
    retVal.funcName = "MTableDupl"

    # Macro
    msg = "%s(ur\"%s\")" % (retVal.funcName, TblName)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        startTime = time.clock()
        ret = lfmtblpy.RD5DuplicateRealTable(TblName.encode(ENC_DB), tableID)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5DuplicateRealTable] retval=%d [PCTblName=%s,TableID=%d] (%.3fms)" % (ret, TblName, tableID, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        else:
            g_WSInfo.appendTableSub(retVal, ret)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $InsertRow
# 【説明】
# 　挿入開始行の前に行を追加します。
# 【引数】
# 　・テーブル名
# 　・挿入開始行
# 　・挿入行数
def MInsertRow(TblName, StartRow, RowCnt):
    retVal = RetVal()
    retVal.funcName = "MInsertRow"

    # Macro
    msg = "%s(ur\"%s\", %d, %d)" % (retVal.funcName, TblName, StartRow, RowCnt)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        startTime = time.clock()
        ret = lfmtblpy.RD5InsertRealRows(tableID, StartRow, RowCnt)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5InsertRealRows] retval=%d [TableID=%d,InsPos=%d,InsCount=%d] (%.3fms)" % (ret, tableID, StartRow, RowCnt, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $AppendRow
# 【説明】
# 追加開始行の後ろに行を追加します。
# 【引数】
# ・テーブル名
# ・追加開始行
# ・追加行数
def MAppendRow(TblName, StartRow, RowCnt):
    retVal = RetVal()
    retVal.funcName = "MAppendRow"

    # Macro
    msg = "%s(ur\"%s\", %d, %d)" % (retVal.funcName, TblName, StartRow, RowCnt)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        startRow = StartRow + 1

        startTime = time.clock()
        ret = lfmtblpy.RD5InsertRealRows(tableID, startRow, RowCnt)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5InsertRealRows] retval=%d [TableID=%d,InsPos=%d,InsCount=%d] (%.3fms)" % (ret, tableID, startRow, RowCnt, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $DeleteRow
# 【説明】
# 行の削除を行います。
# 【引数】
# ・テーブル名
# ・削除開始行
# ・削除行数
# ・集合ID（省略した場合はカレント集合ID）
def MDeleteRow(TblName, StartRow, RowCnt, *SetID):
    retVal = RetVal()
    retVal.funcName = "MDeleteRow"

    # Macro
    if SetID == (): # 省略
        setID = -1 
        msg = "%s(ur\"%s\", %d, %d)" % (retVal.funcName, TblName, StartRow, RowCnt)
    else:
        setID = SetID[0]
        msg = "%s(ur\"%s\", %d, %d, %d)" % (retVal.funcName, TblName, StartRow, RowCnt, setID)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        startTime = time.clock()
        ret = lfmtblpy.RD5DeleteRealRowsEx(tableID, setID, StartRow, RowCnt)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5DeleteRealRowsEx] retval=%d [TableID=%d,SetID=%d,DelStart=%d,DelCount=%d] (%.3fms)" % (ret, tableID, setID, StartRow, RowCnt, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $AddRealFilter
# 【説明】
#　 項目を追加します。
# 【引数】
# 　・追加先テーブル名
# 　・追加項目位置
# 　・追加項目名
# 　・追加項目のデータ型
# 　・項目ファイルパス
# 　・項目ファイル名（拡張子付き）
def MAddRealFilter(TblName, Pos, NewFilName, FilType, Fpath, Fname):
    retVal = RetVal()
    retVal.funcName = "MAddRealFilter"

    # Macro
    msg = "%s(ur\"%s\", \"%s\", ur\"%s\", \"%s\", ur\"%s\", ur\"%s\")" % (retVal.funcName, TblName, Pos, NewFilName, FilType, Fpath, Fname)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        if Pos == "":
            loc = 0
        else:
            fltID = getFilterIDFromName(retVal, tableID, Pos)

            # 全項目リスト取得
            nFltAll = getNFilter(retVal, tableID)
            idListAll = lfmutilpy.CTypeIntAr(nFltAll)
            nFltAll = getFilterIDList(retVal, tableID, idListAll)
            idListAllList = Array2List(idListAll, nFltAll)
            loc = idListAllList.index(fltID) + 1 # 項目位置

        # DataArraySize ← テーブル行数
        dataArraySize = getTotalRows(retVal, tableID)

        # DataTypeNo, DataUnitSize
        if FilType in MAP_DATA_TYPE_CN:
            dataTypeNo   = MAP_DATA_TYPE_CN[FilType]
            dataUnitSize = MAP_DATA_TYPE_SIZE[dataTypeNo]
        else:
            dataTypeNo = 0
            dataUnitSize = 0

        startTime = time.clock()
        ret = lfmtblpy.RD5AddRealFilter2(tableID, loc, NewFilName.encode(ENC_DB), dataTypeNo, dataArraySize, dataUnitSize, Fpath.encode(ENC_OS), Fname.encode(ENC_OS))
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5AddRealFilter2] retval=%d [TableID=%d,Loc=%d,FilterName=%s,DataTypeNo=%d,DataArraySize=%d,DataUnitSize=%d,FilePath=%s,FileName=%s] (%.3fms)"\
            % (ret, tableID, loc, NewFilName, dataTypeNo, dataArraySize, dataUnitSize, Fpath, Fname, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $AddRealFilterNumeric
# 【説明】
# Numeric項目を追加します。
# 【引数】
# ・追加先テーブル名
# ・追加項目位置
# ・追加項目名ｚｚ
# ・追加項目のデータ型
# ・スケール値（0～38の数値を指定）
# ・丸めモード（下記に示す0～6の数値または数値に対応した文字列を指定）
# ・項目ファイルパス
# ・項目ファイル名（拡張子付き）
def MAddRealFilterNumeric(TblName, Pos, NewFilName, FilType, Scale, Mode, Fpath, Fname):
    retVal = RetVal()
    retVal.funcName = "MAddRealFilterNumeric"

    # Macro
    if isinstance(Mode, types.IntType):
        msg = "%s(ur\"%s\", \"%s\", ur\"%s\", \"%s\", %d, %d, ur\"%s\", ur\"%s\")" % (retVal.funcName, TblName, Pos, NewFilName, FilType, Scale, Mode, Fpath, Fname)
    else:
        msg = "%s(ur\"%s\", \"%s\", ur\"%s\", \"%s\", %d, \"%s\", ur\"%s\", ur\"%s\")" % (retVal.funcName, TblName, Pos, NewFilName, FilType, Scale, Mode, Fpath, Fname)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        if Pos == "":
            loc = 0
        else:
            fltID = getFilterIDFromName(retVal, tableID, Pos)

            # 全項目リスト取得
            nFltAll = getNFilter(retVal, tableID)
            idListAll = lfmutilpy.CTypeIntAr(nFltAll)
            nFltAll = getFilterIDList(retVal, tableID, idListAll)
            idListAllList = Array2List(idListAll, nFltAll)
            loc = idListAllList.index(fltID) + 1 # 項目位置

        # DataArraySize ← テーブル行数
        dataArraySize = getTotalRows(retVal, tableID)

        scale = int(Scale)
        if Mode in MAP_ROUND_MODE:
            roundMode = MAP_ROUND_MODE[Mode]
        else:
            roundMode = -1

        startTime = time.clock()
        ret = lfmtblpy.RD5AddRealFilter2Numeric(tableID, loc, NewFilName.encode(ENC_DB), dataArraySize, scale, roundMode, Fpath.encode(ENC_OS), Fname.encode(ENC_OS))
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5AddRealFilter2Numeric] retval=%d [TableID=%d,Loc=%d,FilterName=%s,DataArraySize=%d,Scale=%d,RoundMode=%d,FilePath=%s,FileName=%s] (%.3fms)"\
            % (ret, tableID, loc, NewFilName, dataArraySize, scale, roundMode, Fpath, Fname, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $DuplFilter
# 【説明】
# 　項目の複製を行います。
# 【引数】
# 　・テーブル名
# 　・複製元項目名
def MDuplFilter(TblName, FltName):
    retVal = RetVal()
    retVal.funcName = "MDuplFilter"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\")" % (retVal.funcName, TblName, FltName)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        fltID = getFilterIDFromName(retVal, tableID, FltName)

        startTime = time.clock()
        ret = lfmtblpy.RD5DupRealFilter(tableID, fltID)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5DupRealFilter] retval=%d [TableID=%d,FltID=%d] (%.3fms)" % (ret, tableID, fltID, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $MoveFilter
# 【説明】
# 　項目の移動を行います。
# 【引数】
# 　・テーブル名
# 　・移動対象項目名
#　 ・移動先項目名
def MMoveFilter(TblName, SrcFltNameList, DstFltName):
    retVal = RetVal()
    retVal.funcName = "MMoveFilter"

    # Macro
    msg = "%s(ur\"%s\", %s, ur\"%s\")" % (retVal.funcName, TblName, strList(SrcFltNameList), DstFltName)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        fltID = getFilterIDFromName(retVal, tableID, DstFltName)

        srcFltIDList = []
        for fltName in SrcFltNameList:
            ret = getFilterIDFromName(retVal, tableID, fltName)
            srcFltIDList.append(ret)

        # 全項目リスト取得
        nFltAll = getNFilter(retVal, tableID)
        idListAll = lfmutilpy.CTypeIntAr(nFltAll)
        nFltAll = getFilterIDList(retVal, tableID, idListAll)
        idListAllList = Array2List(idListAll, nFltAll)

#       print str(idListAllList) #debug
        dstIdx = idListAllList.index(fltID)
        for srcFltID in srcFltIDList:
            srcIdx = idListAllList.index(srcFltID)
            startTime = time.clock()
            ret = lfmtblpy.RD5MoveRealFilter(tableID, srcIdx, dstIdx)
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5MoveRealFilter] retval=%d [TableID=%d,FromIndex=%d,ToIndex=%d] (%.3fms)" % (ret, tableID, srcIdx, dstIdx, elapsedTime)
            if ret < 0:
                retVal.appendLogA(msg, MLog.LV_ERR)
                raise MacroError(ret, msg)
            retVal.appendLogA(msg, MLog.LV_DBG)
            x = idListAllList.pop(srcIdx)
            idListAllList.insert(dstIdx, x)
#           print str(idListAllList) #debug
            if dstIdx < srcIdx: # 前方
                dstIdx += 1

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

#$FilterSort


# $DelFilter
# 【説明】
# 　項目の削除を行います。
# 【引数】
# 　・テーブル名
# 　・削除項目名
def MDelFilter(TblName, FltName):
    retVal = RetVal()
    retVal.funcName = "MDelFilter"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\")" % (retVal.funcName, TblName, FltName)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        fltID = getFilterIDFromName(retVal, tableID, FltName)

        ret = delFilter(retVal, tableID, fltID)

    except MacroError, e:
        ret = e.retCode
        print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

def MMultiDelFilter(TblName, FltNameList):
    retVal = RetVal()
    retVal.funcName = "MMultiDelFilter"

    # Macro
    msg = "%s(ur\"%s\", %s)" % (retVal.funcName, TblName, strList(FltNameList))
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        for fltName in FltNameList:
            fltID = getFilterIDFromName(retVal, tableID, fltName)
            ret = delFilter(retVal, tableID, fltID)

    except MacroError, e:
        ret = e.retCode
        print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

#$VisibleFilter


# $RenameFilter
# 【説明】
# 　項目名の変更を行います。
# 【引数】
# 　・テーブル名
# 　・変更前項目名
# 　・変更後項目名
def MRenameFilter(TblName, BeforeFName, AfterFName):
    retVal = RetVal()
    retVal.funcName = "MRenameFilter"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\", ur\"%s\")" % (retVal.funcName, TblName, BeforeFName, AfterFName)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        fltID = getFilterIDFromName(retVal, tableID, BeforeFName)

        startTime = time.clock()
        ret = lfmtblpy.RD5SetFilterName(tableID, fltID, AfterFName.encode(ENC_DB))
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5SetFilterName] retval=%d [TableID=%d,FilterID=%d,FilterName=%s] (%.3fms)" % (ret, tableID, fltID, AfterFName, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

        # 実際に付けられた新しい項目名
        newName = getFilterName(retVal, tableID, fltID)
        retVal.retData = newName
        msg = "NewName=%s" % (newName)
        retVal.appendLogM2(msg)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $TypeConv
# 【説明】
# 　項目の型変換項目複製を行います。
# 【引数】
# 　・テーブル名
# 　・変換対象項目名
# 　・変換データ型
def MTypeConv(TblName, FltName, DestType):
    retVal = RetVal()
    retVal.funcName = "MTypeConv"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\", \"%s\")" % (retVal.funcName, TblName, FltName, DestType)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        fltID = getFilterIDFromName(retVal, tableID, FltName)

        # DestType
        if DestType in MAP_DATA_TYPE_CN:
            destType = MAP_DATA_TYPE_CN[DestType]
        else:
            destType = 0

        startTime = time.clock()
        ret = lfmtblpy.RD5DupRealFilterEx(tableID, fltID, destType)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5DupRealFilterEx] retval=%d [TableID=%d,FltID=%d,DestType=%d] (%.3fms)" % (ret, tableID, fltID, destType, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $TypeConvNumeric
# 【説明】
# 　項目のNumeric型変換複製を行います。
# 【引数】
# 　・テーブル名
# 　・変換対象項目名
# 　・スケール値（0～38の数値を指定）
# 　・丸めモード（下記に示す0～6の数値または数値に対応した文字列を指定）
def MTypeConvNumeric(TblName, FltName, Scale, Mode):
    retVal = RetVal()
    retVal.funcName = "MTypeConvNumeric"

    # Macro
    if isinstance(Mode, types.IntType):
        msg = "%s(ur\"%s\", ur\"%s\", %d, %d)" % (retVal.funcName, TblName, FltName, Scale, Mode)
    else:
        msg = "%s(ur\"%s\", ur\"%s\", %d, \"%s\")" % (retVal.funcName, TblName, FltName, Scale, Mode)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        fltID = getFilterIDFromName(retVal, tableID, FltName)

        scale = int(Scale)
        if Mode in MAP_ROUND_MODE:
            roundMode = MAP_ROUND_MODE[Mode]
        else:
            roundMode = -1

        startTime = time.clock()
        ret = lfmtblpy.RD5DupRealFilterExNumeric(tableID, fltID, scale, roundMode)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5DupRealFilterExNumeric] retval=%d [TableID=%d,SrcFltID=%d,Scale=%d,RoundMode=%d] (%.3fms)" % (ret, tableID, fltID, scale, roundMode, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $Fill
# 【説明】
# 　指定のセルに対し、値を入力します。
# 【引数】
# 　・テーブル名
# 　・Fill対象項目名
# 　・Fill開始行数
# 　・Fill行数
# 　・入力文字列
# 　・集合ID（省略した場合はカレント集合ID）
def MFill(TblName, FltName, StartRow, RowCnt, FillStr, *SetID):
    retVal = RetVal()
    retVal.funcName = "MFill"

    # Macro
    if SetID == (): # 省略
        setID = -1
        msg = "%s(ur\"%s\", ur\"%s\", \"%s\", \"%s\", ur\"%s\")" % (retVal.funcName, TblName, FltName, StartRow, RowCnt, FillStr)
    else:
        setID = SetID[0]
        msg = "%s(ur\"%s\", ur\"%s\", \"%s\", \"%s\", ur\"%s\", %d)" % (retVal.funcName, TblName, FltName, StartRow, RowCnt, FillStr, setID)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        fltID = getFilterIDFromName(retVal, tableID, FltName)

        # 行指定
        startRow = int(StartRow)
        if RowCnt == ALL_FILTERS_MARK:
            # セット行数取得
            ret = getSetSize(retVal, tableID, setID)
            rowCnt = ret - startRow + 1 # 開始行以降全行
        else:
            rowCnt = int(RowCnt)

        # データ型別処理
        fltType = getFilterType(retVal, tableID, fltID)
        if   fltType == lfmtblpy.D5_DT_INTEGER:
            try:
                data = int(FillStr)
            except:
                data = D5_NULL_INT
            startTime = time.clock()
            ret = lfmtblpy.RD5FillRealExIntR1(tableID, setID, fltID, startRow, rowCnt, data)
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5FillRealExIntR1] retval=%d [TableID=%d,SetID=%d,FltID=%d,WriteStart=%d,WriteCount=%d,nData=%d] (%.3fms)" \
                % (ret, tableID, setID, fltID, startRow, rowCnt, data, elapsedTime)
        elif fltType == lfmtblpy.D5_DT_DOUBLE:
            try:
                data = float(FillStr)
            except:
                data = D5_NULL_DBL
            startTime = time.clock()
            ret = lfmtblpy.RD5FillRealExDblR1(tableID, setID, fltID, startRow, rowCnt, data)
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5FillRealExDblR1] retval=%d [TableID=%d,SetID=%d,FltID=%d,WriteStart=%d,WriteCount=%d,nData=%f] (%.3fms)" \
                % (ret, tableID, setID, fltID, startRow, rowCnt, data, elapsedTime)
        elif fltType == lfmtblpy.D5_DT_TIME:
            data = TimeStr2Dbl(FillStr)
            startTime = time.clock()
            ret = lfmtblpy.RD5FillRealExDblR1(tableID, setID, fltID, startRow, rowCnt, data)
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5FillRealExDblR1] retval=%d [TableID=%d,SetID=%d,FltID=%d,WriteStart=%d,WriteCount=%d,nData=%f] (%.3fms)" \
                % (ret, tableID, setID, fltID, startRow, rowCnt, data, elapsedTime)
        elif fltType == lfmtblpy.D5_DT_DATE:
            data = DateStr2Dbl(FillStr)
            startTime = time.clock()
            ret = lfmtblpy.RD5FillRealExDblR1(tableID, setID, fltID, startRow, rowCnt, data)
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5FillRealExDblR1] retval=%d [TableID=%d,SetID=%d,FltID=%d,WriteStart=%d,WriteCount=%d,nData=%f] (%.3fms)" \
                % (ret, tableID, setID, fltID, startRow, rowCnt, data, elapsedTime)
        elif fltType == lfmtblpy.D5_DT_DATETIME:
            data = DateTimeStr2Dbl(FillStr)
            startTime = time.clock()
            ret = lfmtblpy.RD5FillRealExDblR1(tableID, setID, fltID, startRow, rowCnt, data)
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5FillRealExDblR1] retval=%d [TableID=%d,SetID=%d,FltID=%d,WriteStart=%d,WriteCount=%d,nData=%f] (%.3fms)" \
                % (ret, tableID, setID, fltID, startRow, rowCnt, data, elapsedTime)
        elif fltType == lfmtblpy.D5_DT_STRING:
            data = FillStr
            startTime = time.clock()
            ret = lfmtblpy.RD5FillRealExStrR1(tableID, setID, fltID, startRow, rowCnt, data.encode(ENC_DB))
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5FillRealExStrR1] retval=%d [TableID=%d,SetID=%d,FltID=%d,WriteStart=%d,WriteCount=%d,nData=%s] (%.3fms)" \
                % (ret, tableID, setID, fltID, startRow, rowCnt, data, elapsedTime)
        elif fltType == lfmtblpy.D5_DT_DECIMAL:
            nInfo = lfmutilpy.CNumericInfo()
            ret = getNumericInfo(retVal, tableID, fltID, nInfo)
            try:
                float(FillStr) # 数値チェック
                data = lfmutilpy.CNumeric(str(FillStr), nInfo.getScale(), nInfo.getRoundingMode())
            except:
                data = lfmutilpy.CNumeric(NULL_NUM_STR, 0, nInfo.getRoundingMode())
            startTime = time.clock()
            ret = lfmtblpy.RD5FillRealExNumericR1(tableID, setID, fltID, startRow, rowCnt, data.getPtr())
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5FillRealExNumericR1] retval=%d [TableID=%d,SetID=%d,FltID=%d,WriteStart=%d,WriteCount=%d,nData=%s] (%.3fms)" \
                % (ret, tableID, setID, fltID, startRow, rowCnt, FillStr, elapsedTime)

        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $FillEx
# 【説明】
# 　指定のセルに対し、値を入力します。（可変値Fill）
# 【引数】
# 　・テーブル名
# 　・Fill対象項目名
# 　・Fill開始行数
# 　・Fill行数
# 　・入力文字列
# 　・集合ID（省略した場合はカレント集合ID）
# 　・末尾の空白削除 ON/OFF（Y/N)
def MFillEx(TblName, FltName, StartRow, RowCnt, FillList, SetID, ExSpace):
    retVal = RetVal()
    retVal.funcName = "MFillEx"

    # Macro
    if SetID == "": # 省略
        setID = -1
    else:
        setID = int(SetID)
    msg = "%s(ur\"%s\", ur\"%s\", \"%s\", \"%s\", %s, \"%s\", \"%s\")" % (retVal.funcName, TblName, FltName, StartRow, RowCnt, strList(FillList), SetID, ExSpace)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        fltID = getFilterIDFromName(retVal, tableID, FltName)

        # 行指定
        startRow = int(StartRow)
        if RowCnt == ALL_FILTERS_MARK:
            # セット行数取得
            ret = getSetSize(retVal, tableID, setID)
            rowCnt = ret - startRow + 1 # 開始行以降全行
        else:
            rowCnt = int(RowCnt)

        # データ型別処理
        sz = len(FillList)
        fltType = getFilterType(retVal, tableID, fltID)
        if   fltType == lfmtblpy.D5_DT_INTEGER:
            data = lfmutilpy.CTypeIntAr(sz)
            for i, v in enumerate(FillList):
                try:
                    d = int(v)
                except:
                    d = D5_NULL_INT
                data.put(i, d)
        elif fltType == lfmtblpy.D5_DT_DOUBLE:
            data = lfmutilpy.CTypeDblAr(sz)
            for i, v in enumerate(FillList):
                try:
                    d = float(v)
                except:
                    d = D5_NULL_DBL
                data.put(i, d)
        elif fltType == lfmtblpy.D5_DT_TIME:
            data = lfmutilpy.CTypeDblAr(sz)
            for i, v in enumerate(FillList):
                data.put(i, TimeStr2Dbl(v))
        elif fltType == lfmtblpy.D5_DT_DATE:
            data = lfmutilpy.CTypeDblAr(sz)
            for i, v in enumerate(FillList):
                data.put(i, DateStr2Dbl(v))
        elif fltType == lfmtblpy.D5_DT_DATETIME:
            data = lfmutilpy.CTypeDblAr(sz)
            for i, v in enumerate(FillList):
                data.put(i, DateTimeStr2Dbl(v))
        elif fltType == lfmtblpy.D5_DT_STRING:
            data = lfmutilpy.CTypeStrAr(sz)
            if ExSpace == RECONO_MARK_YES: # 末尾空白削除
                for i, v in enumerate(FillList):
                    data.put(i, v.rstrip().encode(ENC_DB))
            else:
                for i, v in enumerate(FillList):
                    data.put(i, v.encode(ENC_DB))
        elif fltType == lfmtblpy.D5_DT_DECIMAL:
            nInfo = lfmutilpy.CNumericInfo()
            ret = getNumericInfo(retVal, tableID, fltID, nInfo)
            data = lfmutilpy.CTypeNumAr(sz, nInfo.getScale(), nInfo.getRoundingMode())
            for i, v in enumerate(FillList):
                try:
                    float(v) # 数値チェック
                    d = str(v)
                except:
                    d = NULL_NUM_STR
                data.put(i, d)

        startTime = time.clock()
        ret = lfmtblpy.RD5OverwriteRealEx(tableID, setID, fltID, startRow, rowCnt, data.getVPtr())
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5OverwriteRealEx] retval=%d [TableID=%d,SetID=%d,FltID=%d,WriteStart=%d,WriteCount=%d,PWData=%s] (%.3fms)" \
            % (ret, tableID, setID, fltID, startRow, rowCnt, strList(data), elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $Calc
# 【説明】
# 　計算を行います。
# 【引数】
# 　・テーブル名
# 　・計算対象項目名
# 　・計算開始行
# 　・計算行数
# 　・計算式
# 　・集合ID（省略した場合はカレント集合ID）
def MCalc(TblName, FltName, StartRow, RowCnt, CalcStr, *SetID):
    retVal = RetVal()
    retVal.funcName = "MCalc"

    # Macro
    if SetID == (): # 省略
        setID = -1
        msg = "%s(ur\"%s\", ur\"%s\", \"%s\", \"%s\", ur\"%s\")" % (retVal.funcName, TblName, FltName, StartRow, RowCnt, CalcStr)
    else:
        setID = SetID[0]
        msg = "%s(ur\"%s\", ur\"%s\", \"%s\", \"%s\", ur\"%s\", %d)" % (retVal.funcName, TblName, FltName, StartRow, RowCnt, CalcStr, setID)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        fltID = getFilterIDFromName(retVal, tableID, FltName)

        # 行指定
        startRow = int(StartRow)
        if RowCnt == ALL_FILTERS_MARK:
            # セット行数取得
            ret = getSetSize(retVal, tableID, setID)
            rowCnt = ret - startRow + 1 # 開始行以降全行
        else:
            rowCnt = int(RowCnt)

        ErrorRep = "                                                                "
        startTime = time.clock()
        ret = lfmtblpy.RD5CalcReal(tableID, setID, fltID, startRow, rowCnt, CalcStr.encode(ENC_DB), ErrorRep)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5CalcReal] retval=%d [TargetTblID=%d,TargetSetID=%d,TargetFID=%d,CalStart=%d,CalCount=%d,PCFormula=%s,ErrorRep=%s] (%.3fms)" \
            % (ret, tableID, setID, fltID, startRow, rowCnt, CalcStr, ErrorRep, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $Categorize
# 【説明】
# 　カテゴリーテーブルを使用して、数値データのカテゴライズを行います。
# 【引数】
# 　・テーブル名
# 　・カテゴライズ対象項目名
# 　・カテゴリーテーブル名
def MCategorize(TblName, FltName, CatTblName):
    retVal = RetVal()
    retVal.funcName = "MCategorize"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\", ur\"%s\")" % (retVal.funcName, TblName, FltName, CatTblName)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        fltID = getFilterIDFromName(retVal, tableID, FltName)
        catTableID = getTableIDFromName(retVal, CatTblName)

        startTime = time.clock()
        ret = lfmtblpy.RD5AddCategoryReal(tableID, fltID, catTableID)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5AddCategoryReal] retval=%d [TargetTblID=%d,TargetFltID=%d,CategoryTblID=%d] (%.3fms)" % (ret, tableID, fltID, catTableID, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)


# $NumericRescale
# 【説明】
# 　Numeric型データのスケール・丸めモードを設定します。
# 【引数】
# 　・テーブル名
# 　・項目名
# 　・スケール値（0～38の数値を指定）
# 　・丸めモード（下記に示す0～6の数値または数値に対応した文字列を指定）
def MNumericRescale(TblName, FltName, Scale, Mode):
    retVal = RetVal()
    retVal.funcName = "MNumericRescale"

    # Macro
    if isinstance(Mode, types.IntType):
        msg = "%s(ur\"%s\", ur\"%s\", %d, %d)" % (retVal.funcName, TblName, FltName, Scale, Mode)
    else:
        msg = "%s(ur\"%s\", ur\"%s\", %d, \"%s\")" % (retVal.funcName, TblName, FltName, Scale, Mode)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        fltID = getFilterIDFromName(retVal, tableID, FltName)

        scale = int(Scale)
        if Mode in MAP_ROUND_MODE:
            roundMode = MAP_ROUND_MODE[Mode]
        else:
            roundMode = -1

        nInfo = lfmutilpy.CNumericInfo(scale, roundMode)
        startTime = time.clock()
        ret = lfmtblpy.RD5SetNumericInfo(tableID, fltID, nInfo.getPtr())
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5SetNumericInfo] retval=%d [TableID=%d,FilterID=%d,scale=%d,rounding_mode=%d] (%.3fms)" \
            % (ret, tableID, fltID, scale, roundMode, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

#$MultiTableDupl
#$MultiRename
#$MultiAddRealFilter
#$MultiDuplFilter
#$MultiDelFilter
#$MultiVisibleFilter
#$MultiRenameFilter
#$MultiTypeConv
#$MultiSetDelete


# === 集合(サブテーブル)操作 ===
# $SetNOT
# 【説明】
# 　集合（サブテーブル）のNOTを抽出します。
# 【引数】
# 　・テーブル名
# 　・NOT対象集合ID
def MSetNOT(TblName, NotSetID):
    retVal = RetVal()
    retVal.funcName = "MSetNOT"

    # Macro
    msg = "%s(ur\"%s\", %d)" % (retVal.funcName, TblName, NotSetID)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        startTime = time.clock()
        ret = lfmtblpy.RD5SetNotReal(tableID, NotSetID)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5SetNotReal] retval=%d [TableID=%d,SetID=%d] (%.3fms)" % (ret, tableID, NotSetID, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

## セット演算共通関数
def SetOp(TblName, SrcSetID, DestSetID, opeNo, retVal):
    ret = -1
    try:
        tableID = getTableIDFromName(retVal, TblName)

        startTime = time.clock()
        ret = lfmtblpy.RD5SetOpeReal(tableID, opeNo, SrcSetID, DestSetID)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5SetOpeReal] retval=%d [TableID=%d,OpeNo=%d,SetAID=%d,SetBID=%d] (%.3fms)" % (ret, tableID, opeNo, SrcSetID, DestSetID, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    return ret

# $SetAND
# 【説明】
# 　２つの集合（サブテーブル）のAND（集合積）を抽出します。
# 【引数】
# 　・テーブル名
# 　・AND対象の集合ID
# 　・ANDターゲットの集合ID
def MSetAND(TblName, SrcSetID, DestSetID):
    retVal = RetVal()
    retVal.funcName = "MSetAND"

    # Macro
    msg = "%s(ur\"%s\", %d, %d)" % (retVal.funcName, TblName, SrcSetID, DestSetID)
    retVal.appendLogM(msg)

    # API
    opeNo = 0 # AND
    ret = SetOp(TblName, SrcSetID, DestSetID, opeNo, retVal)

    # Macro return
    return retVal.makeRetVal(ret)

# $SetOR
# 【説明】
# 　２つの集合（サブテーブル）のOR（集合和）を抽出します。
# 【引数】
# 　・テーブル名
# 　・OR対象の集合ID
# 　・ORターゲットの集合ID
def MSetOR(TblName, SrcSetID, DestSetID):
    retVal = RetVal()
    retVal.funcName = "MSetOR"

    # Macro
    msg = "%s(ur\"%s\", %d, %d)" % (retVal.funcName, TblName, SrcSetID, DestSetID)
    retVal.appendLogM(msg)

    # API
    opeNo = 1 # OR
    ret = SetOp(TblName, SrcSetID, DestSetID, opeNo, retVal)

    # Macro return
    return retVal.makeRetVal(ret)

# $SetSUB
# 【説明】
# 　２つの集合（サブテーブル）のSUBを抽出します。
# 【引数】
# 　・テーブル名
# 　・SUB対象の集合ID
# 　・SUBターゲットの集合ID
def MSetSUB(TblName, SrcSetID, DestSetID):
    retVal = RetVal()
    retVal.funcName = "MSetSUB"

    # Macro
    msg = "%s(ur\"%s\", %d, %d)" % (retVal.funcName, TblName, SrcSetID, DestSetID)
    retVal.appendLogM(msg)

    # API
    opeNo = 2 # SUB
    ret = SetOp(TblName, SrcSetID, DestSetID, opeNo, retVal)

    # Macro return
    return retVal.makeRetVal(ret)

# $SetCurMove
# 【説明】
# 　カレント集合（サブテーブル）を変更します。
# 【引数】
# 　・テーブル名
# 　・移動集合ID
def MSetCurMove(TblName, NewSetID):
    retVal = RetVal()
    retVal.funcName = "MSetCurMove"

    # Macro
    msg = "%s(ur\"%s\", %d)" % (retVal.funcName, TblName, NewSetID)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        startTime = time.clock()
        ret = lfmtblpy.RD5ChangeCurrentSetID(tableID, NewSetID)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5ChangeCurrentSetID] retval=%d [TableID=%d,NewSetID=%d] (%.3fms)" % (ret, tableID, NewSetID, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $SetDelete
# 【説明】
# 　集合（サブテーブル）の削除を行います。
# 【引数】
# 　・テーブル名
# 　・削除する集合ID
def MSetDelete(TblName, DelSetID):
    retVal = RetVal()
    retVal.funcName = "MSetDelete"

    # Macro
    msg = "%s(ur\"%s\", %d)" % (retVal.funcName, TblName, DelSetID)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        ret = deleteSet(retVal, tableID, DelSetID)

    except MacroError, e:
        ret = e.retCode
        print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $DelAllSubTables
# 【説明】
#  　すべての集合（サブテーブル）を削除します。
# 【引数】
#  　・テーブル名
def MDelAllSubTables(TblName):
    retVal = RetVal()
    retVal.funcName = "MDelAllSubTables"

    # Macro
    msg = "%s(ur\"%s\")" % (retVal.funcName, TblName)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        startTime = time.clock()
        ret = lfmtblpy.RD5PurgeSubsets(tableID)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5PurgeSubsets] retval=%d [TableID=%d] (%.3fms)" % (ret, tableID, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $SetComment
# 【説明】
# 　集合（サブテーブル）のコメント編集を行います。
# 【引数】
# 　・テーブル名
# 　・集合ID
# 　・コメント
def MSetComment(TblName, SetID, Scom):
    retVal = RetVal()
    retVal.funcName = "MSetComment"

    # Macro
    msg = "%s(ur\"%s\", %d, ur\"%s\")" % (retVal.funcName, TblName, SetID, Scom)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        ret = setComment(retVal, tableID, SetID, Scom)

    except MacroError, e:
        ret = e.retCode
        print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)


# === 検索・ソート・集計 ===
# $Search
# 【説明】
# 　データの検索を行います。
# 【引数】
# 　・検索するテーブル名
# 　・検索ターゲット項目名
# 　・集合ID
# 　・検索条件式
def MSearch(TblName, TargetCol, SetID, OpeStr):
    retVal = RetVal()
    retVal.funcName = "MSearch"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\", %d, ur\"%s\")" % (retVal.funcName, TblName, TargetCol, SetID, OpeStr)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        # ワイルドカードサーチ
        bWC = False
        i = 0
        lenStr = len(OpeStr)
        while i < lenStr:
            idx = OpeStr.find(SEARCH_SYMBOL, i)
            if idx == -1: # not found
                break
            if (idx < 1) or (OpeStr[idx - 1] != SEARCH_ESCAPE): # エスケープされていない
                bWC = True
                break
            i = idx + 1

        if bWC: # ワイルドカードあり
            fltID = getFilterIDFromName(retVal, tableID, TargetCol)
            startTime = time.clock()
            ret = lfmtblpy.RD5SearchByFieldWildCard(tableID, fltID, SetID, OpeStr.encode(ENC_DB))
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5SearchByFieldWildCard] retval=%d [TableID=%d,FltID=%d,SetID=%d,pc=%s] (%.3fms)" \
                % (ret, tableID, fltID, SetID, OpeStr, elapsedTime)
        else: # ワイルドカードなし
            startTime = time.clock()
            ret = lfmtblpy.RD5SearchByText(tableID, SetID, OpeStr.encode(ENC_DB))
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5SearchByText] retval=%d [TableID=%d,SetID=%d,Text=%s] (%.3fms)" % (ret, tableID, SetID, OpeStr, elapsedTime)

        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

#$MultiSearch


# $Sort
# 【説明】
# 　データのソートを行います。
# 【引数】
# 　・テーブル名
# 　・ソート対象項目名
# 　・集合ID
# 　・ソート順
def MSort(TblName, ItemName, SetId, SortType):
    retVal = RetVal()
    retVal.funcName = "MSort"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\", %d, \"%s\")" % (retVal.funcName, TblName, ItemName, SetId, SortType)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        fltID = getFilterIDFromName(retVal, tableID, ItemName)
        if SetId == -1:
            targetSid = getCurrentSetID(retVal, tableID)
        else:
            targetSid = SetId

        ret = sortTable(retVal, tableID, fltID, SetId, SortType)

    except MacroError, e:
        ret = e.retCode
        print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $MultiSort
def MMultiSort(TblName, SetId, ItemNameList):
    retVal = RetVal()
    retVal.funcName = "MMultiSort"

    # Macro
    msg = "%s(ur\"%s\", %d, \"%s\")" % (retVal.funcName, TblName, SetId, strList(ItemNameList))
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        if SetId == -1:
            targetSid = getCurrentSetID(retVal, tableID)
        else:
            targetSid = SetId

        itemNameList = []
        itemNameList[:] = ItemNameList[:] # コピー
        itemNameList.reverse() # 逆順
        listSid = []
        sid = SetId
        for (fltName, sortType) in itemNameList:
            fltID = getFilterIDFromName(retVal, tableID, fltName)
            ret = sortTable(retVal, tableID, fltID, sid, sortType)
            sid = ret
            listSid.append(sid)
        lastSetId = listSid.pop()

        # 中間セット削除
        for sid in listSid:
            deleteSet(retVal, tableID, sid)

        # セットコメント設定
        sz = len(ItemNameList) - 1
        scom = "MultiSort Set:%d [" % targetSid
        for i, (fltName, sortType) in enumerate(ItemNameList):
            scom += (fltName + ":" + sortType[0])
            if i < sz:
                scom += ','
        scom += "]"
        setComment(retVal, tableID, lastSetId, scom)

        ret = lastSetId

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $XSum
# 【説明】
# 　データの集計を行います。
# 【引数】
# 　・集計対象テーブル名
# 　・集合ID
# 　・次元の項目名
# 　・測度の項目名
# 　・件数
# 　・最大値
# 　・最小値
# 　・合計値
# 　・平均値
def MXSum(TblName, SetID, DItemList, NItemList):
    retVal = RetVal()
    retVal.funcName = "MXSum"

    # Macro
    msg = "%s(ur\"%s\", %d, %s, %s)" % (retVal.funcName, TblName, SetID, strList(DItemList), strList(NItemList))
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        # 項目ID取得オブジェクト
        filterIdFromName = FilterIdFromName(retVal, tableID)

        # 次元
        nDim = len(DItemList)
        dimFltIDs = lfmutilpy.CTypeIntAr(nDim)
        for i, v in enumerate(DItemList):
            ret = filterIdFromName.getId(retVal, v)
            dimFltIDs.put(i, ret)

        # 測度
        nMeasure = len(NItemList)
        if nMeasure > 0:
            msrFltIDs = lfmutilpy.CTypeIntAr(nMeasure)
            summaryTypes = lfmutilpy.CTypeIntAr(nMeasure)
            for i, v in enumerate(NItemList):
                ret = filterIdFromName.getId(retVal, v[0])
                msrFltIDs.put(i, ret)

                type = lfmtblpy.D5_SUMMARY_NONE
                if v[1] == 1:
                    type |= lfmtblpy.D5_SUMMARY_COUNT
                if v[2] == 1:
                    type |= lfmtblpy.D5_SUMMARY_MAX
                if v[3] == 1:
                    type |= lfmtblpy.D5_SUMMARY_MIN
                if v[4] == 1:
                    type |= lfmtblpy.D5_SUMMARY_SUM
                if v[5] == 1:
                    type |= lfmtblpy.D5_SUMMARY_AVERAGE
                summaryTypes.put(i, type)
            argMsrFltIDs = msrFltIDs.getPtr()
            argSummaryTypes = summaryTypes.getPtr()
        else:
            msrFltIDs = None
            summaryTypes = None
            argMsrFltIDs = None
            argSummaryTypes = None

        floatFormats = lfmutilpy.CTypeIntAr(1) # 未使用パラメータなので領域だけ確保

        startTime = time.clock()
        ret = lfmtblpy.RD5NonCubeSum(tableID, SetID, nDim, dimFltIDs.getPtr(), nMeasure, argMsrFltIDs, argSummaryTypes, floatFormats.getPtr())
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5NonCubeSum] retval=%d [TableID=%d,SetID=%d,nDim=%d,DimFltIDs=%s,nMeasure=%d,MsrFltIDs=%s,SummaryTypes=%s] (%.3fms)" \
            % (ret, tableID, SetID, nDim, str(Array2List(dimFltIDs, nDim)) \
                , nMeasure, str(Array2List(msrFltIDs, nMeasure)), str(Array2List(summaryTypes, nMeasure)), elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)


#$MultiSort


# === 子ウィンドウ制御 ===
#$ChildWinOpen【未サポート】
#$ViewTable【未サポート】
#$NotViewTable【未サポート】


# === 設定 ===
# $FloatFormat
# 【説明】
# 　浮動小数点型項目の小数点以下桁数を設定します。
# 【引数】
# 　・テーブル名
# 　・項目名
# 　・設定桁数
def MFloatFormat(TblName, FltName, DisitStr):
    retVal = RetVal()
    retVal.funcName = "MFloatFormat"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\", %d)" % (retVal.funcName, TblName, FltName, DisitStr)
    retVal.appendLogM(msg)

    # API
    try:
        ret = setFilterAttr(retVal, TblName, FltName, UNDER_0_DIGITS_FIELD, DisitStr - 3) # 浮動小数項目の小数点以下グリッド表示桁数(-3)

    except MacroError, e:
        ret = e.retCode
        print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

# $Comma
# 【説明】
# 　整数、浮動小数点データの３桁ごとのカンマ区切りの表示・非表示を切り替えます。
# 【引数】
# 　・テーブル名
# 　・項目名
# 　・0（表示しない）または1（表示する）
def MComma(TblName, FltName, IsOnOff):
    retVal = RetVal()
    retVal.funcName = "MComma"

    # Macro
    msg = "%s(ur\"%s\", ur\"%s\", %d)" % (retVal.funcName, TblName, FltName, IsOnOff)
    retVal.appendLogM(msg)

    # API
    try:
        ret = setFilterAttr(retVal, TblName, FltName, COMMA_ONOFF_FIELD, IsOnOff)

    except MacroError, e:
        ret = e.retCode
        print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

#$VisualizeSpace


# $DelEndSpace
# 【説明】
# 　文字列データの末尾の空白を削除するかどうか設定します。
# 【引数】
# 　・0（削除しない）または1（削除する）
def MDelEndSpace(IsOnOff):
    retVal = RetVal()
    retVal.funcName = "MDelEndSpace"

    # Macro
    msg = "%s(%d)" % (retVal.funcName, IsOnOff)
    retVal.appendLogM(msg)

    # API
    try:
        startTime = time.clock()
        ret = lfmtblpy.RD5SetTailSpaceFlag(IsOnOff)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5SetTailSpaceFlag] retval=%d [NewFlag=%d] (%.3fms)" % (ret, IsOnOff, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

#$MultiFloatFormat
#$MultiComma


# === ﾈｯﾄﾜｰｸ ===
#$Login【未サポート】
#$LogOut【未サポート】
#$Upload【未サポート】
#$Download【未サポート】


# === その他 ===
#ﾌﾞﾛｯｸｺﾒﾝﾄ【未サポート→代替あり】
#$CopyToClipbord
#$CopyToExcel【未サポート】
#$MacroFunc【未サポート】


# $DBCodeSet
# 【説明】
# 　DB文字コードを設定します。
# 【引数】
# 　DB文字コード
def MDBCodeSet(DBCode):
    retVal = RetVal()
    retVal.funcName = "MDBCodeSet"

    # Macro
    msg = "%s(\"%s\")" % (retVal.funcName, DBCode)
    retVal.appendLogM(msg)

    # API
    try:
        startTime = time.clock()
        ret = lfmtblpy.RD5SetDBCharCode(DBCode)
        elapsedTime = (time.clock() - startTime) * 1000
        msg = "[RD5SetDBCharCode] retval=%d [DBCode=%s] (%.3fms)" % (ret, DBCode, elapsedTime)
        if ret < 0:
            retVal.appendLogA(msg, MLog.LV_ERR)
            raise MacroError(ret, msg)
        retVal.appendLogA(msg, MLog.LV_DBG)

        global ENC_DB
        ENC_DB = DBCode

    except MacroError, e:
        ret = e.retCode
        #print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

## セット行数取得
def MGetSetSize(TblName, SetID):
    retVal = RetVal()
    retVal.funcName = "MGetSetSize"

    # Macro
    msg = "%s(ur\"%s\", %d)" % (retVal.funcName, TblName, SetID)
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)

        ret = getSetSize(retVal, tableID, SetID)

    except MacroError, e:
        ret = e.retCode
        print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

##
# 単一データを取得します。
# @param[in]    TblName テーブル名
# @param[in]    FltName 項目名
# @param[in]    SetID   集合ID
# @param[in]    RowNo   セット内順序番号
# @param[out]   RetData 返却データ格納リスト（省略可）※最初の要素[0]に格納される
# @retval   0   成功
# @retval   負  エラーコード
def MGetData1(TblName, FltName, SetID, RowNo, *RetData):
    retVal = RetVal()
    retVal.funcName = "MGetData1"

    # Macro
    if RetData == (): # 省略
        retData = None
        msg = "%s(ur\"%s\", ur\"%s\", %d, %d)" % (retVal.funcName, TblName, FltName, SetID, RowNo)
    else:
        retData = RetData[0]
        msg = "%s(ur\"%s\", ur\"%s\", %d, %d, %s)" % (retVal.funcName, TblName, FltName, SetID, RowNo, strList(retData))
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        fltID = getFilterIDFromName(retVal, tableID, FltName)

        # データ型別処理
        fltType = getFilterType(retVal, tableID, fltID)
        if   fltType == lfmtblpy.D5_DT_INTEGER:
            startTime = time.clock()
            ret = lfmtblpy.RD5GetData1IntR1(tableID, fltID, SetID, RowNo)
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5GetData1IntR1] retval=%d [TableID=%d,FltID=%d,SetID=%d,RowNo=%d] (%.3fms)" % (ret, tableID, fltID, SetID, RowNo, elapsedTime)
        elif fltType in LIST_DOUBLE_TYPE:
            startTime = time.clock()
            ret = lfmtblpy.RD5GetData1DblR1(tableID, fltID, SetID, RowNo)
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5GetData1DblR1] retval=%f [TableID=%d,FltID=%d,SetID=%d,RowNo=%d] (%.3fms)" % (ret, tableID, fltID, SetID, RowNo, elapsedTime)
            if   fltType == lfmtblpy.D5_DT_TIME:
                ret = TimeDbl2Str(ret)
            elif fltType == lfmtblpy.D5_DT_DATE:
                ret = DateDbl2Str(ret)
            elif fltType == lfmtblpy.D5_DT_DATETIME:
                ret = DateTimeDbl2Str(ret)
        elif fltType == lfmtblpy.D5_DT_STRING:
            startTime = time.clock()
            ret = lfmtblpy.RD5GetData1StrR1(tableID, fltID, SetID, RowNo).decode(ENC_DB)
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5GetData1StrR1] retval=%s [TableID=%d,FltID=%d,SetID=%d,RowNo=%d] (%.3fms)" % (ret, tableID, fltID, SetID, RowNo, elapsedTime)
        elif fltType == lfmtblpy.D5_DT_DECIMAL:
            nInfo = lfmutilpy.CNumericInfo()
            ret = getNumericInfo(retVal, tableID, fltID, nInfo)
            nData = lfmutilpy.CNumeric()
            startTime = time.clock()
            ret = lfmtblpy.RD5GetData1NumericR1(tableID, fltID, SetID, RowNo, nData.getPtr())
            elapsedTime = (time.clock() - startTime) * 1000
            sdata = lfmtblpy.RD5NumericNum2StrR1(nData.getPtr(), nInfo.getPtr(), 0, nInfo.getScale())
            msg = "[RD5GetData1NumericR1] retval=%d [TableID=%d,FltID=%d,SetID=%d,RowNo=%d,numVal=[%s]] (%.3fms)" \
                % (ret, tableID, fltID, SetID, RowNo, sdata, elapsedTime)
            ret = sdata

        retVal.appendLogA(msg, MLog.LV_DBG)
        retVal.retData = ret
        if retData != None:
            del retData[:]
            retData.append(ret)
        ret = 0

    except MacroError, e:
        ret = e.retCode
        print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

##
# 複数データを取得します。
# @param[in]    TblName テーブル名
# @param[in]    FltName 項目名
# @param[in]    SetID   集合ID
# @param[in]    RowNo   セット内順序番号
# @param[out]   RetData 返却データ格納リスト（省略可）
# @retval   0以上   取得できたデータ数
# @retval   負  エラーコード
def MGetData1M(TblName, FltName, SetID, RowNo, *RetData):
    retVal = RetVal()
    retVal.funcName = "MGetData1M"

    # Macro
    if RetData == (): # 省略
        retData = None
        msg = "%s(ur\"%s\", ur\"%s\", %d, %d)" % (retVal.funcName, TblName, FltName, SetID, RowNo)
    else:
        retData = RetData[0]
        msg = "%s(ur\"%s\", ur\"%s\", %d, %d, %s)" % (retVal.funcName, TblName, FltName, SetID, RowNo, strList(retData))
    retVal.appendLogM(msg)

    # API
    try:
        tableID = getTableIDFromName(retVal, TblName)
        fltID = getFilterIDFromName(retVal, tableID, FltName)
        nGot = lfmutilpy.CTypeIntAr(1)
        MAX_CACHE = lfmtblpy.D5_MAX_CACHE
        if retData != None:
            retVal.retData = retData
        else:
            retVal.retData = []
        del retVal.retData[:]

        # データ型別処理
        fltType = getFilterType(retVal, tableID, fltID)
        if   fltType == lfmtblpy.D5_DT_INTEGER:
            buf = lfmutilpy.CTypeIntAr(MAX_CACHE * 2)
            startTime = time.clock()
            ret = lfmtblpy.RD5GetData1MIntR1(tableID, fltID, SetID, RowNo, nGot.getPtr(), buf.getPtr())
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5GetData1MIntR1] retval=%d [TableID=%d,FltID=%d,SetID=%s,RowNo=%d][nGot=%d] (%.3fms)" \
                % (ret, tableID, fltID, SetID, RowNo, nGot.at(0), elapsedTime)
            retVal.retData.extend(Array2List(buf, nGot.at(0)))
        elif fltType in LIST_DOUBLE_TYPE:
            buf = lfmutilpy.CTypeDblAr(MAX_CACHE)
            startTime = time.clock()
            ret = lfmtblpy.RD5GetData1MDblR1(tableID, fltID, SetID, RowNo, nGot.getPtr(), buf.getPtr())
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5GetData1MDblR1] retval=%d [TableID=%d,FltID=%d,SetID=%s,RowNo=%d][nGot=%d] (%.3fms)" \
                % (ret, tableID, fltID, SetID, RowNo, nGot.at(0), elapsedTime)
            if   fltType == lfmtblpy.D5_DT_DOUBLE:
                retVal.retData.extend(Array2List(buf, nGot.at(0)))
            elif fltType == lfmtblpy.D5_DT_TIME:
                for i in range(nGot.at(0)):
                    retVal.retData.append(TimeDbl2Str(buf.at(i)))
            elif fltType == lfmtblpy.D5_DT_DATE:
                for i in range(nGot.at(0)):
                    retVal.retData.append(DateDbl2Str(buf.at(i)))
            elif fltType == lfmtblpy.D5_DT_DATETIME:
                for i in range(nGot.at(0)):
                    retVal.retData.append(DateTimeDbl2Str(buf.at(i)))
        elif fltType == lfmtblpy.D5_DT_STRING:
            offset = lfmutilpy.CTypeIntAr(MAX_CACHE)
            buf    = lfmutilpy.CTypeCharAr(lfmtblpy.D5_MAX_STRING_SIZE)
            startTime = time.clock()
            ret = lfmtblpy.RD5GetData1MStrR1(tableID, fltID, SetID, RowNo, nGot.getPtr(), offset.getPtr(), buf.getVPtr())
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5GetData1MStrR1] retval=%d [TableID=%d,FltID=%d,SetID=%s,RowNo=%d][nGot=%d] (%.3fms)" \
                % (ret, tableID, fltID, SetID, RowNo, nGot.at(0), elapsedTime)
            for i in range(nGot.at(0)):
                retVal.retData.append(buf.getPtr(offset.at(i)).decode(ENC_DB))
        elif fltType == lfmtblpy.D5_DT_DECIMAL:
            nInfo = lfmutilpy.CNumericInfo()
            ret = getNumericInfo(retVal, tableID, fltID, nInfo)
            buf = lfmutilpy.CTypeNumAr(MAX_CACHE, nInfo.getScale(), nInfo.getRoundingMode())
            startTime = time.clock()
            ret = lfmtblpy.RD5GetData1MNumericR1(tableID, fltID, SetID, RowNo, nGot.getPtr(), buf.getPtr())
            elapsedTime = (time.clock() - startTime) * 1000
            msg = "[RD5GetData1MNumericR1] retval=%d [TableID=%d,FltID=%d,SetID=%s,RowNo=%d][nGot=%d] (%.3fms)" \
                % (ret, tableID, fltID, SetID, RowNo, nGot.at(0), elapsedTime)
            for i in range(nGot.at(0)):
                retVal.retData.append(buf.at(i))

        retVal.appendLogA(msg, MLog.LV_DBG)
        ret = nGot.at(0)

    except MacroError, e:
        ret = e.retCode
        print >>sys.stderr, e
    except:
        print >>sys.stderr, "Unexpected error:", sys.exc_info()
        raise

    # Macro return
    return retVal.makeRetVal(ret)

## メイン
if __name__ == "__main__":
    print "Start\n"

    # 設定ファイル
    g_MConfig = MConfig(CONFIG_FILE)
    g_MConfig.load()
    print g_MConfig #debug

    # グローバル変数
    ENC_OS = g_MConfig.ENC_OS
    ENC_DB = g_MConfig.ENC_DB

    # 引数
    argvs = sys.argv
    argc = len(argvs)
    if argc > 1:
        ENC_OS = argvs[1]
    if argc > 2:
        ENC_DB = argvs[2]
    print "ENC_OS[%s],ENC_DB[%s]" % (ENC_OS, ENC_DB)
    
    print "\nEnd"
