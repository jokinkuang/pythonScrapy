# -*- coding: utf-8 -*-

# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html
import scrapy
import logging
import re
import time
import datetime

from scrapy.http import Request
from scrapy.http import FormRequest
from scrapy.selector import Selector
from scrapy.settings import Settings
from scrapy.mail import MailSender

from crashMonitor.items import YYVersionItem
from crashMonitor.items import CrashInfoItem

from scrapy.mail import MailSender

# To get your settings from (settings.py):
from scrapy.utils.project import get_project_settings
from scrapy.exceptions import CloseSpider

class CrashSpider(scrapy.Spider):
    name = "crashMonitor"
    settings = get_project_settings() #DOC http://stackoverflow.com/questions/14075941/how-to-access-scrapy-settings-from-item-pipeline

    args = {} #不能直接扩展settings所以使用args ,解决方案：使用settings.set()方法重新设置和扩展（试过也不行！）

    starttime = 0
    mode = "monitor"
    mail = {}
    version_items = []
    crash_items = []

    #从命令行得到的参数都是字符串！！包括''是字符串“‘’”,空是不赋值
    #scrapy.exe crawl crashMonitor -a mode=weekly mode=custom begin=2016-3-8 end=2016-3-9 yy=yy1.7.6.6 module=gametask max=20 mailEnabled=1
    def __init__(self, mode='', yy='', begin='', end='', module='', max='0', mailEnabled='1', mailPass='',*args, **kwargs):
        super(scrapy.Spider, self).__init__(*args, **kwargs)

        #默认监控模式
        if mode == '':
            self.mode = "monitor"
        if not begin == '':
            self.mode = 'custom'
        if not mailPass == '':
            self.settings.set('MAIL_PASS', mailPass)

        #默认开启邮件功能
        self.mail['enabled'] = int(mailEnabled) if mailEnabled.isdigit() else 1

        if self.mode == 'custom':
            self.args['yy'] = str(yy)
            self.args['begin'] = self.parse_date(begin)
            self.args['end'] = self.parse_date(end)
            self.args['module'] = str(module)
            self.args['max'] = int(max) if max.isdigit() else 20

        if not str(mode) == '': #如果指定了mode，则使用mode
            self.mode = str(mode)
            if not mode == 'daily' and not mode == 'weekly' and not mode == 'custom'and not mode == 'monitor':
                logging.error("Mode should be daily weekly custom or monitor")
                raise CloseSpider("Parameters Error")

        #读取配置，配置是公有的
        self.configs = self.getConfigs()

        #monitor模式才有以下属性
        if self.mode == 'monitor':
            if self.configs.has_key('lastCrashNum'):
                self.configs['lastCrashNum'] = int(self.configs['lastCrashNum']) if self.configs['lastCrashNum'].isdigit() else 0
                pass
            else:
                self.configs['lastCrashNum'] = 0
            if self.configs.has_key('lastCrashDate'):
                pass
            else:
                self.configs['lastCrashDate'] = ""

            logging.info("[Before] lastCrashNum: " + str(self.configs['lastCrashNum']))
            logging.info("[Before] lastCrashDate: " + str(self.configs['lastCrashDate']))

        #脚本开始执行时间
        self.starttime = time.time()

    def start_requests(self):
        logging.info("Start Login...")
        #方式一: 加载网页模拟页面登录
        #return [Request("http://crashreport.yy.duowan.com/crashreport/index.php", callback = self.post_login)]  #重写了爬虫类的方法, 实现了自定义请求, 运行成功后会调用callback回调函数

        #方式二：直接POST到登录API
        return [scrapy.FormRequest("http://crashreport.yy.duowan.com/crashreport/login.php",
                                    formdata={
                                    'txtUsername': self.settings['YY_USERNAME'],
                                    'txtPassword': self.settings['YY_PASSWORD'],
                                    'savepasswd': 'true'
                                    },
                                    callback=self.after_login)]

    #FormRequeset
    def post_login(self, response):
        #FormRequeset.from_response是Scrapy提供的一个函数, 用于post表单
        #登陆成功后, 会调用after_login回调函数
        return [FormRequest.from_response(response,
                            formdata = {
                            'txtUsername': self.settings['YY_USERNAME'],
                            'txtPassword': self.settings['YY_PASSWORD'],
                            'savepasswd': 'true'
                            },
                            callback = self.after_login
                            )]


    def after_login(self, response) :
        # 默认重复的请求会被过滤，通过设置dont_filter来强制执行
        logging.debug(response.body)
        if not response.body == "10000":
            logging.info("Login Failed !")
            raise CloseSpider('Login Failed')       #close spider with reason
        else:
            logging.info("Login Successful !")
        return Request("http://crashreport.yy.duowan.com/crashreport/product.php", dont_filter=True, callback=self.getYYCrashList)


    def getYYCrashList(self, response):
        #获取线上所有YY版本
        index = 0
        for sel in response.xpath('//div[@id="version_list"]//tr'):
            logging.debug("version_list xpath:" + str(sel))
            _list = sel.xpath('td/text()').extract()

            if len(_list) < 8:  #忽略table的标题<tr>
                if index > 0:
                    logging.warning("VersionItemXpath: table column is less than 8 : " + str(len(_list)))
                index += 1
                continue

            item = YYVersionItem() #extract得到的是Unicode编码，response.body是utf-8编码，而邮件则需要utf-8编码，在发邮件时再转换
            item['version'] = _list[1]
            item['date'] = _list[2]
            item['status'] = 1 if _list[3] == u'启用' else 0  # 1表示启用，0表示停用
            item['crashNum'] = _list[4]
            item['href'] = sel.xpath('td/a/@href').extract_first() #链接部分的td含有特殊字符，所以单独处理
            self.version_items.append(item)
            logging.debug("Found VersionItem: ")
            logging.debug(item)
            #yield item  #这里就不返回item的生成器了，而是保存到列表里等待处理，否则生成器会

        logging.info("Online YY Version List Size: " + str(len(self.version_items)) )

        if self.mode == 'daily':
            self.mail['subject'] = u"崩溃日报 —— " + self.settings['MAIL_SUBJECT'].decode('utf-8')
            self.mail['to'] = self.settings['MAIL_TO']['daily']
            self.mail['title'] = u'Crash Daily Report on ' + self.nowdatetime()
            return self.dailySchedule()

        elif self.mode == 'weekly':
            self.mail['subject'] = u"崩溃周报 —— " + self.settings['MAIL_SUBJECT'].decode('utf-8')
            self.mail['to'] = self.settings['MAIL_TO']['weekly']
            self.mail['title'] = u'Crash Weekly Report From ' + self.nowdate(-7) + u' To ' + self.nowdatetime()
            return self.weeklySchedule()

        elif self.mode == 'custom':
            self.mail['subject'] = u"崩溃报告 —— " + self.settings['MAIL_SUBJECT'].decode('utf-8')
            self.mail['to'] = self.settings['MAIL_TO']['custom']
            self.mail['title'] = u'Crash Report From ' + self.args['begin'] + ' To ' + self.args['end']
            return self.customSchedule()

        elif self.mode == 'monitor':
            self.mail['subject'] = u'崩溃告警！！！已崩溃{0}例！{1}—— ' + self.settings['MAIL_SUBJECT'].decode('utf-8')
            self.mail['to'] = self.settings['MAIL_TO']['crash']
            self.mail['title'] = u'Crash Monitor on ' + self.nowdatetime()
            return self.dailySchedule()     #monitor其实也是daily的一种

        else:
            logging.error("Spider Mode Error: need daily weekly custom or monitor !")
            exit(1)


    def dailySchedule(self):
        logging.info("Daily Schedule Start...")
        weblist = []
        for item in self.version_items:
            if item['href'] == '':
                continue

            #没有启用不检索
            if not item['status']:
                continue

            #从href里获得参数
            _keys = re.split('\?|=|&', item['href'])
            if len(_keys) < 7:
                logging.warning("VersionHref: href parameters is less than 7 : " + str(len(_keys)))
                continue

            _pkey = _keys[2]
            _vid = _keys[4]
            _type = _keys[6]
            logging.debug("%s %s %s", _pkey, _vid, _type)

            #指定版本
            #if not "8.6.0.0_zh-CN" in item['version']:
            #    continue

            #开始按条件检索崩溃
            url = "http://crashreport.yy.duowan.com/crashreport/searchtime.php"
            request = scrapy.http.FormRequest(url,
                    formdata = {
                    'pkey' : _pkey,
                    'vid' : _vid,
                    'type' : _type,
                    'page' : '1',
                    'act' : '',
                    'date': '6', # 6 means Today
                    'module_name': self.settings['YY_MODULE_NAME'],
                    'analysis_module_name': self.settings['YY_BUSINESS_NAME']
                    },
                    callback=self.getCrashData)
            request.meta['version_item'] = item;    #传递item给response
            weblist.append(request)

        return weblist#[12:13]


    def weeklySchedule(self):
        logging.info("Weekly Schedule Start...")
        weblist = []
        for item in self.version_items: #每个版本
            if item['href'] == '':
                continue

            #没有启用不检索
            if not item['status']:
                continue

            #从href里获得参数
            _keys = re.split('\?|=|&', item['href'])
            if len(_keys) < 7:
                logging.warning("VersionHref: href parameters is less than 7 : " + str(len(_keys)))
                continue

            _pkey = _keys[2]
            _vid = _keys[4]
            _type = _keys[6]
            logging.debug("%s %s %s", _pkey, _vid, _type)

            #指定版本
            #if not "8.6.0.0_zh-CN" in item['version']:
            #    continue

            #开始按条件检索崩溃
            url = "http://crashreport.yy.duowan.com/crashreport/searchtime.php"
            for i in range(7):  #过去一周
                request = scrapy.http.FormRequest(url,
                        formdata = {
                        'pkey' : _pkey,
                        'vid' : _vid,
                        'type' : _type,
                        'page' : '1',
                        'act' : '',
                        'date': str(6 + i), # 6 means Today
                        'module_name': self.settings['YY_MODULE_NAME'],
                        'analysis_module_name': self.settings['YY_BUSINESS_NAME']
                        },
                        callback=self.getCrashData)
                request.meta['version_item'] = item;    #传递item给response
                weblist.append(request)

        return weblist#[12:13]
        pass


    def customSchedule(self):
        logging.warning("Custom mode is developing !")
        pass


    def getCrashData(self, response):
        #logging.debug(response.body)
        version_item = response.meta['version_item']

        index = 0
        for sel in response.xpath('//tr'):
            logging.debug("crash_item xpath:" + str(sel))

            # xpath("//td/text()").extract()会自动过滤空的<td></td>，因此自己遍历
            _list = []
            for td in sel.xpath('td'):
                if 'href' in td.extract():
                    _list.append(td.xpath('a').extract_first()) #可能有多个，只保留一个
                else:
                    _list.append(td.xpath('text()').extract_first(default=u'')) #如果为空，则为u''
                    #注意： 这里不加default，为空时返回的是None，而default=''返回的是Str，而default=u''返回的是Unicode
                    #      如果这里不统一，就会导致 string + string 因为一个为Str，而另一个为Unicode造成TypeError错误！！！

            if len(_list) < 11:  #忽略table的标题<tr>        (查所有时，只有10项，每天报告则有11项)
                if index > 0:
                    logging.warning("CrashItemXpath: table column is less 11 : " + str(len(_list)))
                index += 1
                continue

            item = CrashInfoItem() #extract得到的是Unicode编码，response.body是utf-8编码，而邮件则需要utf-8编码，在发邮件时再转换
            item['crashNum'] = int(_list[0])    #转换为数值以便比较
            item['totalCrashNum'] = _list[1]
            item['crashID'] = _list[2]
            item['moduleName'] = _list[3]
            item['businessName'] = _list[4]
            item['linkman'] = _list[5]
            item['exception'] = _list[6]
            item['problem'] = _list[7]
            item['bugLink'] = _list[8]
            item['autoAnalyze'] = _list[9].replace('/crashreport/','')	#清掉重复的crashreport
            item['firstCrashDate'] = _list[10]
            item['version'] = version_item['version']

            self.crash_items.append(item)
            logging.debug("Found CrashItem:")
            logging.debug(item)

        logging.info("Today Crash List Size: " + str(len(self.crash_items)) )


