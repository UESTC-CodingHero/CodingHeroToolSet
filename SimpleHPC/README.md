HPC 项目说明 (已弃用, 请参考[RCodec](../RCodec), [RHPC](../RHPC), [RProgress](../RProgress))
----
SimpleHPC 主要是用于封装对 [MicroSoft HPC] 集群简单添加任务功能。

本项目主要是用于添加视频编解码任务，但也可以执行其他通用任务。额外地，该项目支持某些辅助模块，例如：获取特定的 hash 码，一个简单的 [HPC 进度更新]功能

Those python scripts are for adding HPC jobs and updating jobs' progress automatically.

Basically, the 'hpc' directory is the original scripts, and the others are generated by running 'setup.bat' or 'python setup.py install'.

For more information, see the source code directly.

Those scripts are packaged as a library, so the caller(Runner Scripts, such as HPM_AI.py, HPM_RA.py and so on) can import this library directly.



[MicroSoft HPC]: https://docs.microsoft.com/en-us/powershell/high-performance-computing/overview?view=hpc16-ps]
[HPC 进度更新]: https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-hpc-server-2008R2/ee783544(v=ws.10)?redirectedfrom=MSDN]
