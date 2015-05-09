# -*- coding: utf-8 -*-
import re
import json
import gzip
import base64
import time
import urllib
import urllib2
import httplib
from StringIO import StringIO
from xbmcswift2 import xbmc
from xbmcswift2 import Plugin
from xbmcswift2 import xbmcgui
try:
    from ChineseKeyboard import Keyboard
except:
    from xbmc import Keyboard

plugin = Plugin()
dialog = xbmcgui.Dialog()
filters = plugin.get_storage('ftcache', TTL=1440)
epcache = plugin.get_storage('epcache', TTL=1440)

baseurl = r'http://www.fuyin.tv'

@plugin.route('/')
def showcatalog():
    """
    show catalog list
    """
    if baseurl in epcache:
       return epcache[baseurl]
    result = _http(baseurl)
    catastr = re.search(r'<div class="nav".*?<ul>(.*?)</ul>',
                        result, re.S)
    catalogs = re.findall(r'<a href="(/content/category.*?)" title="(.*?)"', catastr.group(1),re.S)
    menus = [{
        'label': catalog[-1],
        'path': plugin.url_for('showlist',
                               url='{0}'.format(
                                   catalog[0])),
    } for catalog in catalogs]
    menus.insert(0, {'label': '【搜索视频】选择', 'path': plugin.url_for(
        'searchvideo')})
    menus.append({'label': '热门视频', 'path': plugin.url_for(
       'showhotlist')})
    menus.append({'label': '手动清除缓存【缓存24小时自动失效】',
                  'path': plugin.url_for('clscache')})
    epcache[baseurl] = menus
    return menus

@plugin.route('/searchvideo')
def searchvideo():
    """
    search video
    """
    kb = Keyboard('', u'请输入搜索关键字')
    kb.doModal()
    if not kb.isConfirmed():
        return
    sstr = kb.getText()
    if not sstr:
        return
    keyword = urllib2.quote(sstr.decode('utf8').encode('gbk'))
    url = '/index.php/content/search/?keyword='+keyword+'&type=all'

    return showlist(url)

@plugin.route('/hotlist')
def showhotlist():
    """
    show hot movie list
    """
    hoturl = '/index.php/content/hot/'
    if hoturl in epcache:
        return epcache[hoturl]

    result = _http(baseurl+hoturl)

    ulist = re.search(r'<table(.*?)</table>', result, re.S)
    # get movie list
    movies = re.findall(r'<a href="(.*?)" title="(.*?)"', ulist.group(1), re.S)

    menus = []
    # 0 is url, 1 is title
    for seq, m in enumerate(movies):
        menus.append({
            'label': '{0}. {1}'.format(seq+1, m[1]),
            'path': plugin.url_for('showmovie', url=m[0]),
        })
    
    epcache[hoturl] = menus
    return menus

@plugin.route('/showcatlist/<subcats>')
def showcatlist(subcats):
    """
    show movie subcategory list
    """
    cats = re.findall(r'<a href="(.*?)" title="(.*?)">',subcats,re.S)
    fts = [li[1] for li in cats]
    selitem = dialog.select(u'视频类型',fts)
    if selitem != -1:
	return showlist(cats[selitem][0])

@plugin.route('/showlist/<url>')
def showlist(url):
    """
    show movie list
    """
    if url in epcache:
        return epcache[url]

    result = _http(baseurl+url)

    ulist = re.search(r'<div class="list">.*?<ul>(.*?)</ul>', result, re.S)
    # get movie list
    movies = re.findall(r'_src="(.*?)".*?<dd class="h4"><a href="(.*?)" title="(.*?)".*?keyword=(.*?)&type', ulist.group(1), re.S)

    menus = []
    # 0 is thunmnailimg, 1 is url, 2 is title, 3 is author
    for seq, m in enumerate(movies):
        menus.append({
            'label': '{0}. {1}【{2}】'.format(seq+1, m[2], m[3]),
            'path': plugin.url_for('showmovie', url=m[1]),
            'thumbnail': m[0],
        })
    # add current/total page number

    pagestr=''
    pagenum = re.search(r'<div class="page"><ul>(.*?)</ul>', result, re.S)
    if pagenum:
   	cur = re.search(r'<li class="active">(.*?)</li>',pagenum.group(1))
   	total = re.search(r'<li class="lastly">.*?page/(\d+)/',pagenum.group(1))
        if cur:
	    if total:
                 pagestr = '第'+cur.group(1)+'页 '+'共'+total.group(1)+'页'
	    else:
                 pagestr = '第'+cur.group(1)+'页 '+'共'+cur.group(1)+'页'

        # add pre/next item
        pre = re.search(r'<li class="previous"><a href="(.*?)">(.*?)</a></li>',pagenum.group(1))
        if pre:
            menus.append({
            'label': pre.group(2)+'【'+pagestr+'】',
            'path': plugin.url_for('showlist', url=pre.group(1)),
            })

        nex = re.search(r'<li class="next"><a href="(.*?)">(.*?)</a></li>',pagenum.group(1))
        if nex:
            menus.append({
            'label': nex.group(2)+'【'+pagestr+'】',
            'path': plugin.url_for('showlist', url=nex.group(1)),
            })

    # add subcategory
    subcat = re.search(r'<div class="list_nav border">(.*?)</dl>.*?<div id="Nav">',result,re.S)
    if subcat:
        menus.insert(0,{
            'label': u'[COLOR FFFF0000]视频子类型[选择][/COLOR]',
            'path': plugin.url_for('showcatlist', subcats=subcat.group(1)),
        })
	    
    
    epcache[url] = menus
    return menus

