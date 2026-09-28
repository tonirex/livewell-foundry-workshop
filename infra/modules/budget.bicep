// Resource-group budget with actual-spend alerts (US$150 and US$300 by default).
param name string

@description('Budget amount in the billing currency (USD for the workshop subscriptions).')
param amount int

@description('Alert thresholds in USD. Each becomes an Actual-spend notification at (threshold / amount * 100)%.')
param alertThresholdsUsd array

param contactEmails array = []

@description('First day of the month the budget starts (yyyy-MM-01). Must not move once the budget exists.')
param startDate string

@description('End date. Default: one year after start.')
param endDate string = dateTimeAdd('${startDate}T00:00:00Z', 'P1Y', 'yyyy-MM-dd')

var notifications = reduce(
  map(alertThresholdsUsd, t => {
    'actual-${t}usd': {
      enabled: true
      operator: 'GreaterThanOrEqualTo'
      threshold: (t * 100) / amount
      thresholdType: 'Actual'
      contactEmails: contactEmails
      contactRoles: [
        'Owner'
        'Contributor'
      ]
      locale: 'en-us'
    }
  }),
  {},
  (acc, cur) => union(acc, cur)
)

resource budget 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: name
  properties: {
    category: 'Cost'
    amount: amount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: startDate
      endDate: endDate
    }
    notifications: notifications
  }
}

output id string = budget.id
output name string = budget.name
