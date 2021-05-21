@echo off
python setup.py install

rmdir build /Q /S
rmdir dist /Q /S
rmdir codec.egg-info /Q /S
