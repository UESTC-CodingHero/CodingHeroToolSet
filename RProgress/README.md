ProgressManager 项目说明
----
ProgressManager 集中管理，用于更新 [MicroSoft HPC] 集群任务的[进度更新]。

工作流程：

+ 每添加一个任务时，客户端通过Socket将当前Job的信息发送到ProgressManager端，Job信息包含以下几个方面：
    + Job ID
    + 要跟踪的文件(编码任务时通常为log文件)，如果有多个文件，则以英文逗号分隔
    + 正确合法的有效行的正则表达式
    + 任务结束时，总共的有效行数(和上一个信息共同用于统计进度百分比)
    + 正确合法判断log文件读到结尾的正则表达式(该信息当前无效，暂未使用)。

+ ProgressManager 新建一个线程处理当前Job ID的进度条请求
    + 如果当前任务尚未开始运行，例如资源占满后，任务在排队，则等待被唤醒
    + 如果当前任务正在运行，则一直打开各个追踪的文件，分别统计每个文件的有效行数，更新进度条状态。

+ Job运行结束后，退出线程。

除此之外，ProgressManager目前支持对Job信息进行缓存。当ProgressManager目前支持对Job信息进行缓存被意外关闭后，重新打开进行，会从默认的缓存文件提取任务信息，正确地恢复出之前的状态，进而正确跟踪更新进度条。

[MicroSoft HPC]: https://docs.microsoft.com/en-us/powershell/high-performance-computing/overview?view=hpc16-ps]

[进度更新]: https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-hpc-server-2008R2/ee783544(v=ws.10)?redirectedfrom=MSDN]
