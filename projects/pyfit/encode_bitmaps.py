import sys
from wx.tools import img2py

command_lines = [
    "   -F -i -n Numeric icons/datatype/childwindow_grid_Numeric.gif datatype.py",
    "-a -F -n Float icons/datatype/childwindow_grid_Float.gif datatype.py",
    "-a -F -n Integer icons/datatype/childwindow_grid_Integer.gif datatype.py",
    "-a -F -n Date icons/datatype/childwindow_grid_Date.gif datatype.py",
    "-a -F -n String icons/datatype/childwindow_grid_String.gif datatype.py",
    "-a -F -n Time icons/datatype/childwindow_grid_Time.gif datatype.py",
    "-a -F -n TimeOfDate icons/datatype/childwindow_grid_TimeOfDate.gif datatype.py"
    ]

if __name__ == "__main__":
    for line in command_lines:
        args = line.split()
        img2py.main(args)
