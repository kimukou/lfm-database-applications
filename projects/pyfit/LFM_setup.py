from distutils.core import setup
import glob
import py2exe

setup( name="PyFIT",
       windows = [{'script' : 'LFM_GUI.py'}],
       
       data_files=[("",["LFM_GUI.ini", "LFM_GUI.xrc", "LFM_Macro.ini", "README.txt"]),
                   ("icons",glob.glob("icons/*.*")),
                   ("icons/actions",glob.glob("icons/actions/*.*")),
                   ("icons/actions/disable",glob.glob("icons/actions/disable/*.*")),
                   ("icons/actions/enable",glob.glob("icons/actions/enable/*.*")),
                   ("icons/datatype",glob.glob("icons/datatype/*.*")),
                   ("icons/lifit",glob.glob("icons/lifit/*.*")),
                   ("log",glob.glob("log/*.*")),
                   ("out",glob.glob("out/*.*")),
                   ("sampleData",glob.glob("sampleData/*.*"))]
     )
