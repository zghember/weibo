# coding: utf-8
from selenium import webdriver
from selenium.webdriver.common.proxy import *
import requests
from bs4 import BeautifulSoup
import logging
import time
import pymysql
from selenium.webdriver.common.keys import Keys
import csv

base_url = 'http://weibo.com'
UA = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"

class Wb:
    def __init__(self, raw_cookie="", vip="", username="", password="", proxy_str="", ucur=0, utotal=100):
        cookies_list = raw_cookie.split(';')
        cookies = []
        for c in cookies_list:
            tmp = c.split('=')
            cookies.append({'name': tmp[0], 'value': tmp[1]})
        # self.driver = self.login('pricezgh@gmail.com', 'zhong191200')
        self.vip = vip
        self.conn = pymysql.connect(host='localhost', port=3306, user='root', passwd='', db='weizhishu', charset='utf8')
        self.cursor = self.conn.cursor()

        self.proxy = Proxy({
            'proxyType': ProxyType.MANUAL,
            'httpProxy': proxy_str,
            'ftpProxy': proxy_str,
            'sslProxy': proxy_str,
            'noProxy': ''
        })
        self.driver = self.login_with_cookies(cookies)

    def login(self, username, password):
        browser = webdriver.Firefox(proxy=self.proxy)
        browser.get("http://weibo.com/login.php")
        time.sleep(5)
        user = browser.find_element_by_xpath("//*[@id='pl_login_form']/div[5]/div[1]/div/input")
        user.send_keys(username, Keys.ARROW_DOWN)
        passwd = browser.find_element_by_xpath("//*[@id='pl_login_form']/div[5]/div[2]/div/input")
        passwd.send_keys(password, Keys.ARROW_DOWN)
        vcode = browser.find_element_by_xpath("//*[@id='pl_login_form']/div[5]/div[3]")
        if 'none' not in vcode.get_attribute('style'):
            code = input("verify code:")
            if code:
                vcode.send_keys(code, Keys.ARROW_DOWN)
        browser.find_element_by_xpath("//*[@id='pl_login_form']/div[5]/div[6]/div[1]/a/span").click()
        time.sleep(5)
        print(browser.find_element_by_xpath("//*[@id='v6_pl_content_homefeed']/div[2]/div[3]/div[1]/div[1]/div[3]/div[1]/a[1]").get_attribute("usercard"))
        # cookie_file = open('cookie.dat', 'w')
        # cookie_file.write(str(browser.get_cookies()))
        # cookie_file.close()
        return browser

    def login_with_cookies(self, cookies):
        browser = webdriver.Firefox(proxy=self.proxy)
        browser.get("http://weibo.com/login.php")
        time.sleep(5)
        for cookie in cookies:
            browser.add_cookie(cookie)
        browser.get('http://weibo.com')
        return browser

    def get_html(self, url):
        try:
            self.driver.get(url)
            time.sleep(5)
            html = self.driver.page_source
        except Exception as e:
            html = None
            logging.error(e)
        return html

    def get_weibo(self, uid):
        weibo_list = []
        url = base_url + '/u/%s' % (uid,)
        print(url)
        html = self.get_html(url)
        soup = BeautifulSoup(html)
        details = soup.find_all(attrs={'class': 'WB_detail'})
        for d in details:
            c = d.findChild(attrs={'class': 'WB_from S_txt2'}, recursive=False)
            href = c.find('a')['href']
            tail = href.split('/')[2]
            wid = tail.split('?')[0]
            weibo_list.append(wid)
        return weibo_list

    def gen_url(self, uid, wid, ttype):
        url = base_url + '/%s/%s?type=%s' % (uid, wid, ttype)
        return url

    def get_comment(self, uid, wid):
        comments = []
        url = self.gen_url(uid, wid, 'comment')
        html = self.get_html(url)
        soup = BeautifulSoup(html)
        comment_list = soup.find('div', attrs={'class': 'list_ul'})
        faces = comment_list.findAll('div', attrs={'class': 'WB_face'})
        for face in faces:
            follow = face.find('a')['href']
            comments.append(face.find('a')['href'])
            sql = "insert into weibo_guanxi(weibo_id,uid,uid_flow,hudong) values('%s','%s','%s','%s')"%(wid, uid, follow,'comment')
            self.cursor.execute(sql)
        print(comments)
        pass

    def get_repost(self, uid, wid):
        reposts = []
        url = self.gen_url(uid, wid, 'repost')
        html = self.get_html(url)
        soup = BeautifulSoup(html)
        repost_list = soup.find('div', attrs={'class': 'list_ul'})
        faces = repost_list.findAll('div', attrs={'class': 'WB_face'})
        for face in faces:
            follow = face.find('a')['href']
            reposts.append(follow)
            sql = "insert into weibo_guanxi(weibo_id,uid,uid_flow,hudong) values('%s','%s','%s','%s')"%(wid, uid, follow,'repost')
            self.cursor.execute(sql)
        print(reposts)
        pass

    def get_like(self, uid, wid):
        likes = []
        url = self.gen_url(uid, wid, 'like')
        html = self.get_html(url)
        soup = BeautifulSoup(html)
        repost_list = soup.find('ul', attrs={'class': 'emotion_list'})
        faces = repost_list.findAll('li')
        for face in faces:
            follow = '/' + face['uid']
            likes.append(follow)
            sql = "insert into weibo_guanxi(weibo_id,uid,uid_flow,hudong) values('%s','%s','%s','%s')"%(wid, uid, follow,'like')
            self.cursor.execute(sql)
        print(likes)
        pass

    def get_data(self):
        uid = self.vip
        weibo_list = self.get_weibo(uid)
        for wid in weibo_list:
            self.get_comment(uid, wid)
            self.get_repost(uid, wid)
            self.get_like(uid, wid)

    def get_all_people(self,):
        self.cursor.execute('select distinct uid_flow from weibo_guanxi order by id limit 10')
        all_people = self.cursor.fetchall()
        for item in all_people:
            self.get_people(item[0])

    def get_people(self, uid):
        url = base_url + uid
        soup = BeautifulSoup(self.get_html(url))
        href = soup.find('span', attrs={'class': 'more_txt'}).parent['href']
        detail_url = base_url + href
        soup = BeautifulSoup(self.get_html(detail_url))
        input()

def get_cookies():
    r = requests.get('http://t.v2gg.com/weizhishu/weibohao/wb_cookie.php').text
    cookie_list = r.split('|')
    cookies = []
    for cookie in cookie_list:
        idx = cookie.find('SSO')
        cookies.append(cookie[idx:].strip('\r\n'))
    return cookies

def get_proxys():
    r = requests.get('http://svip.kuaidaili.com/api/getproxy/?orderid=993684485948843&num=300&area=%E5%A4%A7%E9%99%86&browser=1&protocol=1&method=1&an_tr=1&an_an=1&an_ha=1&sp1=1&sp2=1&quality=2&sort=1&format=json&sep=4').text
    data = eval(r)
    plist = data['data']['proxy_list']
    print(plist)
    return plist


if __name__ == '__main__':
    cookie = None
    count = 0
    wb_list = []
    cookies = get_cookies()
    plist = get_proxys()
    length = min(cookies, plist)
    for idx in range(0, length):
        #wb = Wb(raw_cookie=cookie, vip='1991428685', proxy_str=plist[1])
        #wb.get_data()
        wb = Wb(raw_cookie=cookies[idx], proxy_str=plist[idx], ucur=idx, utotal=length)
        wb_list.append(wb)
        wb.get_all_people()
        count += 1
        if count == 2:
            break

        input()
    pass
