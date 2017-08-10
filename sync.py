# This allows gevent to be imported from the ./lib diretory
import os
dir_path = os.path.dirname(os.path.realpath(__file__))
import sys
sys.path.append(dir_path + "/lib/")

import gevent.monkey
gevent.monkey.patch_all()
import gevent

from hesburgh import heslog, hesutil
import json
import re
import shared
import urllib2
import time

# The contentful calls per second is 10, but that's magically gone away, so do 50 at a time
concurentItems = 50

def updateItem(item):
  currentTitle = item.get("fields", {}).get("title", {}).get("en-US")
  currentDesc = item.get("fields", {}).get("description", {}).get("en-US")
  currentPurl = item.get("fields", {}).get("purl", {}).get("en-US")

  alephNumber = item.get("fields", {}).get("alephSystemNumber", {}).get("en-US")
  sysId = item.get('sys', {}).get('id')

  if not alephNumber:
    heslog.warn("No Aleph number for %s" % (sysId))
    return None

  alephItem = shared.getAleph(alephNumber)
  # heslog.debug("number: %s, title: %s" % (alephNumber, currentTitle))
  # heslog.debug(json.dumps(alephItem))

  if (currentDesc != alephItem.get("description")
      or currentPurl != alephItem.get("purl")):
    alephItem["systemNumber"] = alephNumber
    alephItem["name"] = currentTitle

    version = item.get("sys", {}).get("version", 1)

    updated = shared.updateContentful(sysId, version, alephItem)
    if not updated:
      return
    shared.publishContentful(sysId, updated.get("sys", {}).get("version", 1))
  else:
    heslog.debug("Item is the same, not updating")


def run(event, context):
  heslog.addLambdaContext(event, context)

  start = 0
  total = 100

  headers = {
    "Authorization": "Bearer %s" % hesutil.getEnv("OAUTH", throw=True),
  }
  baseUrl = hesutil.getEnv("CONTENTFUL_QUERY_URL", throw=True)

  items = []
  while start < total:
    url = baseUrl + "&skip=%s" % (start)

    req = urllib2.Request(url, headers=headers)
    response = ""
    try:
      response = urllib2.urlopen(req)
    except urllib2.HTTPError as e:
      heslog.error("%s" % e.code)
      heslog.error(e.read())
      return None
    except urllib2.URLError as e:
      heslog.error(e.reason)
      return None

    responseObj = json.loads(response.read())

    start = responseObj.get("skip", 0) + responseObj.get("limit", 100)
    total = responseObj.get("total", 0)

    responseItems = responseObj.get("items", [])
    for item in responseItems:
      if item.get("sys", {}).get("archivedAt", None) is None:
        items.append(item)

  heslog.info("Updating %s items" % len(items))

  start = 0

  timer = hesutil.Timer()
  while len(items) > 0:
    threads = []
    use = items[:concurentItems]
    items = items[concurentItems:]

    heslog.info("Processing items %s through %s" % (start, start + len(use)))
    start += concurentItems
    timer.start()
    for item in use:
      threads.append(gevent.spawn(updateItem, item))

    gevent.joinall(threads)
    dt = timer.end()
    if dt < 1:
      # sleep to make it less likely we hit the contentful api limit
      time.sleep(1 - dt)


  heslog.info("Returning 200 OK")
  return { "statusCode": 200, "body": "" }
