#coding=utf-8
import spiderTools
import hashlib
import requests
import time
import json 
import urllib 
from lxml import etree
from PIL import Image
import re 
import M3u8ToMp4 as m4
from multiprocessing import Queue
import os 
from multiprocessing import Pool
from urllib import parse
import threading 

class Tts_movie(object):
    def __init__(self,username,password,base_dir,process_count = 4,thread_count = 16,):
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
        self.process_count = process_count
        self.thread_count = thread_count
        self.base_dir = base_dir
        self.__tmooc_login(username,password)



    def __get_captcha(self):
        captcha = self.session.get('http://uc.tmooc.cn/validateCode?t=0.5050950644156729').content
        with open("./captcha.jpg", "wb") as f:
            f.write(captcha)
        img=Image.open('./captcha.jpg')
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

    def __get_page(self,url):
        return self.session.get(url,headers=self.headers).text

    def __parse_page(self,obj):
        url = "http://tts.tmooc.cn/user/myTTS?sessionId={}&date={}".format(urllib.parse.quote(obj),urllib.parse.quote(str(time.localtime())))
        html = self.__get_page(url)
        with open('test.html','w',encoding="utf-8") as f:
            f.write(html)
        Cookie = self.session.cookies['versionAndNamesListCookie']
        versionAndNames = parse.unquote(Cookie)
        content = etree.HTML(html)
        course =  parse.unquote(versionAndNames[15:])
        print("解析课程{}......".format(course))
        f = open('tarena_tts.json','w')
        infos = {'course_title':course,'course_infos':[]}
        # 匹配出所有阶段的课程列表
        for node in content.xpath('//div[@class="course-list"]'):
            # 根据每个阶段，获取他的上一个元素，也就是每个阶段的名称
            section = node.xpath('./preceding-sibling::h2[1]/span/text()')[0]
            # 用于存储每个阶段的课程信息
            info = {'section':section,'course_info':[]}
            # 遍历当前阶段所有的课程列表
            for each in node.xpath('.//li[@class="opened"]'):
                # 用于存储每节课的信息
                course_info = {'title':None,'ppt_url':None,'video_info':None,'al_url':None,'zy_url':None}
                # 获取每节课的标题
                title = each.xpath('./p/text()')
                if title:
                    course_info['title']=title[0].replace('\n','').replace('\t','').replace('\r','').replace(' ','')

                # 案例地址
                al_url = each.xpath('./ul/li[@class="al"]/a/@href')
                if al_url:
                    course_info['al_url']=al_url[0]

                # ppt下载地址
                ppt_url = each.xpath('./ul/li[@class="ppt"]/a/@href')
                if ppt_url:
                    course_info['ppt_url']=ppt_url[0]
                    
                # 作业地址
                zy_url = each.xpath('./ul/li[@class="zy"]/a/@href')
                if zy_url:
                    course_info['zy_url']=zy_url[0]

                # 视频播放地址
                sp_url = each.xpath('./ul/li[@class="sp"]/a/@href')
                if sp_url:
                    video_info = self.parse_detail_page(sp_url[0])
                    course_info['video_info']=video_info
                info['course_info'].append(course_info)

            # print(info)
            # 使用生成器返回本章节的内容
            infos['course_infos'].append(info)
            # f.write(json.dumps(info,ensure_ascii=False))
            # f.write("\n")
            # # 将当前阶段的视频信息加入下载队列
            for course_info in info['course_info']:
                for r in course_info['video_info']:
                    print(r)
                    # self.test_download(r['m3u8_url'])
                    # try:
                    #     m4.download(r['m3u8_url'])
                    # except :
                    #     pass 
                    # url = r['m3u8_url']
                    # print(url)
                    # m4.download(url)
        print('解析完成………')
        f.close()
        return infos 
    
    def parse_detail_page(self,url):
        m3u8_url = "http://videotts.it211.com.cn/{0}/{0}.m3u8"
        headers = {
            'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36',
            'Referer':'http://tts.tmooc.cn/studentCenter/toMyttsPage',
        }
        cookie = {
            "isCenterCookie":"yes",
            "eBoxOpenAIDTN201809":"true",
        }
        html = self.session.get(url,headers=headers,cookies=cookie).text
        content = etree.HTML(html)
        video_info = []
        for each in content.xpath('//div[@class="video-list"]//a'):
            title = each.xpath('./@title')[0]
            onclick = each.xpath('./@onclick')
            # 如果有视频信息
            if onclick:
                m3u8_name = re.findall(r"changeVideo\('(.*)\.m3u8'",onclick[0])[0]
                video_info.append({'title':title,'m3u8_url':m3u8_url.format(m3u8_name)})
        return video_info


    def save_ppt(self,dir_path,ppt_url,dir_name):
        """
            保存ppt到本地
        """
        if not ppt_url:
            print('本节课程{}没有ppt资源'.format(dir_name))
            return 
        # 要保存的ppt名称
        ppt_title =dir_name
        # 拼接ppt保存地址
        path = os.path.join(dir_path,"ppt")
        # 判断ppt文件夹是否存在
        if not os.path.exists(path):  
            try:
                os.mkdir(path)
            except:
                pass 
        # 判断ppt的html文件是否存在，没有则创建它
        if not os.path.isfile(os.path.join(path,ppt_title+".html")):
            # 获取ppt网页
            html = self.session.get(ppt_url,headers = self.headers).text
            content = etree.HTML(html) 
            with open(os.path.join(path,ppt_title+".html"),"w",encoding="utf-8") as f:
                f.write(html)
            # 保存ppt中的图片到本地
            for img in content.xpath('//div/img/@src'):
                s = ppt_url.split('/')[0:-1]
                s.append(img)
                src = "/".join(s)
                # print(src)
                # 如果图片没有被保存过则创建他
                if not os.path.isfile(os.path.join(path,img)):
                    # print('下载图片：',src)
                    with open(os.path.join(path,img),"wb") as f:
                        res = self.session.get(src).content
                        f.write(res)
        else:
            print('{}的ppt已经存在，如果想重新下载，请在目录中删除它'.format(dir_name))

    def save_al(self,dir_path,al_url,dir_name,catalogue="案例"):
        """
            保存案例到本地
        """
        if not al_url:
            print('本节课程{}没有案例资源'.format(dir_name))
            return 
        # 要保存的ppt名称
        al_title =dir_name
        # 拼接ppt保存地址
        path = os.path.join(dir_path,catalogue)
        # 判断ppt文件夹是否存在
        if not os.path.exists(path):  
            os.mkdir(path)
        # 判断ppt的html文件是否存在，没有则创建它
        if not os.path.isfile(os.path.join(path,al_title+".html")):
            # 获取ppt网页
            html = self.session.get(al_url,headers = self.headers).text
            content = etree.HTML(html) 
            with open(os.path.join(path,al_title+".html"),"w",encoding="utf-8") as f:
                pattern = "index.files/"
                replace_str = ""
                s = "index.files/"
                html = re.sub(pattern,replace_str,html)
                f.write(html)
            # 保存ppt中的图片到本地
            for img in content.xpath('//img/@src'):
                s = al_url.split('/')[0:-1]
                s.append(img)
                src = "/".join(s)
                img = img.split("/")[-1]
                # 如果图片没有被保存过则创建他
                if not os.path.isfile(os.path.join(path,img)):
                    # print('下载图片：',src)
                    with open(os.path.join(path,img),"wb") as f:
                        res = self.session.get(src).content
                        f.write(res)
        else:
            print('{}的案例已经存在，如果想重新下载，请在目录中删除它'.format(dir_name)) 

    def save_zy(self,dir_path,zy_url,dir_name):
        """
            保存作业到本地 
        """
        if not zy_url:
            print('本节课程{}没有作业资源'.format(dir_name))
            return 
        # 要保存的ppt名称
        zy_title =dir_name
        # 拼接ppt保存地址
        path = os.path.join(dir_path,"作业")
        # 判断ppt文件夹是否存在
        if not os.path.exists(path):  
            os.mkdir(path)
        # 判断ppt的html文件是否存在，没有则创建它
        if not os.path.isfile(os.path.join(path,zy_title+".html")):
            # 获取ppt网页
            html = self.session.get(zy_url,headers = self.headers).text
            content = etree.HTML(html)
            with open(os.path.join(path,zy_title+".html"),"w+",encoding="utf-8") as f:
                data = f.read() 
                pattern = "index.files/"
                replace_str = ""
                s = "index.files/"
                html = re.sub(pattern,replace_str,html)
                f.write(html)
            # 保存ppt中的图片到本地
            for img in content.xpath('//img/@src'):
                s = zy_url.split('/')[0:-1]
                s.append(img)
                src = "/".join(s)
                img = img.split("/")[-1]
                # print(src)
                # 如果图片没有被保存过则创建他
                if not os.path.isfile(os.path.join(path,img)):
                    # print('下载图片：',src)
                    with open(os.path.join(path,img),"wb") as f:
                        res = self.session.get(src).content
                        f.write(res)
            if content.xpath('//button[@class="showAnswer"]'):
                l2 = list(zy_url)
                l2.insert(zy_url.rfind("."),"_answer")
                s3 = "".join(l2)
                # print("存在答案",s3)
                self.save_zy(dir_path,s3,dir_name="答案")

        else:
            print('{}的作业已经存在，如果想重新下载，请在目录中删除它'.format(dir_name))  

       

    def download(self,infos):
        # return 
        # 进程间通信的消息队列 
        # queue = Queue()
        base_dir = self.base_dir 
        # 控制进程数量 
        pool = Pool(processes = self.process_count)
        start_date = time.time()
        # f = open('./tarena_tts.json','r')
        # 获取课程名称
        course_title = infos['course_title']
        # course_title = "Linux"
        # 拼接课程存储路径
        course_dir = os.path.join(base_dir,course_title) 
        pthread = []
        # 判断课程目录是否创建，如果没有则创建
        if not os.path.exists(course_dir):
                os.mkdir(course_dir)
        # for index,data in enumerate(f.readlines()):
        # 循环遍历所有课程信息
        for index,data in enumerate(infos['course_infos']):
            #通过加载本地json的方式获取课程信息
            # info = json.loads(data)
            info = data
            # print('***********************************************')
            # print('本章题目：',info['section'])
            # print('***********************************************')
            # 构建目录文件夹
            chapter_directory = os.path.join(course_dir,str(index)+"-"+info['section']) 
            # print(chapter_directory)
            if not os.path.exists(chapter_directory):
                os.mkdir(chapter_directory)
            # 拼接日志文件路径
            log_path = os.path.join(chapter_directory,"log.json")
            # 遍历每节课程信息
            for course_info in info['course_info']:
                # print("本节标题：",course_info['title'])
                # print("本节ppt：",course_info['ppt_url'])
                # 为了创建目录，剔除非法字符串
                dir_name = re.sub('[\/:、：*?"<>|]','-',course_info['title'])#去掉非法字符  
                # 这个目录是视频最终下载的位置，如果没有则创建它
                dir_path = chapter_directory+ "\\" + dir_name
                if not os.path.exists(dir_path):
                    os.mkdir(dir_path)
                # 使用线程下载ppt
                t_ppt = threading.Thread(target= self.save_ppt,args=(dir_path,course_info['ppt_url'],dir_name))
                t_ppt.start()
                pthread.append(t_ppt)
                self.save_ppt(dir_path,course_info['ppt_url'],dir_name)
                # 使用线程下载案例
                t_al = threading.Thread(target= self.save_al,args=(dir_path,course_info['al_url'],dir_name))
                t_al.start()
                pthread.append(t_al)
                # 使用线程下载作业
                t_zy = threading.Thread(target= self.save_zy,args=(dir_path,course_info['zy_url'],dir_name))
                t_zy.start()
                pthread.append(t_zy)
                # time.sleep(3)
                # break
                # 遍历视频信息
                for video_info in course_info['video_info']:
                    # print("名称：",video_info['title']) 
                    # print("下载地址：",video_info['m3u8_url'])
                    # 组成视频的数据，然后交给下载器去入队列下载
                    data = {'video_info':video_info,'dir_path':dir_path}
                    download = m4.Downloader(data,sess=self.session,thread_count=self.thread_count,base_dir=base_dir,log_path=log_path)
                    #维持执行的进程总数为processes，当一个进程执行完毕后会添加新的进程进去
                    pool.apply_async(func = download.start)  
                    # print('启动成功')
                    # queue.put({'video_info':video_info,'dir_path':dir_path})
            # break
        # 通过json读取课程信息,读取完毕后要关闭文件
        # f.close()           
        pool.close()
        pool.join()   #调用join之前，先调用close函数，否则会出错。执行完close后不会有新的进程加入到pool,join函数等待所有子进程结束
        # 等待ppt下载完成
        for t in pthread:
            t.join()
        print("Sub-process(es) done.")
        print('所用时间：',time.time()-start_date)


    def start(self):
        obj = self.__tts_login()
        if obj:
            # 获取所有的信息
            infos = self.__parse_page(obj)
            # print(infos)
            # 将获取到的信息加入到下载队列 
            # infos = {}
            self.download(infos)



