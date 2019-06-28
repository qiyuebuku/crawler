# -*- coding:utf-8 -*-  
import os
import sys
import requests
import datetime
from Crypto.Cipher import AES
# from binascii import b2a_hex, a2b_hex
# from multiprocessing import Queue 
import re
# from multiprocessing import Process
import time
from threading import Thread
# from queue import Queue

import spiderTools
import hashlib  #md5
import json 
# import urllib  #unquote
from lxml import etree
from PIL import Image
# from multiprocessing import Queue
# from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor



# 用于将Print的内容顺便备份到文件中
# class Logger(object):
#     def __init__(self, filename="Default.log"):
#         self.terminal = sys.stdout
#         self.log = open(filename, "a")
 
#     def write(self, message):
#         self.terminal.write(message)
#         self.log.write(message)
 
#     def flush(self):
#         pass
# path = os.path.abspath(os.path.dirname(__file__))
# type = sys.getfilesystemencoding()
# sys.stdout = Logger('download_log.txt')





class Tts_movie(object):
    def __init__(self,username,password):
        # 构建一个Session对象，可以保存页面Cookie
        self.session = requests.Session()
        # self.headers = {
        #     'User-Agent',spiderTools.getAgent(),
        #     'Origin','http://tts.tmooc.cn',
        #     'Referer', 'http://tts.tmooc.cn'
        #     # 'Referer', 'http://tts.tmooc.cn/video/showVideo?menuId=646408&version=AIDTN201809'
        # }
        # 请求报头
        self.headers = {
            'User-Agent':spiderTools.getAgent(),
            'Origin':'http://www.tmooc.cn',
            'Referer':'http://www.tmooc.cn/'
        }
        obj = hashlib.md5()
        obj.update(password.encode('utf-8'))
        # 登陆tmooc
        password = obj.hexdigest()
        username = username 
        self.__tmooc_login(username,password)



    def __get_captcha(self):
        captcha = self.session.get('http://uc.tmooc.cn/validateCode?t=0.5050950644156729').content
        with open("captcha.jpg", "wb") as f:
            f.write(captcha)
        img=Image.open('captcha.jpg')
        img.show()

    def __tmooc_login(self,username,password):
        # 获取是否需要登陆验证码
        response = self.session.post(
            'http://uc.tmooc.cn/login/loginTimes',
            data = {
                'loginName':username,
                'accountType': 1,
            }
        )
        obj = json.loads(response.text)['obj']
        imgCode = ""
        # 如果需要输入验证码
        if obj != 0:
            self.__get_captcha()
            text = input('请输入验证码：')
            imgCode = text
        #需要访问的url
        url = 'http://uc.tmooc.cn/login'
        #认证信息
        userInfo={
            'loginName': username,
            'password': password,
            'imgCode':imgCode,
            'accountType': 1,
        }
        # 发送登录需要的POST数据，获取登录后的Cookie(保存在session里)
        response = self.session.post(url, data = userInfo, headers = self.headers)
        data = json.loads(response.text)
        if data['msg']!=None:
            print('登陆失败，请重新登陆')
            self.__tmooc_login(username,password)
        else:
            print('登陆成功')

    def __tts_login(self):
        """
        Origin: http://www.tmooc.cn
        X-Requested-With: XMLHttpRequest
        User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36
        Referer: http://www.tmooc.cn/

        """
        url = 'http://uc.tmooc.cn/user/checkTtsUser'
        data = json.loads(self.session.post(url,headers=self.headers).text)
        if data['msg']=="操作成功":
            return data['obj'] 
            """
            // 是TTS用户，进入TTS
            window.open(TTS_MYTTS_URL + "/user/myTTS?sessionId=" + encodeURI(data.obj) + "&date=" + (encodeURI(new Date())));
            """
            print('tts登陆成功')
            return True
        return False 
    def get_sess(self):
        obj = self.__tts_login()
        if obj:
            return self.session










