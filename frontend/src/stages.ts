// The backend currently models these five MIM stages in this order.
export const stages = [
  {
    name: 'Molding',
    short: 'Molding',
    help: 'Molding forms parts from feedstock.',
    optional: false,
  },
  {
    name: 'Debinding',
    short: 'Debinding',
    help: 'Debinding removes binder from molded parts.',
    optional: false,
  },
  {
    name: 'Sintering',
    short: 'Sintering',
    help: 'Sintering densifies parts using heat.',
    optional: false,
  },
  {
    name: 'CNC Machining',
    short: 'CNC',
    help: 'CNC machining is optional; some parts skip this stage.',
    optional: true,
  },
  {
    name: 'Finishing',
    short: 'Finishing',
    help: 'Finishing covers final processing of parts.',
    optional: false,
  },
]