# tts = Tts_movie('343795349@qq.com','yutao6393425')
# tts.parse_detail_page('http://tts.tmooc.cn/video/showVideo?menuId=646361&version=AIDTN201809')
# tts.start()
if __name__ == "__main__":
    # tts = Tts_movie('1194681498@qq.com','ruan19980418',process_count = 5,thread_count = 80)
    tts = Tts_movie('252778285@qq.com','182150ss',process_count = 8,thread_count = 64,base_dir=r"E:\达内视频")
    tts.start()
# tts.test_download('http://videotts.it211.com.cn/D_VIP_TSD_N_FUNCTIONPROJECT_DAY05_11/D_VIP_TSD_N_FUNCTIONPROJECT_DAY05_11.m3u8')


# url="http://uc.tmooc.cn/user/checkTtsUser",
# formdata={
#     'loginName': '1',
#     'password': '1',
#     'accountType': '1',
# }
        
       
# url = 'http://tts.tmooc.cn/studentCenter/toMyttsPage'
# yield scrapy.Request(url, callback=self.get_video_link)





# print(html)

"""
GET http://tts.tmooc.cn/video/showVideo?menuId=646375&version=AIDTN201809 HTTP/1.1
Host: tts.tmooc.cn
User-Agent: User-Agent: Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; 360SE)
Accept-Encoding: gzip, deflate
Accept: */*
Connection: keep-alive
Referer: http://tts.tmooc.cn/studentCenter/toMyttsPage
Cookie: isCenterCookie=yes; eBoxOpenAIDTN201809=true;TMOOC-SESSION=534A06090AE649749C76061002E7B420; cloudAuthorityCookie=0; courseCookie=AID; defaultVersionCookie=AIDTN201809; sessionid=534A06090AE649749C76061002E7B420|E_bfultra; stuClaIdCookie=659200; versionAndNamesListCookie=AIDTN201809N22NPython%25E4%25BA%25BA%25E5%25B7%25A5%25E6%2599%25BA%25E8%2583%25BD%25E5%2585%25A8%25E6%2597%25A5%25E5%2588%25B6%25E8%25AF%25BE%25E7%25A8%258BV05; versionListCookie=AIDTN201809


GET http://tts.tmooc.cn/video/showVideo?menuId=646373&version=AIDTN201809 HTTP/1.1
Host: tts.tmooc.cn
Accept-Encoding: gzip, deflate
Connection: keep-alive
Accept-Language: zh-CN,zh;q=0.9
Upgrade-Insecure-Requests: 1
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36
Referer: http://tts.tmooc.cn/studentCenter/toMyttsPage
Cookie: isCenterCookie=no; eBoxOpenAIDTN201809=true; UM_distinctid=166fe2a09a9276-0dee51c671715c-b79183d-144000-166fe2a09aa464; tedu.local.language=zh-CN; cloudAuthorityCookie=0; courseCookie=AID; uniqueVisitorId=299cd14d-c4a4-4864-6709-5b319adaeaa6; Hm_lvt_51179c297feac072ee8d3f66a55aa1bd=1556986264,1557020887,1557055766,1557106256; TMOOC-SESSION=D895425EE55F439E8B6E79146FBD01CD; isCenterCookie=yes; sessionid=D895425EE55F439E8B6E79146FBD01CD|E_bfultra; versionListCookie=AIDTN201809; defaultVersionCookie=AIDTN201809; versionAndNamesListCookie=AIDTN201809N22NPython%25E4%25BA%25BA%25E5%25B7%25A5%25E6%2599%25BA%25E8%2583%25BD%25E5%2585%25A8%25E6%2597%25A5%25E5%2588%25B6%25E8%25AF%25BE%25E7%25A8%258BV05; stuClaIdCookie=659200; Hm_lpvt_51179c297feac072ee8d3f66a55aa1bd=1557111685; JSESSIONID=AC0C0EF5C8ECE4737084BC88E53C7B8C; Hm_lvt_e997f0189b675e95bb22e0f8e2b5fa74=1557110691,1557111019,1557111425,1557111748; Hm_lpvt_e997f0189b675e95bb22e0f8e2b5fa74=1557111748

    isCenterCookie=no
	eBoxOpenAIDTN201809=true
	TMOOC-SESSION=6230A5805F73448286692DA0ABAF1388
	cloudAuthorityCookie=0
	courseCookie=AID
	defaultVersionCookie=AIDTN201809
	sessionid=6230A5805F73448286692DA0ABAF1388|E_bfultra
	stuClaIdCookie=659200
	versionAndNamesListCookie=AIDTN201809N22NPython%25E4%25BA%25BA%25E5%25B7%25A5%25E6%2599%25BA%25E8%2583%25BD%25E5%2585%25A8%25E6%2597%25A5%25E5%2588%25B6%25E8%25AF%25BE%25E7%25A8%258BV05
	versionListCookie=AIDTN201809

    


    isCenterCookie=no
	eBoxOpenAIDTN201809=true
	TMOOC-SESSION=FE1A3071277E42C1BA69709B0E7EB8D0
	sessionid=FE1A3071277E42C1BA69709B0E7EB8D0|E_bfultra
	cloudAuthorityCookie=0
	versionListCookie=AIDTN201809
	defaultVersionCookie=AIDTN201809
	versionAndNamesListCookie=AIDTN201809N22NPython%25E4%25BA%25BA%25E5%25B7%25A5%25E6%2599%25BA%25E8%2583%25BD%25E5%2585%25A8%25E6%2597%25A5%25E5%2588%25B6%25E8%25AF%25BE%25E7%25A8%258BV05
	courseCookie=AID
	stuClaIdCookie=659200
	isCenterCookie=yes

    CNZZDATA1273669604	591373850-1541862456-null%7C1550725970	uc.tmooc.cn	/	2019-08-22T06:32:22.000Z	56				
Hm_lpvt_51179c297feac072ee8d3f66a55aa1bd	1557113795	.tmooc.cn	/	N/A	50				
Hm_lvt_51179c297feac072ee8d3f66a55aa1bd	1556986264,1557020887,1557055766,1557106256	.tmooc.cn	/	2020-05-05T03:36:35.000Z	82				
JSESSIONID	F2E4A3AE2AD88A3141A2C2432518A811	uc.tmooc.cn	/	N/A	42	✓			
TMOOC-SESSION	FE1A3071277E42C1BA69709B0E7EB8D0	.tmooc.cn	/	N/A	45				
tedu.local.language	zh-CN	uc.tmooc.cn	/	2024-05-04T03:36:40.061Z	24				
uniqueVisitorId





{"code":1,"msg":null,"localCode":null,"obj":0,"name":null,"id":null,"list":null,"count":null}

{"code":1,"msg":null,"localCode":null,"obj":7,"name":null,"id":null,"list":null,"count":null}

POST http://uc.tmooc.cn/login HTTP/1.1
Host: uc.tmooc.cn
Connection: keep-alive
Content-Length: 93
Accept: */*
Origin: http://www.tmooc.cn
X-Requested-With: XMLHttpRequest
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
Referer: http://www.tmooc.cn/
Accept-Encoding: gzip, deflate
Accept-Language: zh-CN,zh;q=0.9
Cookie: tedu.local.language=zh-CN; UM_distinctid=166fe2a09a9276-0dee51c671715c-b79183d-144000-166fe2a09aa464; CNZZDATA1273669604=591373850-1541862456-null%7C1550725970; TMOOC-SESSION=41BEC0C090AD4C73B2A7DAED5DF7DAF7; Hm_lvt_51179c297feac072ee8d3f66a55aa1bd=1556981400,1556986264,1557020887,1557055766; Hm_lpvt_51179c297feac072ee8d3f66a55aa1bd=1557057742; JSESSIONID=3CD758DD3B6938C7127272F9B665EB83

loginName=343795349%40qq.com&password=927a7ba4db67084c569da8a6970195ce&imgCode=&accountType=1



"""



"""
        'AppCount':'1',
        'AppEnabled':'0',
        'EA_port':'54530',
        'haveLogin':'1',
        'IpEnabled':'0',
        'is_reminded':'1',
        'language':'zh_CN',
        'LoginMode':'2',
        'remoteAppCount':'0',
        'scacheUseable':'0',
        'TWFID':'3485e6ed38040029',
        'UsingDkey':'0',
        'webonly':'0',
        'websvr_cookie':'%zd'


"""