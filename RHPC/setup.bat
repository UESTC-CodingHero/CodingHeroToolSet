@echo off
python setup.py install

rmdir build /Q /S
rmdir dist /Q /S
rmdir hpc.egg-info /Q /S