#================================================POST=======================================================
    def close(self, reason):
        if not reason == "finished":
            logging.info("CrashMonitor End With Reason: " + reason)
            return

        #按照crashNum从大到小排序
        self.crash_items.sort(key=lambda CrashInfoItem : CrashInfoItem['crashNum'], reverse=True)
        logging.debug(self.crash_items)

        #得到TOP N
        top = int(self.settings['CRASH_TABLE_SIZE'])
        top = top if top > 0 else 10
        if len(self.crash_items) > top:
            self.crash_items = self.crash_items[:top]

        #monitor模式才有告警
        if self.mode == 'monitor':
            if len(self.crash_items) > 0 and self.crash_items[0]['crashNum'] >= int(self.settings['CRASH_WARNING_LINE']):
                increaseNum = self.crash_items[0]['crashNum'] - self.configs['lastCrashNum']    #跨日时可能有问题，目前忽略
                if self.configs['lastCrashNum'] == 0 and increaseNum > 0:
                    self.mail['subject'] = self.mail['subject'].format( str(self.crash_items[0]['crashNum']),"" )
                elif self.configs['lastCrashNum'] > 0 and increaseNum > 0:
                    self.mail['subject'] = self.mail['subject'].format( str(self.crash_items[0]['crashNum']),"递增了"+str(increaseNum)+"例！" )
                else:
                    logging.info("[Email] reach crash line but no crash increase any more so disable email sending !")
                    self.mail['enabled'] = False    #崩溃没有递增，不发送邮件
            else:
                logging.info("[Email] not reach crash line so disable email sending !")
                self.mail['enabled'] = False    #没有发生崩溃，或没有达到崩溃线，不发送邮件

            #写入配置
            if len(self.crash_items) > 0:
                self.configs['lastCrashNum'] = self.crash_items[0]['crashNum']
            else:
                self.configs['lastCrashNum'] = 0
            self.configs['lastCrashDate'] = self.nowdatetime()
            logging.info("[After] lastCrashNum: " + str(self.configs['lastCrashNum']))
            logging.info("[After] lastCrashDate: " + str(self.configs['lastCrashDate']))

        #保存配置，配置是公有的
        self.saveConfigs(self.configs)

        if not self.settings['MAIL_ENABLED'] or not self.mail['enabled']:
            logging.info("[Email] MAIL is disabled so no Emails sent !")
            #脚本执行结束时间
            logging.info(u"脚本执行时间：%d seconds", (time.time() - self.starttime))
            return

        #生成邮件
        html = u'<center>' + self.mail['subject'] + u'</center>'
        html += u'<center>' + self.mail['title'] + u' Top ' + str(self.settings['CRASH_TABLE_SIZE']) + u'</center>'
        html += self.generateCrashTable()
        html += u'<center>* 注：自动分析里的报告可以看到崩溃堆栈，不过不一定能定位，准确定位还需点击ReportID下载多个dump文件进行分析</center>'
        logging.debug(html)

        #开发调试中，邮件只发给maintainer
        if self.settings['DEVELOPING']:
            logging.info("[Developing] developing mode is on so only send Email to maintainer !")
            self.mail['to'] = self.settings['MAIL_TO']['maintainer']

        #发送邮件
        mailer = MailSender.from_settings(self.settings)
        mailer.send(to=self.mail['to'], subject=self.mail['subject'], body=html.encode('utf-8'), mimetype='text/html;charset=UTF-8')

        #脚本执行结束时间
        logging.info(u"脚本执行时间：%d seconds", (time.time() - self.starttime))

        mailer = MailSender.from_settings(self.settings)
        mailer.send(to=['kuangzukai@yy.com'], subject='OK', body='OK', mimetype='text/html;charset=UTF-8')
        pass


