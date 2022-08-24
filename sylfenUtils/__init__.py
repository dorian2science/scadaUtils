import os,sys
dir_app=os.getcwd()
import os,sys,inspect
cur_frame=sys._getframe()
this_file=__file__
print(this_file)
previous_frame=cur_frame.f_back
print(previous_frame)
# dir_source = os.path.dirname(os.path.abspath())
# dir_local =
# print(dir_source)

# LOG_DIR = os.path.dirname(__appdir)

# os.mkdir('test')