@plugin.route('/showmovie/<url>')
def showmovie(url):
    """
    show episodes list
    """
    if url in epcache:
       return epcache[url]
    result = _http(baseurl+url)

    intro = re.search(r'<div id="intro"(.*?)</ul>',result,re.S)

    thumbnail = re.search(r'<div class="pic"><img src="/style/2011/images/gray.gif" _src="(.*?)"',intro.group(1)).group(1)

    title = re.search(r'<div class="text">.*?<span.*?>(.*?)</span></li>',intro.group(1),re.S).group(1)

    vinfo = {'title':title}

    tit=re.search(r'\[副标题\]:\s+(.*?)</li>',intro.group(1))
    if tit:
	vinfo['originaltitle']= tit.group(1)
    
    source=re.search(u'\[出处\]:\s+(\S+)\s+',intro.group(1))
    if source:
	vinfo['studio']= source.group(1)
    author=re.search(u'\[讲员\]:\s+(\S+)\s+',intro.group(1))
    if author:
	vinfo['writer']= author.group(1)
    genre=re.search(u'\[分类\]:\s+<a href.*?>(.*?)</a>',intro.group(1))
    if genre:
	vinfo['genre']= genre.group(1)
    intrcont= re.search(r'<div class="cont content" id="movie_intro">(.*?)</div>',result,re.S)
    if intrcont:
	vinfo['plot']= intrcont.group(1)
	itemdescs=re.findall(r'(第?\d{2}\D.*?)(?:<br|\s|</p)',intrcont.group(1),re.S)

    #videoinfo = ['video',{'genre':genre,'title':title,'originaltitle':title2,'studio':source,'writer':author,'plot':intrcont}]
    mostr = re.search(r'<div class="cont " id="play">(.*?)</div>',
                           result, re.S)
    molist = re.findall(r'<a id="\d+_view" href="(.*?)".*?<b.*?>(.*?)</b>',mostr.group(1))

    molist = sorted(molist,key=lambda x:x[1])

    menus=[]

    if itemdescs and len(itemdescs)==len(molist):
	for index,item in enumerate(molist):
            menus.append({
            'label': itemdescs[index],
            'label2': title,
            'thumbnail': thumbnail,
            'path': plugin.url_for('playmovie', url=item[0],label=itemdescs[index]),
	    'info':vinfo
            })
    else:
        for movie in molist: 
            menus.append({
            'label': movie[-1],
            'label2': title,
            'thumbnail': thumbnail,
            'path': plugin.url_for('playmovie', url=movie[0],label=movie[-1]),
	    'info':vinfo
            })

    # xbmcswift only support thumbnail view mode
    #xbmc.executebuiltin('Container.SetViewMode(503)')
    epcache[url] = menus

    return menus

@plugin.route('/play/<url>/<label>')
def playmovie(url, label=''):
    """
    play movie
    """
    result = _http(baseurl+url)

    mp4str=re.search(r'<video id="player".*?<source src="(.*?)"',result,re.S)
    if mp4str:
	playurl=mp4str.group(1)
        
        plugin.play_video({
            'label': label, 
            'is_playable': True, 
            'path': playurl
        })

    flashvar = re.search(r'var flashvars = \{(.*?)\};',result,re.S)
    if flashvar:
        rtmpstr= re.search(r'src : "(rtmp.*?)"',flashvar.group(1))
        title= re.search(r'label : "(.*?)"',flashvar.group(1))
        swfurl = re.search(r'var cmp_url = "(.*?)"',result)
        rtmpurl= re.search(r'(rtmp://.*?/.*?)/(.*)',rtmpstr.group(1))
	pageurl=baseurl+url
	playurl= rtmpurl.group(1)+' playpath=mp4:'+rtmpurl.group(2)+' pageUrl='+pageurl+' swfUrl='+swfurl.group(1)

	listitem = xbmcgui.ListItem()
        listitem.setInfo(type="Video", infoLabels={'Title': title.group(1)})
        xbmc.Player().play(playurl, listitem)

        #plugin.play_video({
        #    'label': title.group(1), 
         #   'is_playable': True, 
	 #   'path': urllib.quote_plus(playurl)
            #'path': rtmpstr.group(1)+' swfUrl='+swfurl.group(1)+' pageURL='+pageurl.group(1)+' swfVfy=true live=true'
       # })

@plugin.route('/clscache')
def clscache():
    filters.clear()
    epcache.clear()
    xbmcgui.Dialog().ok(
        '提示框', '清除成功')
    return


def _http(url):
    """
    open url
    """
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) {0}{1}'.
                   format('AppleWebKit/537.36 (KHTML, like Gecko) ',
                         'Chrome/28.0.1500.71 Safari/537.36'))
    req.add_header('Accept-encoding', 'gzip')
    rsp = urllib2.urlopen(req, timeout=30)
    if rsp.info().get('Content-Encoding') == 'gzip':
        buf = StringIO(rsp.read())
        f = gzip.GzipFile(fileobj=buf)
        data = f.read()
    else:
        data = rsp.read()
    rsp.close()
   
    match = re.compile(r'<meta http-equiv=["]?[Cc]ontent-[Tt]ype["]? content="text/html;[\s]?charset=(.+?)"').findall(data)

    if len(match)>0:
        charset = match[0]

    if charset:
        charset = charset.lower()

        if (charset != 'utf-8') and (charset != 'utf8'):
            data = data.decode(charset, 'ignore').encode('utf8', 'ignore')
    return data

if __name__ == '__main__':
    plugin.run()