#邮件正文一开始使用中文，邮件就能自动识别为utf-8编码，而使用英文，很可能引起邮件被以非utf-8编码打开！！！当然也可以强制指定邮件编码
    def generateCrashTable(self):
        html = u'''<div style="font-size: 11.818181991577148px;"><span id="txtCrashReportList">
        <table width="1200"border="0"align="center"cellpadding="0"cellspacing="0"class="dataintable"style="font-family: Arial, Helvetica, sans-serif; margin-top: 0px; border-collapse: collapse; border: 1px solid rgb(136, 136, 136); width: 1022.7272338867188px; word-break: break-all; word-wrap: break-word;">
        <tbody><tr>
        <th width="40"style="font-size: 12px; vertical-align: baseline; padding: 5px; background-color: rgb(204, 204, 204); border: 1px solid rgb(136, 136, 136);">日报告数</th>
        <th width="40"style="font-size: 12px; vertical-align: baseline; padding: 5px; background-color: rgb(204, 204, 204); border: 1px solid rgb(136, 136, 136);">总报告数</th>
        <th width=""  style="font-size: 12px; vertical-align: baseline; padding: 5px; background-color: rgb(204, 204, 204); border: 1px solid rgb(136, 136, 136);">Report ID</th>
        <th width=""  style="font-size: 12px; vertical-align: baseline; padding: 5px; background-color: rgb(204, 204, 204); border: 1px solid rgb(136, 136, 136);">YY版本</th>
        <th width=""  style="font-size: 12px; vertical-align: baseline; padding: 5px; background-color: rgb(204, 204, 204); border: 1px solid rgb(136, 136, 136);">模块名称</th>
        <th width="50"style="font-size: 12px; vertical-align: baseline; padding: 5px; background-color: rgb(204, 204, 204); border: 1px solid rgb(136, 136, 136);">业务模块</th>
        <th width="40"style="font-size: 12px; vertical-align: baseline; padding: 5px; background-color: rgb(204, 204, 204); border: 1px solid rgb(136, 136, 136);">联系人</th>
        <th width="40"style="font-size: 12px; vertical-align: baseline; padding: 5px; background-color: rgb(204, 204, 204); border: 1px solid rgb(136, 136, 136);">异常描述</th>
        <th width="50"style="font-size: 12px; vertical-align: baseline; padding: 5px; background-color: rgb(204, 204, 204); border: 1px solid rgb(136, 136, 136);">问题描述</th>
        <th width="50"style="font-size: 12px; vertical-align: baseline; padding: 5px; background-color: rgb(204, 204, 204); border: 1px solid rgb(136, 136, 136);">Bug单链接</th>
        <th width="35"style="font-size: 12px; vertical-align: baseline; padding: 5px; background-color: rgb(204, 204, 204); border: 1px solid rgb(136, 136, 136);">自动分析</th>
        <th width=""  style="font-size: 12px; vertical-align: baseline; padding: 5px; background-color: rgb(204, 204, 204); border: 1px solid rgb(136, 136, 136);">首次上报时间</th></tr>'''

        for item in self.crash_items:
            #注意：使用%s与%格式化出现TypeError: not all arguments converted during string formatting没有成功，所以使用format格式化。
            row = u'<tr>'
            for i in range(12):
                row += u'''<td width=""style="font-size: 12px; vertical-align: text-top; padding: 5px 2px; background-color: rgb(239, 239, 239); border: 1px solid rgb(170, 170, 170);">{'''\
                        + str(i) + u'''}</td>'''
            row += u'</tr>'
            html += row.format(item['crashNum'], item['totalCrashNum'], item['crashID'], item['version'],
                               item['moduleName'], item['businessName'], item['linkman'], item['exception'],
                               item['problem'], item['bugLink'], item['autoAnalyze'], item['firstCrashDate'])

        html += u'''</tbody></table></span></div>'''
        return html.replace('href="','href="http://crashreport.yy.duowan.com/crashreport/')

    #format:{ key:value }
    def getConfigs(self):
        configs = {}
        confile = None
        try:
            #If the file cannot be opened, IOError is raised
            confile = open('config.ini', 'r')
            for line in confile:
                _parts = line.split("=")
                if len(_parts) == 2:
                    configs[_parts[0].strip()] = _parts[1].strip()
            confile.close()
        except IOError:
            pass
        except Exception:
            confile.close()
            pass
        return configs

    #format: key=value
    def saveConfigs(self, configs):
        confile = open('config.ini', 'w')
        try:
            for key, value in configs.items():
                confile.write(key + "=" + str(value) + "\n")
        finally:
             confile.close()

    #format: yy-mm-dd
    def parse_date(self, s):
        list = s.split('-')
        if len(list) < 3:
            logging.error("Date Format should be yy-mm-dd")
            exit(1)
        return datetime(int(list[0]), int(list[1]), int(list[2]))

    #format: yy-mm-dd HH:MM:SS
    def nowdatetime(self, days=0):
        date = datetime.datetime.now() + datetime.timedelta(days=days)
        return date.strftime('%Y-%m-%d %H:%M:%S')

    #format: yy-mm-dd
    def nowdate(self, days=0):
        date = datetime.datetime.now() + datetime.timedelta(days=days)
        return date.strftime('%Y-%m-%d')
        #return time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(date.timetuple()))

