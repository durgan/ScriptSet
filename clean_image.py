#!/usr/bin/python
# -*- coding: UTF-8 -*-
print "\n"
print "╔══════════════════════════════ ♡ ═ ♫ ♫ ♫ ═ ♡ ═══════════════════════════════╗"
print "║                                                                            ║"
print "║                Docker images clear tool. Author: durgan                    ║"
print "║                                                                            ║"
print "╚══════════════════════════════ ♡ ═ ♫ ♫ ♫ ═ ♡ ═══════════════════════════════╝"

import sys, os, json, httplib, urllib, base64, socket,subprocess,re, commands
CREATED_DAYS = 5;
print "\nBegin to list all the docker images..."



#查询所有符合规则的镜像
def queryAllImg():
    (status, image_list) = commands.getstatusoutput("docker ps --format '{{.ID}} {{.Image}} {{.RunningFor}}' -a")
    if status != 0:
        print "Error: error code='%s' " % status
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
            CREATED = column[2]
            CREATEED_UNIT = column[3]


            dict = {'CONNECTID': CONNECTID, 'IMAGE': IMAGE, 'CREATED': CREATED,'CREATEED_UNIT':CREATEED_UNIT}
            if needAnalysis(IMAGE,dict):
                obsolete_images.append(dict)
    return obsolete_images

#通过image名字判断是否需要进行分析删除
def needAnalysis(IMAGE,dic):
    #dev - peer1.org1.durgan.com - testhan110 - 1.0 - 1489a641b51e6387b00b9c6fd47d30fbc835b61d7bb4d950d20313a596de35c8
    searchObj = re.search(r'dev-peer(.*).org(.*).durgan.com-(.*)-(.*)-.*', IMAGE, re.M | re.I)
    if searchObj:
        print "匹配成功："+IMAGE
        print searchObj.group(1)
        print searchObj.group(2)
        print searchObj.group(3)
        print searchObj.group(4)
        dic['peerversion']=searchObj.group(1)
        dic['orgversion'] = searchObj.group(2)
        dic['chaincode'] = searchObj.group(3)
        dic['chaincodeversion'] = searchObj.group(4)
        return True
    else:
        print "匹配失败："+IMAGE
        return False

#删除每一个镜像
def delEveryImg(img):
    rmicmd = ['docker','rm','-f',img]
    prog = subprocess.Popen(rmicmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdoutput, erroutput) = prog.communicate()  # Returns (stdoutdata, stderrdata): stdout and stderr are ignored, here
    if prog.returncode:
        #Error response from daemon: conflict: unable to remove repository reference "dev-peer1.org1.durgan.com-hanee-1.0-6355ced9ff696fcd7a9c91cc46349bf45ec437710df48052bb0a9537e4da94ae" (must force) - container 972c07ead456 is using its referenced image f5759dffed9d
        errorInfo = str(stdoutput)
        CONNECTIONID = txt_wrap_by("container "," is",errorInfo)
        print CONNECTIONID
        if cmp(CONNECTIONID,"-1")==0:
            print "出现异常错误无法删除："+errorInfo
        else:
            if stopRuningImg(CONNECTIONID):
                delImg(img)
            else:
                print "关闭镜像失败，无法继续删除"
    else:
        print "删除未运行镜像成功："+img

def delImg(img):
    rmicmd = ['docker','rm','-f',img]
    prog = subprocess.Popen(rmicmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdoutput, erroutput) = prog.communicate()  # Returns (stdoutdata, stderrdata): stdout and stderr are ignored, here
    errorInfo = str(stdoutput)
    if prog.returncode:
        print "停止后删除镜像失败 img:"+img+",errorInfo:"+errorInfo
    else:
        print "删除已运行镜像成功:"+img

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
    for img in obsolete_images:
        CONNECTID = img['CONNECTID']
        CREATED = img["CREATED"]
        CREATEED_UNIT = img["CREATEED_UNIT"]
        print  "CREATED" + CREATED
        print  "CREATEED_UNIT" + CREATEED_UNIT
        if cmp(CREATEED_UNIT,'weeks')==0:
            toDelImages.append(CONNECTID)
            continue
        if cmp(CREATEED_UNIT,'days')==0 and int(CREATED)>=CREATED_DAYS:
            toDelImages.append(CONNECTID)
            continue
    return toDelImages

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

if __name__=="__main__":
    print("start")
    # img = raw_input('input img to del:')
    # delEveryImg(img)
    obsolete_images = queryAllImg()
    toDelImages1 = delRule1(obsolete_images)
    toDelImages2 = delRule2(obsolete_images)
    totalToDelImages = toDelImages1+toDelImages2
    totalResultImgs = list(set(totalToDelImages))
    #去重 todo
    for i in range(0, len(totalResultImgs)):
        print i, totalResultImgs[i]
        delEveryImg(totalResultImgs[i])

    print "Complete to delete obsoleted images."