class Downloader(object):
    def __init__(self,data,sess=None,thread_count=5,base_dir = None,log_path=None):
        super().__init__()
        self.thread_count = thread_count
        self.data = data 
        if not base_dir:
            base_dir = os.getcwd() + "download"
        self.base_dir = base_dir
        self.headers = {
            'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36',
            'Origin':'http://tts.tmooc.cn',
            'Referer': 'http://tts.tmooc.cn/video/showVideo?menuId=646373&version=AIDTN201809'
        }
        self.download_path = None 
        self.sess = sess 
        self.log_path = log_path
        self.error_count = 0
        # self.err_log = open('./error.log','w')



    def new_date_dir(self,dir_path):
        """
            新建日期文件夹
        """
        download_path = dir_path
        download_path = os.path.join(download_path, datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
        print("download_path",download_path)
        os.mkdir(download_path)

    def get_html(self,url):
        """
            获取url请求中的内容 
        """
        text = self.sess.get(url,headers=self.headers).text
        return text

    def parse_cryptor(self,file_lines):
        """
            从key_url中获取密钥并返回
        """
        headers = {
            'Origin': 'http://tts.tmooc.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36',
            'Referer': 'http://tts.tmooc.cn/video/showVideo?menuId=646417&version=AIDTN201809',
        }
        key_url = None
        try:
            for line in file_lines:
                # 找解密Key
                if "#EXT-X-KEY" in line: 
                    method_pos = line.find("METHOD")
                    comma_pos = line.find(",")
                    method = line[method_pos:comma_pos].split('=')[1]
                    print ("Decode Method：", method)
                    uri_pos = line.find("URI")
                    quotation_mark_pos = line.rfind('"')
                    key_path = line[uri_pos:quotation_mark_pos].split('"')[1]
                    # key解密密钥URL
                    key_url = key_path 
                    break
            if key_url:
                res = self.sess.get(key_url,headers=headers)
                key = res.content
                print("key",len(key))
                print(key)
                if len(key): # AES 解密
                    cryptor = AES.new(key, AES.MODE_CBC, key) 
                    return cryptor
            return None 
        except Exception as e:
            print('错误：',e)
            # self.err_log.write(str(e))
            
            return None

    def parse_ts_url(self,file_lines):
        try:
            for index, line in enumerate(file_lines):
                # 找ts地址并下载
                if "EXTINF" in line: 
                    # 拼出ts片段的URL
                    pd_url = file_lines[index + 1] 
                    yield pd_url 
                    
        except Exception as e:
            # self.err_log.write(str(e))
            
            return None


    def get_ts(self,ts_url,name,ts_list):
        # count = 0
        # while not ts_url_queue.empty():
            # ts_url = ts_url_queue.get()
            # print("线程",name+ts_url)
        try:
            res = self.sess.get(ts_url,headers = self.headers)
            serial_number = ts_url.split('-')[-1].split('.')[0]
            ts_list.append({'serial_number':int(serial_number),'res':res})
        except Exception as e:
            print('下载：{},出错：{}'.format(ts_url,e))
            self.error_count+=1
            
            # if count>=3:
            #     break
            #     count+=1 
            #     # self.err_log.write(str(e))
               
            #     continue
       

    def load_locally_video(self,ts_list,title,dir_path,cryptor):
        """
            将视频写入到本地 
        """
        try:
            ts_infos = sorted(ts_list,key=lambda x:x['serial_number'])
            print(ts_infos)
            with open(os.path.join(dir_path, title + ".mp4"), 'ab') as f:
                for ts_info in ts_infos:
                    res = ts_info['res']
                    try:
                        f.write(cryptor.decrypt(res.content))
                    except Exception as e:
                        # 如果下载下来的视频有问题，请注释掉本行
                        f.write(res.content)
                        # self.err_log.write(str(e))
                        
                        print('warning：',e)
                        continue
            return True
        except Exception as e:
            # self.err_log.write(str(e))
            print('未知错误：',e)
            return False
    @staticmethod
    def getFileSize(filePath, size=0):
        print(filePath)
        for root, dirs, files in os.walk(filePath):
            for f in files:
                size += os.path.getsize(os.path.join(root, f))
                print(f)
        return size


    def is_exist(self,m3u8_url,flog):
        """
            判断当前这个视频是否已经存在
        """
        for line in flog:
            data = json.loads(line)
            # print("b",data['m3u8_url'])
            if m3u8_url == data['m3u8_url']:
                # print('m3u8_url已经存在于日志当中')
                # time.sleep(5)
                return True
        print("开始下载：",m3u8_url)        
        # print('no')
        # time.sleep(10)
        return False

    def start(self):
        """
            启动
        """
        if not os.path.exists(self.base_dir):
            os.mkdir(self.base_dir)
        self.download = self.base_dir
        info = self.data 
        url = info['video_info']['m3u8_url']
        if not os.path.isfile(self.log_path):
            with open(self.log_path,'w') as f:
                pass 
        flog = open(self.log_path,'r+')
         # 视频名称
        title = info['video_info']['title']
        # 视频保存地址
        dir_path = os.path.join(info['dir_path'],"视频")
        # 判断ppt文件夹是否存在
        if not os.path.exists(dir_path):  
            os.mkdir(dir_path)

        # 如果这个视频已经存在，则不下载
        # if self.is_exist(url,flog):
        #     print('跳过视频：{}，因为已经下载过了'.format(os.path.join(dir_path,title) ) )
        # else:
        # 二次验证视频是否已经存在
        # 获取文件必须存在并且文件的大小大于0则表示不用下载此视频 
        movie_path = os.path.join(dir_path, title + ".mp4")
        if os.path.isfile(movie_path) and os.path.getsize(movie_path):
            print('视频{}已经存在，如果想重新下载，请删除此视频，然后再试'.format(movie_path))
            data = {'title':title,'m3u8_url':url}
            flog.write(json.dumps(data))
            flog.write("\n")
        else:
            # 下载视频
            # 获取M3U8文件内容
            all_content = self.get_html(url) 
            # with open('test2.m3u8','w') as f:
            #     f.write(all_content)
            file_lines = all_content.split("\n")
            # 获取密钥
            cryptor = self.parse_cryptor(file_lines)
            # print(cryptor)
            # print(url)
            # print(all_content)
            # print(file_lines)
            # if cryptor:
            # 创建ts_url队列 
            # ts_url_queue = Queue()
            # 创建线程池下载所有的ts视频
            t = ThreadPoolExecutor(self.thread_count)  # 4
            print("正在下载：{}...".format(os.path.join(dir_path,title)))
            ts_list = []
            for i,ts_url in enumerate(self.parse_ts_url(file_lines)):
                # ts_url_queue.put(ts_url)
                # thread_download = []
                # 创建存放ts结果的队列 
                if self.error_count>=5:
                    print('在下载{}时出现错误，下载地址为：{}'.format(title,movie_path))
                    break 

                name = "{}号下载线程".format(i)
                t.submit(self.get_ts,ts_url,name,ts_list)
                # for i in range(self.thread_count):
                #     name = "{}号下载线程".format(i)
                #     t.submit(self.get_ts,ts_url,name,ts_list)
                    # thread_download.append(t)
                
                # for i in thread_download:
                #     t.join()
            t.shutdown()    #相当于进程的close + join   等待子线程执行完再执行主线程
            # print(ts_list)
            # 将下载的视频保存到本地 
            if self.load_locally_video(ts_list,title,dir_path,cryptor):
                print('下载视频完成')
                data = {'title':title,'m3u8_url':url}
                flog.write(json.dumps(data))
                flog.write("\n")
                print(movie_path)
        # else:
        #     print('没有获取到密钥!!!')
        #     print('sources_dir:',url)
        #     print('m3u8_url',movie_path)
        flog.close()
        

   
if __name__ == '__main__':
    # info_list = [{'serial_number': '0', 'res': '<Response [200]>'}, {'serial_number': '1', 'res': '<Response [200]>'}, {'serial_number': '11', 'res': '<Response [200]>'}, {'serial_number': '14', 'res': '<Response [200]>'}, {'serial_number': '18', 'res': <Response [200]>}, {'serial_number': '19', 'res': <Response [200]>}, {'serial_number': '21', 'res': <Response [200]>}, {'serial_number': '25', 'res': <Response [200]>}, {'serial_number': '26', 'res': <Response [200]>}, {'serial_number': '27', 'res': <Response [200]>}, {'serial_number': '28', 'res': <Response [200]>}, {'serial_number': '3', 'res': <Response [200]>}, {'serial_number': '30', 'res': <Response [200]>}, {'serial_number': '31', 'res': <Response [200]>}, {'serial_number': '32', 'res': <Response [200]>}, {'serial_number': '33', 'res': <Response [200]>}, {'serial_number': '34', 'res': <Response [200]>}, {'serial_number': '35', 'res': <Response [200]>}, {'serial_number': '38', 'res': <Response [200]>}, {'serial_number': '39', 'res': <Response [200]>}, {'serial_number': '4', 'res': <Response [200]>}, {'serial_number': '40', 'res': <Response [200]>}, {'serial_number': '45', 'res': <Response [200]>}, {'serial_number': '46', 'res': <Response [200]>}, {'serial_number': '51', 'res': <Response [200]>}, {'serial_number': '52', 'res': <Response [200]>}, {'serial_number': '53', 'res': <Response [200]>}, {'serial_number': '54', 'res': <Response [200]>}, {'serial_number': '55', 'res': <Response [200]>}, {'serial_number': '59', 'res': <Response [200]>}, {'serial_number': '6', 'res': <Response [200]>}, {'serial_number': '60', 'res': <Response [200]>}, {'serial_number': '61', 'res': <Response [200]>}, {'serial_number': '62', 'res': <Response [200]>}, {'serial_number': '63', 'res': <Response [200]>}]
    # info_list = []
    # for i in range(10):
    #     info_list.append({'serial_number':i,'res':'sdfsdfs324'})
    # ts_info = sorted(info_list,key=lambda x:x['serial_number'],reverse=True)
    # print(ts_info)
    mru8_url = "http://videotts.it211.com.cn/D_VIP_TSD_N_TESTTHEORY03_DAY03_04/D_VIP_TSD_N_TESTTHEORY03_DAY03_04.m3u8" 
    # mru8_url = "http://videotts.it211.com.cn/aid18111210am/aid18111210am.m3u8" 
    # mru8_url = "http://videotts.it211.com.cn/aid18111206pm/aid18111206pm.m3u8" 
    # mru8_url = "http://videotts.it211.com.cn/aid18111224am/aid18111224am.m3u8" 
    # mru8_url = "http://videotts.it211.com.cn/aid18111229am/aid18111229am.m3u8" 
    video_info = {'title':'test_sesss23432','m3u8_url':mru8_url}
    dir_path = r"C:\Users\11946\Desktop\爬虫\download\test"
    log_path = r"C:\Users\11946\Desktop\爬虫\download\test\test1\log.json"
    tts = Tts_movie('1194681498@qq.com','ruan19980418')
    sess = tts.get_sess()
    data = {'video_info':video_info,'dir_path':dir_path}
    download = Downloader(data,sess,thread_count=64,base_dir=dir_path,log_path=log_path)
    download.start()
#     import json 
#     queue = Queue()
#     base_dir = r'C:\Users\11946\Desktop\爬虫\download\\'
#     download = Downloader(queue,32,base_dir)
#     download.start()
#     # exit()
#     with open('./tarena_tts.json','r') as f: 
#         pass 
#         for data in f.readlines():
#             info = json.loads(data)
#             # print('***********************************************')
#             # print('本章题目：',info['section'])
#             # print('***********************************************')
#             chapter_directory = base_dir+info['section']
#             if not os.path.exists(chapter_directory):
#                 os.mkdir(chapter_directory)
#             for course_info in info['course_info']:
#                 # print("本节标题：",course_info['title'])
#                 # print("本节ppt：",course_info['ppt_url'])
#                 dir_name = re.sub('[\/:、：*?"<>|]','-',course_info['title'])#去掉非法字符  
#                 dir_path = chapter_directory+ "\\" + dir_name
#                 if not os.path.exists(dir_path):
#                     os.mkdir(dir_path)
#                 # 在当前目录下创建信息文件
#                 # 程序在下次访问这个目录时
#                 # 首先会查看这个文件中的信息
#                 # 然后根据其中的信息进行下载
#                 f_log = open(dir_path+"\\log.json",'a')
#                 for video_info in course_info['video_info']:
#                     # print("名称：",video_info['title'])
#                     # print("下载地址：",video_info['m3u8_url'])
#                     queue.put({'video_info':video_info,'dir_path':dir_path})
#                 # print('================================')
#                 # queue.put(video_info)
    