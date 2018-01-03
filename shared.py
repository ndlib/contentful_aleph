from hesburgh import heslog, hesutil
import json
import urllib2
import urllib
import time

alephToCf = {
  "name": "title",
  "description": "description",
  "purl": "purl",
  "urls": "urls",
  "provider": "provider",
  "publisher": "publisher",
  "platform": "platform",
  "includes": "includes",
  "access": "access",
}


def isDifferent(alephItem, currentItem):
  for aField, cfField in alephToCf.iteritems():
    if currentItem.get(cfField, {}).get("en-US") != alephItem.get(aField):
      return True
  return False


def getAleph(alephNumber):
  url = hesutil.getEnv("ALEPH_URL", throw=True)
  url = url.replace("<<systemNumber>>", alephNumber)

  req = urllib2.Request(url)
  return makeRequest(req, "aleph: %s" % alephNumber)


def makeRequest(req, meta):
  while True:
    try:
      response = urllib2.urlopen(req)
      return json.loads(response.read())
    except urllib2.HTTPError as e:
      # aleph likely timed out
      if e.code == 504:
        heslog.warn("Got a 504 - request timed out, retrying %s" % meta)
        continue

      resetHeader = e.headers.get("X-Contentful-RateLimit-Reset")
      if resetHeader and int(resetHeader) > 0:
        headerTime = int(resetHeader)
        heslog.warn("%s Hit contentful api limit, sleeping for %s" % (meta, headerTime))
        time.sleep(headerTime)
        continue

      heslog.error("Error code: %s  %s" % (e.code, meta))
      heslog.error(e.read())
      return False
    except urllib2.URLError as e:
      heslog.error(e.reason)
      return False


def updateContentful(entryId, version, alephItem, currentItem):
  heslog.info("Updating %s:%s" % (entryId, version))
  url = hesutil.getEnv("CONTENTFUL_URL", throw=True)
  url = url.replace("<<entryId>>", entryId)

  fields = {
    "alephSystemNumber": currentItem.get("alephSystemNumber"),
    "image": currentItem.get("image"),
  }

  for aField, cfField in alephToCf.iteritems():
    fields[cfField] = { "en-US": alephItem.get(aField) }

  data = { "fields": fields }

  headers = {
    "Content-Type": "application/vnd.contentful.management.v1+json",
    "X-Contentful-Content-Type": "resource",
    "Authorization": "Bearer %s" % hesutil.getEnv("OAUTH", throw=True),
    "X-Contentful-Version": version,
  }

  req = urllib2.Request(url, data=json.dumps(data), headers=headers)
  req.get_method = lambda: 'PUT'
  return makeRequest(req, entryId)


def publishContentful(entryId, version):
  heslog.info("Publishing %s:%s" % (entryId, version))

  url = hesutil.getEnv("CONTENTFUL_URL", throw=True)
  url = url.replace("<<entryId>>", entryId)
  url += "/published"

  headers = {
    "Content-Type": "application/vnd.contentful.management.v1+json",
    "X-Contentful-Content-Type": "resource",
    "Authorization": "Bearer %s" % hesutil.getEnv("OAUTH", throw=True),
    "X-Contentful-Version": version,
  }

  req = urllib2.Request(url, headers=headers)
  req.get_method = lambda: 'PUT'
  return makeRequest(req, entryId)

