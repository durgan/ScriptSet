#!/usr/bin/python
# -*- coding: UTF-8 -*-
print "\n"
print "╔══════════════════════════════ ♡ ═ ♫ ♫ ♫ ═ ♡ ═══════════════════════════════╗"
print "║                                                                            ║"
print "║                Docker images clear tool. Author: durgan                    ║"
print "║                                                                            ║"
print "╚══════════════════════════════ ♡ ═ ♫ ♫ ♫ ═ ♡ ═══════════════════════════════╝"

from threading import Timer
import sys, os, json, httplib, urllib, base64, socket,subprocess,re,time,logging,argparse, commands
CREATED_UNIT = 'DAY'; # DAY HOUR MINUTE
CREATED_NUM = 1;
logFilename = '/opt/pylogging.log'
execTime = 5*60 #定时器周期执行间隔时间，单位秒
rule2close = False

#查询所有符合规则的镜像
def queryAllImg():
    print "\nBegin to list all the docker images..."
    (status, image_list) = commands.getstatusoutput("docker ps --format '{{.ID}} {{.Image}} {{.CreatedAt }}' -a")
    if status != 0:
        print "Error: error code='%s' " % status
        logging.info("Error: error code='%s' " % status)
        raise Exception("获取镜像列表出错!")
    else:
        obsolete_images = []
        latestImageDic = {}
        list = image_list.split('\n')
        for row in list:
            column = row.split()
            CONNECTID = column[0]
            #第一行排除
            if cmp(CONNECTID, 'CONTAINER')==0:
                continue
            IMAGE = column[1]
            CREATED_DAY = column[2]
            CREATED_TIME = column[3]

            dict = {'CONNECTID': CONNECTID, 'IMAGE': IMAGE, 'CREATED_DAY': CREATED_DAY,'CREATED_TIME':CREATED_TIME}
            if needAnalysis(IMAGE,dict):
                obsolete_images.append(dict)
    return obsolete_images

#通过image名字判断是否需要进行分析删除
def needAnalysis(IMAGE,dic):
    if 'common' in IMAGE:
        print "匹配失败（common）："+IMAGE
        logging.info("匹配失败（common）："+IMAGE)
        return False;
    searchObj = re.search(r'dev-peer(.*).org(.*).durgan.com-(.*)-(.*)-.*', IMAGE, re.M | re.I)
    if searchObj:
        print "匹配成功："+IMAGE +"   CONNECTID:"+dic['CONNECTID']
        logging.info("匹配成功："+IMAGE+"   CONNECTID:"+dic['CONNECTID'])
        print searchObj.group(1)
        logging.info(searchObj.group(1))
        print searchObj.group(2)
        logging.info(searchObj.group(2))
        print searchObj.group(3)
        logging.info(searchObj.group(3))
        print searchObj.group(4)
        logging.info(searchObj.group(4))
        dic['peerversion']=searchObj.group(1)
        dic['orgversion'] = searchObj.group(2)
        dic['chaincode'] = searchObj.group(3)
        dic['chaincodeversion'] = searchObj.group(4)
        return True
    else:
        print "匹配失败："+IMAGE
        logging.info("匹配失败："+IMAGE)
        return False

#删除每一个镜像
def delEveryImg(img):
    rmicmd = ['docker','rm','-f',img]
    prog = subprocess.Popen(rmicmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdoutput, erroutput) = prog.communicate()  # Returns (stdoutdata, stderrdata): stdout and stderr are ignored, here
    if prog.returncode:
        errorInfo = str(stdoutput)
        CONNECTIONID = txt_wrap_by("container "," is",errorInfo)
        print CONNECTIONID
        if cmp(CONNECTIONID,"-1")==0:
            logging.error("出现异常错误无法删除："+errorInfo)
            print "出现异常错误无法删除："+errorInfo
        else:
            if stopRuningImg(CONNECTIONID):
                delImg(img)
            else:
                print "关闭镜像失败，无法继续删除"
                logging.error("关闭镜像失败，无法继续删除" + CONNECTIONID)
    else:
        print "删除未运行镜像成功："+img
        logging.info("删除未运行镜像成功："+img)

def delImg(img):
    rmicmd = ['docker','rm','-f',img]
    prog = subprocess.Popen(rmicmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdoutput, erroutput) = prog.communicate()  # Returns (stdoutdata, stderrdata): stdout and stderr are ignored, here
    errorInfo = str(stdoutput)
    if prog.returncode:
        print "停止后删除镜像失败 img:"+img+",errorInfo:"+errorInfo
        logging.error("停止后删除镜像失败 img:"+img+",errorInfo:"+errorInfo)
    else:
        print "删除已运行镜像成功:"+img
        logging.info("删除已运行镜像成功:"+img)

#关闭正在运行的镜像
def stopRuningImg(CONNECTIONID):
    stopcmd = ['docker', 'stop', CONNECTIONID]
    prog = subprocess.Popen(stopcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdoutput, erroutput) = prog.communicate()
    print stdoutput
    print erroutput
    if prog.returncode:
        print "关闭失败"
        return False
    else:
        print "关闭成功"
        return True

