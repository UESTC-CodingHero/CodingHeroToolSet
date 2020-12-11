@echo off

REM 此脚本用于运行hpc job, 具体的用法及说明，请看README

set mode=RA
set workdir=\\%CCP_SCHEDULER%\%cd::=%\%mode%

set cfg=..\..\config.txt
set encoder=uavs3e.exe
set decoder=decoder.exe

REM example for common encoders
REM UAVS3E: 0(I)|41.0| 34.2136 42.7877 43.0454| 0.9041 0.9595 0.9622|  252248|  43272|L0         |L1         |[]
REM set valid_line_reg=$\s*(\d+)\s*\(\s*[I^|P^|B]\)\^|\s*(\d+\.\d+)\^|\s*(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\^|.+$

REM HPM: 0      ( I) 57   34.4594   38.2793   38.2322   24720     25930     0.9709138   [L0 ] [L1 ]
REM set valid_line_reg=$\s*(\d+)\s+\(\s*[I^|P^|B]\)\s+(\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+)\s+(\d+)\s+(0\.\d+).+$

REM Encoded frame count               = 60
REM set end_line_reg=$Encoded\s*frame\s*count\s+=\s*(\d+)$

set valid_line_reg=$\s*(\d+)\s*\(\s*[I^|P^|B]\)\^|\s*(\d+\.\d+)\^|\s*(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\^|.+$
set end_line_reg=$Encoded\s*frame\s*count\s+=\s*(\d+)$
set file={stderr}
set total={frames}

set who=cxl
set email=842363192@qq.com
FOR /F %%i IN ('python hpc_hashcode.py %encoder%') DO @set hashcode=%%i

REM 设置各种目录，且创建好这些目录(如果不存在)
set stdout_dir=%workdir%\stdout
set stderr_dir=%workdir%\stderr
set rec_dir=%workdir%\rec
set bin_dir=%workdir%\bitstream
set dec_dir=%workdir%\dec
mkdir %stdout_dir%
mkdir %stderr_dir%
mkdir %rec_dir%
mkdir %bin_dir%
mkdir %dec_dir%
set temp_dir=E:\tempYUV
set seqs_dir=D:\YUV\AVS3_Test_Sequences

REM 离线编解码命令
set encoder_cmd=%encoder% --config %cfg% -i %seqs_dir%\{seq}.yuv -w {width} -h {height} --fps_num {fps} -d {bit_depth} -f {frames} -q {qp} -p {intra_period} -o %temp_dir%\{bin} -r %temp_dir%\{rec} -s 1 1^>{stdout} 2^>{stderr}
set decoder_cmd=%decoder% -i %temp_dir%\{bin} -o %temp_dir%\{dec}

set copy_rec_cmd=copy /y %temp_dir%\{rec} %rec_dir%
set copy_bin_cmd=copy /y %temp_dir%\{bin} %bin_dir%
set copy_dec_cmd=copy /y %temp_dir%\{dec} %dec_dir%
set del_rec=del %temp_dir%\{rec}
set del_bin=del %temp_dir%\{bin}
set del_dec=del %temp_dir%\{dec}

REM 相邻的参数之间用空格隔开，同一个参数内不能含空格，否则会导致脚本解析失败
REM internal key words:
REM 1. --hpc    : special arguments for hpc cluster
REM 2. --cmd    : special command string for executable file(including itself)
REM 3. arg      : positional arguments for the above two

REM 传递给HPC job的命令
REM 只编码命令
set cmd="%encoder_cmd% ^& %copy_rec_cmd% ^& %del_rec% ^& %copy_bin_cmd% ^& %del_bin%"
REM 编码且解码命令
REM set cmd="%encoder_cmd% ^& %copy_rec_cmd% ^& %del_rec% ^& %decoder_cmd% ^& %copy_bin_cmd% ^& %del_bin% ^& %copy_dec_cmd% ^& %del_dec%"

REM 一般来说，E2680设置2个核, X5680设置3个核，以防止服务器负载大、温度高
set cores=2
REM Node01,Node02,Node03,Node04,Node05,Node06,Node07,Node08,Node09,Node10
REM R720Node01,R720Node02,R720Node03,R720Node04
set nodes=*
REM X5680,E2680
set groups=E2680
set mem=#int({width}*{height}*6*32/1000000+0.5)#
set priority=2200

set hpc="--name=%who%_%hashcode%_%mode%_{seq}_{qp} --cores=%cores% --nodes=%nodes% --groups=%groups% --memory=%mem% --priority=%priority% --workdir=%workdir% --stdout={stdout} --stderr={stderr} --file=%file% --total=%total% --valid_line_reg=%valid_line_reg% --end_line_reg=%end_line_reg%"
set run=python hpc_job.py --hpc=%hpc% --cmd=%cmd%
set extra=bin=%who%_%hashcode%_{seq}_{qp}.bin rec=%who%_%hashcode%_rec_{seq}_{qp}.yuv dec=%who%_%hashcode%_dec_{seq}_{qp}.yuv stdout=%stdout_dir%/{seq}_{qp}.log stderr=%stderr_dir%/{seq}_{qp}.log

REM 4k
%run% seq=Tango2_3840x2160_60fps_10bit_420                     width=3840    height=2160    fps=60  bit_depth=10  frames=120 qp=(27,32,38,45) intra_period=64 skip=0 %extra%
%run% seq=ParkRunning3_3840x2160_50fps_10bit_420               width=3840    height=2160    fps=50  bit_depth=10  frames=100 qp=(27,32,38,45) intra_period=48 skip=0 %extra%
%run% seq=Campfire_3840x2160_30fps_10bit_420_bt709_videoRange  width=3840    height=2160    fps=30  bit_depth=10  frames=60  qp=(27,32,38,45) intra_period=32 skip=0 %extra%
%run% seq=DaylightRoad2_3840x2160_60                           width=3840    height=2160    fps=60  bit_depth=10  frames=120 qp=(27,32,38,45) intra_period=64 skip=0 %extra%

%run% seq=Cactus_1920x1080_50                                  width=1920    height=1080    fps=50  bit_depth=8   frames=100 qp=(27,32,38,45) intra_period=48 skip=0 %extra%
%run% seq=BasketballDrive_1920x1080_50                         width=1920    height=1080    fps=50  bit_depth=8   frames=100 qp=(27,32,38,45) intra_period=48 skip=0 %extra%
%run% seq=MarketPlace_1920x1080_60fps_10bit_420                width=1920    height=1080    fps=60  bit_depth=10  frames=120 qp=(27,32,38,45) intra_period=64 skip=0 %extra%
%run% seq=RitualDance_1920x1080_60fps_10bit_420                width=1920    height=1080    fps=60  bit_depth=10  frames=120 qp=(27,32,38,45) intra_period=64 skip=0 %extra%

%run% seq=City_1280x720_60             					       width=1280    height=720     fps=60  bit_depth=8   frames=120 qp=(27,32,38,45) intra_period=64 skip=0 %extra%
%run% seq=Crew_1280x720_60             					       width=1280    height=720     fps=60  bit_depth=8   frames=120 qp=(27,32,38,45) intra_period=64 skip=0 %extra%
%run% seq=vidyo1_1280x720_60           					       width=1280    height=720     fps=60  bit_depth=8   frames=120 qp=(27,32,38,45) intra_period=64 skip=0 %extra%
%run% seq=vidyo3_1280x720_60           					       width=1280    height=720     fps=60  bit_depth=8   frames=120 qp=(27,32,38,45) intra_period=64 skip=0 %extra%

