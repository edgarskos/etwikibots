#!/usr/bin/python
# -*- coding: utf-8 -*-

'''

kontrolli kas (täpsustusega) lehed on lingitud pealehelt

'''

import sys, os
sys.path.append("/shared/pywikipedia/core")
import pywikibot
import MySQLdb, re
from time import strftime

# "constants"

# wikipedia article namespace
WP_ARTICLE_NS = 0
# output debug messages
DEBUG = False

def connectWikiDatabase(lang):
    '''
Connect to the wiki database
'''
    if (lang):
        hostName = lang + 'wiki.labsdb'
        dbName = lang + 'wiki_p'
        conn = MySQLdb.connect(host=hostName, db=dbName,
            read_default_file=os.path.expanduser("~/.my.cnf"),
            use_unicode=True, charset='utf8')
        cursor = conn.cursor()
        return (conn, cursor)

def getSubPages(cursor):
    outSubPages = []
    query = """SELECT page_title
FROM page
WHERE page_title LIKE '%(%'
AND page_namespace = 0
AND page_is_redirect = 0
"""
    #cursor.execute( query, (WP_ARTICLE_NS, ) )
    cursor.execute( query )
    if DEBUG:
        print cursor._executed
    while True:
        try:
            (pageTitle,) = cursor.fetchone()
            outSubPages.append( pageTitle )
        except TypeError:
            break
    
    return outSubPages

def getRedirTitle(inPage, cursor):
    redirTitle = ''

    query = """SELECT page_id FROM page
WHERE page_title = %s
AND page_namespace = %s
AND page_is_redirect = 1"""
    cursor.execute(query, (inPage, WP_ARTICLE_NS))
       
    if DEBUG:
        print cursor._executed
        
    if (cursor.rowcount):
        (pageId,) = cursor.fetchone()
        t_query = """SELECT rd_title FROM redirect
WHERE rd_from = %s
AND rd_namespace = %s"""
        cursor.execute(t_query, (pageId, WP_ARTICLE_NS))
        if (cursor.rowcount):
            (redirTitle,) = cursor.fetchone()
    
    redirTitle = unicode(redirTitle, "utf-8", errors='ignore')
            
    return redirTitle

def getIncomingRedirs(inPage, cursor):
    outIncomingRedirs = []
    query = """SELECT page_title FROM page
JOIN redirect ON page.page_id = redirect.rd_from
WHERE rd_title = %s
AND rd_namespace = %s"""
    cursor.execute(query, (inPage, WP_ARTICLE_NS))
    while True:
        try:
            (fromPageId,) = cursor.fetchone()
            outIncomingRedirs.append( fromPageId )
        except TypeError:
            break
        
    return outIncomingRedirs
    
def isLinkedFromMain(subPage, mainPage, cursor):
    #subPage = subPage.replace(u' ', u'_')
    #mainPage = mainPage.replace(u' ', u'_')
    query = """SELECT 1 FROM page
JOIN pagelinks ON page.page_id = pagelinks.pl_from
WHERE page_title = %s
AND page_namespace = %s
AND pl_namespace = %s
AND pl_title = %s """
    cursor.execute(query, (mainPage, WP_ARTICLE_NS, WP_ARTICLE_NS, subPage))
    if DEBUG:
        print cursor._executed
        print 'rowcount: %d' % (cursor.rowcount)

    isLinked = False
    if (cursor.rowcount):
        isLinked = True
    else: #check incoming redirs to subPage
        inRedirs = getIncomingRedirs(subPage, cursor)
        for inRedirTitle in inRedirs:
            query = """SELECT 1 FROM page
JOIN pagelinks ON page.page_id = pagelinks.pl_from
WHERE page_title = %s
AND page_namespace = %s
AND pl_namespace = %s
AND pl_title = %s """
            cursor.execute(query, (mainPage, WP_ARTICLE_NS, WP_ARTICLE_NS, inRedirTitle))
            if DEBUG:
                print cursor._executed
            if (cursor.rowcount):
                isLinked = True
                break

    return isLinked

   
def main():
    targetWiki = u'et'
    outText = u''
    wikiSite = pywikibot.getSite( targetWiki, u'wikipedia' )
    reportPageName = u'Kasutaja:WikedKentaur/linkimata täpsustusmärkega lehed'
    
    (conn, cursor) = connectWikiDatabase(targetWiki)
    subPages = getSubPages(cursor)
    prevLetter = u''
    
    for subPage in subPages:
        subPage = unicode(subPage, "utf-8", errors='ignore')
        mainPage = re.sub(u"_+\(.+\)", u"", subPage)
        origMainPage = mainPage
        isLinked = False
        if (mainPage != subPage):
            redirTitle = getRedirTitle(mainPage, cursor)
            if (redirTitle):
                mainPage = redirTitle
            isLinked = isLinkedFromMain(subPage, mainPage, cursor)
            if (not isLinked):
                disambPage = origMainPage + u'_(täpsustus)'
                isLinked = isLinkedFromMain(subPage, disambPage, cursor)

        if (not isLinked):
            firstLetter = subPage[0]
            firstLetter.upper()
            if (firstLetter != prevLetter):
                #pywikibot.output( u"\n== " + firstLetter + u' ==' )
                outText += u"\n== " + firstLetter + u" ==\n"
                prevLetter = firstLetter
            #pywikibot.output( u'* [[' + subPage + u']]')
            outText += u'* [[' + subPage + u"]] <--- [[" + origMainPage + u"]]\n"
    
    reportPage = pywikibot.Page(wikiSite, reportPageName)

    localtime = strftime("%Y-%m-%d %H:%M:%S")
    addTxt = u"Linkimata täpsustusmärkega lehed " + localtime + u" seisuga.\n\n"
    footer = u"\n\n[[Kategooria:Tähelepanu ootavad artiklid|Linkimata täpsustusmärkega lehed]]"
    outText = addTxt + outText + footer
    #print outText
    commentText = u'uuendan'
    
    reportPage.put(outText, comment = commentText)
    
        
if __name__ == "__main__":
    try:
        main()
    finally:
        pywikibot.stopme()
