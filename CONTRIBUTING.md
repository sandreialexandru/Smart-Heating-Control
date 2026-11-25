# Contributing

*Română: [CONTRIBUTING.ro.md](CONTRIBUTING.ro.md)*

- **A bug**: open an issue with the *Bug report* form. Issues are for bugs
  only.
- **A question about the setup**: ask in the
  [Q&A discussions](https://github.com/sandreialexandru/Smart-Heating-Control/discussions/categories/q-a).
- **An idea or a feature request**: propose it in the
  [Ideas discussions](https://github.com/sandreialexandru/Smart-Heating-Control/discussions/categories/ideas),
  where others can add their vote and say how their setup would use it.
- **A translation**: in [issue #12](https://github.com/sandreialexandru/Smart-Heating-Control/issues/12)
  or as a pull request.

## How feature requests are decided

Smart Heating Control is built to work the same way for every house: one set
of rules, tested together, that controls the heating through the climate
entities and helpers you already have. Every option added is one more thing
every user meets in the settings, and one more combination that has to keep
working with all the others, release after release.

So a request is weighed by three questions:

- **Does it help many houses, or one setup?** A need tied to one device, one
  integration or one way of living may be real and still not belong in the
  core.
- **Can it be done already?** Many particular needs are covered by what SHC
  exposes: the occupancy template, the calendar, the services, the
  `advanced_climate_decision_changed` event, and Home Assistant automations
  around them. The answer to a request is often an example of how.
- **What does it cost the others?** A change that adds complexity or risk to
  the core, to the order of the rules, or to the learning, must bring enough
  to everyone to be worth it.

What is not in scope: monitoring or controlling equipment other than the
heating (boilers, meters, other integrations), and turning the panel into an
editable dashboard. The card can be placed on your own dashboard next to any
other card.

A request that is not taken is not a judgement of the need or of the person.
It is how the integration stays reliable for everyone who runs it. The votes and
the setups in the
[Ideas discussions](https://github.com/sandreialexandru/Smart-Heating-Control/discussions/categories/ideas)
show how many houses an idea would help.
