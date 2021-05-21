@echo off
python setup.py install

rmdir build /Q /S
rmdir dist /Q /S
rmdir hpc_progress.egg-info /Q /S