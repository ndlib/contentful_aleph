jest.mock('util')

const nock = require('nock')
const sync = require('../src/sync')

describe('sync', () => {
  beforeAll(() => {
    console.log = jest.fn()
    console.warn = jest.fn()
  })

  const cfGoodItems = [
    {
      sys: {
        id: 'foo',
      },
      fields: {
        alephSystemNumber: { 'en-US': '1234' },
      },
    },
    {
      sys: {
        id: 'bar',
      },
      fields: {
        alephSystemNumber: { 'en-US': '5678' },
      },
    },
  ]
  const cfBadItems = [
    {
      sys: {
        id: 'baz',
      },
      fields: {
        test: 'data',
      },
    },
  ]
  const cfItems = cfGoodItems.concat(cfBadItems)

  describe('valid request', () => {
    let fetchNock
    let updateNocks = {}
    let publishNocks = {}
    let alephNocks = {}

    beforeEach(() => {
      fetchNock = nock(process.env.CONTENTFUL_CMA_URL)
        .intercept('/entries', 'GET')
        .query(true)
        .reply(200, {
          items: cfItems,
        })
      cfItems.forEach(item => {
        const id = item.sys.id

        if (item.fields && item.fields.alephSystemNumber) {
          alephNocks[id] = nock(process.env.ALEPH_GATEWAY_URL)
            .get(`/${item.fields.alephSystemNumber['en-US']}`)
            .query(true)
            .reply(200, { name: `test_${id}` })
        }
        updateNocks[id] = nock(process.env.CONTENTFUL_CMA_URL)
          .intercept(`/entries/${id}`, 'PUT')
          .query(true)
          .reply(200, {})
        publishNocks[id] = nock(process.env.CONTENTFUL_CMA_URL)
          .intercept(`/entries/${id}/published`, 'PUT')
          .query(true)
          .reply(200, {})
      })
    })

    afterEach(() => {
      nock.cleanAll()
      fetchNock = undefined
      alephNocks = undefined
      updateNocks = undefined
      publishNocks = undefined
    })

    it('should call update and publish for each valid item', async () => {
      await sync.handler(null, null, () => {
        expect(fetchNock.isDone()).toBe(true)
        expect(cfItems.length).toBeGreaterThan(1)
        cfGoodItems.forEach(item => {
          const id = item.sys.id
          expect(alephNocks[id].isDone()).toBe(true)
          expect(updateNocks[id].isDone()).toBe(true)
          expect(publishNocks[id].isDone()).toBe(true)
        })
      })
    })
  })
})
