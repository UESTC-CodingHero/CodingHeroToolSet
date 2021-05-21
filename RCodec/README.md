Codec 项目说明
----
Codec 用于添加编解码任务, 可以向[MicroSoft HPC]集群或本地提交

同时Codec 也包含了Codec 对应的日志收集任务。

工作流程：

+ 调用SupportedCodec.init() 通过配置文件注册全局变量和支持的编码器
+ 选择合适的编码器
+ 调用该编码器的go()即可, 如果要自定义一些任务, 可参考go()在外部实现

[MicroSoft HPC]: https://docs.microsoft.com/en-us/powershell/high-performance-computing/overview?view=hpc16-ps]
