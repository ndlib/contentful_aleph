from hesburgh import heslog, hesutil
import json
import urllib2
import urllib

def getAleph(alephNumber):
  url = hesutil.getEnv("ALEPH_URL", throw=True)
  url = url.replace("<<systemNumber>>", alephNumber)

  req = urllib2.Request(url)
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

  return json.loads(response.read())


def updateContentful(entryId, version, updateInfo):
  heslog.addContext(version=version)
  url = hesutil.getEnv("CONTENTFUL_URL", throw=True)
  url = url.replace("<<entryId>>", entryId)

  data = {
    "fields": {
      "title": {
        "en-US": updateInfo.get("name"),
      },
      "description": {
        "en-US": updateInfo.get("description"),
      },
      "purl": {
        "en-US": updateInfo.get("purl"),
      },
      "alephSystemNumber": {
        "en-US": updateInfo.get("systemNumber"),
      }
    }
  }

  headers = {
    "Content-Type": "application/vnd.contentful.management.v1+json",
    "X-Contentful-Content-Type": "resource",
    "Authorization": "Bearer %s" % hesutil.getEnv("OAUTH", throw=True),
    "X-Contentful-Version": version,
  }

  req = urllib2.Request(url, data=json.dumps(data), headers=headers)
  req.get_method = lambda: 'PUT'
  try:
    urllib2.urlopen(req)
  except urllib2.HTTPError as e:
    heslog.error("%s" % e.code)
    heslog.error(e.read())
  except urllib2.URLError as e:
    heslog.error(e.reason)