#删除规则1：同一chaincode，删除旧版本
def delRule1(obsolete_images):
    toDelImages = []
    # 找出所有chaincode最新的版本
    lasterVersoinDic = {}
    for img in obsolete_images:
        chaincode = img['chaincode']
        chaincodeversionstr = img['chaincodeversion']
        chaincodeversion = float(chaincodeversionstr)
        if lasterVersoinDic.has_key(chaincode):
            old_chaincode_version = lasterVersoinDic.get(chaincode)
            if old_chaincode_version<chaincodeversion:
                lasterVersoinDic[chaincode] = chaincodeversion
        else:
            lasterVersoinDic[chaincode] = chaincodeversion

    #根据最大版本号筛选低于最大版本号的image
    for key,value in lasterVersoinDic.items():
        for img in obsolete_images:
            chaincode = img['chaincode']
            if cmp(chaincode,key)!=0:
                continue
            chaincodeversionstr = img['chaincodeversion']
            chaincodeversion = float(chaincodeversionstr)
            if chaincodeversion<value:
                CONNECTID = img['CONNECTID']
                toDelImages.append(CONNECTID)
                break

    return toDelImages

#删除规则2：创建时间已经超过固定天数的image.默认 5 day
def delRule2(obsolete_images):
    toDelImages = []
    if rule2close:
        return toDelImages
    now = int(time.time())
    for img in obsolete_images:
        CONNECTID = img['CONNECTID']
        CREATED_TIME = img["CREATED_TIME"]
        CREATED_DAY = img["CREATED_DAY"]
        #print  "CREATED_DAY" + CREATED_DAY
        #print  "CREATED_TIME" + CREATED_TIME

        analysiTime = CREATED_DAY+" "+CREATED_TIME
        analysisTimeStruct = time.strptime(analysiTime, "%Y-%m-%d %H:%M:%S")
        analysisTimeStamp = int(time.mktime(analysisTimeStruct))
        spaceTime = 0
        doDel = False
        if cmp(CREATED_UNIT,'DAY')==0:
            spaceTime = 60*60*24*CREATED_NUM
            doDel = True
        elif cmp(CREATED_UNIT,'HOUR')==0:
            spaceTime = 60 * 60 * CREATED_NUM
            doDel = True
        elif cmp(CREATED_UNIT,'MINUTE')==0:
            spaceTime = 60 * CREATED_NUM
            doDel = True
        if doDel and (spaceTime + analysisTimeStamp) < now:
            CONNECTID = img['CONNECTID']
            toDelImages.append(CONNECTID)
    return toDelImages

#日志配置相关
def configure_log():
    # Define a Handler and set a format which output to file
    logging.basicConfig(
        level=logging.DEBUG,  # 定义输出到文件的log级别，大于此级别的都被输出
        format='%(asctime)s  %(filename)s : %(levelname)s  %(message)s',  # 定义输出log的格式
        datefmt='%Y-%m-%d %A %H:%M:%S',  # 时间
        filename=logFilename,  # log文件名
        filemode='a')  # 写入模式“w”或“a”
    # Define a Handler and set a format which output to console
    # console = logging.StreamHandler()  # 定义console handler
    # console.setLevel(logging.DEBUG)  # 定义该handler级别
    # formatter = logging.Formatter('%(asctime)s  %(filename)s : %(levelname)s  %(message)s')  # 定义该handler格式
    # console.setFormatter(formatter)
    # logging.getLogger().addHandler(console)  # 实例化添加handler
    # Print information              # 输出日志级别
    logging.debug('logger debug message')
    logging.info('logger info message')
    logging.warning('logger warning message')
    logging.error('logger error message')
    logging.critical('logger critical message')

#截取两个字符串中间的字符串
def txt_wrap_by(start_str, end, html):
    start = html.find(start_str)
    if start >= 0:
        start += len(start_str)
        end = html.find(end, start)
        if end >= 0:
            return html[start:end].strip()
        else:
            return "-1"
    else:
        return "-1"

#处理配置
def init_config():
    global execTime
    global rule2close
    global CREATED_UNIT
    global CREATED_NUM
    global logFilename
    configure_log()
    logging.info(execTime)
    logging.info(rule2close)
    logging.info("CREATED_UNIT:"+CREATED_UNIT)
    logging.info(CREATED_NUM)
    logging.info(logFilename)

#主业务体
def doClean():
    logging.info("开始执行")
    obsolete_images = queryAllImg()
    toDelImages1 = delRule1(obsolete_images)
    toDelImages2 = delRule2(obsolete_images)
    totalToDelImages = toDelImages1 + toDelImages2
    totalResultImgs = list(set(totalToDelImages))
    for i in range(0, len(totalResultImgs)):
        print i, totalResultImgs[i]
        delEveryImg(totalResultImgs[i])
    logging.info("执行结束")
    print "Complete to delete obsoleted images."
    Timer(execTime, doClean).start()

#处理命令行入参
def  init_arg():
    global execTime
    global rule2close
    global CREATED_UNIT
    global CREATED_NUM
    global logFilename
    parser = argparse.ArgumentParser(description='manual to this script')
    parser.add_argument('-exectime', type=int, default=600, help='指定定时器执行周期，单位：秒，默认600')
    parser.add_argument('-rule2close', type=str, default='False', help='是否关闭规则2（超过天数的容器关闭），True关闭，False不关闭。默认False')
    parser.add_argument('-createdunit', type=str, default='DAY',
                        help='规则2（超过天数的容器关闭）中针对时间的单位，通常与creatednum配合使用。DAY:天，HOUR：小时 MINUTE：分钟。默认DAY')
    parser.add_argument('-creatednum', type=int, default=1, help='规则2（超过天数的容器关闭）中针对时间的时长，通常与createdunit配合使用。默认1')
    parser.add_argument('-logfilename', type=str, default='/opt/pylogging.log', help='日志文件存放路径。默认/opt/pylogging.log')
    args = parser.parse_args()
    execTime =  args.exectime
    if cmp(args.rule2close,"True")==0:
        rule2close = True
    CREATED_UNIT = args.createdunit
    CREATED_NUM = args.creatednum
    logFilename = args.logfilename


if __name__=="__main__":
    init_arg()
    init_config()
    doClean()

