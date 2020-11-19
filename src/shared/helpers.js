const fetch = require('node-fetch')
const { t: typy } = require('typy')

const alephToCf = {
  name: 'title',
  description: 'description',
  purl: 'purl',
  urls: 'urls',
  relatedResources: 'relatedResources',
  provider: 'provider',
  publisher: 'publisher',
  platform: 'platform',
  includes: 'includes',
  access: 'access',
  accessNotes: 'accessNotes',
}

const getHeaders = (version) => ({
  Authorization: `Bearer ${process.env.CONTENTFUL_MANAGEMENT_TOKEN}`,
  'Content-Type': 'application/vnd.contentful.management.v1+json',
  'X-Contentful-Content-Type': 'resource',
  'X-Contentful-Version': version,
})

const isDifferent = (alephItem, currentItem) => {
  if (!typy(currentItem, 'databaseLetter.en-US').safeString) {
    return true
  }

  return Object.keys(alephToCf).some(alephField => {
    const contentfulField = alephToCf[alephField]
    const typyValue = typy(currentItem, `${contentfulField}.en-US`)
    const cfValue = (typyValue.isArray ? typyValue.safeArray : typyValue.safeString)

    const typyAlephValue = typy(alephItem[alephField])
    const alephValue = (typyAlephValue.isArray ? typyAlephValue.safeArray : typyAlephValue.safeString)
    return cfValue !== alephValue
  })
}

const getAleph = async (alephNumber) => {
  const url = `${process.env.ALEPH_GATEWAY_URL}/${alephNumber}`
  return makeRequest(url, `aleph: ${alephNumber}`)
}

const makeRequest = async (url, meta, requestOptions) => {
  const handleError = (e) => {
    // aleph likely timed out
    if (e.status === 504) {
      console.warn(`Got a 504 - request timed out, retrying ${meta}`)

      const resetHeader = parseInt(e.headers.get('X-Contentful-RateLimit-Reset'))
      if (resetHeader > 0) {
        console.warn(`${meta} Hit contentful api limit. Retrying in ${resetHeader}ms`)
        setTimeout(() => makeRequest(url, meta), resetHeader)
      }
    } else {
      console.error(`Error code: ${e.status} | ${meta}`)
      throw e
    }
  }

  return fetch(url, requestOptions)
    .then(res => res.ok ? res.json() : handleError(res))
    .catch(handleError)
}

const updateContentful = async (entryId, version, alephItem, currentItem) => {
  const url = `${process.env.CONTENTFUL_CMA_URL}/entries/${entryId}`

  // start with current fields, then overwrite what we want to
  // This allows us to add fields to the content type without updating this script
  const fields = currentItem

  Object.keys(alephToCf).forEach(alephField => {
    const contentfulField = alephToCf[alephField]
    // Don't overwrite the title field
    if (contentfulField === 'title' && fields.title) {
      return
    }

    fields[contentfulField] = { 'en-US': alephItem[alephField] }
  })

  // add the databaseLetter field if it is blank
  if (!fields.databaseLetter) {
    const firstChar = alephItem.name[0]
    const digitRegex = /\d/
    fields.databaseLetter = {
      // Get first letter without accent/diacritic mark and lowercase.
      'en-US': digitRegex.test(firstChar) ? '#' : firstChar.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(),
    }
  }

  return makeRequest(url, entryId, {
    method: 'PUT',
    body: JSON.stringify({
      fields: fields,
    }),
    headers: getHeaders(version),
  })
}

const publishContentful = (entryId, version) => {
  const url = `${process.env.CONTENTFUL_CMA_URL}/entries/${entryId}/published`

  return makeRequest(url, entryId, {
    method: 'PUT',
    headers: getHeaders(version),
  })
}

module.exports = {
  isDifferent,
  getAleph,
  makeRequest,
  updateContentful,
  publishContentful,
}
