# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy

class crashMonitorItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass #只是一个空语句，用于使格式完整（不仅仅看起来，也用于使空类、空函数能够通过编译，像上面的TutorialItem空类）

class YYVersionItem(scrapy.Item):
    version = scrapy.Field()    #版本
    date = scrapy.Field()       #发布日期
    status = scrapy.Field()     #崩溃状态
    crashNum = scrapy.Field()   #崩溃总数
    href = scrapy.Field()       #崩溃报告URL
    pass

#时段报告数	总报告数	Report ID	模块名称	业务模块	联系人	异常描述	问题描述	Bug单链接	自动分析	首次上报时间
class CrashInfoItem(scrapy.Item):
    crashNum = scrapy.Field()       #当日崩溃总数量（或当周崩溃总数量）
    totalCrashNum = scrapy.Field()  #当前崩溃点崩溃总数
    crashID = scrapy.Field()        #崩溃ID
    version = scrapy.Field()        #发生崩溃的版本
    moduleName = scrapy.Field()     #模块名称
    businessName = scrapy.Field()   #业务模块
    linkman = scrapy.Field()        #联系人
    exception = scrapy.Field()      #异常描述
    problem = scrapy.Field()        #问题描述
    bugLink = scrapy.Field()        #Bug单链接
    autoAnalyze = scrapy.Field()    #自动分析
    firstCrashDate = scrapy.Field() #首次崩溃日期
    pass
