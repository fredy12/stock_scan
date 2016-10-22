# -*- coding: utf-8 -*-
'''
Find minimum market value of stock
Created on 2016-10-22

@author: tongkai.ytk(ziyu) <tongkai.ytk@alibaba-inc.com>
'''

import re
import json
import time
import requests
import multiprocessing


class Worker(multiprocessing.Process):
    
    def __init__(self, work_queue, result_queue):
        self.work_queue = work_queue
        self.result_queue = result_queue
        super(Worker, self).__init__()

    def run(self):
        while not self.work_queue.empty():
            func, args, kwargs = self.work_queue.get()
            print 'finish[%s], working... %s' % (self.result_queue.qsize(), args)
            res = func(*args, **kwargs)
            self.result_queue.put(res)


def value_get(codes):
    r = requests.get("http://qt.gtimg.cn/q=%s" % codes)
    if r.status_code == 200:
        if "pv_none_match" not in r.text:
            return r.text
    return "FAILED"


def analyse_result(result_queue):
    all_result = []
    while not result_queue.empty():
        all_result.append(result_queue.get())
    
    analysis_results = []
    fail_num = 0
    for temp_result in all_result:
        if temp_result == "FAILED":
            fail_num += 1
            continue
        
        for result in temp_result.split('\n'):
            splited_result = result.split('~')
            try:
                stock_code = splited_result[2]
                stock_name = splited_result[1]
                pe = splited_result[39]
                pb = splited_result[46]
                tmc = splited_result[45]
                mc = splited_result[44]
            except Exception:
                print result
            
            try:
                if (float(mc) != 0.00 or float(tmc) != 0.00) and (float(tmc) <= 50.0 or float(mc) <= 50.0):
                    analysis_results.append((stock_code, stock_name, pe, pb, tmc, mc))
            except Exception:
                continue
        
    print 'Failed num: %s' % fail_num
    print '代码\t名称\tPE\tPB\t总市值\t流通市值'
    for stock_code, stock_name, pe, pb, tmc, mc in analysis_results:
        print "%s\t%s\t%s\t%s\t%s\t%s" % (stock_code, stock_name, pe, pb, tmc, mc)


class Stock(object):
    
    def __init__(self, code_list, worker_num, value_get_func):
        self.codes_list = code_list    # every codes_list is like sh000001,sh000002
        self.work_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.workers = []
        self._init_work_pool(worker_num)
        self.value_get_func = value_get_func

    def _init_work_pool(self, worker_num):
        for _ in xrange(worker_num):
            self.workers.append(Worker(self.work_queue, self.result_queue))

    def start_work(self):
        for codes in self.codes_list:
            self.work_queue.put((self.value_get_func, (codes,), {}))
        for worker in self.workers:
            worker.start()
        while not self.work_queue.empty():
            time.sleep(1)
        print "########### wait 5s"
        time.sleep(5)
        analyse_result(self.result_queue)


def get_all_code_from_eastmoney(size=50):
    all_code_url = "http://quote.eastmoney.com/stocklist.html"
    r = requests.get(all_code_url)
    #print r.text
    all_code_list = re.findall(r'''quote.eastmoney.com/([a-z]{2,}[0-9]{6,}).html"''', r.text)
    
    if len(all_code_list) == 0:
        raise Exception("cannot get all code")
    
    with open('/tmp/all_code_list', 'w') as f:
        f.write(json.dumps(all_code_list))
        
    # divide list into some str lists like ['sh000001,sh000002']
    divided_code_list = []
    for i in xrange(0, len(all_code_list), size):
        if i+size > len(all_code_list):
            code_str = ','.join(all_code_list[i:])
        else:
            code_str = ','.join(all_code_list[i:i+size])
        divided_code_list.append(code_str)
    return divided_code_list


if __name__ == '__main__':
    worker_num = 3
    sleep_time = 1
    
    all_codes = get_all_code_from_eastmoney()
    stock = Stock(all_codes, worker_num, value_get)
    stock.start_work()
